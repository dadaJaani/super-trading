# Trading Bot Platform — System Design

> **This document describes the target architecture and product vision.**  
> For what is actually implemented today, see [project-status.md](./project-status.md).  
> Folder names here (`api/`, `dashboard/`) map to `backend/` and `frontend/` in the repo.  
> Ports in diagrams (3000/3001) differ from current dev defaults (3211/3210).

## Overview

A locally hosted, multi-bot trading platform. Python handles all ML, signal generation, and bot execution. NestJS serves as the API/orchestration layer. React provides a real-time dashboard. OANDA is the first broker integration (gold, forex). Designed to scale to 15+ bots with shared or independent brains.

---

## Technology Decisions

| Layer | Technology | Why |
|---|---|---|
| Bot Engine | Python | ML libraries (sklearn, pytorch, pandas) all live here. No alternative. |
| API / Orchestration | NestJS (TypeScript) | Bridges Python bots and React FE. WebSocket server. Familiar to you. |
| Frontend | React + TailwindCSS | Real-time dashboard via WebSocket. |
| Database | PostgreSQL + TimescaleDB | TimescaleDB is a Postgres extension purpose-built for time-series (candle data, trades). One DB, two uses. |
| Message Bus | Redis (Pub/Sub) | Python bots publish events (trade fired, signal generated). NestJS subscribes and forwards to FE via WebSocket. Lightweight, fast. |
| Push Notifications | Pushover API | Simple mobile push. One API call from Python. Free tier generous. |
| OANDA Integration | oandapyV20 (Python) | Official Python wrapper for OANDA v20 REST API + streaming. |
| News / LLM | Python + Anthropic API | News fetched in Python, sent to Claude API for sentiment scoring. |

---

## High-Level Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                        YOUR LOCAL MACHINE                        │
│                                                                  │
│  ┌─────────────┐     ┌──────────────────────────────────────┐   │
│  │  React FE   │◄────│         NestJS API Server            │   │
│  │  :3000      │     │         :3001                        │   │
│  │             │     │  - REST endpoints (read-only for now)│   │
│  │  Dashboard  │     │  - WebSocket server (ws://)          │   │
│  └─────────────┘     │  - Subscribes to Redis               │   │
│                       └──────────────┬───────────────────────┘   │
│                                      │                            │
│                              ┌───────▼────────┐                  │
│                              │  Redis Pub/Sub  │                  │
│                              │  :6379          │                  │
│                              └───────▲────────┘                  │
│                                      │                            │
│  ┌───────────────────────────────────┼──────────────────────┐   │
│  │              PYTHON BOT ENGINE    │                        │   │
│  │                                   │                        │   │
│  │  ┌─────────────────────────────────────────────────────┐  │   │
│  │  │              Shared Services Layer                   │  │   │
│  │  │                                                      │  │   │
│  │  │  ┌──────────────┐  ┌──────────────┐  ┌──────────┐  │  │   │
│  │  │  │ News Fetcher │  │ LLM Sentiment│  │ OANDA    │  │  │   │
│  │  │  │ (RSS/APIs)   │  │ Engine       │  │ Streamer │  │  │   │
│  │  │  └──────────────┘  └──────────────┘  └──────────┘  │  │   │
│  │  │                                                      │  │   │
│  │  │  ┌──────────────┐  ┌──────────────┐                 │  │   │
│  │  │  │ ML Model     │  │ Economic     │                 │  │   │
│  │  │  │ Registry     │  │ Calendar     │                 │  │   │
│  │  │  └──────────────┘  └──────────────┘                 │  │   │
│  │  └─────────────────────────────────────────────────────┘  │   │
│  │                                                             │   │
│  │  ┌──────────┐  ┌──────────┐  ┌──────────┐  ┌──────────┐  │   │
│  │  │  Bot 1   │  │  Bot 2   │  │  Bot 3   │  │  Bot N   │  │   │
│  │  │ XAU/USD  │  │ XAU/USD  │  │ EUR/USD  │  │  ...     │  │   │
│  │  │ Strategy │  │ Strategy │  │ Strategy │  │          │  │   │
│  │  │    A     │  │    B     │  │    C     │  │          │  │   │
│  │  └──────────┘  └──────────┘  └──────────┘  └──────────┘  │   │
│  └───────────────────────────────────────────────────────────┘   │
│                                                                  │
│  ┌──────────────────────┐    ┌──────────────────────┐           │
│  │  PostgreSQL +        │    │  OANDA API           │           │
│  │  TimescaleDB  :5432  │    │  (cloud, external)   │           │
│  └──────────────────────┘    └──────────────────────┘           │
└─────────────────────────────────────────────────────────────────┘
```

---

## Component Breakdown

### 1. Python Bot Engine

The heart of the system. Runs as a set of Python processes.

#### 1a. Shared Services Layer

These run once and serve all bots:

**News Fetcher**
- Polls Reuters/Bloomberg RSS feeds every 2 minutes
- Pulls economic calendar events from Finnhub API
- Stores raw headlines in PostgreSQL with timestamps
- Publishes new headlines to Redis channel `news:raw`

**LLM Sentiment Engine**
- Subscribes to `news:raw`
- Batches headlines, sends to Claude API
- Prompt: "Score this headline's impact on XAU/USD: -1.0 (very bearish) to +1.0 (very bullish). Return JSON only."
- Stores scored sentiment in DB
- Publishes to Redis `news:scored`

**OANDA Price Streamer**
- Single WebSocket connection to OANDA streaming API
- Receives real-time tick data for all subscribed instruments
- Aggregates ticks into 1-min and 1-hour OHLCV candles
- Stores to TimescaleDB hypertable
- Publishes candle-close events to Redis `candles:XAU_USD:H1` etc.

**ML Model Registry**
- Loads trained `.pkl` / `.pt` model files at startup
- Exposes `predict(features)` function
- Shared across bots that use the same model
- Hot-reloadable without restarting bots

**Economic Calendar Monitor**
- Checks for high-impact events (Fed, CPI, NFP)
- Broadcasts `calendar:alert` 30 min before event
- Bots can pause/reduce size during high-uncertainty windows

#### 1b. Individual Bots

Each bot is a Python class/process with:

```python
class GoldMomentumBot:
    id = "gold_momentum_v1"
    instrument = "XAU_USD"
    strategy = "momentum"
    
    # What shared services it uses
    uses_models = ["xgb_gold_direction_v2"]
    uses_sentiment = True
    
    def on_candle(self, candle): ...      # fires every hour
    def on_sentiment(self, score): ...   # fires on new LLM score
    def on_calendar_alert(self, event): ... # fires 30min before event
    def evaluate_signal(self): ...       # combines all inputs → decision
    def execute(self, direction, size): ... # sends order to OANDA
    def publish_state(self): ...         # pushes state to Redis → FE
```

Each bot subscribes to the Redis channels it needs. Lightweight, clean, independent.

---

### 2. NestJS API Server

Sits between Python and the React FE. Two jobs:

**REST API (read-only for now)**
```
GET /api/bots              → list all bots + current status
GET /api/bots/:id          → single bot detail
GET /api/bots/:id/trades   → trade history
GET /api/bots/:id/signals  → signal log
GET /api/performance        → aggregate P&L
GET /api/news              → recent scored news feed
```

**WebSocket Server**
- Subscribes to all Redis channels on startup
- Forwards events to connected React clients in real time
- Events pushed to FE:
  - `bot:state` — every bot's live status, P&L, open trade
  - `trade:opened` / `trade:closed` — when a bot fires
  - `news:scored` — new sentiment-scored headline
  - `signal:generated` — ML model output + confidence
  - `candle:close` — price update

NestJS is thin here — it's a relay and API layer, not business logic.

---

### 3. React Frontend Dashboard

Single page app. Real-time via WebSocket connection to NestJS.

**Layout:**
```
┌─────────────────────────────────────────────────┐
│  HEADER: System status | Total P&L | Live clock  │
├──────────────┬──────────────────────────────────┤
│  BOT LIST    │  SELECTED BOT DETAIL              │
│              │                                   │
│  Bot 1 ● RUN │  XAU/USD Momentum Bot             │
│  P&L: +$142  │  ┌──────────────────────────┐    │
│              │  │  Price chart + trades     │    │
│  Bot 2 ● RUN │  └──────────────────────────┘    │
│  P&L: -$23   │                                   │
│              │  Open Trade: LONG 1oz @ $3,240    │
│  Bot 3 ⬤ ERR │  Current: $3,251 | P&L: +$11     │
│              │                                   │
│  Bot 4 ○ STP │  Signal: BUY | Confidence: 0.82  │
│              │  Trigger: "Fed signals pause"     │
└──────────────┴──────────────────────────────────┤
│  NEWS FEED                                       │
│  [+0.74] Fed signals rate pause → Gold bullish   │
│  [-0.31] USD strengthens on jobs data            │
└─────────────────────────────────────────────────┘
```

**Key components:**
- `BotList` — sidebar, all bots, color-coded status, mini P&L
- `BotDetail` — selected bot. Chart, open trade, signal log
- `SignalPanel` — ML confidence score + what triggered it
- `NewsFeed` — live LLM-scored headlines with sentiment score
- `PerformancePage` — aggregate charts, win rate, drawdown

---

### 4. Database Schema (PostgreSQL + TimescaleDB)

```sql
-- Time-series price data (TimescaleDB hypertable)
CREATE TABLE candles (
  time        TIMESTAMPTZ NOT NULL,
  instrument  TEXT NOT NULL,         -- 'XAU_USD'
  granularity TEXT NOT NULL,         -- 'H1', 'M1'
  open        DECIMAL,
  high        DECIMAL,
  low         DECIMAL,
  close       DECIMAL,
  volume      INTEGER
);
SELECT create_hypertable('candles', 'time');

-- Bot registry
CREATE TABLE bots (
  id          TEXT PRIMARY KEY,      -- 'gold_momentum_v1'
  name        TEXT,
  instrument  TEXT,
  strategy    TEXT,
  status      TEXT,                  -- 'running', 'stopped', 'error'
  config      JSONB,                 -- position size, risk params
  created_at  TIMESTAMPTZ
);

-- Trade log
CREATE TABLE trades (
  id            UUID PRIMARY KEY,
  bot_id        TEXT REFERENCES bots(id),
  oanda_trade_id TEXT,
  instrument    TEXT,
  direction     TEXT,                -- 'LONG' or 'SHORT'
  units         INTEGER,
  open_price    DECIMAL,
  close_price   DECIMAL,
  open_time     TIMESTAMPTZ,
  close_time    TIMESTAMPTZ,
  pnl           DECIMAL,
  status        TEXT                 -- 'open', 'closed'
);

-- Signal log
CREATE TABLE signals (
  id            UUID PRIMARY KEY,
  bot_id        TEXT REFERENCES bots(id),
  time          TIMESTAMPTZ,
  direction     TEXT,
  confidence    DECIMAL,             -- 0.0 to 1.0
  ml_features   JSONB,              -- snapshot of inputs
  news_trigger  TEXT,               -- headline that contributed
  acted_on      BOOLEAN
);

-- News + sentiment
CREATE TABLE news (
  id            UUID PRIMARY KEY,
  time          TIMESTAMPTZ,
  source        TEXT,
  headline      TEXT,
  sentiment_score DECIMAL,          -- -1.0 to +1.0
  instruments   TEXT[],             -- ['XAU_USD', 'EUR_USD']
  raw_response  JSONB               -- full LLM response
);
```

---

### 5. Redis Channel Map

```
candles:XAU_USD:H1        → new hourly candle closed
candles:XAU_USD:M1        → new 1-min candle
news:raw                  → unscored headline from fetcher
news:scored               → LLM-scored headline
calendar:alert            → upcoming high-impact event
signal:{bot_id}           → bot generated a signal
trade:opened:{bot_id}     → bot opened a trade
trade:closed:{bot_id}     → bot closed a trade
bot:state:{bot_id}        → periodic state snapshot (every 5s)
system:error              → any component error
```

---

### 6. Push Notification Flow (Pushover)

```python
# In any Python component
import pushover

def notify(title, message, priority=0):
    pushover.send(
        token="your_app_token",
        user="your_user_key",
        title=title,
        message=message,
        priority=priority  # 1 = high, 2 = requires confirmation
    )

# Examples:
notify("Trade Opened", "Gold Momentum Bot: LONG 1oz @ $3,240")
notify("Trade Closed", "Gold Momentum Bot: +$47 profit")
notify("BOT ERROR", "gold_momentum_v1 crashed: connection timeout", priority=2)
notify("Kill Switch", "All bots halted due to drawdown limit")
```

---

## Folder Structure

```
trading-platform/
│
├── bots/                          # Python — bot engine
│   ├── shared/
│   │   ├── news_fetcher.py        # RSS + Finnhub poller
│   │   ├── sentiment_engine.py    # LLM scoring via Claude API
│   │   ├── oanda_streamer.py      # Price stream → candles
│   │   ├── model_registry.py      # Load/serve ML models
│   │   ├── calendar_monitor.py    # Economic event watcher
│   │   ├── db.py                  # PostgreSQL connection
│   │   ├── redis_client.py        # Redis pub/sub
│   │   └── notifier.py            # Pushover push notifications
│   │
│   ├── strategies/
│   │   ├── base_bot.py            # Abstract base class all bots extend
│   │   ├── gold_momentum_v1.py    # Bot 1: XAU/USD momentum
│   │   ├── gold_sentiment_v1.py   # Bot 2: XAU/USD news-driven
│   │   └── ...
│   │
│   ├── ml/
│   │   ├── train/
│   │   │   ├── fetch_data.py      # Download historical candles
│   │   │   ├── build_features.py  # Calculate indicators, label spikes
│   │   │   ├── train_model.py     # Train XGBoost / LSTM
│   │   │   └── evaluate.py        # Backtest, walk-forward test
│   │   └── models/
│   │       ├── xgb_gold_v1.pkl    # Saved trained models
│   │       └── lstm_gold_v1.pt
│   │
│   ├── main.py                    # Starts all shared services + bots
│   └── requirements.txt
│
├── api/                           # NestJS — API + WebSocket server
│   ├── src/
│   │   ├── bots/                  # Bot REST endpoints
│   │   ├── trades/                # Trade history endpoints
│   │   ├── news/                  # News feed endpoints
│   │   ├── performance/           # P&L aggregation
│   │   ├── gateway/               # WebSocket gateway
│   │   │   └── trading.gateway.ts # Redis → WebSocket relay
│   │   └── main.ts
│   └── package.json
│
├── dashboard/                     # React frontend
│   ├── src/
│   │   ├── components/
│   │   │   ├── BotList.tsx
│   │   │   ├── BotDetail.tsx
│   │   │   ├── TradeChart.tsx
│   │   │   ├── SignalPanel.tsx
│   │   │   ├── NewsFeed.tsx
│   │   │   └── PerformanceCharts.tsx
│   │   ├── hooks/
│   │   │   └── useWebSocket.ts    # WS connection + event routing
│   │   ├── store/                 # Zustand state management
│   │   └── App.tsx
│   └── package.json
│
└── docker-compose.yml             # PostgreSQL + Redis + TimescaleDB
```

---

## Data Flow — Full Lifecycle of One Trade

```
1. OANDA Streamer receives XAU/USD tick
        ↓
2. Tick aggregated into 1H candle close
        ↓
3. Redis publishes: candles:XAU_USD:H1
        ↓
4. Gold Momentum Bot receives candle event
        ↓
5. Bot calculates technical features (RSI, MACD, BB position)
        ↓
6. Bot queries ML Model Registry → predict(features)
        → Model returns: direction=LONG, confidence=0.81
        ↓
7. Bot checks latest sentiment score from DB
        → sentiment_score = +0.63 (bullish news)
        ↓
8. Bot checks economic calendar
        → No Fed event in next 4 hours ✓
        ↓
9. Signal passes all filters → Execute trade
        ↓
10. Bot calls OANDA API → opens LONG position
        ↓
11. Bot publishes to Redis:
        signal:gold_momentum_v1 → {direction, confidence, trigger}
        trade:opened:gold_momentum_v1 → {instrument, price, units}
        ↓
12. NestJS receives Redis event
        ↓
13. NestJS forwards via WebSocket to React dashboard
        ↓
14. Dashboard updates in real time: new open trade shown
        ↓
15. Pushover sends push notification to your phone
        "Trade Opened: LONG XAU/USD @ $3,241 | Confidence 81%"
        ↓
16. Bot monitors position every minute
        ↓
17. Take-profit or stop-loss hit → OANDA closes trade
        ↓
18. Bot records result to DB, publishes trade:closed event
        ↓
19. Dashboard P&L updates, trade moves to history
```

---

## Phase 1 Build Order (Gold + OANDA first)

Build in this exact sequence — each step is testable before moving on:

```
Week 1 — Foundation
  ✓ Docker: PostgreSQL + TimescaleDB + Redis running locally
  ✓ DB schema created
  ✓ OANDA paper trading account set up + API keys
  ✓ oanda_streamer.py: connect, receive ticks, store candles

Week 2 — Data + ML
  ✓ fetch_data.py: download 3 years XAU/USD hourly history
  ✓ build_features.py: calculate indicators, label spikes
  ✓ train_model.py: train first XGBoost classifier
  ✓ evaluate.py: backtest on held-out data

Week 3 — First Bot
  ✓ base_bot.py: abstract base class
  ✓ gold_momentum_v1.py: first real bot using trained model
  ✓ model_registry.py: load + serve model
  ✓ notifier.py: Pushover integration

Week 4 — News + LLM Layer
  ✓ news_fetcher.py: RSS + Finnhub polling
  ✓ sentiment_engine.py: Claude API scoring
  ✓ Bot updated to consume sentiment scores
  ✓ calendar_monitor.py: economic event awareness

Week 5 — API + Dashboard
  ✓ NestJS API server: REST endpoints
  ✓ WebSocket gateway: Redis → FE relay
  ✓ React dashboard: BotList, BotDetail, NewsFeed
  ✓ Real-time P&L, open trades, signal log

Week 6 — Paper Trading
  ✓ Run full system on OANDA paper account
  ✓ Monitor for 2 weeks before any real money
  ✓ Fix edge cases, connection drops, error handling
```

---

## Key Design Principles

**Python for everything trading-related.** ML training, signal generation, order execution, news processing. NestJS never touches OANDA directly.

**Redis as the nervous system.** All components are decoupled. A bot doesn't know the dashboard exists. The dashboard doesn't know how bots work. Redis is the only coupling point.

**One bot, one strategy, one process.** Clean. If Bot 3 crashes, Bots 1 and 2 keep running. Easy to add new bots without touching existing ones.

**Shared services are singletons.** One news fetcher, one OANDA stream connection, one LLM engine. Bots consume their output — they don't each make their own API calls.

**Paper trade first, always.** OANDA paper account is identical to live API. Never go live without 2+ weeks of paper trading with real data.
