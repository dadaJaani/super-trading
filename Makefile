.PHONY: up down install dev dev-api dev-fe dev-bots db-reset logs

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

dev-api:
	cd backend && npm run start:dev

dev-fe:
	cd frontend && npm run dev

dev-bots:
	cd bots && PATH="$$HOME/.local/bin:$$PATH" uv run python main.py

dev:
	@echo "Starting infrastructure..."
	@$(MAKE) up
	@echo "Starting backend, frontend, and bots..."
	@trap 'kill 0' EXIT; \
		$(MAKE) dev-api & \
		$(MAKE) dev-fe & \
		$(MAKE) dev-bots & \
		wait

db-reset:
	docker compose down -v
	docker compose up -d
	@echo "Waiting for postgres to be ready..."
	@sleep 5
	@echo "Database reset complete."
