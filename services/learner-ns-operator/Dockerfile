FROM python:3.11-slim

# Security: Create non-root user
RUN groupadd -g 10001 operator && \
    useradd -u 10001 -g operator -d /app -s /bin/bash operator

# Install system dependencies
RUN apt-get update && \
    apt-get install -y --no-install-recommends \
        ca-certificates \
        curl \
    && rm -rf /var/lib/apt/lists/*

# Create app directory
WORKDIR /app

# Copy requirements and install Python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY main.py handlers.py ./

# Create necessary directories
RUN mkdir -p /tmp && \
    chown -R operator:operator /app /tmp

# Security: Switch to non-root user
USER operator

# Health check
HEALTHCHECK --interval=30s --timeout=5s --start-period=30s --retries=3 \
  CMD curl -f http://localhost:8080/healthz || exit 1

# Expose health check port
EXPOSE 8080

# Run the operator
CMD ["python3", "main.py"]
