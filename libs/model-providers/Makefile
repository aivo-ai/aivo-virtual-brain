# Makefile for AIVO Model Providers library

.PHONY: help install install-dev test test-cov lint format type-check clean build examples

# Default target
help:
	@echo "AIVO Model Providers Library"
	@echo "Available targets:"
	@echo "  install      - Install the package"
	@echo "  install-dev  - Install with development dependencies"
	@echo "  test         - Run tests"
	@echo "  test-cov     - Run tests with coverage"
	@echo "  lint         - Run linting checks"
	@echo "  format       - Format code with black and isort"
	@echo "  type-check   - Run mypy type checking"
	@echo "  clean        - Clean build artifacts"
	@echo "  build        - Build the package"
	@echo "  examples     - Run example usage"

# Installation
install:
	pip install -e .

install-dev:
	pip install -e ".[test]"

# Testing
test:
	pytest -v

test-cov:
	pytest --cov=aivo_model_providers --cov-report=html --cov-report=term-missing

# Code quality
lint:
	black --check .
	isort --check-only .
	flake8 aivo_model_providers tests

format:
	black .
	isort .

type-check:
	mypy aivo_model_providers

# Build and distribution
clean:
	rm -rf build/
	rm -rf dist/
	rm -rf *.egg-info/
	find . -type d -name __pycache__ -exec rm -rf {} +
	find . -type f -name "*.pyc" -delete

build: clean
	python -m build

# Examples
examples:
	python examples.py

# Development workflow
dev-setup: install-dev
	@echo "Development environment setup complete!"
	@echo "Run 'make test' to run tests"
	@echo "Run 'make examples' to run examples"

# CI/CD helpers  
ci-test: install-dev
	pytest --cov=aivo_model_providers --cov-report=xml --junitxml=test-results.xml

ci-lint:
	black --check .
	isort --check-only .
	mypy aivo_model_providers
