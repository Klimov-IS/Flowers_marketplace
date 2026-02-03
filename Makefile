# Makefile for common development tasks

.PHONY: help install db-up db-down migrate run test lint format clean

help:  ## Show this help
	@echo "Available commands:"
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | awk 'BEGIN {FS = ":.*?## "}; {printf "  \033[36m%-15s\033[0m %s\n", $$1, $$2}'

install:  ## Install dependencies
	pip install -r requirements.txt

db-up:  ## Start PostgreSQL
	cd infra && docker compose up -d
	@echo "Waiting for database..."
	@sleep 3

db-down:  ## Stop PostgreSQL
	cd infra && docker compose down

db-reset:  ## Reset database (WARNING: deletes all data)
	cd infra && docker compose down -v
	cd infra && docker compose up -d
	@sleep 3
	alembic upgrade head

migrate:  ## Run database migrations
	alembic upgrade head

run:  ## Start API server
	uvicorn apps.api.main:app --reload

test:  ## Run tests
	pytest -v

test-unit:  ## Run unit tests only
	pytest tests/unit/ -v

test-integration:  ## Run integration tests only
	pytest tests/integration/ -v

lint:  ## Lint code
	ruff check .

format:  ## Format code
	black .

clean:  ## Clean temporary files
	find . -type d -name __pycache__ -exec rm -rf {} +
	find . -type d -name .pytest_cache -exec rm -rf {} +
	find . -type d -name .ruff_cache -exec rm -rf {} +
	find . -type f -name "*.pyc" -delete

setup: install db-up migrate  ## Full setup (install + db + migrate)
	@echo "\n✓ Setup complete! You can now run 'make run' to start the API."
