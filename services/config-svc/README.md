# Feature Flags & Remote Config Service (S4-14)

A comprehensive feature flag and remote configuration service for the AIVO Virtual Brains platform. This service enables controlled rollouts, A/B testing, and runtime configuration management with advanced targeting rules.

## Features

- **Feature Flags**: Boolean, string, number, and JSON flag types
- **Targeting Rules**: Advanced user/context-based targeting with multiple operators
- **Rollout Strategies**: Percentage rollouts, whitelists, blacklists, and hash-based distribution
- **Grade Band Awareness**: K-5, 6-8, 9-12, and adult targeting for educational contexts
- **Tenant & Role Targeting**: Multi-tenant support with role-based access
- **Real-time Evaluation**: Fast flag evaluation with Redis caching
- **TypeScript SDK**: Full-featured client with React hooks
- **Fallback Support**: Graceful degradation when service is unavailable

## Architecture

```
┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│   Web Client    │    │   Mobile App    │    │   Backend Svc   │
│                 │    │                 │    │                 │
│ @aivo/config-   │    │ Config SDK      │    │ SDK/Direct API  │
│ client + React  │    │                 │    │                 │
└─────────┬───────┘    └─────────┬───────┘    └─────────┬───────┘
          │                      │                      │
          └──────────────────────┼──────────────────────┘
                                 │
                    ┌─────────────┼─────────────┐
                    │             │             │
                    │    Config Service         │
                    │    (FastAPI)              │
                    │                           │
                    │  ┌─────────────────────┐  │
                    │  │  Flag Evaluator     │  │
                    │  └─────────────────────┘  │
                    │  ┌─────────────────────┐  │
                    │  │  Targeting Engine   │  │
                    │  └─────────────────────┘  │
                    │  ┌─────────────────────┐  │
                    │  │  Redis Cache        │  │
                    │  └─────────────────────┘  │
                    └─────────────────────────────┘
```

## Quick Start

### 1. Start the Config Service

```bash
cd services/config-svc
pip install -r requirements.txt
uvicorn app.main:app --reload --port 8080
```

### 2. Use in Web Application

```typescript
import { initializeConfigClient, useFlag, FlagGate } from '@aivo/config-client';

// Initialize client
const client = initializeConfigClient({
  baseUrl: 'http://localhost:8080',
  apiKey: 'your-api-key', // Optional
  cacheTtl: 60000, // 1 minute
});

// React component with feature flag
function ChatInterface() {
  const { value: streamingEnabled } = useFlag('chat.streaming', false, {
    userId: 'user123',
    role: 'teacher',
    gradeBand: '6-8'
  });

  return (
    <div>
      {streamingEnabled ? (
        <StreamingChat />
      ) : (
        <StandardChat />
      )}
    </div>
  );
}

// Conditional rendering with gate
function GameSection() {
  return (
    <FlagGate
      flagKey="game.enabled"
      context={{ gradeBand: 'k-5' }}
      fallback={<p>Games not available</p>}
    >
      <EducationalGames />
    </FlagGate>
  );
}
```

### 3. Direct API Usage

```bash
# Evaluate single flag
curl -H "x-user-id: user123" \
     -H "x-role: teacher" \
     -H "x-grade-band: k-5" \
     http://localhost:8080/flags/game.enabled/evaluate

# Evaluate multiple flags
curl -X POST http://localhost:8080/flags/evaluate \
  -H "Content-Type: application/json" \
  -d '{
    "flags": ["chat.streaming", "game.enabled"],
    "context": {
      "userId": "user123",
      "role": "teacher",
      "gradeBand": "k-5"
    }
  }'

# Get all user flags
curl -H "x-user-id: user123" \
     -H "x-role: teacher" \
     http://localhost:8080/flags/user
```

## Feature Flags Configuration

### Default Flags

#### `chat.streaming`

- **Type**: Boolean
- **Description**: Enable streaming responses in AI chat
- **Targeting**: Grade bands 6-8, 9-12, adult only
- **Rollout**: 50% gradual rollout

#### `game.enabled`

- **Type**: Boolean
- **Description**: Enable educational game features
- **Targeting**: K-5 and 6-8 grade bands
- **Rollout**: Full rollout

#### `slp.asrProvider`

- **Type**: String
- **Description**: Speech recognition provider for SLP
- **Variations**:
  - `premium`: azure-speech (for premium tenants)
  - `standard`: whisper (default)
  - `basic`: web-speech
- **Targeting**: Premium tier gets Azure Speech

#### `sel.enabled`

- **Type**: Boolean
- **Description**: Social-Emotional Learning features
- **Targeting**: Teachers and counselors only
- **Rollout**: 30% tenant-based rollout

#### `provider.order`

- **Type**: JSON
- **Description**: AI model provider priority order
- **Variations**:
  - `cost_optimized`: ['azure', 'openai', 'anthropic']
  - `quality_first`: ['anthropic', 'openai', 'azure']
  - `speed_first`: ['openai', 'azure', 'anthropic']

### Targeting Rules

Targeting rules support multiple operators:

- `equals`, `not_equals`: Exact matching
- `in`, `not_in`: List membership
- `contains`, `starts_with`, `ends_with`: String operations
- `greater_than`, `less_than`: Numeric comparisons
- `regex_match`: Regular expression matching

### Context Attributes

Standard context attributes:

- `user_id`: Unique user identifier
- `session_id`: Session identifier
- `tenant_id`: Tenant/organization ID
- `role`: User role (teacher, student, admin, counselor)
- `grade_band`: Educational level (k-5, 6-8, 9-12, adult)
- `tenant_tier`: Subscription tier (basic, premium, enterprise)
- `variation`: Specific variation key
- `custom_attributes`: Additional context data

## API Reference

### Core Endpoints

- `GET /health` - Health check
- `GET /readiness` - Readiness check
- `GET /flags` - List all flags
- `GET /flags/{key}` - Get flag definition
- `GET /flags/{key}/evaluate` - Evaluate single flag
- `POST /flags/evaluate` - Evaluate multiple flags
- `GET /flags/user` - Get all user flags
- `POST /flags/refresh` - Refresh cache

### Configuration Endpoints

- `GET /config/chat` - Chat configuration
- `GET /config/games` - Games configuration
- `GET /config/slp` - SLP configuration
- `GET /config/sel` - SEL configuration

### Request Headers

Use these headers to pass context:

- `x-user-id`: User ID
- `x-session-id`: Session ID
- `x-tenant-id`: Tenant ID
- `x-user-role`: User role
- `x-grade-band`: Grade band
- `x-tenant-tier`: Tenant tier
- `x-variation`: Variation key

## TypeScript SDK

### Installation

```bash
npm install @aivo/config-client
```

### React Integration

```typescript
import { ConfigProvider, useFlag, useFlags, useChatConfig } from '@aivo/config-client/react';

function App() {
  return (
    <ConfigProvider
      client={configClient}
      initialContext={{ userId: 'user123', role: 'teacher' }}
    >
      <MyApp />
    </ConfigProvider>
  );
}

function MyApp() {
  // Single flag
  const { value: gamesEnabled } = useFlag('game.enabled', false);

  // Multiple flags
  const { flags } = useFlags(['chat.streaming', 'sel.enabled']);

  // Specialized config
  const { config: chatConfig } = useChatConfig();

  return (
    <div>
      {gamesEnabled && <GameSection />}
      {flags['sel.enabled'] && <SELFeatures />}
      <Chat streaming={chatConfig.streamingEnabled} />
    </div>
  );
}
```

### Client Methods

```typescript
// Evaluate flags
const value = await client.evaluateFlag("chat.streaming", context);
const flags = await client.evaluateFlags(["flag1", "flag2"], context);

// Get configurations
const chatConfig = await client.getChatConfig(context);
const gamesConfig = await client.getGamesConfig(context);

// List flags
const allFlags = await client.listFlags();
const enabledFlags = await client.listFlags({ enabled: true });

// Cache management
await client.refreshCache();
client.clearCache();
```

## Testing

### Unit Tests

```bash
cd services/config-svc
pytest tests/ -v
```

### Integration Tests

```bash
# Start service first
uvicorn app.main:app --port 8080 &

# Run integration tests
pytest tests/integration/ -v
```

### Load Testing

```bash
# Install artillery
npm install -g artillery

# Run load test
artillery run tests/load/config-service.yml
```

## Deployment

### Docker

```dockerfile
FROM python:3.11-slim

WORKDIR /app
COPY requirements.txt .
RUN pip install -r requirements.txt

COPY app/ ./app/
EXPOSE 8080

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8080"]
```

### Kubernetes

```yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: config-service
spec:
  replicas: 3
  selector:
    matchLabels:
      app: config-service
  template:
    metadata:
      labels:
        app: config-service
    spec:
      containers:
        - name: config-service
          image: aivo/config-service:latest
          ports:
            - containerPort: 8080
          env:
            - name: REDIS_URL
              value: "redis://redis:6379/0"
          resources:
            requests:
              memory: "128Mi"
              cpu: "100m"
            limits:
              memory: "256Mi"
              cpu: "200m"
```

### Environment Variables

- `REDIS_URL`: Redis connection string
- `LOG_LEVEL`: Logging level (DEBUG, INFO, WARNING, ERROR)
- `CACHE_TTL`: Cache TTL in seconds (default: 300)
- `REFRESH_INTERVAL`: Background refresh interval (default: 60)

## Monitoring

### Metrics

The service exposes Prometheus metrics:

- `flag_evaluations_total`: Total flag evaluations
- `flag_evaluation_duration_seconds`: Evaluation latency
- `cache_hits_total`: Cache hit rate
- `active_flags_count`: Number of active flags

### Health Checks

- `/health`: Basic health check
- `/readiness`: Readiness check with flag count

### Logging

Structured logging with correlation IDs:

```json
{
  "timestamp": "2024-01-15T10:30:00Z",
  "level": "INFO",
  "message": "Flag evaluated",
  "flag_key": "chat.streaming",
  "user_id": "user123",
  "value": true,
  "evaluation_time_ms": 2.5
}
```

## Development

### Local Setup

```bash
# Clone repository
git clone https://github.com/aivo/virtual-brains.git
cd virtual-brains/services/config-svc

# Install dependencies
pip install -r requirements.txt
pip install -r requirements-dev.txt

# Start Redis (for caching)
docker run -d -p 6379:6379 redis:alpine

# Run service
uvicorn app.main:app --reload --port 8080
```

### Adding New Flags

1. Update `models.py` default flags
2. Add flag to documentation
3. Update TypeScript SDK types
4. Add integration tests
5. Update configuration endpoints if needed

### Adding New Targeting Rules

1. Add operator to `TargetingOperator` enum
2. Implement evaluation logic in `TargetingRule.evaluate()`
3. Add unit tests
4. Update documentation

## Security

- API key authentication support
- Request validation with Pydantic
- Rate limiting (implement with middleware)
- CORS configuration
- Input sanitization for context attributes

## Performance

- Redis caching with configurable TTL
- Background cache refresh
- Connection pooling
- Async/await throughout
- Efficient flag evaluation algorithms

## License

MIT License - see LICENSE file for details.
