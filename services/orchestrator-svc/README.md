# AIVO Orchestrator Service (S1-14)

Event-driven orchestration service that consumes educational events and produces intelligent level suggestions and game break triggers.

## Overview

The Orchestrator Service is a core component of the AIVO educational platform that:

- **Consumes Events**: Processes educational events from various services (assessments, coursework, SEL monitoring)
- **Intelligent Decision Making**: Uses rule-based logic to make educational decisions
- **Action Generation**: Produces level suggestions and wellness interventions
- **Multi-Service Integration**: Coordinates actions across learner-svc, notification-svc, and other services

## Architecture

```
Event Sources → Redis Streams → Event Consumer → Orchestration Engine → Action Execution
     ↓                ↓              ↓                    ↓                  ↓
- Assessment-svc   Redis         EventConsumer     OrchestrationEngine   HTTP Clients
- Coursework       Consumer      - EventType       - Rule Logic         - learner-svc
- SEL Monitor      Groups        - Event Data      - Level Decisions     - notification-svc
- Progress         - Scalable    - Action Gen      - Break Scheduling    - Response Tracking
```

## Event Types Supported

### Input Events

- `BASELINE_COMPLETE`: Initial assessment completion with strengths/challenges
- `SLP_UPDATED`: Speech Language Pathology updates requiring accommodation
- `SEL_ALERT`: Social-Emotional Learning alerts requiring intervention
- `COURSEWORK_ANALYZED`: Learning session analysis with performance metrics
- `ASSESSMENT_COMPLETE`: Assessment completion events
- `LEARNER_PROGRESS`: General progress updates
- `ENGAGEMENT_LOW`: Low engagement detection events

### Output Actions

- `LEVEL_SUGGESTED`: Difficulty level adjustments via learner-svc REST API
- `GAME_BREAK`: Wellness break scheduling via notification-svc
- `SEL_INTERVENTION`: Social-emotional interventions
- `LEARNING_PATH_UPDATE`: Personalized learning path modifications

## Rule Engine

### Level Adjustment Rules

- **Level Up**: Performance ≥ 85% OR 5+ consecutive correct answers
- **Level Down**: Performance ≤ 35% OR 3+ consecutive incorrect answers
- **Boundaries**: Respects BEGINNER → ADVANCED difficulty range

### Game Break Scheduling

- **Session Duration**: Break after 25+ minutes of continuous learning
- **Low Engagement**: Immediate break when engagement < 30%
- **Minimum Interval**: 15 minutes between breaks
- **Break Types**: Movement, attention, mindfulness, energizer

### SEL Interventions

- **Alert Threshold**: 2+ alerts within 1 hour timeframe
- **High Severity**: Immediate intervention regardless of count
- **Intervention Types**: Anxiety support, frustration management, confidence building

## Installation

```bash
cd services/orchestrator-svc

# Install dependencies
pip install -r requirements.txt

# Run service
uvicorn app.main:app --reload --port 8080

# Run tests
pytest tests/ -v
```

## Configuration

Environment variables:

```bash
REDIS_URL=redis://localhost:6379
LEARNER_SVC_URL=http://localhost:8001
NOTIFICATION_SVC_URL=http://localhost:8002
LOG_LEVEL=INFO
```

## API Endpoints

### Health and Monitoring

- `GET /health` - Service health check with component status
- `GET /stats` - Orchestration statistics and metrics

### Testing and Development

- `POST /internal/trigger` - Manual event trigger for testing

Example trigger:

```bash
curl -X POST http://localhost:8080/internal/trigger \
  -H "Content-Type: application/json" \
  -d '{
    "type": "BASELINE_COMPLETE",
    "learner_id": "learner-123",
    "tenant_id": "tenant-456",
    "data": {
      "overall_score": 0.75,
      "strengths": ["reading", "math_basics"],
      "challenges": ["writing", "complex_math"]
    }
  }'
```

## Event Processing Flow

1. **Event Ingestion**: Redis streams consumer groups receive events
2. **State Management**: Learner state updated with event data
3. **Rule Evaluation**: OrchestrationEngine processes event through rule engine
4. **Action Generation**: Intelligent actions generated based on rules and state
5. **Action Execution**: HTTP requests sent to target services (learner-svc, notification-svc)
6. **Statistics Tracking**: Metrics updated for monitoring and analytics

## Testing

### Rule Threshold Tests

```bash
# Test level adjustment rules
pytest tests/test_rules.py::TestLevelAdjustmentRules -v

# Test game break scheduling
pytest tests/test_rules.py::TestGameBreakScheduling -v

# Test SEL intervention logic
pytest tests/test_rules.py::TestSELInterventionRules -v
```

### Integration Tests

```bash
# Test full event processing pipeline
pytest tests/test_rules.py::TestStatisticsTracking -v

# Test error handling
pytest tests/test_rules.py::TestErrorHandling -v
```

## Service Integration

### learner-svc Integration

- **Endpoint**: `PUT /api/learners/{learner_id}/level`
- **Payload**: Level suggestion with reasoning and confidence score
- **Response**: Acknowledgment of level update

### notification-svc Integration

- **Endpoint**: `POST /api/notifications/schedule`
- **Payload**: Game break or SEL intervention notification
- **Response**: Scheduled notification confirmation

## Production Considerations

- **Scaling**: Redis consumer groups provide horizontal scaling
- **Reliability**: Event retry logic with exponential backoff
- **Monitoring**: Comprehensive statistics and health checks
- **Error Handling**: Graceful degradation on service unavailability

## Development

### Adding New Event Types

1. Add to `EventType` enum in `consumer.py`
2. Create handler method in `OrchestrationEngine`
3. Add processing logic in `process_event` method
4. Create comprehensive tests in `test_rules.py`

### Adding New Action Types

1. Add to `ActionType` enum in `consumer.py`
2. Create execution method in `EventConsumer`
3. Update statistics tracking in `OrchestrationEngine`
4. Add integration tests for new action execution

## S1-14 Implementation Status ✅

- [x] Event consumption from Redis streams with consumer groups
- [x] Comprehensive rule-based orchestration engine
- [x] Level suggestion logic with performance thresholds
- [x] Game break scheduling with timing and engagement rules
- [x] SEL intervention triggers with severity handling
- [x] Multi-service integration (learner-svc, notification-svc)
- [x] Comprehensive test suite with rule threshold validation
- [x] Statistics tracking and health monitoring
- [x] Production-ready error handling and logging
