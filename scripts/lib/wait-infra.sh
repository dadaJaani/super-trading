# Shared Docker + Postgres + Redis bootstrap for run scripts.
# Sourced by run-trading.sh and run-dashboard.sh — not executed directly.

wait_infra_bootstrap() {
  if [[ ! -f .env ]]; then
    die "No .env file. Run: cp .env.example .env  (then add your OANDA keys)"
  fi

  if ! command -v docker >/dev/null 2>&1; then
    die "Docker not found. Install Docker Desktop: https://docs.docker.com/get-docker/"
  fi

  if ! docker info >/dev/null 2>&1; then
    die "Docker is not running. Open Docker Desktop and try again."
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
}
