# Stage-2 Verification Guide

## Overview

Stage-2 readiness verification validates the complete system integration including model fabric, learning engines, and data pipelines.

## Quick Start

### Prerequisites

- Node.js 20.19.4
- pnpm 9.11.0
- Docker and Docker Compose
- k6 (for performance tests)

### Local Verification

```bash
# Start all services
pnpm run compose:up

# Wait for services to start (30-60 seconds)
pnpm run health:check

# Run complete Stage-2 verification
pnpm run verify-stage2

# Run performance smoke tests
pnpm run test:performance

# Run complete integration suite
pnpm run test:integration
```

### Individual Components

```bash
# Check service health only
pnpm run health:check

# Run specific verification steps
tsx scripts/verify-stage2.ts --step=enrollment
tsx scripts/verify-stage2.ts --step=assessment
tsx scripts/verify-stage2.ts --step=content

# Performance tests only
k6 run scripts/stage2-performance.js
```

## Verification Steps

### 1. Infrastructure Health

- Docker Compose container status
- Database connectivity (PostgreSQL)
- Message queue health (RabbitMQ)
- Cache system (Redis)
- Search engine (OpenSearch)

### 2. Service Health Checks

- `auth-svc` (port 3001) - Authentication service
- `user-svc` (port 3002) - User management service
- `learner-svc` (port 3003) - Learning analytics service
- `assessment-svc` (port 3004) - Assessment engine
- `slp-svc` (port 3005) - Lesson registry service
- `inference-gateway-svc` (port 3006) - AI inference gateway
- `search-svc` (port 3007) - Search and discovery service

### 3. End-to-End Workflows

#### Student Enrollment Flow

1. **Registration** - New student account creation
2. **Authentication** - JWT token generation and validation
3. **Tenant Assignment** - School/organization assignment
4. **Profile Setup** - Learning preferences and goals

#### Assessment & Learning Flow

1. **Baseline Assessment** - IRT-based skill evaluation
2. **Adaptive Questioning** - Dynamic difficulty adjustment
3. **IEP Generation** - Individualized education plan creation
4. **Progress Tracking** - Learning analytics and milestones

#### Content Generation Flow

1. **Lesson Request** - AI-powered lesson generation
2. **Model Routing** - Provider selection and fallback
3. **Content Creation** - Educational content generation
4. **Approval Workflow** - Quality review and publishing

#### Data Processing Flow

1. **Event Capture** - Learning event recording
2. **Stream Processing** - Real-time event processing
3. **ETL Pipeline** - Data transformation and loading
4. **Analytics** - Metrics calculation and reporting

#### Advanced Workflows

1. **Coursework Analysis** - AI-powered work evaluation
2. **Game Generation** - Educational game creation
3. **Notification System** - Email and alert delivery

### 4. Performance SLOs

- **Inference Gateway**: p95 < 300ms for lesson generation
- **Search Service**: p95 < 100ms for content queries
- **User Service**: p95 < 150ms for profile operations
- **Auth Service**: p95 < 50ms for token validation

## Success Criteria

### Functional Requirements ✅

- [ ] All end-to-end workflows complete successfully
- [ ] No critical errors in application logs
- [ ] All health checks returning green status
- [ ] Data consistency maintained across services

### Performance Requirements ⚡

- [ ] SLO targets met for all critical services
- [ ] Load testing passes at target capacity
- [ ] Memory usage within acceptable limits
- [ ] Database query performance optimized

### Quality Requirements 🔍

- [ ] Test coverage > 80% for critical paths
- [ ] Static code analysis passes
- [ ] Security vulnerability scans clean
- [ ] Documentation up to date

## Troubleshooting

### Common Issues

#### Services Won't Start

```bash
# Check container status
docker-compose ps

# Check service logs
docker-compose logs service-name

# Restart specific service
docker-compose restart service-name
```

#### Performance Tests Failing

```bash
# Check if services are under load
docker stats

# Increase test timeouts
export K6_TIMEOUT=10s

# Run single user test first
k6 run --vus 1 --iterations 1 scripts/stage2-performance.js
```

#### Verification Script Errors

```bash
# Enable debug logging
export DEBUG=true

# Run with verbose output
tsx scripts/verify-stage2.ts --verbose

# Check specific step
tsx scripts/verify-stage2.ts --step=enrollment --debug
```

### Environment Variables

```bash
# Base URL for services (default: http://localhost)
export BASE_URL=http://localhost

# Authentication token (auto-generated if not provided)
export AUTH_TOKEN=your_jwt_token

# Database connection
export DATABASE_URL=postgresql://user:pass@localhost:5432/aivo

# Redis connection
export REDIS_URL=redis://localhost:6379

# OpenSearch connection
export OPENSEARCH_URL=http://localhost:9200
```

## CI/CD Integration

### GitHub Actions

The verification runs automatically on:

- Push to `main` or `develop` branches
- Pull requests to `main`

### Manual CI Trigger

```bash
# Run verification in CI mode
CI=true pnpm run verify-stage2

# Skip interactive prompts
CI=true pnpm run test:integration
```

## Reports and Artifacts

### Verification Report

After running `pnpm run verify-stage2`, a detailed report is generated:

- `stage2-verification-report.json` - Complete verification results
- Console output with step-by-step status
- Performance metrics and timings

### Performance Reports

K6 generates detailed performance reports:

- Response time percentiles (p50, p95, p99)
- Error rates and success rates
- Request rate and throughput
- Custom SLO validation results

## Next Steps

After Stage-2 verification passes:

1. Review the verification report for any warnings
2. Address any performance issues identified
3. Update the Stage-2 checklist as complete
4. Proceed to Stage-3 production deployment preparation

## Support

For issues with Stage-2 verification:

1. Check the troubleshooting section above
2. Review service logs in Docker Compose
3. Run individual verification steps to isolate issues
4. Check the GitHub Actions CI logs for detailed error information
