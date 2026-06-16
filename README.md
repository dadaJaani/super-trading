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

```bash
# 1. Clone and configure
cp .env.example .env

# 2. Start Postgres (TimescaleDB) + Redis
make up

# 3. Install dependencies
make install

# 4. Run everything (backend, frontend, bots)
make dev
```

Or run services individually:

```bash
make dev-api    # NestJS API on http://localhost:3001
make dev-fe     # Vite dashboard on http://localhost:5173
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
| Frontend   | http://localhost:5173   |
| Backend    | http://localhost:3001   |
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

## Database reset

```bash
make db-reset
```

This drops volumes and re-runs the init SQL (schema + seed bots).

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
