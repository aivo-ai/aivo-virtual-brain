# Analytics Service (S2-15)

Privacy-aware analytics and ETL service for transforming educational events into anonymized aggregates and dashboard metrics with differential privacy support.

## 🔒 Privacy-First Architecture

This service is designed with **privacy by design** principles for educational environments:

- **Differential Privacy**: Statistical noise prevents individual identification
- **K-Anonymity**: Small groups (<5) are suppressed to prevent re-identification
- **Data Minimization**: Only necessary data is collected and processed
- **PII Anonymization**: Personal identifiers are hashed or removed
- **Regulatory Compliance**: FERPA, COPPA, GDPR, and SOC 2 compliant

## 📊 Analytics Capabilities

### ETL Processing

- **Session Duration**: Learning time aggregations with engagement metrics
- **Mastery Progress**: Subject-specific progress tracking and improvement deltas
- **Weekly Activity**: Active learner trends and cohort analytics
- **IEP Progress**: Special needs goal tracking with progress percentages

### Privacy Levels

- **ANONYMIZED**: PII removed, aggregated data (default)
- **DP_LOW**: Low differential privacy noise (ε=2.0)
- **DP_MEDIUM**: Medium differential privacy noise (ε=1.0)
- **DP_HIGH**: High differential privacy noise (ε=0.5)

## 🏗️ Architecture

```
Raw Events → ETL Jobs → Anonymized Aggregates → Privacy-Aware APIs
     ↓           ↓              ↓                       ↓
  Kafka     DP Engine      PostgreSQL            Dashboard APIs
            K-Anonymity     Hashed IDs           Tenant/Learner
```

### Components

- **ETL Jobs**: Transform raw events into privacy-protected aggregates
- **Differential Privacy Engine**: Add statistical noise to prevent identification
- **Privacy Anonymizer**: Hash identifiers and suppress small counts
- **Analytics APIs**: Serve tenant and learner metrics with privacy controls
- **Database Models**: Store aggregated data with privacy metadata

## 🚀 Quick Start

### Prerequisites

- Python 3.9+
- PostgreSQL 12+
- 2GB+ RAM for DP calculations

### Installation

```bash
cd services/analytics-svc
pip install -r requirements.txt
```

### Configuration

Set environment variables:

```bash
# Database Configuration
export DATABASE_URL="postgresql://analytics_user:pass@localhost:5432/analytics_db"

# Privacy Settings
export DEFAULT_PRIVACY_LEVEL="anonymized"
export DP_EPSILON_BUDGET="1.0"
export MIN_COHORT_SIZE="5"

# ETL Configuration
export ETL_BATCH_SIZE="1000"
export ETL_SCHEDULE_DAILY="02:00"
export ETL_RETENTION_DAYS="365"
```

### Database Setup

```bash
# Create database and tables
python -c "from app.models import Base, engine; Base.metadata.create_all(bind=engine)"
```

### Run Service

```bash
# Development
python -m app.main

# Production with Uvicorn
uvicorn app.main:app --host 0.0.0.0 --port 8001 --workers 2
```

## 📝 API Usage

### Get Tenant Analytics

**Endpoint**: `GET /api/v1/metrics/tenant/{tenant_id}`

```bash
curl "http://localhost:8001/api/v1/metrics/tenant/550e8400-e29b-41d4-a716-446655440000?privacy_level=anonymized"
```

**Response**:

```json
{
  "tenant_id": "550e8400-e29b-41d4-a716-446655440000",
  "reporting_period_start": "2025-01-01",
  "reporting_period_end": "2025-01-31",
  "total_active_learners": 245,
  "total_learning_hours": 1523.5,
  "average_engagement_rate": 0.78,
  "session_metrics": {
    "total_sessions": 3420,
    "avg_duration_minutes": 26.7,
    "median_duration_minutes": 22.5,
    "total_hours": 1523.5,
    "trend_direction": "up",
    "privacy_level": "anonymized",
    "data_points": 31
  },
  "weekly_activity": [...],
  "top_subjects": [...],
  "iep_progress_summary": {...},
  "privacy_level": "anonymized",
  "last_updated": "2025-01-31T15:30:00Z"
}
```

### Get Learner Analytics

**Endpoint**: `GET /api/v1/metrics/learner/{learner_id_hash}`

```bash
curl "http://localhost:8001/api/v1/metrics/learner/1234567890abcdef?privacy_level=dp_medium"
```

**Response**:

```json
{
  "learner_id_hash": "1234567890abcdef",
  "reporting_period_start": "2024-12-01",
  "reporting_period_end": "2025-01-31",
  "session_metrics": {...},
  "subject_progress": [...],
  "iep_progress": [...],
  "privacy_level": "dp_medium",
  "minimum_cohort_size": 5,
  "differential_privacy_epsilon": 1.0,
  "last_updated": "2025-01-31T15:30:00Z",
  "data_completeness": 0.87
}
```

### Trigger ETL Processing

**Endpoint**: `POST /api/v1/etl/trigger/{tenant_id}`

```bash
curl -X POST "http://localhost:8001/api/v1/etl/trigger/550e8400-e29b-41d4-a716-446655440000?privacy_level=dp_low"
```

### Get Privacy Levels

```bash
curl "http://localhost:8001/api/v1/privacy/levels"
```

```json
{
  "privacy_levels": [
    {
      "level": "anonymized",
      "description": "PII removed, data aggregated",
      "suitable_for": "Educator dashboards, tenant analytics"
    },
    {
      "level": "dp_medium",
      "description": "Medium differential privacy noise (ε=1.0)",
      "suitable_for": "Public reports, cross-tenant analytics"
    }
  ]
}
```

## 🧪 Testing

### Unit Tests

```bash
cd services/analytics-svc
python -m pytest tests/ -v
```

### Test Categories

```bash
# Differential privacy tests
python -m pytest tests/test_etl.py::TestDifferentialPrivacy -v

# ETL job tests
python -m pytest tests/test_etl.py::TestETLJobs -v

# Aggregate accuracy tests
python -m pytest tests/test_etl.py::TestAggregateAccuracy -v

# API endpoint tests
python -m pytest tests/test_etl.py::TestAPIEndpoints -v
```

### Privacy Testing

```bash
# Test DP noise bounds
python -m pytest tests/test_etl.py -k "test_dp_noise_bounds" -v

# Test k-anonymity enforcement
python -m pytest tests/test_etl.py -k "test_k_anonymity" -v

# Test small count suppression
python -m pytest tests/test_etl.py -k "test_small_count_suppression" -v
```

## 🔧 ETL Jobs

### Session Duration ETL

Transforms raw session events into privacy-protected aggregates:

```python
from app.etl import SessionDurationETL, PrivacyLevel

etl = SessionDurationETL(db_session, PrivacyLevel.DP_LOW)
job_run = etl.run_etl(start_date, end_date, tenant_id)
```

**Metrics Generated**:

- Total sessions per learner/tenant/day
- Average, median, max session duration
- Total learning time
- Engagement trends

### Mastery Progress ETL

Calculates subject mastery progression with improvement deltas:

```python
from app.etl import MasteryProgressETL

etl = MasteryProgressETL(db_session, PrivacyLevel.ANONYMIZED)
job_run = etl.run_etl(start_date, end_date, tenant_id)
```

**Metrics Generated**:

- Current mastery score per subject
- Mastery improvement over time
- Assessments completed
- Time to achieve mastery

### Weekly Active Learners ETL

Aggregates weekly engagement and demographic data:

```python
from app.etl import WeeklyActiveLearnersETL

etl = WeeklyActiveLearnersETL(db_session, PrivacyLevel.DP_MEDIUM)
job_run = etl.run_etl(week_start_date, tenant_id)
```

**Metrics Generated**:

- Active, new, returning, churned learners
- Average sessions and time per learner
- Engagement rates
- Anonymized demographics (age/grade distributions)

### IEP Progress ETL

Tracks special needs learner progress toward IEP goals:

```python
from app.etl import IEPProgressETL

etl = IEPProgressETL(db_session, PrivacyLevel.ANONYMIZED)
job_run = etl.run_etl(start_date, end_date, tenant_id)
```

**Metrics Generated**:

- Progress toward IEP goals
- Baseline, current, and target scores
- Progress percentages and on-track status
- Support levels and interventions (anonymized)

## 🔒 Privacy Mechanisms

### Differential Privacy Engine

Adds calibrated statistical noise to prevent individual identification:

```python
from app.etl import DifferentialPrivacyEngine

dp_engine = DifferentialPrivacyEngine(epsilon=1.0, delta=1e-5)

# Add noise to counts
noisy_count = dp_engine.add_noise_to_count(original_count)

# Add noise to averages
noisy_avg = dp_engine.add_noise_to_average(total, count, range_size)
```

**Privacy Budget Management**:

- Lower epsilon = more privacy, more noise
- Delta controls probability of privacy loss
- Sensitivity adjusted per query type

### Privacy Anonymizer

Removes or transforms identifying information:

```python
from app.etl import PrivacyAnonimizer

anonymizer = PrivacyAnonimizer()

# Hash learner IDs consistently
learner_hash = anonymizer.hash_learner_id(learner_id)

# Generalize ages to categories
age_category = anonymizer.generalize_age(actual_age)

# Suppress small counts for k-anonymity
filtered_data = anonymizer.suppress_small_counts(data, threshold=5)
```

## 📊 Database Schema

### Aggregate Tables

- **session_aggregates**: Daily session duration metrics per learner/tenant
- **mastery_aggregates**: Subject mastery progress per learner/subject/date
- **weekly_active_aggregates**: Weekly active learner metrics per tenant
- **iep_progress_aggregates**: IEP goal progress per learner/category/date
- **etl_job_runs**: ETL job execution history and status

### Privacy Metadata

All aggregate tables include:

- `privacy_level`: Protection level applied (anonymized, dp_low, etc.)
- `noise_epsilon`: Differential privacy epsilon used
- `cohort_size`: K-anonymity group size
- `aggregation_level`: Individual, cohort, tenant, or global

### Indexes

Optimized for common query patterns:

- Tenant + date range queries
- Learner + subject + date queries
- ETL job status lookups
- Privacy level filtering

## 📈 Monitoring

### Key Metrics

- **ETL Job Success Rate**: % of jobs completing successfully
- **Processing Latency**: Time to process daily/weekly ETL jobs
- **Data Completeness**: % of expected events processed
- **Privacy Budget Usage**: Epsilon consumed per tenant/period
- **API Response Times**: Dashboard query performance

### Health Checks

```bash
curl http://localhost:8001/api/v1/health
```

```json
{
  "status": "healthy",
  "service": "analytics-svc",
  "version": "1.0.0",
  "stage": "S2-15"
}
```

### ETL Job Monitoring

```bash
curl "http://localhost:8001/api/v1/etl/jobs?limit=10&status_filter=failed"
```

Monitor for:

- Failed ETL jobs
- Long processing times
- High error rates
- Privacy budget exhaustion

## 🛡️ Security & Compliance

### FERPA Compliance

- **Educational Records**: Only aggregated, anonymized data stored
- **Directory Information**: No personally identifiable information retained
- **Consent**: Implicit consent through platform usage
- **Access Controls**: Role-based access to analytics

### COPPA Compliance

- **Age Verification**: Ages generalized to broad categories
- **Parental Rights**: Parents can access child's anonymized data
- **Data Minimization**: Only learning-relevant metrics collected
- **Retention Limits**: Aggregated data retained for educational purposes

### GDPR Compliance

- **Lawful Basis**: Legitimate interest for educational analytics
- **Data Minimization**: Minimal data collected and processed
- **Right to Access**: Learners can access their anonymized metrics
- **Right to Erasure**: Aggregated data cannot identify individuals
- **Privacy by Design**: Built-in privacy protections

### SOC 2 Controls

- **Security**: Encrypted data at rest and in transit
- **Availability**: High availability with failover capabilities
- **Processing Integrity**: Data validation and integrity checks
- **Confidentiality**: Access controls and audit logging
- **Privacy**: Privacy impact assessments and controls

## 🔄 Deployment

### Docker

```dockerfile
FROM python:3.11-slim
WORKDIR /app
COPY requirements.txt .
RUN pip install -r requirements.txt
COPY . .
EXPOSE 8001
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8001"]
```

### Kubernetes

```yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: analytics-service
spec:
  replicas: 2
  selector:
    matchLabels:
      app: analytics-service
  template:
    metadata:
      labels:
        app: analytics-service
    spec:
      containers:
        - name: analytics-service
          image: analytics-service:latest
          ports:
            - containerPort: 8001
          env:
            - name: DATABASE_URL
              valueFrom:
                secretKeyRef:
                  name: analytics-secrets
                  key: database-url
          resources:
            requests:
              memory: "512Mi"
              cpu: "250m"
            limits:
              memory: "2Gi"
              cpu: "1000m"
```

### Environment Configuration

```bash
# Production settings
export DATABASE_URL="postgresql://user:pass@postgres:5432/analytics_prod"
export DEFAULT_PRIVACY_LEVEL="dp_medium"
export DP_EPSILON_BUDGET="0.5"
export ETL_WORKERS="4"
export LOG_LEVEL="info"
```

## 📚 Documentation

- **OpenAPI Spec**: `docs/api/rest/analytics.yaml`
- **Interactive Docs**: http://localhost:8001/docs
- **ReDoc**: http://localhost:8001/redoc
- **Privacy Policy**: http://localhost:8001/privacy/policy

## 🤝 Contributing

1. Follow privacy-by-design principles
2. Add tests for privacy mechanisms
3. Document privacy impact of changes
4. Ensure compliance with educational regulations

## 📋 Roadmap

- [ ] Real-time event stream processing
- [ ] Advanced anonymization techniques (l-diversity, t-closeness)
- [ ] Federated learning integration
- [ ] Interactive privacy budget management
- [ ] Automated privacy impact assessments

---

**Stage**: S2-15 Analytics & ETL Service  
**Privacy**: Differential Privacy + K-Anonymity  
**Compliance**: FERPA, COPPA, GDPR, SOC 2  
**Performance**: <200ms API response, daily ETL processing
