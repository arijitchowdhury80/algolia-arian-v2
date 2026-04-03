#!/usr/bin/env bash
# ============================================================================
# scaffold-project.sh — Standard Project Initializer
# Creates the full project structure, CLAUDE.md, Makefile, and starter files.
#
# Usage:
#   ./scaffold-project.sh <project-name> [--with-frontend] [--with-temporal]
#
# Examples:
#   ./scaffold-project.sh pip --with-frontend --with-temporal
#   ./scaffold-project.sh algolia-coe-site --with-frontend
#   ./scaffold-project.sh data-pipeline
# ============================================================================

set -euo pipefail

RED='\033[0;31m'
GREEN='\033[0;32m'
BLUE='\033[0;34m'
BOLD='\033[1m'
NC='\033[0m'

if [ $# -lt 1 ]; then
    echo -e "${RED}Usage: ./scaffold-project.sh <project-name> [--with-frontend] [--with-temporal]${NC}"
    exit 1
fi

PROJECT_NAME="$1"
PACKAGE_NAME=$(echo "$PROJECT_NAME" | tr '-' '_')
WITH_FRONTEND=false
WITH_TEMPORAL=false

shift
while [[ $# -gt 0 ]]; do
    case $1 in
        --with-frontend) WITH_FRONTEND=true; shift ;;
        --with-temporal) WITH_TEMPORAL=true; shift ;;
        *) echo "Unknown arg: $1"; exit 1 ;;
    esac
done

echo -e "${BOLD}═══════════════════════════════════════════════════════${NC}"
echo -e "${BOLD}  Scaffolding: $PROJECT_NAME${NC}"
echo -e "${BOLD}═══════════════════════════════════════════════════════${NC}"
echo ""

# ── Create Directory Structure ──────────────────────────────────────────────

mkdir -p "$PROJECT_NAME"
cd "$PROJECT_NAME"

# Docs
mkdir -p docs/decisions docs/specs docs/research docs/source-docs docs/user-guide docs/runbooks

# Backend source
mkdir -p "src/$PACKAGE_NAME/core" "src/$PACKAGE_NAME/api/routers" "src/$PACKAGE_NAME/db" "src/$PACKAGE_NAME/services" "src/$PACKAGE_NAME/modules"
touch "src/$PACKAGE_NAME/__init__.py" "src/$PACKAGE_NAME/core/__init__.py" "src/$PACKAGE_NAME/api/__init__.py" "src/$PACKAGE_NAME/api/routers/__init__.py" "src/$PACKAGE_NAME/db/__init__.py" "src/$PACKAGE_NAME/services/__init__.py" "src/$PACKAGE_NAME/modules/__init__.py"

# Scripts
mkdir -p src/scripts

# Tests
mkdir -p tests/unit tests/integration tests/e2e
touch tests/__init__.py tests/unit/__init__.py tests/integration/__init__.py tests/e2e/__init__.py

# Data
mkdir -p data/fixtures data/seeds data/exports

# Temporal (if requested)
if [ "$WITH_TEMPORAL" = true ]; then
    mkdir -p "src/$PACKAGE_NAME/orchestrator"
    touch "src/$PACKAGE_NAME/orchestrator/__init__.py"
fi

# Frontend (if requested)
if [ "$WITH_FRONTEND" = true ]; then
    mkdir -p frontend/src/app frontend/src/components frontend/src/api frontend/src/hooks frontend/src/lib frontend/public
fi

# Alembic
mkdir -p alembic/versions

# GitHub
mkdir -p .github/workflows

echo -e "${GREEN}✓ Directory structure created${NC}"

# ── Create CLAUDE.md (Project-Specific) ─────────────────────────────────────

cat > CLAUDE.md << 'CLAUDEMD'
# CLAUDE.md — Project-Specific Instructions

## Project Overview
<!-- Update this section with project-specific context -->
Project: {PROJECT_NAME}
Description: {TODO: One-line description}
Tech Stack: Python 3.12, FastAPI, PostgreSQL, Redis, Pydantic v2

## Quick Start
```bash
# Start infrastructure
docker compose up -d

# Install dependencies
uv sync

# Run migrations
alembic upgrade head

# Start the application
make dev

# Run tests
make test
```

## Current Phase
<!-- Update this as you progress through phases -->
Phase: 0 — Foundation
Status: Starting
Next task: Read docs/specs/ for the current phase specification

## Key Files to Read First
1. This CLAUDE.md
2. docs/specs/ — current phase specification
3. src/{PACKAGE_NAME}/core/types.py — core contracts
4. src/{PACKAGE_NAME}/core/module.py — module interface
5. docs/decisions/ — all prior decisions

## Project-Specific Rules
<!-- Add any rules specific to this project -->
- TODO: Add project-specific rules here

## Session Log
Check docs/decisions/session-log-*.md for what happened in previous sessions.
CLAUDEMD

# Replace placeholders
sed -i '' "s/{PROJECT_NAME}/$PROJECT_NAME/g" CLAUDE.md 2>/dev/null || sed -i "s/{PROJECT_NAME}/$PROJECT_NAME/g" CLAUDE.md
sed -i '' "s/{PACKAGE_NAME}/$PACKAGE_NAME/g" CLAUDE.md 2>/dev/null || sed -i "s/{PACKAGE_NAME}/$PACKAGE_NAME/g" CLAUDE.md

echo -e "${GREEN}✓ CLAUDE.md created${NC}"

# ── Create Makefile ─────────────────────────────────────────────────────────

cat > Makefile << 'MAKEFILE'
.PHONY: dev test lint typecheck format migrate scaffold-module clean

# Start development server
dev:
	uvicorn src.$(PACKAGE).main:app --reload --host 0.0.0.0 --port 8000

# Run all tests
test:
	pytest -v

# Run unit tests only (fast)
test-unit:
	pytest tests/unit/ -v

# Run integration tests
test-integration:
	pytest tests/integration/ -v

# Lint and format check
lint:
	ruff check .
	ruff format --check .

# Type check
typecheck:
	mypy src/ --strict

# Auto-format code
format:
	ruff format .
	ruff check --fix .

# Run database migrations
migrate:
	alembic upgrade head

# Create a new migration
migration:
	@read -p "Migration message: " msg; alembic revision --autogenerate -m "$$msg"

# Full quality check (run before any PR or completion claim)
check: lint typecheck test
	@echo "✓ All checks passed"

# Clean generated files
clean:
	find . -type d -name __pycache__ -exec rm -rf {} + 2>/dev/null || true
	find . -type f -name "*.pyc" -delete 2>/dev/null || true
	rm -rf .pytest_cache .mypy_cache .ruff_cache htmlcov
MAKEFILE

# Replace package name placeholder
sed -i '' "s/\$(PACKAGE)/$PACKAGE_NAME/g" Makefile 2>/dev/null || sed -i "s/\$(PACKAGE)/$PACKAGE_NAME/g" Makefile

echo -e "${GREEN}✓ Makefile created${NC}"

# ── Create .env.example ────────────────────────────────────────────────────

cat > .env.example << 'ENVFILE'
# Database
DATABASE_URL=postgresql+asyncpg://pip:pip_dev_password@localhost:5432/pip

# Redis
REDIS_URL=redis://localhost:6379

# API Keys (get these from the respective services)
ANTHROPIC_API_KEY=
BUILTWITH_API_KEY=
SIMILARWEB_API_KEY=
APIFY_TOKEN=
TAVILY_API_KEY=

# Temporal
TEMPORAL_HOST=localhost:7233
TEMPORAL_NAMESPACE=default

# Application
APP_ENV=development
LOG_LEVEL=INFO
ENVFILE

echo -e "${GREEN}✓ .env.example created${NC}"

# ── Create .gitignore ──────────────────────────────────────────────────────

cat > .gitignore << 'GITIGNORE'
# Python
__pycache__/
*.py[cod]
*.egg-info/
dist/
build/
.venv/
.mypy_cache/
.pytest_cache/
.ruff_cache/
htmlcov/
.coverage

# Environment
.env
.env.local
.env.production

# Node
node_modules/
frontend/node_modules/
.next/

# IDE
.vscode/
.idea/
*.swp
*.swo
.DS_Store

# Data
data/exports/*
!data/exports/.gitkeep

# Docker
*.log
GITIGNORE

echo -e "${GREEN}✓ .gitignore created${NC}"

# ── Create docker-compose.yml ──────────────────────────────────────────────

cat > docker-compose.yml << 'DOCKER'
services:
  postgres:
    image: postgres:16-alpine
    environment:
      POSTGRES_DB: pip
      POSTGRES_USER: pip
      POSTGRES_PASSWORD: pip_dev_password
    ports:
      - "5432:5432"
    volumes:
      - pgdata:/var/lib/postgresql/data
    healthcheck:
      test: ["CMD-SHELL", "pg_isready -U pip"]
      interval: 5s
      timeout: 5s
      retries: 5

  redis:
    image: redis:7-alpine
    ports:
      - "6379:6379"
    healthcheck:
      test: ["CMD", "redis-cli", "ping"]
      interval: 5s
      timeout: 5s
      retries: 5

volumes:
  pgdata:
DOCKER

echo -e "${GREEN}✓ docker-compose.yml created${NC}"

# ── Create conftest.py ─────────────────────────────────────────────────────

cat > tests/conftest.py << 'CONFTEST'
"""Shared test fixtures for all test types."""

import pytest


@pytest.fixture
def sample_domain():
    """Test domain — brooks.com is our standard test target."""
    return "brooks.com"


@pytest.fixture
def sample_company_name():
    return "Brooks Running"
CONFTEST

echo -e "${GREEN}✓ Test conftest created${NC}"

# ── Create README.md ───────────────────────────────────────────────────────

cat > README.md << README
# $PROJECT_NAME

## Quick Start

\`\`\`bash
# Start infrastructure
docker compose up -d

# Install Python dependencies
uv sync

# Copy environment file and fill in API keys
cp .env.example .env

# Run database migrations
make migrate

# Start development server
make dev

# Run tests
make test

# Full quality check
make check
\`\`\`

## Project Structure

See CLAUDE.md for the full directory layout and development workflow.

## Documentation

All documentation lives in \`docs/\`:
- \`docs/specs/\` — Technical specifications
- \`docs/decisions/\` — Architectural Decision Records
- \`docs/research/\` — Market research and competitive analysis
- \`docs/user-guide/\` — End-user documentation
README

echo -e "${GREEN}✓ README.md created${NC}"

# ── Create gitkeep files for empty dirs ─────────────────────────────────────

touch data/exports/.gitkeep
touch docs/decisions/.gitkeep
touch docs/specs/.gitkeep
touch docs/research/.gitkeep
touch docs/source-docs/.gitkeep
touch docs/user-guide/.gitkeep
touch docs/runbooks/.gitkeep
touch alembic/versions/.gitkeep

# ── Create ADR template ────────────────────────────────────────────────────

cat > docs/decisions/000-template.md << 'ADR'
# ADR-{NNN}: {Title}

**Date:** {YYYY-MM-DD}
**Status:** Proposed | Accepted | Deprecated | Superseded
**Deciders:** {who was involved}

## Context
{Why this decision was needed. What problem are we solving?}

## Decision
{What we decided to do.}

## Alternatives Considered
{What else we evaluated and why we rejected it.}

## Consequences
{What this means going forward. Both positive and negative.}
ADR

echo -e "${GREEN}✓ ADR template created${NC}"

# ── Summary ─────────────────────────────────────────────────────────────────

echo ""
echo -e "${BOLD}═══════════════════════════════════════════════════════${NC}"
echo -e "${BOLD}  ✓ Project scaffolded: $PROJECT_NAME${NC}"
echo -e "${BOLD}═══════════════════════════════════════════════════════${NC}"
echo ""
echo -e "  ${BLUE}Next steps:${NC}"
echo -e "  1. cd $PROJECT_NAME"
echo -e "  2. Copy the global CLAUDE.md to ~/.claude/CLAUDE.md"
echo -e "  3. Update CLAUDE.md with project-specific details"
echo -e "  4. cp .env.example .env && fill in API keys"
echo -e "  5. docker compose up -d"
echo -e "  6. Start building — read docs/specs/ for the current phase spec"
echo ""
