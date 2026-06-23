#!/usr/bin/env bash
# Start Postgres + Redis and the Python trading bot engine only.
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

if ! command -v uv >/dev/null 2>&1; then
  warn "uv not found — install: curl -LsSf https://astral.sh/uv/install.sh | sh"
  die "uv is required for the Python bot engine"
fi

if [[ ! -d bots/.venv ]]; then
  log "Python deps missing — running make install..."
  make install
fi

wait_infra_bootstrap

echo "  Trading engine only (no API / dashboard)."
echo "  Dashboard: run ${CYAN}make run-dashboard${NC} in another terminal."
echo ""
echo "Press Ctrl+C to stop bots (Docker keeps running)."
echo ""

cd bots && exec uv run python main.py
