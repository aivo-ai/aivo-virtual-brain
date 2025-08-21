# Admin Service Development Scripts

# Start development server
start-dev:
	uvicorn app.main:app --reload --host 0.0.0.0 --port 8020

# Install dependencies
install:
	pip install -r requirements.txt

# Run tests
test:
	pytest test_admin_service.py -v

# Run linting
lint:
	black app/ --check
	isort app/ --check-only
	flake8 app/
	mypy app/

# Format code
format:
	black app/
	isort app/

# Run with docker
docker-build:
	docker build -t aivo-admin-svc .

docker-run:
	docker run -p 8020:8000 --env-file .env aivo-admin-svc

# Database operations
db-init:
	python -c "import asyncio; from app.database import init_db; asyncio.run(init_db())"

# Generate test token
test-token:
	python -c "from app.auth import generate_jwt_token; print(generate_jwt_token('test_admin', 'admin@test.com', ['staff', 'tenant_admin']))"

# Clean up
clean:
	find . -type d -name __pycache__ -exec rm -rf {} +
	find . -type f -name "*.pyc" -delete

# Help
help:
	@echo "Available commands:"
	@echo "  start-dev     - Start development server"
	@echo "  install       - Install dependencies"
	@echo "  test          - Run tests"
	@echo "  lint          - Run code quality checks"
	@echo "  format        - Format code"
	@echo "  docker-build  - Build Docker image"
	@echo "  docker-run    - Run with Docker"
	@echo "  db-init       - Initialize database"
	@echo "  test-token    - Generate test JWT token"
	@echo "  clean         - Clean up Python cache files"

.PHONY: start-dev install test lint format docker-build docker-run db-init test-token clean help
