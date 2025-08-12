# Payment Service

**AIVO Payment Service** with comprehensive Stripe integration for billing, trials, and subscription management.

##  Features

###  Billing & Subscriptions
- **30-day trials** with automatic conversion to paid subscriptions
- **Flexible billing terms** with progressive discounts:
  - Monthly: No discount
  - Quarterly (3 months): 20% off  
  - Half-yearly (6 months): 30% off
  - Yearly (12 months): 50% off
- **Sibling discounts**: 10% off for additional learners in the same family
- **Real-time quote calculation** with transparent pricing breakdown

###  Enterprise Features
- **District/School invoicing** for institutional customers
- **PO number tracking** for procurement compliance  
- **Manual payment collection** with 30-day terms
- **Bulk seat allocation** for district-wide deployments

###  Payment Failure Management
- **Grace periods**: 7 days after payment failure before restrictions
- **Automated dunning process**:
  - Day 3: First reminder email
  - Day 7: Second reminder email  
  - Day 14: Final notice email
  - Day 21: Automatic subscription cancellation
- **Subscription state management** with proper status tracking

###  Security & Compliance
- **Stripe webhook verification** with signature validation
- **Secrets management** via environment variables and vault integration
- **Audit trail** for all payment operations
- **PCI compliance** through Stripe's secure infrastructure

##  API Endpoints

### Trial Management
`ash
POST /trial/start
{
  "guardian_id": "guardian_123",
  "learner_id": "learner_123", 
  "email": "parent@example.com"
}
`

### Pricing & Quotes  
`ash
POST /plan/quote
{
  "seats": 3,
  "term": "yearly",
  "siblings": 2
}

# Response includes detailed pricing breakdown
{
  "base_price_cents": 2999,
  "total_seats": 3,
  "term": "yearly",
  "term_discount_percent": 0.50,
  "sibling_discount_percent": 0.10,
  "subtotal_cents": 107964,
  "term_discount_cents": 53982,
  "sibling_discount_cents": 7197,  
  "total_cents": 46785
}
`

### Checkout & Billing
`ash
POST /plan/checkout
{
  "learner_id": "learner_123",
  "guardian_id": "guardian_123",
  "term": "monthly",
  "seats": 1,
  "success_url": "https://app.aivo.com/success",
  "cancel_url": "https://app.aivo.com/cancel"
}
`

### District Invoicing
`ash
POST /district/invoice  
{
  "tenant_id": "district_001",
  "seats": 30,
  "billing_period_start": "2025-08-01",
  "billing_period_end": "2025-08-31",
  "po_number": "PO-2025-001"
}
`

### Webhook Processing
`ash
POST /webhooks/stripe
# Handles Stripe webhook events:
# - invoice.payment_failed
# - customer.subscription.updated  
# - checkout.session.completed
`

##  Configuration

### Environment Variables
`ash
# Stripe Configuration (from vault/secrets)
STRIPE_SECRET_KEY=sk_live_...
STRIPE_PUBLISHABLE_KEY=pk_live_...
STRIPE_WEBHOOK_SECRET=whsec_...

# Database Configuration
DATABASE_URL=postgresql://user:pass@localhost/payment_db

# Redis Configuration (for caching/tasks)
REDIS_URL=redis://localhost:6379/0

# Business Configuration
TRIAL_DURATION_DAYS=30
GRACE_PERIOD_DAYS=7
DUNNING_FAILURE_DAYS=3,7,14
CANCELLATION_DAY=21

# Discount Configuration  
QUARTERLY_DISCOUNT=0.20
HALF_YEAR_DISCOUNT=0.30
YEARLY_DISCOUNT=0.50
SIBLING_DISCOUNT=0.10

# Service URLs
TENANT_SERVICE_URL=http://localhost:8002
USER_SERVICE_URL=http://localhost:8001
`

### Stripe Products Setup
The service automatically manages Stripe products and prices for:
- Base monthly subscription (.99/month)
- Term-based pricing with automatic discount calculation
- District/institutional billing at standard rates

##  Quick Start

### Development Setup
`ash
# Install dependencies
pip install -r requirements.txt
pip install -r requirements-dev.txt

# Configure environment
cp .env.example .env
# Edit .env with your Stripe keys

# Run tests
python -m pytest tests/ -v

# Start development server
python -m uvicorn main:app --host 0.0.0.0 --port 8004 --reload
`

### Docker Deployment
`ash
# Build image
docker build -t aivo/payment-svc:latest .

# Run container
docker run -p 8004:8004 \
  -e STRIPE_SECRET_KEY= \
  -e DATABASE_URL= \
  aivo/payment-svc:latest
`

### Stripe CLI Integration
`ash
# Listen for webhooks during development
stripe listen --forward-to localhost:8004/webhooks/stripe

# Trigger test events
stripe trigger invoice.payment_failed
stripe trigger customer.subscription.updated  
stripe trigger checkout.session.completed
`

##  Testing

### Unit Tests
`ash
# Run full test suite
python -m pytest tests/ -v --cov=app

# Run specific test categories
python -m pytest tests/test_payment_api.py -v
python -m pytest tests/test_pact_contracts.py -v
`

### Contract Tests
Uses Pact for consumer-driven contract testing with:
- Stripe API integration
- Tenant service integration
- User service integration

### Test Coverage
- API endpoint testing with mocked Stripe responses
- Pricing calculation validation
- Webhook event processing
- Dunning process simulation
- Contract verification with external services

##  Monitoring & Observability

### Structured Logging
All operations are logged with structured JSON for:
- Payment processing events
- Subscription lifecycle changes
- Dunning process execution  
- Webhook event handling
- Error tracking and debugging

### Health Checks
- GET /health: Service health status
- GET /: Service capabilities and configuration
- Database connectivity monitoring
- Stripe API connectivity validation

### Metrics (Future)
- Payment success/failure rates
- Subscription conversion rates
- Dunning process effectiveness
- Revenue tracking and reporting

##  Error Handling

### Payment Failures
- Automatic retry logic for transient failures
- Grace period activation with user notifications
- Graduated dunning process with email escalation
- Subscription cancellation with proper cleanup

### Webhook Processing
- Signature verification for all incoming webhooks
- Idempotent event processing to handle duplicates
- Error logging and alerting for failed webhook events
- Automatic retry for failed webhook processing

### Service Integration
- Circuit breaker pattern for external service calls
- Graceful degradation when dependencies are unavailable
- Proper error propagation with meaningful messages

##  Pricing Structure

### Base Pricing
- Monthly subscription: .99/month per seat
- All pricing in USD cents for precision

### Term Discounts
- Quarterly (3 months): 20% discount = .98 total
- Half-yearly (6 months): 30% discount = .96 total  
- Yearly (12 months): 50% discount = .94 total

### Family Discounts
- Sibling discount: 10% off additional seats within same family
- Applied per sibling seat, not to primary seat

### District Pricing
- Institutional rate: .99/month per seat (no discounts)
- Manual invoicing with 30-day payment terms
- Volume pricing negotiated separately for large districts

##  Webhook Events

### Supported Events
1. **invoice.payment_failed**
   - Triggers dunning process initiation
   - Updates subscription to past_due status
   - Schedules reminder email sequence

2. **customer.subscription.updated**  
   - Updates local subscription records
   - Handles status transitions (active, canceled, past_due)
   - Manages trial-to-paid conversions

3. **checkout.session.completed**
   - Activates new subscriptions
   - Creates local subscription records
   - Triggers welcome email and access provisioning

### Event Processing
- Signature verification using Stripe webhook secrets
- Idempotent processing to handle duplicate events
- Structured logging for audit trails
- Error handling with retry mechanisms

##  Architecture

### Service Dependencies
- **Stripe API**: Primary payment processing
- **PostgreSQL**: Subscription and payment records  
- **Redis**: Caching and background task queuing
- **Tenant Service**: District seat allocation
- **User Service**: Account status updates

### Design Patterns
- **Service Layer**: Business logic separation
- **Repository Pattern**: Data access abstraction
- **Event-Driven**: Webhook-based state management
- **Circuit Breaker**: External service resilience
- **Audit Trail**: Complete payment operation logging

### Data Flow
1. Trial/Checkout  Stripe API  Local Record Creation
2. Payment Success  Webhook  Service Integration  User Access
3. Payment Failure  Webhook  Dunning Process  Email Notifications
4. Subscription Updates  Webhook  Local State Sync  Access Control

##  Security Considerations

### Secrets Management
- All Stripe keys managed via environment variables
- Webhook secrets for signature verification
- Database credentials via secure configuration
- No secrets in source code or logs

### Data Protection
- PCI compliance through Stripe infrastructure
- Minimal payment data storage locally
- Encrypted data transmission (HTTPS only)
- Audit logging for compliance

### Access Control
- API authentication for admin endpoints
- Webhook signature verification
- Rate limiting for API endpoints
- Input validation and sanitization

---

**Service URL**: http://localhost:8004  
**Documentation**: http://localhost:8004/docs  
**Health Check**: http://localhost:8004/health

For questions or support, contact the AIVO Engineering team.
