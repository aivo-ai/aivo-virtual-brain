# FinOps Service

The FinOps service provides comprehensive cost metering and budget management for AI inference operations across the AIVO platform. It tracks costs per service, tenant, learner, and model while providing real-time budget alerts and cost optimization suggestions.

## Features

- **Multi-Provider Cost Tracking**: Supports OpenAI, Google Gemini, and AWS Bedrock
- **Granular Budgeting**: Per-service, per-tenant, per-learner, and global budgets
- **Real-time Monitoring**: Budget alerts with configurable thresholds
- **Cost Optimization**: Automated suggestions for reducing AI inference costs
- **Multi-channel Alerts**: Email, Slack, webhooks, and SMS notifications
- **Automatic Pricing Updates**: Keeps provider pricing data current

## Architecture

### Core Components

- **Cost Calculator**: Multi-provider cost calculation engine
- **Budget Monitor**: Real-time budget tracking and alerting
- **Alert Manager**: Multi-channel notification system
- **Pricing Updater**: Automatic provider pricing updates
- **Authentication**: JWT-based auth with role-based access control

### Database Schema

- `usage_events`: Individual AI inference events with costs
- `budgets`: Budget definitions and current status
- `budget_alerts`: Alert history and configurations
- `provider_pricing`: Current pricing data from AI providers
- `cost_summaries`: Aggregated cost data for reporting

## API Endpoints

### Usage Events

- `POST /usage-events` - Record new usage event
- `GET /usage-events` - Query usage events with filters
- `GET /usage-events/{event_id}` - Get specific usage event

### Cost Queries

- `GET /costs/query` - Query costs with flexible filters
- `GET /costs/summary` - Get cost summaries by period
- `GET /costs/by-service` - Get costs grouped by service
- `GET /costs/by-learner` - Get costs grouped by learner
- `GET /costs/optimization-suggestions` - Get cost optimization suggestions

### Budget Management

- `POST /budgets` - Create new budget
- `GET /budgets` - List budgets with filters
- `GET /budgets/{budget_id}` - Get specific budget
- `PUT /budgets/{budget_id}` - Update budget
- `DELETE /budgets/{budget_id}` - Delete budget
- `GET /budgets/{budget_id}/status` - Get budget status

### Alerts

- `GET /alerts` - List budget alerts
- `GET /alerts/{alert_id}` - Get specific alert
- `POST /alerts/test` - Test alert channels

### Health & Monitoring

- `GET /health` - Service health check
- `GET /metrics` - Prometheus metrics

## Configuration

The service is configured via environment variables:

### Database

- `DATABASE_URL`: PostgreSQL connection URL
- `DATABASE_POOL_SIZE`: Connection pool size (default: 10)
- `DATABASE_MAX_OVERFLOW`: Max overflow connections (default: 20)

### Authentication

- `JWT_SECRET`: JWT signing secret
- `JWT_ALGORITHM`: JWT algorithm (default: HS256)
- `JWT_EXPIRATION_MINUTES`: Token expiration (default: 60)

### Alert Channels

- `SLACK_WEBHOOK_URL`: Slack webhook for alerts
- `SENDGRID_API_KEY`: SendGrid API key for email alerts
- `TWILIO_ACCOUNT_SID`: Twilio SID for SMS alerts
- `TWILIO_AUTH_TOKEN`: Twilio auth token
- `TWILIO_FROM_NUMBER`: Twilio sender number

### Provider APIs

- `OPENAI_API_KEY`: OpenAI API key for pricing updates
- `GOOGLE_APPLICATION_CREDENTIALS`: Google credentials for Gemini pricing
- `AWS_ACCESS_KEY_ID`: AWS access key for Bedrock pricing
- `AWS_SECRET_ACCESS_KEY`: AWS secret key

### Monitoring

- `PROMETHEUS_METRICS_ENABLED`: Enable Prometheus metrics (default: true)
- `BUDGET_CHECK_INTERVAL`: Budget check interval in seconds (default: 300)
- `COST_AGGREGATION_INTERVAL`: Cost aggregation interval in seconds (default: 3600)

## Deployment

### Docker

```bash
cd services/finops-svc
docker build -t finops-svc .
docker run -p 8080:8080 --env-file .env finops-svc
```

### Kubernetes

```bash
kubectl apply -f k8s/
```

### Local Development

```bash
cd services/finops-svc
pip install -r requirements.txt
uvicorn app.main:app --reload --port 8080
```

## Monitoring

The service provides comprehensive monitoring through:

- **Prometheus Metrics**: Cost, budget, and performance metrics
- **Health Checks**: Database and external service health
- **Structured Logging**: JSON logs with correlation IDs
- **Grafana Dashboard**: Pre-built FinOps visualization dashboard

### Key Metrics

- `finops_total_cost_usd`: Total costs across all providers
- `finops_cost_by_provider_usd`: Costs by AI provider
- `finops_cost_by_service_usd`: Costs by service
- `finops_cost_by_learner_usd`: Costs by learner
- `finops_budget_percentage_used`: Budget utilization percentage
- `finops_budget_alerts_active`: Active budget alerts
- `finops_tokens_total`: Token usage by model

## Testing

Run the test suite:

```bash
cd services/finops-svc
pytest tests/ -v
```

Test coverage:

```bash
pytest tests/ --cov=app --cov-report=html
```

## Provider Integration

### OpenAI

- Tracks GPT-3.5, GPT-4, and embedding model usage
- Automatic pricing updates from OpenAI API
- Input/output token cost calculation

### Google Gemini

- Supports Gemini Pro and Gemini Pro Vision
- Character-based pricing model
- Image processing cost calculation

### AWS Bedrock

- Claude, Llama, and Titan model support
- Input/output token pricing
- Region-specific pricing

## Cost Optimization

The service provides automated cost optimization suggestions:

- **Model Selection**: Recommends cheaper models for similar tasks
- **Batch Processing**: Suggests batching for efficiency
- **Token Optimization**: Identifies excessive token usage
- **Provider Switching**: Compares costs across providers
- **Usage Patterns**: Analyzes usage for optimization opportunities

## Security

- **Authentication**: JWT-based authentication required for all endpoints
- **Authorization**: Role-based access control (admin, tenant-admin, user)
- **Data Isolation**: Tenant-based data segregation
- **Audit Logging**: Complete audit trail of all operations
- **Input Validation**: Comprehensive request validation
- **Rate Limiting**: Configurable rate limits per endpoint

## API Documentation

Complete OpenAPI documentation is available at:

- Swagger UI: `http://localhost:8080/docs`
- ReDoc: `http://localhost:8080/redoc`
- OpenAPI JSON: `http://localhost:8080/openapi.json`

## Support

For issues and support:

- Check logs: `kubectl logs -f deployment/finops-svc`
- Health endpoint: `GET /health`
- Metrics endpoint: `GET /metrics`
- Documentation: `/docs`
