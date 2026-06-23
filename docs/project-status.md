# Project Status

**Living document** — what is implemented vs what is next. For how to run the system, see [README.md](../README.md). For target architecture (not current reality), see [trading-bot-system-design.md](./trading-bot-system-design.md).

| Doc | Use for |
|-----|---------|
| This file | Built vs backlog, pitfalls |
| README | Commands, testing, env |
| trading-bot-system-design.md | Vision only (banner at top) |
| AGENTS.md | AI/human coding rules |

Current state of the super-trading platform.

## Bot configuration (JSON)

Bots and broker accounts are defined in JSON under `bots/config/`:

| File | Purpose |
|------|---------|
| `bots/config/accounts.json` | Broker account refs — env var names only, no secrets |
| `bots/config/accounts.local.json` | Optional local overrides (gitignored) |
| `bots/config/bots/*.json` | One file per bot: title, description, account, strategy, params |

On engine start, `bot_sync` upserts all bot JSON files into Postgres `bots` (title → `name`, plus `description`, `broker`, `account_ref`). Strategy logic stays in `bots/strategies/`.

**Multi-account OANDA:** map each account in `accounts.json` to env vars (e.g. `OANDA_API_KEY_2` / `OANDA_ACCOUNT_ID_2` for `oanda_paper_2`). Assign bots via `"account": "oanda_paper_2"` in their JSON file.

**Add a new bot:**

1. Create `bots/config/bots/my_bot.json` with `id`, `title`, `description`, `account`, `strategy`, `instrument`, `enabled`, `params`.
2. Register the strategy class in `bots/shared/bot_registry.py` (`STRATEGY_CLASSES`).
3. Implement strategy in `bots/strategies/`.
4. Restart `make run-trading` (syncs to DB automatically).

Test connectivity: `make test-oanda` or `uv run python scripts/test_oanda.py --account oanda_paper_1`.

## Market data (polling, not streaming)

Price data uses **OANDA REST polling** — there is no tick WebSocket stream yet.

| Data | Mechanism | Interval | Storage |
|------|-----------|----------|---------|
| Completed candles (M5, H1) | REST candles API | 30s | Postgres `candles` + Redis `candles:*` |
| Live mid-price | REST pricing API | 15s | Redis `price:*` only |
| Account NAV | REST account summary | 5 min | Postgres `balance_snapshots` (per `account_ref`) |

Nest relays Redis to the frontend via SSE (`/api/stream/market`) and Socket.IO. Historical chart bars come from `/api/candles` (backfilled on streamer start).

## Run commands (separate trading vs dashboard)

| Command | Runs | Use when |
|---------|------|----------|
| `make run-trading` | Docker + Python bots | Live paper trading — leave running |
| `make run-dashboard` | Docker + Nest + Vite | FE/API dev — restart without stopping bots |
| `make dev-bots` / `make dev-api` / `make dev-fe` | Single service, no Docker bootstrap | Power users with `make up` already |
| `make start` | All in one terminal | Rare full-stack smoke test |

Trade opens/closes log `TRADE OPEN` / `TRADE CLOSE` lines to the run-trading console.

## ML training data flow

1. **Live:** `run-trading` appends completed bars to Postgres `candles`.
2. **Export:** `make export-candles INSTRUMENT=XAU_USD GRANULARITY=M5` → `bots/data/candles/.../candles.parquet`.
3. **Train:** per-bot scripts in `bots/ml/train/` (no generic `make train`). Re-export before each training run.

---

## What's done

### Infrastructure

- [x] **Docker Compose** — Postgres 16 + Redis 7 with healthchecks and persistent volumes
- [x] **Database schema** — `candles`, `bots`, `trades`, `signals`, `news`, `balance_snapshots` via [docker/postgres/init.sql](../docker/postgres/init.sql)
- [x] **Bot JSON config** — `bots/config/accounts.json` + per-bot files; sync to Postgres on engine start
- [x] **Environment template** — Root [`.env.example`](../.env.example) shared by all services (multi-account OANDA vars)
- [x] **Dev tooling** — [Makefile](../Makefile) with `run-trading`, `run-dashboard`, `export-candles`, `db-reset`

### Python (`bots/`)

- [x] Project layout with `uv` + `pyproject.toml`
- [x] OANDA REST client with per-account credentials (`bot_registry` + `OandaClient`)
- [x] Candle poller (`oanda_streamer`), price poller, balance tracker
- [x] SMA crossover bots (`gold_sma_v1` H1 shadow, `gold_sma_m5_v1` M5 paper)
- [x] `main.py` — loads bots from JSON config, starts services per account

### Backend (`backend/`)

- [x] NestJS app with global `/api` prefix, CORS, validation pipe
- [x] TypeORM entities mirroring the DB schema (`synchronize: false`)
- [x] REST modules: `bots`, `trades`, `news`, `performance`, `candles`
- [x] SSE market stream + Redis pub/sub + Socket.IO gateway

### Frontend (`frontend/`)

- [x] Vite + React + TypeScript + Tailwind CSS v4
- [x] Zustand store + `useWebSocket` + SSE price/candle updates
- [x] SMA dashboard: bot list (with descriptions), price chart, balance chart, decision log, open trades

---

## What's not done yet

Honest gaps as of the SMA paper-trading milestone. The [design doc](./trading-bot-system-design.md) Phase 1 checklist is aspirational — use this section for reality.

### Market data

- [x] REST polling for M5/H1 candles + mid-price (30s / 15s)
- [x] Backfill on streamer start, Postgres `candles` + Redis publish
- [ ] OANDA tick **WebSocket** stream (design target; not implemented)
- [ ] M1 / M30 (and other) granularities in central streamer
- [ ] Explicit single “market data service” module (streamer exists but not fully isolated from bot process)

### ML pipeline

- [x] Postgres live candles + `make export-candles` → Parquet
- [ ] `fetch_data.py` — bulk historical download (5–10 years) into Postgres
- [ ] `build_features.py`, `train_model.py`, `evaluate.py` — stubs only
- [ ] `model_registry.py` — load `.pkl` / `.pt` at runtime
- [ ] First ML bot (`gold_momentum_v1`) wired to predictions

### Bots & execution

- [x] SMA crossover bots (H1 shadow, M5 paper) via JSON config + multi-account OANDA
- [x] Trade/signal persistence, Redis → Nest → dashboard
- [ ] `gold_sentiment_v1`, momentum/ML bots — stubs
- [ ] Kill switch (max drawdown halt, stop-all)
- [ ] Robust reconnect / partial-failure handling

### News & alerts

- [ ] `news_fetcher.py`, `sentiment_engine.py`, `calendar_monitor.py` — stubs
- [ ] `notifier.py` — Pushover

### Dashboard (polish)

- [x] Price chart, balance chart, decision log, open trades, bot descriptions
- [ ] Trade overlays on price chart
- [ ] Multi-account balance display

### Production readiness

- [ ] 2+ weeks continuous paper soak test
- [ ] Tighter Redis channel subscriptions (dev uses broad patterns)
- [ ] Live capital path with explicit safeguards (not started)

---

## Recommended next steps

Work in this order — each step should be testable before moving on:

1. **Historical bootstrap** — implement `fetch_data.py` to backfill years of M5/H1 (then M1/M30 as needed)
2. **ML bot** — features + train + `model_registry`; train from exported Parquet per bot
3. **Granularities** — add M1/M30 to central streamer for future strategies
4. **News/sentiment** — wire stubs as filters on a working ML bot
5. **Soak test** — `make run-trading` for 2+ weeks; add kill switch and reconnect hardening

---

## Things to be careful about

### Architecture boundaries

| Rule | Why |
|------|-----|
| **Python owns all trading logic** | ML, signals, OANDA orders, news/LLM — all in `bots/` |
| **NestJS is a relay + read API only** | Never call OANDA or run strategies from the backend |
| **Redis is the only coupling** | Bots don't know about the dashboard; the dashboard doesn't know bot internals |
| **One bot, one strategy** | Crashes are isolated; easy to add bots without touching existing ones |

### Trading safety

- **Paper trade first, always.** OANDA practice API is identical to live. No real money until 2+ weeks of stable paper trading.
- **Never commit `.env`** or API keys. Use `.env.example` for documentation only.
- **Add a kill switch early** — max drawdown halt, manual stop-all command.
- **Validate order size and direction** before every OANDA call.

### Development pitfalls

- **Port conflicts** — Default Postgres (5432) and Redis (6379) may be taken by other Docker projects. Override in `.env` (see README troubleshooting).
- **TypeORM `synchronize: false`** — Schema changes go through [docker/postgres/init.sql](../docker/postgres/init.sql) or future migrations. Do not enable auto-sync in production.
- **Socket.IO URL** — `VITE_WS_URL` must be `http://localhost:3210`, not `ws://`. The Socket.IO client expects an HTTP origin.
- **Folder names vs design doc** — The design doc uses `api/` and `dashboard/`; this repo uses `backend/` and `frontend/`. Same roles, different names.
- **Design doc checkmarks** — The Phase 1 section in the design doc describes the target build, not completed work. Use this file for actual status.
- **`init.sql` runs once per volume** — Changing schema requires `make db-reset` (drops data).
- **Redis pub/sub pattern** — The gateway uses `psubscribe('*')` for development. Tighten channel patterns before production.

### Dependency notes

- **Python**: managed with `uv` ([`bots/pyproject.toml`](../bots/pyproject.toml)). `pyarrow` installed for Parquet export; full ML stack (`pandas`, `scikit-learn`, etc.) not added yet.
- **Node**: npm in `backend/` and `frontend/` separately — no root workspace yet.
- **Docker required** for Postgres and Redis. Apps run on the host, not in containers.

---

## Quick reference

| Service | Default URL |
|---------|-------------|
| Frontend | http://localhost:3211 |
| Backend API | http://localhost:3210/api |
| SSE market stream | http://localhost:3210/api/stream/market |
| WebSocket | http://localhost:3210 (Socket.IO) |
| Postgres | localhost:5432 |
| Redis | localhost:6379 |

### Makefile (daily)

| Command | Use |
|---------|-----|
| `make run-trading` | Live bots — leave running |
| `make run-dashboard` | API + FE — restart without stopping bots |
| `make export-candles` | Snapshot Postgres candles to Parquet |
| `make test-oanda` | OANDA connectivity check |

```bash
cp .env.example .env
make install
make run-trading    # terminal 1 — bots
make run-dashboard  # terminal 2 — API + FE
```
