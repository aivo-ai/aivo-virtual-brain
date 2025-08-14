# AIVO Model Registry Service - Development Makefile
# S2-02 Implementation: Common development tasks

.PHONY: help install dev test lint format clean docker-build docker-up docker-down migrate

# Default target
help: ## Show this help message
	@echo "AIVO Model Registry Service - Available commands:"
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | awk 'BEGIN {FS = ":.*?## "}; {printf "\033[36m%-20s\033[0m %s\n", $$1, $$2}'

# Development setup
install: ## Install Python dependencies
	pip install -r requirements.txt

dev: ## Start development server with auto-reload
	python -m uvicorn app.main:app --host 0.0.0.0 --port 8003 --reload

# Testing
test: ## Run all tests
	pytest tests/ -v

test-cov: ## Run tests with coverage
	pytest tests/ --cov=app --cov-report=html --cov-report=term

test-watch: ## Run tests in watch mode
	pytest tests/ -f

# Code quality
lint: ## Run linting checks
	flake8 app/ tests/
	mypy app/

format: ## Format code with black and isort
	black app/ tests/
	isort app/ tests/

format-check: ## Check code formatting
	black --check app/ tests/
	isort --check-only app/ tests/

# Database operations
migrate: ## Run database migrations
	alembic upgrade head

migrate-generate: ## Generate new migration
	alembic revision --autogenerate -m "$(MESSAGE)"

migrate-downgrade: ## Downgrade one migration
	alembic downgrade -1

db-reset: ## Reset database (WARNING: destructive)
	alembic downgrade base
	alembic upgrade head

# Docker operations
docker-build: ## Build Docker image
	docker build -t aivo-model-registry:latest .

docker-up: ## Start services with Docker Compose
	docker-compose up -d

docker-down: ## Stop services
	docker-compose down

docker-logs: ## View service logs
	docker-compose logs -f model-registry-svc

docker-shell: ## Shell into running container
	docker-compose exec model-registry-svc /bin/bash

# Testing with Docker
docker-test: ## Run tests in Docker environment
	docker-compose -f docker-compose.yml --profile testing up -d test-model-registry-db
	sleep 5
	POSTGRES_PORT=5434 POSTGRES_DB=test_model_registry pytest tests/ -v
	docker-compose --profile testing down

# Database management
db-shell: ## Connect to database shell
	docker-compose exec model-registry-db psql -U postgres -d model_registry

db-backup: ## Backup database
	docker-compose exec model-registry-db pg_dump -U postgres model_registry > backup_$(shell date +%Y%m%d_%H%M%S).sql

db-restore: ## Restore database from backup (set BACKUP_FILE)
	docker-compose exec -T model-registry-db psql -U postgres model_registry < $(BACKUP_FILE)

# Cleanup
clean: ## Clean up temporary files
	find . -type f -name "*.pyc" -delete
	find . -type d -name "__pycache__" -delete
	find . -type d -name "*.egg-info" -exec rm -rf {} +
	rm -rf .pytest_cache
	rm -rf .coverage
	rm -rf htmlcov/
	rm -rf dist/
	rm -rf build/

clean-docker: ## Clean up Docker resources
	docker-compose down -v
	docker system prune -f
	docker volume prune -f

# API documentation
docs: ## Open API documentation
	@echo "API Documentation available at:"
	@echo "  Swagger UI: http://localhost:8003/docs"
	@echo "  ReDoc:      http://localhost:8003/redoc"
	@echo "  OpenAPI:    http://localhost:8003/openapi.json"

# Health check
health: ## Check service health
	curl -f http://localhost:8003/health | jq .

# Load test data
seed-data: ## Load sample test data
	python scripts/seed_data.py

# Performance testing
perf-test: ## Run performance tests
	locust -f tests/performance/locustfile.py --host=http://localhost:8003

# Security scan
security-scan: ## Run security scan
	bandit -r app/
	safety check

# Full CI pipeline
ci: clean format-check lint test ## Run full CI pipeline

# Production deployment helpers
prod-check: ## Pre-production checks
	@echo "Running pre-production checks..."
	python -m app.database --check-connection
	alembic current
	pytest tests/ -x --tb=short

# Monitoring
stats: ## Show service statistics
	curl -s http://localhost:8003/stats | jq .

retention-stats: ## Show retention statistics
	curl -s http://localhost:8003/retention/stats | jq .
