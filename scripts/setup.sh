#!/usr/bin/env bash
# First-time setup: .env, deps, Docker, fresh DB schema.
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"

export PATH="${HOME}/.local/bin:${PATH}"

CYAN='\033[0;36m'
GREEN='\033[0;32m'
NC='\033[0m'

echo -e "${CYAN}==>${NC} Super Trading — first-time setup"

if [[ ! -f .env ]]; then
  cp .env.example .env
  echo -e "${GREEN}Created .env from .env.example${NC}"
  echo "  → Edit .env and add OANDA_API_KEY + OANDA_ACCOUNT_ID"
else
  echo "  .env already exists (skipped)"
fi

if ! command -v docker >/dev/null 2>&1 || ! docker info >/dev/null 2>&1; then
  echo "  Start Docker Desktop, then run: make setup"
  exit 1
fi

make install
make db-reset

echo ""
echo -e "${GREEN}Setup complete.${NC} Start everything with:"
echo "  make start"
