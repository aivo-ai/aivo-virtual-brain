# aivo-virtual-brains Makefile
# Local development infrastructure management

.PHONY: help up down restart logs ps clean health init

# Default target
help: ## Show this help message
	@echo 'Usage: make <target>'
	@echo ''
	@echo 'Targets:'
	@awk 'BEGIN {FS = ":.*?## "} /^[a-zA-Z_-]+:.*?## / {printf "  %-15s %s\n", $$1, $$2}' $(MAKEFILE_LIST)

# Core stack management
up: init ## Start all services in detached mode
	docker compose up -d
	@echo "🚀 Development stack is starting..."
	@echo "⏳ Waiting for services to be healthy..."
	@make health

down: ## Stop all services
	docker compose down
	@echo "🛑 Development stack stopped"

restart: down up ## Restart all services

logs: ## Show logs for all services
	docker compose logs -f

logs-service: ## Show logs for specific service (usage: make logs-service SERVICE=postgres)
	docker compose logs -f $(SERVICE)

ps: ## Show running services
	docker compose ps

# Health checks
health: ## Check health of all services
	@echo "🔍 Checking service health..."
	@docker compose ps --format "table {{.Name}}\t{{.Status}}\t{{.Ports}}"
	@echo ""
	@echo "📊 Service endpoints:"
	@echo "  PostgreSQL:     localhost:5432 (user: aivo, db: aivo_dev)"
	@echo "  Redis:          localhost:6379 (password: dev123)"
	@echo "  MinIO:          localhost:9000 (admin/dev123456)"
	@echo "  MinIO Console:  localhost:9001"
	@echo "  Redpanda:       localhost:19092 (Kafka API)"
	@echo "  OpenSearch:     localhost:9200"
	@echo "  Kong Proxy:     localhost:8000"
	@echo "  Kong Admin:     localhost:8001"
	@echo "  Kong GUI:       localhost:8002"
	@echo "  Apollo Router:  localhost:4000"
	@echo "  OTEL Collector: localhost:4317 (gRPC), localhost:4318 (HTTP)"
	@echo "  Jaeger UI:      localhost:16686"
	@echo "  Prometheus:     localhost:9090"
	@echo "  Loki:           localhost:3100"
	@echo "  Grafana:        localhost:3000 (admin/dev123)"

test-endpoints: ## Test key service endpoints
	@echo "🧪 Testing service endpoints..."
	@echo -n "PostgreSQL:     "
	@docker compose exec -T postgres pg_isready -U aivo -d aivo_dev && echo "✅ Healthy" || echo "❌ Unhealthy"
	@echo -n "Redis:          "
	@docker compose exec -T redis redis-cli -a dev123 ping | grep -q PONG && echo "✅ Healthy" || echo "❌ Unhealthy"
	@echo -n "OpenSearch:     "
	@curl -s http://localhost:9200/_cluster/health | grep -q green && echo "✅ Healthy" || echo "❌ Unhealthy"
	@echo -n "Kong Admin:     "
	@curl -s http://localhost:8001/ > /dev/null && echo "✅ Healthy" || echo "❌ Unhealthy"
	@echo -n "Apollo Router:  "
	@curl -s http://localhost:4000/health > /dev/null && echo "✅ Healthy" || echo "❌ Unhealthy"

# Volume management
clean: ## Remove all containers and volumes (⚠️  DESTRUCTIVE)
	@echo "⚠️  This will remove all containers, networks, and volumes"
	@echo "Press Ctrl+C to cancel, Enter to continue..."
	@read
	docker compose down -v --remove-orphans
	docker volume prune -f
	@echo "🧹 Cleaned up all development data"

clean-containers: ## Remove containers only (keep volumes)
	docker compose down --remove-orphans
	@echo "🧹 Removed containers (volumes preserved)"

# Development helpers
pull: ## Pull latest images
	docker compose pull
	@echo "📦 Updated all service images"

build: ## Build custom images (if any)
	docker compose build
	@echo "🔨 Built custom images"

# Initialization
init: ## Create necessary directories and config files
	@echo "🔧 Initializing development infrastructure..."
	@mkdir -p infra/postgres/init
	@mkdir -p infra/kong
	@mkdir -p infra/apollo
	@mkdir -p infra/otel
	@mkdir -p infra/prometheus
	@mkdir -p infra/loki
	@mkdir -p infra/grafana/provisioning/{dashboards,datasources}
	@echo "📁 Created configuration directories"

# Service-specific commands
postgres-shell: ## Connect to PostgreSQL shell
	docker compose exec postgres psql -U aivo -d aivo_dev

redis-shell: ## Connect to Redis shell
	docker compose exec redis redis-cli -a dev123

minio-setup: ## Setup MinIO buckets
	@echo "🪣 Setting up MinIO buckets..."
	@docker compose exec minio mc alias set local http://localhost:9000 minio_admin dev123456
	@docker compose exec minio mc mb local/uploads --ignore-existing
	@docker compose exec minio mc mb local/assets --ignore-existing
	@echo "✅ MinIO buckets created"

# Quick start
dev: up minio-setup ## Start development stack and setup initial data
	@echo "🎉 Development environment ready!"
	@make health
