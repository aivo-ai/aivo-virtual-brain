# Docker development environment for AIVO Model Providers

FROM python:3.11-slim

WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    build-essential \
    curl \
    git \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements
COPY pyproject.toml ./
COPY README.md ./

# Install Python dependencies
RUN pip install --no-cache-dir -e ".[test]"

# Copy source code
COPY aivo_model_providers/ ./aivo_model_providers/
COPY tests/ ./tests/
COPY examples.py ./
COPY Makefile ./

# Set environment variables for development
ENV PYTHONPATH=/app
ENV PYTHONUNBUFFERED=1

# Default command
CMD ["python", "-m", "pytest", "-v"]
