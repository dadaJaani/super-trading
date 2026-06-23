# Super Trading Platform

Locally hosted multi-bot trading platform. Python handles ML, signals, and execution. NestJS provides the API and WebSocket relay. React powers the real-time dashboard.

See [docs/trading-bot-system-design.md](docs/trading-bot-system-design.md) for full architecture.
See [docs/project-status.md](docs/project-status.md) for what's done, next steps, and cautions.

## Prerequisites

- [Docker](https://docs.docker.com/get-docker/) (Docker Compose v2)
- [Node.js](https://nodejs.org/) 20+
- [Python](https://www.python.org/) 3.12+
- [uv](https://docs.astral.sh/uv/) (recommended) or pip + venv

## Quick start

**First time only:**

```bash
cp .env.example .env          # then add OANDA_API_KEY + OANDA_ACCOUNT_ID
make setup                    # install deps + create DB schema + seed bots
```

**Every day — run trading and dashboard separately:**

```bash
# Terminal 1 — live bots (leave running)
make run-trading

# Terminal 2 — API + dashboard (restart freely without stopping bots)
make run-dashboard
```

Each command starts Postgres + Redis if needed. Ctrl+C in the dashboard terminal does not stop bots.

| What            | URL |
|-----------------|-----|
| Dashboard       | http://localhost:3211 |
| API             | http://localhost:3210/api |
| WebSocket       | http://localhost:3210 |

Trade opens/closes print `TRADE OPEN` / `TRADE CLOSE` lines in the **run-trading** terminal.

`make start` still runs everything in one terminal (useful for smoke tests); prefer the split commands above.

Or run services individually (no Docker bootstrap):

```bash
make up         # Postgres + Redis only
make dev-api    # NestJS API on http://localhost:3210
make dev-fe     # Vite dashboard on http://localhost:3211
make dev-bots   # Python bot engine
```

## ML training data (Postgres + Parquet)

While `make run-trading` is collecting bars, completed candles land in Postgres `candles`. Before training a bot-specific model, export the granularity that bot uses:

```bash
make export-candles INSTRUMENT=XAU_USD GRANULARITY=M5    # e.g. bot 1
make export-candles INSTRUMENT=XAU_USD GRANULARITY=M30   # e.g. bot 2
```

Output: `bots/data/candles/{instrument}/{granularity}/candles.parquet` (gitignored).

Then run **per-bot** training scripts (no generic `make train`):

```bash
cd bots && uv run python -m ml.train.build_features --bot gold_momentum_v1 ...
cd bots && uv run python -m ml.train.train_model --bot gold_momentum_v1 ...
```

Re-export before each training run to include new bars collected since the last export.

## Project structure

```
super-trading/
├── bots/
│   ├── config/          # accounts.json + per-bot JSON (no secrets)
│   ├── strategies/      # bot logic
│   ├── shared/          # OANDA, Redis, streamer, bot_registry
│   ├── ml/train/        # export_candles, training stubs
│   └── data/            # Parquet exports (gitignored)
├── backend/             # NestJS REST API + WebSocket/SSE relay
├── frontend/            # React dashboard (Vite + Tailwind)
├── docker/              # Postgres init SQL
└── docs/                # Design + status
```

## Makefile commands

| Command | What it runs |
|---------|----------------|
| `make setup` | First time: `.env`, install, `db-reset` |
| `make run-trading` | Docker + Python bots only |
| `make run-dashboard` | Docker + Nest API + Vite FE |
| `make start` | All three in one terminal (smoke test; prefer split above) |
| `make up` | Postgres + Redis only |
| `make dev-bots` / `dev-api` / `dev-fe` | Single service, no Docker bootstrap |
| `make export-candles` | Postgres → Parquet (`INSTRUMENT`, `GRANULARITY`) |
| `make test-oanda` / `smoke-trade` / `diagnose` | OANDA + system checks |
| `make db-reset` | Wipe DB volume, re-apply `init.sql` |

## Services

| Service    | URL / Port              |
|------------|-------------------------|
| Frontend   | http://localhost:3211   |
| Backend    | http://localhost:3210   |
| PostgreSQL | localhost:5432          |
| Redis      | localhost:6379          |

## API endpoints

- `GET /api/bots` — list bots (synced from JSON config when bots run)
- `GET /api/bots/:id` — bot detail
- `GET /api/bots/:id/trades` — trade history (`?status=open` supported)
- `GET /api/bots/:id/signals` — signal log
- `GET /api/candles` — historical OHLCV (`instrument`, `granularity`, `limit`)
- `GET /api/news` — recent news feed
- `GET /api/performance` — aggregate P&L summary
- `GET /api/performance/balance` — balance history for chart
- `GET /api/stream/market` — SSE relay of Redis price + candle events

Socket.IO on `http://localhost:3210` relays bot state, trades, signals, and balance updates from Redis.

## Testing OANDA and the SMA bots

After `make setup` (or `make db-reset` when seed/schema changes):

```bash
make up
make test-oanda      # read-only: balance, price, M5/H1 candles, open trades
make smoke-trade     # open + close 1 paper unit on XAU/USD
make diagnose        # candle counts, signal counts, SMA preview
make run-trading     # bots only
make run-dashboard   # API + FE only
```

Open **http://localhost:3211** — default bot is **Gold SMA M5 Test** (faster signals than H1).

| Step | What to check |
|------|----------------|
| `make test-oanda` | All lines show `PASS` |
| `make smoke-trade` | Trade appears in OANDA practice UI |
| `make diagnose` | M5 candle count >= 50 after bots start |
| Dashboard | Price chart ~120 bars immediately; live price via SSE |
| M5 bot | `bots/logs/gold_sma_m5_v1.log` — `evaluate` every ~5 min |
| H1 bot | Shadow mode (`execute_trades: false`) — logs only, no orders |

**No trades in hours?** SMA only trades on **crossover** (not every bar). You should still see **HOLD** rows in Decision Log every M5 close. Zero crosses in a trending market is normal.

**Price data:** Python polls OANDA REST (M5/H1 candles every 30s, mid-price every 15s). Nest relays to the browser via **SSE** `GET /api/stream/market` (no OANDA keys in NestJS).

## Database reset

```bash
make db-reset
```

This drops volumes and re-runs [docker/postgres/init.sql](docker/postgres/init.sql). SMA bots are defined in `bots/config/bots/*.json` and upserted to Postgres when you start `make run-trading`.

Add `uv` to your PATH if needed (after install):

```bash
export PATH="$HOME/.local/bin:$PATH"
```

## Python without uv

```bash
cd bots
python -m venv .venv
source .venv/bin/activate
pip install -e .
python main.py
```

## Troubleshooting

**Port conflicts:** If ports 5432 or 6379 are already in use, override in `.env` and restart:

```bash
POSTGRES_PORT=5433
REDIS_PORT=6380
DATABASE_URL=postgresql://trading:trading@localhost:5433/trading
REDIS_URL=redis://localhost:6380
make up
```

## Environment variables

Copy `.env.example` to `.env` and fill in external API keys when ready:

- `OANDA_API_KEY` / `OANDA_ACCOUNT_ID` — primary OANDA paper account (`oanda_paper_1`)
- `OANDA_API_KEY_2` / `OANDA_ACCOUNT_ID_2` — optional second account (`oanda_paper_2`)
- `OANDA_ENV` — `practice` or `live`
- `ANTHROPIC_API_KEY` — LLM sentiment scoring
- `PUSHOVER_TOKEN` / `PUSHOVER_USER` — mobile notifications
- `FINNHUB_API_KEY` — economic calendar
