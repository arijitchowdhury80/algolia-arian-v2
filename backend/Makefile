.PHONY: dev dev-frontend dev-all test lint typecheck format install migrate infra worker

install:
	uv sync --all-extras

dev:
	uvicorn prism_platform.main:app --reload --host 0.0.0.0 --port 8000

# Frontend dev server — uses node -e workaround because the directory path
# contains ":" characters (COE:PIP) which break pnpm/npm PATH resolution.
# This is the ONLY reliable way to start Next.js from this directory.
# When the project moves to a colon-free path, replace with: cd frontend && pnpm dev
FRONTEND_DIR := $(CURDIR)/frontend
NEXT_BIN := $(shell find $(FRONTEND_DIR)/node_modules -path "*/next/dist/bin/next" -maxdepth 6 2>/dev/null | head -1)

dev-frontend:
	@echo "Clearing .next cache..."
	@rm -rf $(FRONTEND_DIR)/.next
	@echo "Starting Next.js dev server on :3000..."
	@node -e "process.chdir('$(FRONTEND_DIR)'); require('$(NEXT_BIN)');" -- dev --turbopack --port 3000

# Start both backend and frontend together (backend in background)
dev-all:
	@echo "Starting backend on :8000 and frontend on :3000..."
	@uvicorn prism_platform.main:app --reload --host 0.0.0.0 --port 8000 & \
	sleep 2 && $(MAKE) dev-frontend

worker:
	python scripts/start_worker.py

infra:
	docker compose up -d

infra-down:
	docker compose down

migrate:
	alembic upgrade head

test:
	pytest -v

lint:
	ruff check .

format:
	ruff format .

typecheck:
	mypy prism_platform/

check: lint typecheck test
