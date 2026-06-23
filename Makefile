.PHONY: up down install setup start run-trading run-dashboard dev dev-api dev-fe dev-bots db-reset logs stop wait-db export-candles test-oanda smoke-trade diagnose

INSTRUMENT ?= XAU_USD
GRANULARITY ?= M5

up:
	docker compose up -d

down:
	docker compose down

logs:
	docker compose logs -f

install:
	cd backend && npm install
	cd frontend && npm install
	cd bots && PATH="$$HOME/.local/bin:$$PATH" uv sync

# First time: copy .env, install deps, reset DB with schema + seed bots
setup:
	@bash scripts/setup.sh

# Trading bot engine only (Postgres + Redis + Python bots)
run-trading:
	@bash scripts/run-trading.sh

# Nest API + React dashboard only (Postgres + Redis + API + FE)
run-dashboard:
	@bash scripts/run-dashboard.sh

# Full stack in one terminal — prefer run-trading + run-dashboard in separate terminals
start:
	@echo "warning: make start runs everything in one process group."
	@echo "  For live bots + FE dev, use: make run-trading  (terminal 1)"
	@echo "                              make run-dashboard (terminal 2)"
	@echo ""
	@bash scripts/start-all.sh

dev-api:
	cd backend && npm run start:dev

dev-fe:
	cd frontend && npm run dev

dev-bots:
	cd bots && PATH="$$HOME/.local/bin:$$PATH" uv run python main.py

# Alias for start (deprecated)
dev: start

db-reset:
	docker compose down -v
	docker compose up -d
	@$(MAKE) wait-db
	@echo "Database reset complete."

wait-db:
	@echo "Waiting for Postgres..."
	@for i in $$(seq 1 60); do \
		if docker compose exec -T postgres pg_isready -U trading -d trading >/dev/null 2>&1; then \
			echo "Postgres is ready."; \
			exit 0; \
		fi; \
		sleep 2; \
	done; \
	echo "Postgres failed to start. Last logs:"; \
	docker compose logs postgres --tail 25; \
	exit 1

# Stop app containers (keeps data volumes)
stop:
	docker compose down

# Export Postgres candles to Parquet for ML training (per instrument/granularity)
export-candles:
	cd bots && PATH="$$HOME/.local/bin:$$PATH" uv run python -m ml.train.export_candles \
		--instrument $(INSTRUMENT) --granularity $(GRANULARITY)

test-oanda:
	cd bots && PATH="$$HOME/.local/bin:$$PATH" uv run python scripts/test_oanda.py

smoke-trade:
	cd bots && PATH="$$HOME/.local/bin:$$PATH" uv run python scripts/smoke_trade.py

diagnose:
	cd bots && PATH="$$HOME/.local/bin:$$PATH" uv run python scripts/bot_diagnose.py
