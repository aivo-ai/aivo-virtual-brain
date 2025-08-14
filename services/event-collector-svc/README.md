# Event Collector Service (S2-14)

High-throughput event ingestion service for batch processing and Kafka integration with fault tolerance and backpressure handling.

## 🎯 Features

- **Batch Event Ingestion**: HTTP POST endpoint supporting 1-1000 events per batch
- **Gzip Compression**: Automatic decompression of gzipped payloads for bandwidth efficiency
- **Kafka Integration**: Reliable event streaming with learner_id partitioning
- **Dead Letter Queue**: Poison pill and retry failure handling
- **Disk Buffering**: 30-minute outage tolerance with local storage
- **Backpressure Handling**: Graceful degradation under high load
- **Performance Monitoring**: Comprehensive metrics and health checks

## 📊 Performance Targets

- **Throughput**: 2,000 events per second (EPS)
- **Latency**: p99 ≤ 40ms processing time
- **Availability**: 30-minute buffer tolerance for Kafka outages
- **Batch Size**: 1-1000 events per request

## 🏗️ Architecture

```
Client → HTTP/gRPC → Event Validation → Kafka Producer
                           ↓
                    Disk Buffer ← Backpressure
                           ↓
                      Dead Letter Queue
```

### Components

- **HTTP Router**: FastAPI endpoint for batch collection (`/api/v1/collect`)
- **Event Schemas**: Pydantic V2 models for validation
- **Kafka Writer**: Async producer with partitioning and DLQ support
- **Disk Buffer**: Local storage for Kafka outage scenarios
- **Metrics**: Processing statistics and health monitoring

## 🚀 Quick Start

### Prerequisites

- Python 3.9+
- Kafka cluster
- 100MB+ disk space for buffering

### Installation

```bash
cd services/event-collector-svc
pip install -r requirements.txt
```

### Configuration

Set environment variables:

```bash
# Kafka Configuration
export KAFKA_BOOTSTRAP_SERVERS="localhost:9092"
export KAFKA_TOPIC="events"
export KAFKA_CLIENT_ID="event-collector-svc"
export DLQ_TOPIC="events-dlq"

# Buffer Configuration
export BUFFER_DIR="./data/buffer"
export MAX_BUFFER_SIZE_MB="100"

# Performance Tuning
export KAFKA_MAX_IN_FLIGHT="1"
export KAFKA_COMPRESSION_TYPE="gzip"
export KAFKA_ACKS="all"
```

### Run Service

```bash
# Development
python -m app.main

# Production with Uvicorn
uvicorn app.main:app --host 0.0.0.0 --port 8000 --workers 4
```

## 📝 API Usage

### Collect Events

**Endpoint**: `POST /api/v1/collect`

**Simple Array Format**:

```bash
curl -X POST http://localhost:8000/api/v1/collect \
  -H "Content-Type: application/json" \
  -d '[
    {
      "event_id": "123e4567-e89b-12d3-a456-426614174000",
      "learner_id": "learner_001",
      "tenant_id": "tenant_alpha",
      "event_type": "interaction",
      "timestamp": "2024-01-15T10:30:00Z",
      "source_service": "learning-app",
      "event_data": {
        "action": "click",
        "element": "next_button"
      },
      "metadata": {}
    }
  ]'
```

**Batch Request Format**:

```bash
curl -X POST http://localhost:8000/api/v1/collect \
  -H "Content-Type: application/json" \
  -d '{
    "batch_id": "550e8400-e29b-41d4-a716-446655440000",
    "events": [...],
    "metadata": {
      "source": "mobile-app",
      "version": "2.1.0"
    }
  }'
```

**Gzipped Request**:

```bash
echo '[{"event_id":"123...", ...}]' | gzip | curl -X POST \
  -H "Content-Type: application/json" \
  -H "Content-Encoding: gzip" \
  --data-binary @- \
  http://localhost:8000/api/v1/collect
```

### Response Format

```json
{
  "batch_id": "550e8400-e29b-41d4-a716-446655440000",
  "accepted_count": 100,
  "rejected_count": 0,
  "processing_time_ms": 25.3,
  "kafka_partition": 2,
  "dlq_events": [],
  "warnings": []
}
```

### Health Check

```bash
curl http://localhost:8000/api/v1/health
```

```json
{
  "status": "healthy",
  "kafka_connected": true,
  "buffer_status": {
    "buffered_batches": 0,
    "buffer_size_mb": 0.0
  },
  "throughput_metrics": {
    "events_per_second": 1850.3,
    "avg_processing_time_ms": 15.2
  },
  "uptime_seconds": 3600
}
```

### Metrics

```bash
curl http://localhost:8000/api/v1/metrics
```

```json
{
  "events_processed_total": 1500000,
  "events_per_second": 2100.5,
  "kafka_writes_total": 15000,
  "dlq_events_total": 75,
  "buffer_events_count": 0,
  "avg_processing_time_ms": 18.4,
  "p99_processing_time_ms": 35.8
}
```

## 🧪 Testing

### Unit Tests

```bash
cd services/event-collector-svc
python -m pytest tests/ -v
```

### Performance Benchmarks

```bash
# 2k EPS benchmark
python -m pytest tests/test_ingest.py::TestPerformanceBenchmarks::test_2k_eps_benchmark -v

# Run all benchmarks
python -m pytest tests/test_ingest.py --benchmark -v
```

### Load Testing with curl

```bash
# Generate test events
curl -X POST http://localhost:8000/api/v1/test/events?count=1000

# Concurrent requests
for i in {1..50}; do
  curl -X POST http://localhost:8000/api/v1/test/events?count=20 &
done
wait
```

## 🔧 Event Schema

### Base Event Structure

```json
{
  "event_id": "uuid",
  "learner_id": "uuid",
  "tenant_id": "uuid",
  "event_type": "interaction|progress|assessment|error|system",
  "priority": "low|medium|high|critical",
  "timestamp": "2024-01-15T10:30:00Z",
  "source_service": "service-name",
  "event_data": {
    "action": "click",
    "element": "button_id",
    "custom_fields": "..."
  },
  "metadata": {
    "session_id": "session_123",
    "additional_context": "..."
  }
}
```

### Event Types

- **interaction**: User interactions (clicks, views, etc.)
- **progress**: Learning progress updates
- **assessment**: Quiz/test results
- **error**: Error events and exceptions
- **system**: System-level events

## 🚨 Error Handling

### HTTP Status Codes

- **200**: All events processed successfully
- **207**: Partial success (some events to DLQ)
- **400**: Invalid JSON or schema validation failed
- **413**: Batch too large (>1000 events)
- **422**: All events rejected (sent to DLQ)
- **503**: Service unavailable (Kafka writer not initialized)

### Dead Letter Queue

Failed events are automatically sent to DLQ with:

- Original event data
- Error details
- Retry count
- Failure timestamp

### Poison Pill Handling

Events that fail more than 3 times are permanently quarantined to prevent infinite retry loops.

## 📊 Monitoring

### Key Metrics

- **events_processed_total**: Cumulative event count
- **events_per_second**: Current throughput
- **p99_processing_time_ms**: 99th percentile latency
- **kafka_writes_total**: Successful Kafka writes
- **dlq_events_total**: Events sent to DLQ
- **buffer_events_count**: Events in disk buffer

### Health Indicators

- **kafka_connected**: Kafka cluster connectivity
- **buffer_status**: Disk buffer utilization
- **throughput_metrics**: Current performance
- **uptime_seconds**: Service uptime

### Alerts

Set up monitoring alerts for:

- EPS drops below 1000
- p99 latency exceeds 40ms
- DLQ rate exceeds 5%
- Buffer utilization exceeds 80%
- Kafka connection failures

## 🛠️ Configuration

### Environment Variables

| Variable                  | Default          | Description                |
| ------------------------- | ---------------- | -------------------------- |
| `KAFKA_BOOTSTRAP_SERVERS` | `localhost:9092` | Kafka cluster endpoints    |
| `KAFKA_TOPIC`             | `events`         | Primary event topic        |
| `DLQ_TOPIC`               | `events-dlq`     | Dead letter queue topic    |
| `BUFFER_DIR`              | `./data/buffer`  | Disk buffer directory      |
| `MAX_BUFFER_SIZE_MB`      | `100`            | Maximum buffer size        |
| `KAFKA_MAX_RETRIES`       | `3`              | Kafka retry attempts       |
| `KAFKA_COMPRESSION_TYPE`  | `gzip`           | Message compression        |
| `KAFKA_ACKS`              | `all`            | Write acknowledgment level |

### Kafka Topics

Ensure these topics exist:

```bash
# Primary event topic (3 partitions for learner_id distribution)
kafka-topics --create --topic events --partitions 3 --replication-factor 2

# Dead letter queue
kafka-topics --create --topic events-dlq --partitions 1 --replication-factor 2
```

## 🔄 Deployment

### Docker

```dockerfile
FROM python:3.11-slim
WORKDIR /app
COPY requirements.txt .
RUN pip install -r requirements.txt
COPY . .
EXPOSE 8000
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
```

### Kubernetes

```yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: event-collector
spec:
  replicas: 3
  selector:
    matchLabels:
      app: event-collector
  template:
    metadata:
      labels:
        app: event-collector
    spec:
      containers:
        - name: event-collector
          image: event-collector:latest
          ports:
            - containerPort: 8000
          env:
            - name: KAFKA_BOOTSTRAP_SERVERS
              value: "kafka:9092"
          resources:
            requests:
              memory: "256Mi"
              cpu: "250m"
            limits:
              memory: "512Mi"
              cpu: "500m"
```

## 📚 Documentation

- **OpenAPI Spec**: `docs/api/rest/event-collector.yaml`
- **Interactive Docs**: http://localhost:8000/docs
- **ReDoc**: http://localhost:8000/redoc

## 🤝 Contributing

1. Follow conventional commit format
2. Add tests for new features
3. Ensure benchmarks pass
4. Update documentation

## 📋 TODO

- [ ] gRPC streaming interface
- [ ] Prometheus metrics export
- [ ] Circuit breaker pattern
- [ ] Event deduplication
- [ ] Schema evolution support

---

**Stage**: S2-14 Event Collector Service  
**Performance**: 2k EPS, p99 ≤ 40ms  
**Reliability**: Kafka + DLQ + Disk Buffering
