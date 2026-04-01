.PHONY: help up down build logs pki migrate agent-build agent-installer test clean

help:
	@echo "UEM Platform - Available Targets"
	@echo ""
	@echo "  make up              Start the full stack (docker compose up)"
	@echo "  make down            Stop all services"
	@echo "  make build           Build all Docker images"
	@echo "  make logs            Tail all service logs"
	@echo "  make pki             Generate CA + server certificates"
	@echo "  make migrate         Run Alembic database migrations"
	@echo "  make agent-build     Build the Windows agent exe (requires Wine or Windows)"
	@echo "  make agent-installer Build NSIS installer for the agent"
	@echo "  make test            Run backend tests"
	@echo "  make clean           Remove containers and volumes"
	@echo ""

# ── Stack management ────────────────────────────────────────
up:
	docker compose up -d

down:
	docker compose down

build:
	docker compose build

logs:
	docker compose logs -f

restart:
	docker compose restart

# ── PKI ─────────────────────────────────────────────────────
pki:
	@echo "Generating PKI certificates..."
	bash pki/gen_ca.sh
	bash pki/gen_server_cert.sh
	@echo "Certificates generated in pki/ca/"

# ── Database ─────────────────────────────────────────────────
migrate:
	docker compose exec backend alembic upgrade head

migrate-gen:
	docker compose exec backend alembic revision --autogenerate -m "$(MSG)"

migrate-down:
	docker compose exec backend alembic downgrade -1

# ── Agent Build ───────────────────────────────────────────────
agent-build:
	@echo "Building Windows agent executable..."
	cd agent && python build_installer.py --target exe

agent-installer:
	@echo "Building Windows MSI/NSIS installer..."
	cd agent && python build_installer.py --target installer

# ── Testing ───────────────────────────────────────────────────
test:
	docker compose exec backend pytest tests/ -v --tb=short

test-local:
	cd server/backend && python -m pytest tests/ -v --tb=short

# ── Development ───────────────────────────────────────────────
dev:
	docker compose -f docker-compose.yml -f docker-compose.dev.yml up

shell-backend:
	docker compose exec backend bash

shell-db:
	docker compose exec postgres psql -U uem -d uem

# ── Cleanup ───────────────────────────────────────────────────
clean:
	docker compose down -v --remove-orphans
	find . -name "__pycache__" -type d -exec rm -rf {} + 2>/dev/null || true
	find . -name "*.pyc" -delete 2>/dev/null || true
