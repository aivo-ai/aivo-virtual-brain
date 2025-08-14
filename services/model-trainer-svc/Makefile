.PHONY: help install test lint format clean dev build run docker-test

# Colors for terminal output
YELLOW := \033[1;33m
GREEN := \033[1;32m
RED := \033[1;31m
NC := \033[0m # No Color

help: ## Show this help message
	@echo '$(YELLOW)Available commands:$(NC)'
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | sort | awk 'BEGIN {FS = ":.*?## "}; {printf "  $(GREEN)%-15s$(NC) %s\n", $$1, $$2}'

install: ## Install dependencies
	@echo '$(YELLOW)Installing dependencies...$(NC)'
	pip install --upgrade pip
	pip install -r requirements.txt

test: ## Run tests
	@echo '$(YELLOW)Running tests...$(NC)'
	python -m pytest tests/ -v --tb=short

test-coverage: ## Run tests with coverage
	@echo '$(YELLOW)Running tests with coverage...$(NC)'
	python -m pytest tests/ -v --cov=app --cov-report=html --cov-report=term

lint: ## Run linting
	@echo '$(YELLOW)Running linting...$(NC)'
	ruff check app tests
	mypy app

format: ## Format code
	@echo '$(YELLOW)Formatting code...$(NC)'
	black app tests
	isort app tests
	ruff format app tests

format-check: ## Check code formatting
	@echo '$(YELLOW)Checking code formatting...$(NC)'
	black --check app tests
	isort --check-only app tests

clean: ## Clean up temporary files
	@echo '$(YELLOW)Cleaning up...$(NC)'
	find . -type f -name "*.pyc" -delete
	find . -type d -name "__pycache__" -delete
	find . -type d -name "*.egg-info" -exec rm -rf {} + 2>/dev/null || true
	rm -rf .coverage htmlcov/ .pytest_cache/

dev: ## Run development server
	@echo '$(YELLOW)Starting development server...$(NC)'
	uvicorn app.main:app --reload --host 0.0.0.0 --port 8003

dev-worker: ## Run development worker
	@echo '$(YELLOW)Starting development worker...$(NC)'
	celery -A app.celery worker --loglevel=info

dev-scheduler: ## Run development scheduler
	@echo '$(YELLOW)Starting development scheduler...$(NC)'
	celery -A app.celery beat --loglevel=info

build: ## Build Docker image
	@echo '$(YELLOW)Building Docker image...$(NC)'
	docker build -t aivo/model-trainer:latest .

run: ## Run with Docker Compose
	@echo '$(YELLOW)Starting services with Docker Compose...$(NC)'
	docker-compose up --build

run-detached: ## Run with Docker Compose in background
	@echo '$(YELLOW)Starting services in background...$(NC)'
	docker-compose up -d --build

stop: ## Stop Docker Compose services
	@echo '$(YELLOW)Stopping services...$(NC)'
	docker-compose down

docker-test: ## Run tests in Docker
	@echo '$(YELLOW)Running tests in Docker...$(NC)'
	docker-compose exec trainer python -m pytest tests/ -v

logs: ## View service logs
	@echo '$(YELLOW)Viewing logs...$(NC)'
	docker-compose logs -f trainer

db-upgrade: ## Run database migrations
	@echo '$(YELLOW)Running database migrations...$(NC)'
	alembic upgrade head

db-revision: ## Create new database revision
	@echo '$(YELLOW)Creating new database revision...$(NC)'
	@read -p "Enter revision message: " message; \
	alembic revision --autogenerate -m "$$message"

seed-data: ## Seed database with test data
	@echo '$(YELLOW)Seeding database with test data...$(NC)'
	python scripts/seed_data.py

health: ## Check service health
	@echo '$(YELLOW)Checking service health...$(NC)'
	curl -f http://localhost:8003/health || echo "$(RED)Service is not healthy$(NC)"

stats: ## Get service statistics
	@echo '$(YELLOW)Getting service statistics...$(NC)'
	curl -s http://localhost:8003/stats | python -m json.tool

pre-commit: format lint test ## Run pre-commit checks
	@echo '$(GREEN)Pre-commit checks passed!$(NC)'

ci-test: format-check lint test ## Run CI tests
	@echo '$(GREEN)CI tests passed!$(NC)'
