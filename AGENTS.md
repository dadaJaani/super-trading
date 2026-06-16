# Agent Instructions

Instructions for AI coding agents working in this repository.

## Read first

1. [docs/project-status.md](docs/project-status.md) — what's done, what's next, pitfalls
2. [docs/trading-bot-system-design.md](docs/trading-bot-system-design.md) — architecture and data flow
3. [README.md](README.md) — how to run locally

## Project overview

Locally hosted multi-bot trading platform:

| Directory | Stack | Role |
|-----------|-------|------|
| `bots/` | Python 3.12, uv | ML, signals, OANDA execution, Redis pub/sub |
| `backend/` | NestJS, TypeORM, Socket.IO | REST API + WebSocket relay (no trading logic) |
| `frontend/` | Vite, React, Tailwind, Zustand | Real-time dashboard |

Infrastructure: TimescaleDB (Postgres) + Redis via Docker Compose.

## Hard rules

1. **Python owns trading.** Never add OANDA calls, strategy logic, or ML inference to `backend/`.
2. **NestJS relays only.** REST reads from Postgres; WebSocket forwards Redis events to the frontend.
3. **Redis is the message bus.** Components communicate through documented channels (see design doc).
4. **Paper trade first.** No live-money paths without explicit user request and safeguards.
5. **Never commit secrets.** Do not add `.env`, API keys, or credentials to git.
6. **Minimal diffs.** Match existing conventions; don't refactor unrelated code.
7. **No empty catch blocks.** Log errors; fail visibly during development.

## Folder layout

```
bots/           Python bot engine
backend/        NestJS API (NOT "api/" from design doc)
frontend/       React dashboard (NOT "dashboard/" from design doc)
docker/         Postgres init SQL
docs/           Design + status docs
```

## Running locally

```bash
cp .env.example .env
make up          # Postgres + Redis
make install     # npm + uv deps
make dev-api     # :3001
make dev-fe      # :5173
make dev-bots    # Python engine
```

If ports 5432/6379 are in use, override `POSTGRES_PORT`, `REDIS_PORT`, `DATABASE_URL`, and `REDIS_URL` in `.env`.

## Code conventions

### Python (`bots/`)

- Package manager: **uv** (`uv sync`, `uv run python main.py`)
- Settings: `shared/config.py` via pydantic-settings, reads root `.env`
- New bots extend `strategies/base_bot.py`
- Shared services are singletons started from `main.py`
- Stub files have docstrings and typed signatures — replace stubs with real logic incrementally

### Backend (`backend/`)

- npm, NestJS modules per domain (`bots`, `trades`, `news`, `performance`, `gateway`)
- Global prefix: `/api`
- TypeORM entities in `src/entities/` — **`synchronize: false`**
- Schema changes: update `docker/postgres/init.sql`, then `make db-reset`
- Config loads root `.env` via `@nestjs/config`
- WebSocket: Socket.IO gateway in `src/gateway/trading/trading.gateway.ts`

### Frontend (`frontend/`)

- Vite env vars: `VITE_API_URL`, `VITE_WS_URL` (HTTP origin for Socket.IO, not `ws://`)
- State: Zustand in `src/store/tradingStore.ts`
- WebSocket hook: `src/hooks/useWebSocket.ts`
- Components in `src/components/` — keep presentational; data via store

## Redis channels

```
candles:{instrument}:{granularity}   e.g. candles:XAU_USD:H1
news:raw
news:scored
calendar:alert
signal:{bot_id}
trade:opened:{bot_id}
trade:closed:{bot_id}
bot:state:{bot_id}
system:error
```

## API endpoints

```
GET /api/bots
GET /api/bots/:id
GET /api/bots/:id/trades
GET /api/bots/:id/signals
GET /api/news
GET /api/performance
```

## What to work on next

See [docs/project-status.md](docs/project-status.md). Priority order:

1. OANDA price streamer (real ticks → DB + Redis)
2. Historical data + ML training pipeline
3. First real bot with paper trading
4. End-to-end Redis → WebSocket → dashboard flow
5. News/sentiment layer

## Testing expectations

- Verify `make up` health before testing DB/Redis code
- Backend: `cd backend && npm run build`
- Frontend: `cd frontend && npm run build`
- Python: `cd bots && uv run python -c "from shared.db import ping; assert ping()"`
- Do not add tests unless they cover meaningful behavior

## Common mistakes to avoid

- Putting business logic in NestJS controllers
- Using `ws://` for `VITE_WS_URL` (use `http://`)
- Enabling TypeORM `synchronize: true`
- Assuming design doc ✓ marks mean code is implemented
- Forgetting to update `DATABASE_URL` when changing `POSTGRES_PORT`
- Adding ML dependencies to `pyproject.toml` before they're needed
