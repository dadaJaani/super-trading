#!/usr/bin/env bash
# Start Postgres + Redis and Nest API + Vite dashboard (no Python bots).
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

# shellcheck source=lib/wait-infra.sh
source "$(dirname "${BASH_SOURCE[0]}")/lib/wait-infra.sh"

if [[ ! -d backend/node_modules ]] || [[ ! -d frontend/node_modules ]]; then
  log "Node deps missing — running make install..."
  make install
fi

wait_infra_bootstrap

echo "  Dashboard   ${CYAN}http://localhost:3211${NC}"
echo "  API         ${CYAN}http://localhost:3210/api${NC}"
echo "  WebSocket   ${CYAN}http://localhost:3210${NC}"
echo ""
echo "  Live bots: run ${CYAN}make run-trading${NC} in another terminal."
echo ""
echo "Press Ctrl+C to stop API + dashboard (Docker keeps running)."
echo ""

cleanup() {
  echo ""
  log "Stopping dashboard services..."
  kill 0 2>/dev/null || true
}
trap cleanup INT TERM

(
  cd backend && exec npm run start:dev
) &

(
  cd frontend && exec npm run dev
) &

wait
