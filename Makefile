# Makefile for lseg-toolkit development

.PHONY: help test test-quick lint format check ci-local clean install install-hooks

CI_LOCAL_VENV ?= /tmp/jl-lseg-ci-venv

help:  ## Show this help message
	@echo "Available commands:"
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | sort | awk 'BEGIN {FS = ":.*?## "}; {printf "  \033[36m%-15s\033[0m %s\n", $$1, $$2}'

install:  ## Install dependencies via uv
	uv sync

install-hooks:  ## Install git pre-commit hooks for this clone
	uv run --group test pre-commit install

test:  ## Run all tests
	uv run pytest tests/ -v

test-quick:  ## Run tests without coverage
	uv run pytest tests/ -q --tb=short --no-cov

lint:  ## Check code quality with ruff (no fixes)
	uv run ruff check src/ tests/

format:  ## Auto-format code with ruff
	uv run ruff check src/ tests/ --fix
	uv run ruff format src/ tests/

check:  ## Run all checks before commit (lint + format + tests)
	@echo "==> Running ruff linter..."
	uv run ruff check src/ tests/ --fix
	@echo ""
	@echo "==> Running ruff formatter..."
	uv run ruff format src/ tests/
	@echo ""
	@echo "==> Running tests..."
	uv run pytest tests/ -q --tb=short
	@echo ""
	@echo "All checks passed! Safe to commit."

ci-local:  ## Mirror Woodpecker CI locally using a frozen test-only environment
	@echo "==> Syncing frozen lint/typecheck environment at $(CI_LOCAL_VENV)..."
	UV_PROJECT_ENVIRONMENT=$(CI_LOCAL_VENV) uv sync --frozen --only-group test
	@echo ""
	@echo "==> Running ruff linter..."
	$(CI_LOCAL_VENV)/bin/ruff check src/ tests/
	@echo ""
	@echo "==> Running ruff formatter check..."
	$(CI_LOCAL_VENV)/bin/ruff format --check src/ tests/
	@echo ""
	@echo "==> Running mypy..."
	MYPYPATH=src $(CI_LOCAL_VENV)/bin/mypy src/
	@echo ""
	@echo "==> Syncing frozen test environment..."
	UV_PROJECT_ENVIRONMENT=$(CI_LOCAL_VENV) uv sync --frozen
	@echo ""
	@echo "==> Running unit-test CI suite..."
	$(CI_LOCAL_VENV)/bin/pytest tests/ -m "not integration" --no-cov -v
	@echo ""
	@echo "Local CI mirror passed."

clean:  ## Remove generated files
	find . -type d -name __pycache__ -exec rm -rf {} + 2>/dev/null || true
	find . -type f -name "*.pyc" -delete
	rm -rf .pytest_cache htmlcov .coverage
	rm -rf build dist *.egg-info

.DEFAULT_GOAL := help
