# Guardian Identity Verification Service (S6-03)

A COPPA-compliant guardian identity verification service that provides **micro-charge verification** ($0.10 via Stripe) as the primary method with **KBA (Knowledge-Based Authentication) fallback** for non-EU regions. This service is specifically designed for verifying parent/guardian identity in educational technology platforms.

## 🎯 Features

### Core Verification Methods

- **🏦 Micro-Charge Verification**: $0.10 charge via Stripe with automatic refund
- **🧠 Knowledge-Based Authentication (KBA)**: Multi-vendor support (LexisNexis, Experian, ID Analytics)
- **🌍 Geographic Compliance**: Country-specific verification method availability
- **⚡ Rate Limiting**: Guardian and IP-based rate limiting with lockout mechanisms

### Privacy & Compliance

- **👶 COPPA Compliance**: Automatic data retention and scrubbing
- **🇪🇺 GDPR Support**: EU-specific privacy controls and consent management
- **🔒 Privacy-First Design**: Minimal data collection with automatic cleanup
- **📋 Audit Logging**: Comprehensive audit trail with automatic retention

### Integration Features

- **🔗 Onboarding Integration**: React component for seamless wizard integration
- **🚪 Consent Gating**: Blocks protected features until verification complete
- **📊 Analytics**: Verification success rates and compliance metrics
- **🔄 Webhook Support**: Real-time verification status updates

## 🏗️ Architecture

```
┌─────────────────┐    ┌──────────────────┐    ┌─────────────────┐
│   Web Client    │────│ Verification API │────│ Payment Gateway │
│ (React/Next.js) │    │   (FastAPI)      │    │    (Stripe)     │
└─────────────────┘    └──────────────────┘    └─────────────────┘
                                │
                                ├─── PostgreSQL Database
                                ├─── Redis (Rate Limiting)
                                ├─── KBA Vendors
                                └─── Audit & Monitoring
```

## 🚀 Quick Start

### Prerequisites

- Python 3.11+
- PostgreSQL 14+
- Redis 6+
- Stripe Account (for production)

### Installation

1. **Clone and setup**:

```bash
cd services/verification-svc
python -m venv venv
source venv/bin/activate  # or `venv\Scripts\activate` on Windows
pip install -r requirements.txt
```

2. **Configure environment**:

```bash
cp .env.example .env
# Edit .env with your configuration
```

3. **Setup database**:

```bash
# Create database
createdb verification_db

# Run migrations
alembic upgrade head
```

4. **Start the service**:

```bash
uvicorn app.main:app --reload --port 8000
```

### Docker Setup

```bash
# Build image
docker build -t verification-svc .

# Run with docker-compose
docker-compose up verification-svc
```

## 📋 Configuration

### Required Environment Variables

```bash
# Database
DATABASE_URL=postgresql+asyncpg://user:pass@localhost:5432/verification_db

# Stripe (Production)
STRIPE_API_KEY=sk_live_...
STRIPE_WEBHOOK_SECRET=whsec_...

# KBA Vendors
LEXISNEXIS_USERNAME=your_username
LEXISNEXIS_PASSWORD=your_password
EXPERIAN_USERNAME=your_username
EXPERIAN_PASSWORD=your_password

# Security
SECRET_KEY=your-secret-key
JWT_SECRET_KEY=your-jwt-secret
```

### Geographic Configuration

```bash
# COPPA-applicable countries (default: US)
COPPA_COUNTRIES=US

# GDPR-applicable countries (EU member states)
GDPR_COUNTRIES=AT,BE,BG,HR,CY,CZ,DK,EE,FI,FR,DE,GR,HU,IE,IT,LV,LT,LU,MT,NL,PL,PT,RO,SK,SI,ES,SE

# Countries where KBA is not available
KBA_RESTRICTED_COUNTRIES=
```

## 🔧 API Reference

### Start Verification

```http
POST /api/v1/verification/start
Content-Type: application/json

{
  "guardian_user_id": "guardian_123",
  "tenant_id": "tenant_456",
  "preferred_method": "micro_charge",
  "guardian_country": "US"
}
```

### Check Verification Status

```http
GET /api/v1/verification/{verification_id}/status
```

### Micro-Charge Flow

```http
POST /api/v1/verification/{verification_id}/charge/create-intent
{
  "payment_method_id": "pm_1234567890"
}
```

### KBA Flow

```http
POST /api/v1/verification/{verification_id}/kba/start
{
  "first_name": "John",
  "last_name": "Doe",
  "date_of_birth": "1980-01-01",
  "address": {...}
}
```

## 🧪 Testing

### Run Tests

```bash
# All tests
pytest

# Specific test categories
pytest tests/test_verification_flow.py::TestMicroChargeVerification
pytest tests/test_verification_flow.py::TestKBAVerification
pytest tests/test_verification_flow.py::TestRateLimiting
```

### Test Coverage

```bash
pytest --cov=app --cov-report=html
open htmlcov/index.html
```

### Integration Tests

```bash
# Requires test database and mock services
pytest tests/integration/
```

## 🔒 Security Considerations

### Data Protection

- **PII Scrubbing**: Automatic removal of sensitive data after verification
- **Hashed Storage**: IP addresses and user agents stored as hashes
- **Encryption**: All sensitive data encrypted at rest
- **Access Logs**: Comprehensive audit trail with automatic retention

### Rate Limiting

- **Guardian Limits**: 5 attempts/hour, 10 attempts/day
- **IP Limits**: 20 attempts/hour, 50 attempts/day
- **Lockout**: 24-hour lockout after excessive attempts
- **Bypass**: Emergency bypass for legitimate users

### Compliance Features

- **COPPA**: Automatic data retention and parental consent verification
- **GDPR**: Right to deletion and data portability
- **SOC 2**: Security controls and monitoring
- **PCI DSS**: Payment data protection (via Stripe)

## 🌍 Geographic Policies

### Verification Method Availability

| Region    | Micro-Charge | KBA | Notes                           |
| --------- | ------------ | --- | ------------------------------- |
| US        | ✅           | ✅  | Full verification suite         |
| Canada    | ✅           | ✅  | Full verification suite         |
| EU        | ✅           | ❌  | GDPR compliance, KBA restricted |
| UK        | ✅           | ✅  | Post-Brexit policies            |
| Australia | ✅           | ✅  | Local privacy laws              |
| Other     | ✅           | ❌  | Micro-charge only               |

### Compliance Requirements

- **EU/GDPR**: Additional consent required, data residency
- **US/COPPA**: Enhanced protection for users under 13
- **Canada/PIPEDA**: Privacy impact assessments
- **Australia/Privacy Act**: Local data handling requirements

## 🎨 Frontend Integration

### React Component Usage

```tsx
import { GuardianVerify } from "@/components/onboarding/GuardianVerify";

export function OnboardingWizard() {
  return (
    <GuardianVerify
      guardianUserId="guardian_123"
      tenantId="tenant_456"
      onVerified={(result) => {
        console.log("Guardian verified:", result);
        // Proceed to next step
      }}
      onError={(error) => {
        console.error("Verification failed:", error);
      }}
    />
  );
}
```

### Verification States

- **`pending`**: Verification not started
- **`in_progress`**: User actively verifying
- **`verified`**: Successfully verified
- **`failed`**: Verification failed
- **`expired`**: Verification session expired
- **`rate_limited`**: Too many attempts

## 📊 Monitoring & Analytics

### Key Metrics

- **Verification Success Rate**: Overall success percentage
- **Method Preference**: Micro-charge vs KBA usage
- **Geographic Distribution**: Verification attempts by country
- **Failure Reasons**: Common failure categories
- **Performance**: API response times and availability

### Alerting

- **High Failure Rate**: >20% failures in 1 hour
- **Service Unavailability**: Health check failures
- **Rate Limit Abuse**: Excessive lockouts
- **Payment Issues**: Stripe webhook failures

### Dashboards

- **Grafana**: Real-time verification metrics
- **Prometheus**: System and business metrics
- **Loki**: Centralized log aggregation
- **Alerts**: PagerDuty integration for critical issues

## 🔄 Deployment

### Production Checklist

- [ ] Environment variables configured
- [ ] Database migrations applied
- [ ] Stripe webhooks configured
- [ ] KBA vendor credentials verified
- [ ] Rate limiting configured
- [ ] Monitoring alerts enabled
- [ ] Backup procedures tested
- [ ] Security scan completed

### Health Checks

```bash
# Service health
curl http://localhost:8000/health

# Database connectivity
curl http://localhost:8000/health/database

# External dependencies
curl http://localhost:8000/health/dependencies
```

### Scaling Considerations

- **Horizontal Scaling**: Stateless service design
- **Database**: Read replicas for analytics
- **Cache**: Redis cluster for rate limiting
- **CDN**: Static assets via CloudFront
- **Load Balancer**: Multi-AZ deployment

## 📖 Documentation

- **API Documentation**: `/docs` (Swagger UI)
- **Schema Documentation**: `/redoc` (ReDoc)
- **Architecture Decision Records**: `docs/adr/`
- **Runbooks**: `docs/runbooks/`
- **Security Policies**: `docs/security/`

## 🤝 Contributing

1. **Fork** the repository
2. **Create** a feature branch (`git checkout -b feature/amazing-feature`)
3. **Commit** your changes (`git commit -m 'Add amazing feature'`)
4. **Push** to the branch (`git push origin feature/amazing-feature`)
5. **Open** a Pull Request

### Development Guidelines

- **Code Style**: Black, isort, flake8
- **Type Hints**: Required for all functions
- **Tests**: Minimum 80% coverage
- **Documentation**: Update README and docstrings
- **Security**: SAST scan required

## 📄 License

This project is licensed under the MIT License - see the [LICENSE](../../LICENSE) file for details.

## 🆘 Support

- **Issues**: GitHub Issues
- **Documentation**: Internal Wiki
- **Emergency**: PagerDuty escalation
- **Security**: security@aivo.com

---

**Built with ❤️ for COPPA-compliant guardian verification**
