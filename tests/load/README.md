# Load Testing with k6

This directory contains comprehensive load testing suites for the AIVO platform services using [k6](https://k6.io/). The tests validate Service Level Objectives (SLOs) and ensure performance standards are maintained across all environments.

## 🎯 Test Suites

### Gateway Service (`gateway-generate.js`)

Tests AI inference endpoints with focus on:

- **Generate Endpoint**: Text generation with various models (GPT-3.5, GPT-4)
- **Embeddings Endpoint**: Text embedding generation
- **SLO Targets**: Generate p95 ≤ 300ms, Embeddings p95 ≤ 200ms

### Assessment Service (`assessment.js`)

Tests assessment functionality including:

- **Answer Recording**: Student answer submissions
- **Assessment Creation**: Creating new assessments
- **Grading**: Automated and manual grading workflows
- **SLO Targets**: Answer p95 ≤ 150ms, Create p95 ≤ 200ms, Grade p95 ≤ 300ms

### Search Service (`search.js`)

Tests search and discovery features:

- **Search Suggestions**: Auto-complete functionality
- **Full-Text Search**: Complex queries with filters
- **Document Indexing**: Adding content to search index
- **SLO Targets**: Suggest p95 ≤ 120ms, Search p95 ≤ 200ms, Index p95 ≤ 500ms

## 🚀 Running Tests

### Quick Start (Local)

```bash
# Make script executable
chmod +x scripts/run-load-tests.sh

# Run smoke tests on all services
./scripts/run-load-tests.sh

# Run load test on specific service
./scripts/run-load-tests.sh load gateway

# Run stress test on all services
./scripts/run-load-tests.sh stress all
```

### Manual k6 Execution

```bash
# Install k6
curl -L https://github.com/grafana/k6/releases/download/v0.47.0/k6-v0.47.0-linux-amd64.tar.gz | tar xz
sudo mv k6-v0.47.0-linux-amd64/k6 /usr/local/bin/

# Run specific test
cd tests/load/k6
BASE_URL=http://localhost:8080 TEST_TYPE=smoke k6 run gateway-generate.js
```

### Using Docker Compose (Test Environment)

```bash
# Start test environment
docker-compose -f docker-compose.test.yml up -d

# Wait for services to be ready
docker-compose -f docker-compose.test.yml ps

# Run tests against local environment
./scripts/run-load-tests.sh smoke all local

# Cleanup
docker-compose -f docker-compose.test.yml down -v
```

## 📊 Test Types

### Smoke Tests (30 seconds)

- **Purpose**: Quick regression detection in CI/CD
- **Load**: 3-8 concurrent users per service
- **Trigger**: Every pull request
- **Failure**: Blocks merge if SLOs violated

### Load Tests (10-15 minutes)

- **Purpose**: Sustained performance validation
- **Load**: 50-100 concurrent users per service
- **Trigger**: Nightly schedule (2 AM UTC)
- **Failure**: Alerts team, doesn't block deployment

### Stress Tests (20-30 minutes)

- **Purpose**: Capacity planning and breaking point discovery
- **Load**: 200-300 concurrent users per service
- **Trigger**: Weekly or manual
- **Failure**: Used for capacity planning

## 🎯 SLO Validation

Each test validates specific Service Level Objectives:

### Response Time SLOs

- **Gateway Generate**: p95 ≤ 300ms
- **Gateway Embeddings**: p95 ≤ 200ms
- **Assessment Answer**: p95 ≤ 150ms
- **Search Suggest**: p95 ≤ 120ms
- **Search Query**: p95 ≤ 200ms

### Reliability SLOs

- **Error Rate**: < 1% for smoke, < 0.5% for load tests
- **Availability**: > 99.9% successful requests
- **Throughput**: Service-specific concurrent user targets

### Build Integration

- **PR Smoke Tests**: SLO violations fail the build
- **Nightly Load Tests**: SLO violations trigger alerts
- **Weekly Stress Tests**: Results used for capacity planning

## 🔧 Configuration

### Environment Variables

```bash
# Required
BASE_URL=http://localhost:8080        # Target environment
API_KEY=your-api-key                  # Authentication token
TENANT_ID=test-tenant                 # Tenant for testing

# Optional
LEARNER_ID=test-learner              # Learner ID for assessment tests
TEST_TYPE=smoke                      # Test scenario (smoke/load/stress)
```

### Test Scenarios

Each test includes multiple scenarios with different load patterns:

```javascript
scenarios: {
  smoke: {
    executor: 'constant-vus',
    vus: 5,
    duration: '30s'
  },
  load: {
    executor: 'ramping-vus',
    stages: [
      { duration: '2m', target: 20 },
      { duration: '5m', target: 50 },
      { duration: '2m', target: 0 }
    ]
  }
}
```

## 📈 Results and Reporting

### Test Outputs

- **JSON Results**: Detailed metrics for analysis
- **Summary Files**: Key performance indicators
- **SLO Reports**: Compliance status for each service
- **Performance Report**: Markdown summary for PRs

### Result Files

```
test-results/
├── 20240820_143022/           # Timestamp directory
│   ├── gateway-results.json   # Raw k6 metrics
│   ├── gateway-summary.json   # Summary statistics
│   ├── gateway-slo-report.json # SLO compliance
│   └── load-test-report.md    # Human-readable report
```

### CI Integration

- **PR Comments**: Automatic performance reports
- **Artifact Upload**: Test results stored for analysis
- **Build Status**: SLO violations fail PR builds
- **Alerting**: Team notifications for SLO breaches

## 🔍 Monitoring Integration

### Prometheus Metrics

Tests expose custom metrics for monitoring:

```javascript
// Custom metrics in tests
export const errorRate = new Rate("errors");
export const generateDuration = new Trend("generate_duration");
export const embeddingsDuration = new Trend("embeddings_duration");
```

### Grafana Dashboards

- **Load Test Dashboard**: Real-time test execution metrics
- **SLO Compliance Dashboard**: Historical SLO tracking
- **Performance Trends**: Long-term performance analysis

## 🛠 Troubleshooting

### Common Issues

#### Test Failures

```bash
# Check service health
curl -f http://localhost:8080/health

# Verify authentication
curl -H "Authorization: Bearer $API_KEY" http://localhost:8080/api/v1/health

# Check test configuration
echo $BASE_URL $API_KEY $TEST_TYPE
```

#### SLO Violations

1. **Review Recent Changes**: Check recent deployments
2. **Resource Utilization**: Monitor CPU, memory, database
3. **External Dependencies**: Verify third-party service health
4. **Network Latency**: Check network conditions
5. **Test Environment**: Ensure test environment is clean

#### CI/CD Issues

```bash
# Debug locally
./scripts/run-load-tests.sh smoke gateway local

# Check Docker environment
docker-compose -f docker-compose.test.yml logs gateway

# Verify service startup
docker-compose -f docker-compose.test.yml ps
```

### Performance Debugging

#### Slow Response Times

1. **Application Profiling**: Use APM tools to identify bottlenecks
2. **Database Queries**: Analyze slow query logs
3. **Resource Constraints**: Check CPU, memory limits
4. **External APIs**: Monitor third-party response times

#### High Error Rates

1. **Error Logs**: Analyze application error patterns
2. **Configuration**: Verify service configuration
3. **Dependencies**: Check database, cache, external service health
4. **Rate Limiting**: Verify no rate limit violations

## 📚 References

### Documentation

- [k6 Documentation](https://k6.io/docs/)
- [k6 Best Practices](https://k6.io/docs/testing-guides/test-types/)
- [SLO Documentation](../docs/slo.md)

### Test Development

- [k6 JavaScript API](https://k6.io/docs/javascript-api/)
- [Custom Metrics](https://k6.io/docs/javascript-api/k6-metrics/)
- [Thresholds](https://k6.io/docs/using-k6/thresholds/)

### CI/CD Integration

- [GitHub Actions k6](https://github.com/marketplace/actions/k6-load-test)
- [k6 Cloud Integration](https://k6.io/docs/cloud/)
- [Performance Testing in CI/CD](https://k6.io/docs/testing-guides/automated-performance-testing/)

## 🚦 SLO Guardrails

The load testing suite enforces SLO compliance through:

1. **Automated Testing**: Every PR runs smoke tests
2. **SLO Validation**: Tests fail if SLOs are violated
3. **Continuous Monitoring**: Nightly load tests track trends
4. **Capacity Planning**: Weekly stress tests inform scaling
5. **Performance Budgets**: Error budgets prevent regressions

This ensures the AIVO platform maintains high performance standards and excellent user experience across all environments.
