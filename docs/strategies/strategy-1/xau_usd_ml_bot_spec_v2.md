# XAU/USD Machine-Learning Trading Bot — Developer Specification (v2)

**Scope:** This document is the implementation contract for a systematic XAU/USD (spot gold, OANDA CFD)
trading bot. It supersedes the original "Comprehensive Algorithmic Trading Strategy for XAU/USD" report and
folds in the corrections from the design review. It is written so a Python developer can build it without needing
the original document.

**System split (already in place):**
- **Python backend** — the brain. Owns the training pipeline, the live inference + execution loop, all ML, all
  risk math. This is the main thing this spec describes.
- **NestJS middle layer** — thin relay: exposes REST/WebSocket so the frontend can read bot state; passes
  commands through. No trading logic lives here.
- **React frontend** — read-only dashboard (state, positions, equity, model health). Controls later.

**Two programs, run differently:**
1. **`train.py`** — the *offline training pipeline*. **You run this manually** (weekly recommended). It produces a
   versioned model artifact. It never touches the live account.
2. **`bot.py`** — the *live trading bot*. Runs continuously. Loads the latest model artifact, streams prices,
   makes decisions, sends orders. It **never** trains.

These two share code (feature engineering, config) but are separate entry points. The bot must be able to run
for days using a frozen model while you retrain on your own schedule.

---

## 0. Design principles (read first)

1. **Costs are the enemy, not the market.** Gold (~$4,150/oz at time of writing) has a real spread (~$0.20–0.40
   normal, several dollars during news). Every decision is evaluated *net of cost*. A strategy that looks great
   gross and negative net is the default outcome, not the exception.
2. **The model outputs a calibrated probability, not a yes/no.** Everything downstream (whether to trade, how big)
   is driven by that probability combined with an expected payoff.
3. **Reward:risk geometry must be sane.** Target and stop are measured on the *same* scale (ATR multiples). We
   never set a tiny target against a large stop.
4. **No look-ahead, ever.** A feature computed at the close of candle *t* may only use information available at or
   before *t*. Labels look forward; features never do. Validation uses purged/embargoed walk-forward splits.
5. **Timeframe is a config parameter.** The default is M5 entries / M30 context (from the original design), but
   the same pipeline must run on M15/H1 by changing config. M5 scalping has the worst cost-to-edge ratio of any
   horizon; you should backtest M15 and H1 too and let the numbers decide. Do not hard-code "5 minutes" anywhere.

---

## 1. Instrument & cost model

| Property | Value / rule |
|---|---|
| Instrument | `XAU_USD` on OANDA v20 |
| Unit | 1 unit = 1 troy ounce. OANDA allows fractional units. |
| P&L | A $1 move in price = $1 P&L per unit held. Work in **dollars per ounce**, not "pips" (gold pip definitions vary by broker and cause bugs). |
| Spread (cost) | `spread = ask - bid`, in $/oz. Capture it live and historically (see §3). |
| Round-trip cost | ≈ one full spread per round trip, plus financing/swap on overnight holds. Model both. |
| Trading hours | ~23h/day, Sunday ~22:00 UTC to Friday ~21:00 UTC, with a daily break. Handle the weekend gap explicitly. |

**Cost gate (used everywhere):** a trade is only considered if its *expected* favorable move exceeds a safety
multiple of the live spread. Default `expected_move >= 2.0 * spread_live`. This is a hard pre-filter, separate
from the sizing math.

---

## 2. Architecture: the two loops

```
                          ┌────────────────────────────┐
   (you run manually)     │      TRAINING PIPELINE      │
   weekly  ────────────►  │  train.py                   │
                          │  fetch history → features → │
                          │  labels → purged walk-fwd   │
                          │  CV → calibrate → backtest   │
                          │  → write model artifact (vN) │
                          └──────────────┬──────────────┘
                                         │  model_vN.pkl + metadata.json
                                         ▼
                          ┌────────────────────────────┐
   (always on)            │       LIVE BOT              │
                          │  bot.py                     │
   OANDA stream  ───────► │  load latest model artifact │
   /v20/pricing/stream    │  aggregate candles          │ ──► OANDA orders
                          │  build feature row (causal) │     /v20/orders
                          │  predict prob + magnitude   │
                          │  calibrate → size → gate    │ ──► Redis pub/sub ──► Nest ──► React
                          │  send bracket order         │
                          │  monitor drift / guardrails │
                          └────────────────────────────┘
```

The bot publishes everything it does to Redis; Nest relays to the React dashboard. The bot is the only thing
allowed to talk to the live account.

---

## 3. Data layer

### 3.1 Where to get substantial historical XAU/USD data

Ranked by usefulness for this project:

1. **OANDA v20 candles endpoint (primary — matches your execution venue).**
   `GET /v3/instruments/XAU_USD/candles`
   - This is the most important source because it comes from the venue you actually trade on, so the price
     distribution matches production.
   - **Request the price components you need:** `price=MBA` returns **M**id, **B**id and **A**sk candles in one
     response. The bid/ask close gives you a **historical spread** (`ask_close - bid_close`) — this is how you get
     spread history without a tick archive (OANDA does *not* publish an unlimited tick archive).
   - **Pagination:** max ~5000 candles per request. Page with `from`/`to` (RFC3339 UTC) or `count`. To build
     several years of M5 (~105k candles/year), loop requests by date window and concatenate.
   - **Only use completed candles:** each candle has a `complete` boolean. Discard `complete=false`.
   - **Caveat:** historical candles are *base-price* (mid) and may differ slightly from your account's live
     pricing group. Document this gap; it mostly matters for the bid/ask spread proxy.

2. **Dukascopy (free, tick-level, for realistic backtests).** Swiss-bank tick history for `XAUUSD`, downloadable
   (e.g. via the `dukascopy-node` tool or JForex). Use this when you want tick-accurate spread and slippage
   modeling in the backtest. Heavier to process; great for validation, overkill for routine retraining.

3. **Commercial vendors (paid, highest quality / convenience).** FirstRate Data, Polygon.io (`C:XAUUSD`),
   Databento, TickData.com, Kibot. Use if you want clean, ready-to-load minute or tick history without scraping
   OANDA's pagination.

**Recommendation:** Build the routine training pipeline on **OANDA `price=MBA` candles** (matches venue, free,
gives spread). Keep a one-time **Dukascopy** tick pull for a high-fidelity cost-aware backtest. Treat anything
older than ~3–4 years with suspicion for *microstructure* features — gold's volatility/spread regime in 2020–2022
is not 2026. Longer history is fine for *macro/trend* features.

### 3.2 Storage format

Keep three tiers, do not blur them:

| Tier | Format | Purpose |
|---|---|---|
| **Raw bars (immutable archive)** | **Parquet**, partitioned `instrument/granularity/year/month` | Source of truth. Never edited after write. |
| **Serving / dashboard** | **TimescaleDB** hypertable (you already have it) | Live queries, charts, recent bars for the bot. |
| **Feature matrix (versioned)** | **Parquet**, tagged with a feature-spec hash | Reproducible training input. Each training run records which feature-matrix version it used. |

Why Parquet for ML: columnar, compresses ~5–10x, loads into pandas/polars in seconds, and is immutable/versioned
so a model is always reproducible from a known file. Why Timescale for serving: fast time-range queries and it
feeds the dashboard you already built.

**Bar schema (one row per completed candle):**

```
ts_close        TIMESTAMPTZ   -- candle CLOSE time, UTC. This is the row's timestamp.
granularity     TEXT          -- 'M5', 'M30', ...
open, high, low, close   FLOAT8   -- mid prices
bid_close, ask_close     FLOAT8   -- for spread = ask_close - bid_close
volume          INT           -- OANDA TICK volume (see note)
complete        BOOL          -- always TRUE in stored rows
```

> **Note on "volume":** OANDA's volume is **tick volume** (number of price updates), not traded volume — gold is
> OTC, there is no true volume. Treat all volume-derived features (VWAP distance, VROC) as *activity* proxies,
> not money-flow. They are still useful, just don't over-trust them.

### 3.3 Processing into ML-ready data

Do all of this **causally** (no future leakage):

1. **UTC everywhere.** Store and compute in UTC. Convert for display only.
2. **Use candle CLOSE time as the row timestamp.** A feature for the M5 bar that closed at 12:05:00 is "known" at
   12:05:00, not 12:00:00.
3. **Multi-timeframe alignment without leakage.** M30 features become available only at the M30 close. When you
   attach an M30 feature to an M5 row, use the **most recent M30 value whose close ≤ the M5 row's close**
   (`merge_asof` backward join). Never the M30 candle the M5 bar is currently inside.
4. **Warmup trim.** Indicators (EMA-34, ATR-14, etc.) are invalid until enough history exists. Drop the warmup
   region per training window rather than imputing.
5. **Gaps & sessions.** Mark weekend/holiday gaps; do not compute "rate of change" across a 2-day gap as if it
   were one bar. Add a `bars_since_session_open` style feature if useful.
6. **Scaling fit on train only.** If you scale/normalize features, fit the scaler on the training fold and apply
   to validation/live — never fit on the full dataset (that leaks).
7. **Persist the feature matrix** as versioned Parquet with a hash of the feature definitions, so a model can
   always be rebuilt byte-for-byte.

---

## 4. Feature engineering

Three groups. Each feature is computed at the close of the entry-timeframe candle (default M5).

### Group A — Macro context (M30), used as a directional filter
- EMA fast (13) and slow (34): values, and `ema_fast - ema_slow`, and slope of each.
- MACD (12, 26, 9): MACD line, signal, and histogram (the histogram is the macro momentum score).
- A single derived **regime flag**: `macro_up / macro_down / macro_flat` from EMA relationship + MACD sign. The
  bot uses this to *lock out* counter-trend entries (e.g. disallow longs when `macro_down`).

### Group B — Micro execution metrics (M5)
- **VWAP distance:** `close - rolling_VWAP` (rolling, intraday, reset per session). Activity-weighted, not
  volume-weighted in the true sense — see the volume note.
- **VROC:** volume rate-of-change over a 6-candle window (liquidity acceleration proxy).
- **ATR(14):** the volatility unit that drives both stops and targets. Everything risk-related is in ATR units.
- Returns/log-returns over the last *k* candles; candle body/range ratios; distance from recent high/low.

### Group C — Spread & sentiment (CORRECTED from the original doc)
The original treated the OANDA "order book imbalance" as a real-time order book and called it the most predictive
input. **It is not a real order book.** OANDA's order/position book reflects only OANDA's own retail clients,
updates every **5 minutes (premium) / 15 minutes (non-premium)**, and historical snapshots are not reliably
reconstructable for training. Therefore:

- **Live spread** `S_t = ask - bid` (from the stream) — **keep this, it's the genuinely useful, truly real-time
  input.** Plus `spread / rolling_mean(spread, 20)` as a "spread stress" feature.
- **Order/position book imbalance** — **demote to an optional slow sentiment feature**, sampled at its true
  cadence and explicitly lagged (e.g., "OANDA client net-long %, as of the last snapshot, ≥5 min old"). Treat it
  as possibly *contrarian* retail sentiment, not as support/resistance. **Do not include it in the first model
  version** unless/until you have recorded enough live snapshots to also have it in training — otherwise you have
  a live feature with no training column, which silently corrupts the model.

---

## 5. Labeling — corrected triple-barrier

We keep the triple-barrier method (it's a legitimate, respected technique) but fix the geometry.

For each entry candle at time *t*, with `ATR = ATR_M5(t)`:
- **Upper barrier:** `close(t) + tp_mult * ATR`
- **Lower barrier:** `close(t) - sl_mult * ATR`
- **Vertical barrier:** `max_horizon` candles ahead (e.g. 6 M5 candles = 30 min).

**Critical change:** target and stop are *both ATR-scaled*, with `tp_mult >= sl_mult` to keep reward:risk ≥ ~1:1.
Suggested start: `tp_mult = 2.0`, `sl_mult = 1.5` (reward:risk ≈ 1.3:1), tuned in backtest. **Never** set the
target to a multiple of spread while the stop is a multiple of ATR — that was the fatal flaw in v1 (tiny target,
huge stop, demanding ~88% win rate).

**Label assignment** over the look-ahead window:
- `+1` (long-favorable): upper barrier touched first.
- `-1` (short-favorable): lower barrier touched first.
- `0` (no-trade): vertical barrier hit first (timed out). 

> Do **not** dump "violent two-sided whipsaw" into the same class as "quiet chop." If both barriers are touched in
> the same bar (ambiguous), either (a) drop the sample, or (b) use intrabar tick/М1 data to break the tie. Lumping
> opposite regimes into one label confuses the model.

**Meta-labeling (recommended structure):**
1. **Primary model / rule** decides *direction* (can even be the macro filter: "consider long when macro_up").
2. **Secondary ML model** predicts *the probability the primary signal hits its target before its stop* — i.e. a
   binary "take it / skip it" probability. This is cleaner than a 3-class classifier + separate regressor on the
   same rows, and the probability it outputs is exactly what the sizing logic needs.
3. **Magnitude regressor (optional):** predicts expected favorable excursion in ATR units, used for the payoff
   term in sizing.

---

## 6. Models

- **Primary algorithm:** LightGBM or XGBoost (gradient-boosted trees). Correct choice for tabular features; do
  **not** start with LSTM/ARIMA stacking — ARIMA has ~zero edge on 5-min returns and LSTM overfits and rarely
  beats GBM here. Add complexity only if a clean baseline already shows net-positive edge.
- **Output:** the secondary (meta) model outputs a raw score → **must be calibrated** (next section) into a
  probability `p` that the trade reaches target before stop.
- **Magnitude model (optional):** GBM regressor → expected favorable move `m̂` in ATR units.
- **Abstention is first-class:** the model is allowed (encouraged) to say "no trade." Most candles should be
  no-trade.

---

## 7. Probability calibration (REQUIRED for the sizing idea to work)

Tree models are systematically overconfident; a raw "0.9" is not a 90% probability. Before any sizing:

1. Hold out a calibration set **inside each walk-forward fold** (never the same data used to fit the model).
2. Fit **isotonic regression** (preferred with enough data) or **Platt scaling** mapping raw score → calibrated
   `p`.
3. Validate calibration with a **reliability diagram** and **Brier score**. A well-calibrated model: of all
   trades it labeled `p≈0.7`, ~70% actually hit target first.
4. Ship the calibrator *with* the model artifact. The bot applies it to every prediction.

Without this step, the confidence-based sizing below will systematically over-bet on inflated scores.

---

## 8. Position sizing — confidence-based, done right

This is the corrected, EV-driven version of your idea (calibrate → combine with payoff → fractional Kelly → cap →
abstain). It subsumes "big size on high confidence, no trade on low confidence" but for principled reasons.

**Inputs per candidate trade:**
- `p` — calibrated probability the trade hits target before stop (§7).
- `b` — payoff odds = expected reward / risk. Use either the fixed `tp_mult / sl_mult`, or the regressor's `m̂`
  over the stop distance: `b = m̂ / sl_mult` (both in ATR units).
- `stop_$` — stop distance in dollars/oz = `sl_mult * ATR`.
- `equity` — current account equity.
- Config: `kelly_fraction λ` (start 0.25), `risk_cap` (hard ceiling per trade, e.g. 0.75–1.0% of equity),
  `min_risk_floor` (below this, skip).

**Step 1 — Edge / Kelly fraction:**
```
f_star = p - (1 - p) / b        # optimal growth fraction; <= 0 means no edge
```
**Step 2 — Abstain if no edge:** `if f_star <= 0: NO TRADE`. (This is your "low confidence = don't trade" zone,
arising naturally — a low `p` or a poor payoff makes `f_star` non-positive.)

**Step 3 — Fractional Kelly + hard cap:**
```
risk_fraction = clamp(λ * f_star, 0, risk_cap)
if risk_fraction < min_risk_floor: NO TRADE
```
**Step 4 — Convert to ounces:**
```
units = (equity * risk_fraction) / stop_$
```
**Step 5 — Round** to OANDA's allowed precision; re-check the cost gate (§1) and spread-stress override (§12).

**Why this beats "scale lot by raw confidence":**
- It uses *calibrated* probability, so the size reflects real edge, not model bravado.
- It uses *payoff*, so a high-confidence-but-tiny-reward trade is correctly sized small or skipped.
- Fractional Kelly + cap prevents the blow-ups that full Kelly and naive confidence-scaling cause (high-confidence
  predictions are exactly where an overfit model is most wrong).
- The "no-trade / normal / large" tiers you wanted emerge from `f_star` instead of arbitrary thresholds — though
  you can still impose discrete tiers on top if your dev prefers simpler ops.

**Portfolio guardrail (matters once you scale to many bots):** cap *total* simultaneous risk across all open
positions (e.g. ≤ 3–4% of equity), and watch correlation — several "high-confidence" gold trades in a trend can
all lose together if the regime breaks.

---

## 9. Training pipeline (`train.py`) and cadence

### 9.1 Steps (run manually)
1. **Fetch / update history** from OANDA (`price=MBA`), append to raw Parquet + Timescale. Idempotent.
2. **Build feature matrix** (§3.3, §4), versioned.
3. **Build labels** (§5).
4. **Purged, embargoed walk-forward CV** (§9.3) — this is mandatory, not optional.
5. **Fit model** per fold, **calibrate** (§7) on held-out calibration slice.
6. **Cost-aware backtest** (§10) on the out-of-sample folds.
7. **Gate the release:** only promote the new model if it beats the incumbent *and* the benchmarks net of costs
   (§10). Otherwise keep the old model and alert.
8. **Write artifact:** `model_vN.pkl` (model + calibrator + scaler) plus `metadata.json` (feature-spec hash, data
   window, CV metrics, backtest stats, git commit). The bot loads the newest *promoted* artifact.

### 9.2 Cadence — weekly vs monthly
- **Default: weekly**, run on the weekend (market closed), for an M5 strategy. M5 microstructure drifts fast
  enough that monthly is usually too slow.
- **Also retrain on trigger:** if the live drift monitor (§12) fires, retrain regardless of schedule.
- **Monthly is acceptable only if** the drift monitor stays quiet and weekly retrains show negligible change —
  let the data tell you. Make cadence a config value, not a hard-coded cron.
- **Rolling window:** 2–4 years for a model dominated by microstructure features; longer is fine for macro/trend
  features. Consider recency weighting (more weight on recent samples). Test window length as a hyperparameter.

### 9.3 Validation: purged + embargoed walk-forward (CRITICAL)
Because labels look forward `max_horizon` candles, adjacent samples **overlap**. Naive k-fold CV leaks the future
into training and produces fake-good metrics. Use:
- **Walk-forward:** train on [t0, t1], validate on [t1, t2], roll forward. Never validate on data older than
  training.
- **Purge:** remove training samples whose label window overlaps the validation window.
- **Embargo:** drop a small buffer of samples immediately after each validation block before resuming training.
- (Reference: López de Prado, *Advances in Financial Machine Learning* — purging & embargoing.)

This single change is usually the difference between a backtest that lies and one that's trustworthy.

---

## 10. Backtesting protocol (do this before risking a cent)

A backtest is only believable if it's **cost-aware**:
- Apply the **historical spread** (`ask-bid` from `price=MBA`, or Dukascopy ticks) as the entry/exit cost.
- Model **slippage** (entries during the candle after signal; widen fills during volatile bars).
- Model **financing/swap** on any overnight holds.
- Model **requotes/rejects** in fast markets (simulate a fraction of orders failing during news).
- Use only the **out-of-sample, purged walk-forward** predictions — never in-sample.

**Report and gate on:**
- Net equity curve, **net** Sharpe and Sortino, max drawdown, win rate, average R, profit factor.
- **Benchmarks it must beat (net):** (a) buy-and-hold gold — gold is up >230% since 2020, so this bar is high;
  (b) a trivial EMA-crossover baseline. If the ML model can't beat a dumb baseline net of costs, it has no edge.
- Trade frequency and average cost-as-%-of-gross-edge (the metric that kills scalpers).

If the strategy is net-negative or fails the benchmarks, **do not deploy** — change horizon (try M15/H1),
features, or labels and iterate.

---

## 11. Live execution loop (`bot.py`) — step by step

On every completed entry candle (default M5 close):

1. **Aggregate & confirm candle.** From the `/v20/pricing/stream`, aggregate ticks into the M5 candle; confirm
   close via the candles endpoint `complete=true`. Capture live `bid`, `ask`, `spread`.
2. **Build feature row causally** (§3.3): M5 features from the just-closed candle, M30 features via backward
   as-of join, live spread + spread-stress. (Order-book sentiment only if it's in the trained model.)
3. **Macro interlock.** Evaluate macro regime. If `macro_down`, set `allow_long=False`; if `macro_up`, set
   `allow_short=False`. (Configurable: you may allow counter-trend with penalty instead of hard lock.)
4. **Predict.** `raw = model.predict(row)` → `p = calibrator(raw)`. Optionally `m̂ = regressor(row)`.
5. **Cost gate.** Require `expected_move ≥ 2.0 * spread_live` (§1). If false → no trade.
6. **Spread-stress override.** If `spread_live > k * rolling_mean(spread,20)` (news widening) → cancel/skip,
   regardless of signal. Gold's biggest moves are news; this keeps you out of the worst slippage.
7. **Size** via §8 (calibrated `p`, payoff `b`, fractional Kelly, cap, abstain). If `units == 0` → no trade.
8. **Compute bracket:** entry (market or limit), stop = `entry ∓ sl_mult*ATR`, take-profit = `entry ± tp_mult*ATR`.
9. **Transmit a single linked bracket order** to OANDA (`/v3/accounts/{id}/orders`) with the stop-loss and
   take-profit attached, so risk is **server-side** and survives a local disconnect.
10. **Publish** decision + reasoning + order result to Redis → Nest → React.
11. **Record** the prediction, features, calibrated `p`, size, and outcome for the drift monitor and the next
    retrain.

---

## 12. Risk & safety guardrails

- **Per-trade risk ceiling:** `risk_cap` (≤1% equity), enforced in sizing (§8).
- **Daily loss limit:** halt new entries for the session after cumulative loss exceeds a configured % of equity.
- **Max concurrent risk:** cap total open risk across positions/bots (§8 portfolio guardrail).
- **Spread-stress override:** §11.6.
- **Latency interlock:** if order round-trip > 200 ms, rely on the server-side bracket; if the *stream* drops or
  staleness exceeds a threshold, **flatten or freeze**, don't trade on stale data.
- **Drift freeze (corrected stats):** the original "7% accuracy drop over 50 trades" is too noisy to be
  meaningful. Instead monitor, over a **larger rolling window (≥200 predictions)**:
  - **Calibration drift** — rolling Brier score / log-loss vs. the model's CV baseline.
  - **Feature drift** — PSI or KS test on live feature distributions vs. training distribution.
  - **Performance drift** — rolling realized R / Sharpe vs. a bootstrap confidence band from the backtest.
  Trigger an **automatic entry freeze + alert + retrain** when any breaches its band. Keep collecting data while
  frozen.
- **Kill switch:** a manual flag (via dashboard → Nest → Redis) that flattens and halts the bot immediately.

---

## 13. Monitoring & metrics (dashboard)

Surface on the React dashboard: live equity & open positions; per-trade log with calibrated `p`, size, R; rolling
net Sharpe/drawdown; rolling Brier score (calibration health); feature-drift (PSI) gauges; spread regime;
model version + age; guardrail states (frozen? daily-loss hit? stream healthy?).

---

## 14. Config (single source of truth)

Everything tunable lives in one config (YAML/env), consumed by both `train.py` and `bot.py`:
```
instrument: XAU_USD
entry_tf: M5            # try M15 / H1 too
context_tf: M30
atr_period: 14
tp_mult: 2.0
sl_mult: 1.5
max_horizon: 6          # candles
cost_gate_mult: 2.0
spread_stress_mult: 1.8
kelly_fraction: 0.25
risk_cap: 0.0075        # 0.75% equity
min_risk_floor: 0.001
daily_loss_limit: 0.03
max_concurrent_risk: 0.04
train_window_years: 3
retrain_cadence: weekly
```

---

## 15. Build order (suggested)

1. Data layer: OANDA fetch (`price=MBA`) + Parquet archive + Timescale; verify spread history is sane.
2. Feature + label builders (causal), with unit tests for no-leakage (assert features never use future bars).
3. Purged walk-forward CV harness + cost-aware backtester + benchmarks. **Get an honest net number here before
   building anything fancy.**
4. Model + calibration; reliability diagram.
5. Sizing module (§8) with the calibrator wired in.
6. `train.py` end-to-end → versioned artifact + release gate.
7. `bot.py` live loop on a **demo/practice account** first; paper-trade hundreds of trades across regimes.
8. Drift monitor + guardrails + dashboard wiring.
9. Only then, small real size — and keep comparing live slippage vs. backtest assumptions.

---

### Final reality check
The two things most likely to decide whether this makes money: (1) the **net-of-cost backtest with purged
walk-forward** in step 3 — if it isn't positive there, nothing downstream saves it; and (2) **whether M5 is even
the right horizon** — run M15 and H1 through the identical pipeline, because a wider horizon usually has a far
better edge-to-cost ratio for a spread-bearing OTC instrument like gold. This document is a blueprint, not a
promise of profitability, and none of it is financial advice; validate on a demo account before risking capital.
