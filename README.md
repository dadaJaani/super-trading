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

**Every day — one command starts everything:**

```bash
make start
```

That starts Postgres + Redis (Docker), then the API, dashboard, and bot engine in one terminal.

| What            | URL |
|-----------------|-----|
| Dashboard       | http://localhost:3211 |
| API             | http://localhost:3210/api |
| WebSocket       | http://localhost:3210 |

Press **Ctrl+C** to stop the app processes (Docker keeps running). Use `make stop` to stop Docker too.

Or run services individually:

```bash
make up         # Postgres + Redis only
make dev-api    # NestJS API on http://localhost:3210
make dev-fe     # Vite dashboard on http://localhost:3211
make dev-bots   # Python bot engine
```

## Project structure

```
super-trading/
├── bots/       # Python bot engine (ML, OANDA, Redis pub/sub)
├── backend/    # NestJS REST API + WebSocket gateway
├── frontend/   # React dashboard (Vite + Tailwind)
├── docker/     # Database init scripts
└── docs/       # System design
```

## Services

| Service    | URL / Port              |
|------------|-------------------------|
| Frontend   | http://localhost:3211   |
| Backend    | http://localhost:3210   |
| PostgreSQL | localhost:5432          |
| Redis      | localhost:6379          |

## API endpoints (stub)

- `GET /api/bots` — list bots
- `GET /api/bots/:id` — bot detail
- `GET /api/bots/:id/trades` — trade history
- `GET /api/bots/:id/signals` — signal log
- `GET /api/news` — recent news feed
- `GET /api/performance` — aggregate P&L

WebSocket events are relayed from Redis via the NestJS gateway.

## Testing OANDA and the SMA bots

After `make setup` (or `make db-reset` when seed/schema changes):

```bash
make up
make test-oanda      # read-only: balance, price, M5/H1 candles, open trades
make smoke-trade     # open + close 1 paper unit on XAU/USD
make diagnose        # candle counts, signal counts, SMA preview
make start           # full stack
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

This drops volumes and re-runs the init SQL (schema + seed bots including `gold_sma_m5_v1`).

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

- `OANDA_API_KEY` / `OANDA_ACCOUNT_ID` — OANDA paper trading
- `ANTHROPIC_API_KEY` — LLM sentiment scoring
- `PUSHOVER_TOKEN` / `PUSHOVER_USER` — mobile notifications
- `FINNHUB_API_KEY` — economic calendar
