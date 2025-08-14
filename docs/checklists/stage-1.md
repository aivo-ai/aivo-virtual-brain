# Stage-1 Readiness Checklist

## 🎯 Stage-1 Definition

Complete foundational architecture with core services, authentication, enrollment flows, and observability infrastructure ready for production deployment.

## ✅ Infrastructure & DevOps

### Container Orchestration

- [ ] Docker Compose configured with all core services
- [ ] PostgreSQL 16 database with health checks
- [ ] Redis 7 cache with authentication
- [ ] MinIO S3-compatible storage
- [ ] All services have proper health/readiness endpoints

### Service Architecture

- [ ] **Auth Service** (`auth-svc`) - Authentication and JWT management
- [ ] **User Service** (`user-svc`) - User profile and RBAC management
- [ ] **Enrollment Router** (`enrollment-router`) - District vs Parent flow routing
- [ ] **Learner Service** (`learner-svc`) - Learner profile management
- [ ] **Assessment Service** (`assessment-svc`) - Assessment lifecycle
- [ ] **Payment Service** (`payment-svc`) - Transaction processing
- [ ] **IEP Service** (`iep-svc`) - IEP lifecycle management
- [ ] **Tenant Service** (`tenant-svc`) - Multi-tenancy and SCIM

### Observability Stack

- [ ] Grafana dashboards for all 6 core services
- [ ] FinOps dashboard with cost tracking
- [ ] Prometheus alert rules (5xx>2%, P95 SLI breaches)
- [ ] 15 alert rules configured with 5m evaluation
- [ ] Synthetic load testing infrastructure
- [ ] Mock health server with realistic metrics

## ✅ Authentication & Authorization

### JWT & Security

- [ ] JWT service with RS256 signing
- [ ] JWKS endpoint for public key distribution
- [ ] Password service with bcrypt hashing
- [ ] TOTP service for 2FA support
- [ ] Redis session management

### Login Flow

- [ ] `/auth/login` endpoint returns valid JWT
- [ ] Token validation across services
- [ ] Role-based access control (RBAC)
- [ ] Session management with Redis

## ✅ Enrollment Flows

### District Enrollment (B2B)

- [ ] District context routing in enrollment-router
- [ ] Seat allocation for district learners
- [ ] Tenant-based provisioning
- [ ] SCIM integration for district user management

### Parent Enrollment (B2C)

- [ ] Parent flow routing without tenant context
- [ ] Checkout URL generation for trial signup
- [ ] Payment processing integration ready

### Enrollment Endpoints

- [ ] `POST /enroll` handles both district and parent flows
- [ ] Proper EnrollmentRequest/Response models
- [ ] Context-based routing logic functional

## ✅ API Contracts & Testing

### SDK Integration

- [ ] Python SDK (`libs/sdk-py`) with core service clients
- [ ] Web SDK (`libs/sdk-web`) with TypeScript types
- [ ] Contract validation across all services
- [ ] Mock Service Workers (MSW) for testing

### Test Coverage

- [ ] Health endpoint tests for all services
- [ ] Authentication flow tests
- [ ] Enrollment flow tests (district + parent)
- [ ] Contract compliance validation
- [ ] Integration tests with mocks

## ✅ Security & Compliance

### Security Policies

- [ ] Edge policies configured in Kong
- [ ] Threat model documented
- [ ] Security scanning (OSV, Trivy) passing
- [ ] Dependency vulnerability checks green

### Data Protection

- [ ] PostgreSQL with proper user permissions
- [ ] Redis authentication enabled
- [ ] MinIO access control configured
- [ ] Environment variable security

## ✅ Monitoring & Alerts

### Service Level Indicators (SLIs)

- [ ] HTTP request rate monitoring
- [ ] Error rate tracking (5xx errors)
- [ ] Response time percentiles (P50, P95, P99)
- [ ] AI inference latency tracking

### Alert Rules

- [ ] 5xx error rate > 2% alerts (5m evaluation)
- [ ] P95 latency > 1000ms alerts
- [ ] AI inference latency alerts (>2s-5s based on service)
- [ ] Business metric alerts (transaction failures, compliance scores)

### Cost Monitoring (FinOps)

- [ ] Infrastructure cost tracking per service
- [ ] Payment revenue monitoring
- [ ] Cost efficiency metrics (per request, per inference)
- [ ] Stage-2 AI inference cost placeholders ready

## ✅ CI/CD & Quality Gates

### Automated Testing

- [ ] Lint checks passing across all services
- [ ] Type checking (TypeScript/Python) green
- [ ] Unit tests passing
- [ ] Integration tests with Docker Compose
- [ ] Contract validation in CI

### Security Scanning

- [ ] `pnpm run sec:osv` - OSV vulnerability scanning
- [ ] `pnpm run sec:trivy` - Trivy security scanning
- [ ] `pnpm run sec:deps` - Dependency deprecation checks
- [ ] All security scans green in CI

### Stage-1 Verifier

- [ ] `pnpm run verify-stage1` passes locally
- [ ] Stage-1 verifier passes in GitHub Actions CI
- [ ] Health checks green for all services
- [ ] Login → Enrollment happy paths functional
- [ ] Mock services responding correctly

## 🚀 Deployment Readiness

### Environment Configuration

- [ ] Production environment variables template
- [ ] Database migrations ready
- [ ] Service configuration validated
- [ ] Resource requirements documented

### Performance Baseline

- [ ] Load testing results recorded
- [ ] Performance benchmarks established
- [ ] Resource utilization measured
- [ ] Capacity planning completed

### Documentation

- [ ] API documentation up to date
- [ ] Deployment guides complete
- [ ] Troubleshooting guides ready
- [ ] Architecture decision records (ADRs) current

## 🏷️ Release Criteria

### Final Validation

- [ ] All checklist items verified ✅
- [ ] `pnpm run verify-stage1` passing ✅
- [ ] No critical security vulnerabilities ✅
- [ ] Performance requirements met ✅
- [ ] Documentation complete ✅

### Git Tag

- [ ] **Tag `v1.0.0-stage1`** applied to main branch
- [ ] Release notes created
- [ ] Changelog updated
- [ ] Stage-1 milestone closed

---

## ⚡ Quick Verification

```bash
# Run comprehensive Stage-1 verification
pnpm run verify-stage1

# Start infrastructure
docker compose up -d

# Check all services health
curl http://localhost:8000/health  # auth-svc
curl http://localhost:8020/health  # user-svc
curl http://localhost:8030/health  # enrollment-router

# Test authentication flow
curl -X POST http://localhost:8000/auth/login \
  -H "Content-Type: application/json" \
  -d '{"email":"test@example.com","password":"test123"}'

# Test enrollment flows
curl -X POST http://localhost:8030/enroll \
  -H "Content-Type: application/json" \
  -d '{"learner_profile":{"learner_temp_id":"temp123","first_name":"John","last_name":"Doe","email":"john@example.com"},"context":{"tenant_id":"district-001"}}'
```

**Stage-1 Status**: 🟡 **In Progress** → Target: 🟢 **Ready for v1.0.0-stage1**
