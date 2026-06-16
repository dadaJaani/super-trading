# Project Status

Current state of the super-trading platform as of the initial scaffold. For full architecture, see [trading-bot-system-design.md](./trading-bot-system-design.md).

## What's done

### Infrastructure

- [x] **Docker Compose** — TimescaleDB (Postgres 16) + Redis 7 with healthchecks and persistent volumes
- [x] **Database schema** — `candles` (hypertable), `bots`, `trades`, `signals`, `news` via [docker/postgres/init.sql](../docker/postgres/init.sql)
- [x] **Seed data** — Two placeholder bots: `gold_momentum_v1`, `gold_sentiment_v1`
- [x] **Environment template** — Root [`.env.example`](../.env.example) shared by all services
- [x] **Dev tooling** — [Makefile](../Makefile) with `up`, `install`, `dev`, `db-reset`

### Python (`bots/`)

- [x] Project layout with `uv` + `pyproject.toml`
- [x] Shared service stubs: `db`, `redis_client`, `news_fetcher`, `sentiment_engine`, `oanda_streamer`, `model_registry`, `calendar_monitor`, `notifier`
- [x] Strategy stubs: `base_bot`, `gold_momentum_v1`, `gold_sentiment_v1`
- [x] ML training stubs under `ml/train/`
- [x] `main.py` entry point — verifies DB/Redis connectivity, starts stub services and bots

### Backend (`backend/`)

- [x] NestJS app with global `/api` prefix, CORS, validation pipe
- [x] TypeORM entities mirroring the DB schema (`synchronize: false`)
- [x] REST modules: `bots`, `trades`, `news`, `performance`
- [x] Redis pub/sub service (`ioredis`)
- [x] WebSocket gateway (Socket.IO) relaying Redis events to the frontend

### Frontend (`frontend/`)

- [x] Vite + React + TypeScript + Tailwind CSS v4
- [x] Zustand store + `useWebSocket` hook
- [x] Dashboard shell: `BotList`, `BotDetail`, `TradeChart`, `SignalPanel`, `NewsFeed`, `PerformanceCharts`
- [x] Fetches bots and performance from the API on load

---

## What's not done yet

Everything below is **stubbed or missing business logic**. The design doc Phase 1 checklist marks many items with ✓ — those refer to the target build, not current implementation.

### Week 1 — Foundation (next priority)

- [ ] OANDA paper account + API keys in `.env`
- [ ] Real `oanda_streamer.py` — connect, receive ticks, aggregate candles, write to TimescaleDB, publish to Redis

### Week 2 — Data + ML

- [ ] `fetch_data.py` — download historical XAU/USD candles
- [ ] `build_features.py` — indicators and labels
- [ ] `train_model.py` — first XGBoost model
- [ ] `evaluate.py` — backtest / walk-forward

### Week 3 — First Bot

- [ ] Wire `gold_momentum_v1` to real model predictions
- [ ] `model_registry.py` — load `.pkl` / `.pt` files
- [ ] `notifier.py` — Pushover integration
- [ ] Real order execution via OANDA

### Week 4 — News + LLM

- [ ] `news_fetcher.py` — RSS + Finnhub
- [ ] `sentiment_engine.py` — Claude API scoring
- [ ] `calendar_monitor.py` — high-impact event alerts

### Week 5 — API + Dashboard (partially scaffolded)

- [x] REST endpoints exist but return DB data only (no live bot state yet)
- [x] WebSocket gateway exists but needs end-to-end event flow from Python
- [ ] Real-time P&L, open trades, signal log driven by live Redis events
- [ ] Price chart with trade overlays

### Week 6 — Paper Trading

- [ ] Full system run on OANDA paper account
- [ ] 2+ weeks monitoring before any live capital
- [ ] Error handling for connection drops, restarts, partial failures

---

## Recommended next steps

Work in this order — each step should be testable before moving on:

1. **OANDA streamer** — Get ticks flowing into `candles` table and Redis `candles:XAU_USD:H1`
2. **Historical data + first model** — Train and save a model; load it in `model_registry`
3. **First real bot** — `gold_momentum_v1` consumes candles + model output; paper trades only
4. **End-to-end event flow** — Bot publishes to Redis → Nest relays → dashboard updates
5. **News + sentiment layer** — Add as a filter on top of the working bot
6. **Paper trading soak test** — Run continuously for 2 weeks

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
- **Socket.IO URL** — `VITE_WS_URL` must be `http://localhost:3001`, not `ws://`. The Socket.IO client expects an HTTP origin.
- **Folder names vs design doc** — The design doc uses `api/` and `dashboard/`; this repo uses `backend/` and `frontend/`. Same roles, different names.
- **Design doc checkmarks** — The Phase 1 section in the design doc describes the target build, not completed work. Use this file for actual status.
- **TimescaleDB init runs once** — Changing `init.sql` requires `make db-reset` to reapply (drops data).
- **Redis pub/sub pattern** — The gateway uses `psubscribe('*')` for development. Tighten channel patterns before production.

### Dependency notes

- **Python**: managed with `uv` (see `bots/pyproject.toml`). ML deps (`pandas`, `scikit-learn`, etc.) are not installed yet.
- **Node**: npm in `backend/` and `frontend/` separately — no root workspace yet.
- **Docker required** for Postgres and Redis. Apps run on the host, not in containers.

---

## Quick reference

| Service | Default URL |
|---------|-------------|
| Frontend | http://localhost:5173 |
| Backend API | http://localhost:3001/api |
| WebSocket | http://localhost:3001 (Socket.IO) |
| Postgres | localhost:5432 |
| Redis | localhost:6379 |

```bash
cp .env.example .env
make up && make install
make dev-api   # terminal 1
make dev-fe    # terminal 2
make dev-bots  # terminal 3
```
