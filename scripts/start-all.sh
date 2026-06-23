#!/usr/bin/env bash
# Start Docker (Postgres + Redis) and all app services in one terminal.
# Prefer: make run-trading + make run-dashboard in separate terminals.
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"

export PATH="${HOME}/.local/bin:${PATH}"

RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
CYAN='\033[0;36m'
NC='\033[0m'

log() { echo -e "${CYAN}==>${NC} $*"; }
warn() { echo -e "${YELLOW}warning:${NC} $*"; }
die() { echo -e "${RED}error:${NC} $*" >&2; exit 1; }

if [[ ! -f .env ]]; then
  die "No .env file. Run: cp .env.example .env  (then add your OANDA keys)"
fi

if ! command -v docker >/dev/null 2>&1; then
  die "Docker not found. Install Docker Desktop: https://docs.docker.com/get-docker/"
fi

if ! docker info >/dev/null 2>&1; then
  die "Docker is not running. Open Docker Desktop and try again."
fi

if ! command -v uv >/dev/null 2>&1; then
  warn "uv not found — install: curl -LsSf https://astral.sh/uv/install.sh | sh"
  die "uv is required for the Python bot engine"
fi

if [[ ! -d backend/node_modules ]] || [[ ! -d frontend/node_modules ]] || [[ ! -d bots/.venv ]]; then
  log "Dependencies missing — running make install..."
  make install
fi

log "Starting Postgres + Redis..."
docker compose up -d

log "Waiting for Postgres..."
for i in $(seq 1 60); do
  if docker compose exec -T postgres pg_isready -U trading -d trading >/dev/null 2>&1; then
    break
  fi
  if [[ $i -eq 60 ]]; then
    echo ""
    docker compose logs postgres --tail 25
    die "Postgres did not become ready. Run: make db-reset  (wipes DB volume)"
  fi
  sleep 2
done

log "Waiting for Redis..."
for i in $(seq 1 30); do
  if docker compose exec -T redis redis-cli ping >/dev/null 2>&1; then
    break
  fi
  if [[ $i -eq 30 ]]; then
    die "Redis did not become ready. Try: make logs"
  fi
  sleep 1
done

echo ""
echo -e "${GREEN}Infrastructure ready.${NC}"
echo ""
echo "  Dashboard   ${CYAN}http://localhost:3211${NC}"
echo "  API         ${CYAN}http://localhost:3210/api${NC}"
echo "  WebSocket   ${CYAN}http://localhost:3210${NC}"
echo ""
echo "Press Ctrl+C to stop all services (Docker keeps running)."
echo ""

cleanup() {
  echo ""
  log "Stopping app services..."
  kill 0 2>/dev/null || true
}
trap cleanup INT TERM

(
  cd backend && exec npm run start:dev
) &

(
  cd frontend && exec npm run dev
) &

(
  cd bots && exec uv run python main.py
) &

wait
