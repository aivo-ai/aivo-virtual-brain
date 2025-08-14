# Edge Security Policies - S1-18 Implementation

## Overview

AIVO Virtual Brains implements comprehensive security policies at the gateway edge using Kong API Gateway with custom Lua plugins. This document outlines the security controls, JWT validation requirements, consent enforcement, and PII protection mechanisms.

## Security Architecture

### 1. Kong Gateway Security Stack

```
Request → Kong Gateway → Security Plugins → Downstream Services
                ↓
        [dash_context] (Priority: 1000)
        [learner_scope] (Priority: 950)
        [consent_gate] (Priority: 900)
        [jwt] (Kong Built-in)
        [cors] (Kong Built-in)
        [rate-limiting] (Kong Built-in)
```

### 2. JWT Authentication Requirements

#### JWT Claims Structure

```json
{
  "sub": "user_12345",
  "learner_uid": "learner_67890",
  "role": "learner|teacher|guardian|admin",
  "tenant_id": "tenant_abc123",
  "dash_context": "learner|teacher|guardian|admin",
  "exp": 1735689600,
  "iat": 1735686000
}
```

#### Authentication Flows

1. **Missing JWT → 401 Unauthorized**
   - No `Authorization: Bearer <token>` header
   - Invalid/expired JWT token
   - Missing required `dash_context` claim

2. **Invalid Scope → 403 Forbidden**
   - Path contains `/learners/{learnerId}` but JWT `learner_uid` ≠ path `learnerId`
   - Learner attempting to access other learner's data
   - Missing required consent for privacy-sensitive operations

3. **Valid Access → 200 OK**
   - JWT valid with required claims
   - Scope validation passed (learner_uid matches or bypass role)
   - Consent requirements satisfied

## Security Plugin Details

### 1. dash_context Plugin (Priority: 1000)

**Purpose**: Validates JWT tokens and injects dashboard context headers for downstream services.

**Key Security Features**:

- JWT validation with `resty.jwt`
- Dashboard context validation (`learner`, `teacher`, `guardian`, `admin`)
- Required JWT claims enforcement
- Correlation ID injection for audit trails

**Security Tests**:

- ✅ No JWT → 401 with `MISSING_JWT` code
- ✅ Invalid JWT → 401 with `INVALID_JWT` code
- ✅ Missing `dash_context` → 401 with `MISSING_CONTEXT` code
- ✅ Invalid context value → 403 with `INVALID_CONTEXT` code
- ✅ Valid JWT + context → Headers injected

### 2. learner_scope Plugin (Priority: 950)

**Purpose**: Enforces learner data access isolation by validating JWT `learner_uid` matches path parameters.

**Key Security Features**:

- Path parameter extraction (`/learners/{learnerId}`)
- JWT `learner_uid` claim validation
- Role-based bypass for `admin` and `teacher` roles
- Scope violation prevention

**Security Tests**:

- ✅ Path learner ID ≠ JWT learner_uid → 403 `LEARNER_SCOPE_VIOLATION`
- ✅ Missing learner_uid claim → 403 `NO_LEARNER_SCOPE`
- ✅ Admin role bypass → Access granted
- ✅ Matching learner_uid → Access granted with validation headers

### 3. consent_gate Plugin (Priority: 900)

**Purpose**: Enforces privacy consent requirements for sensitive operations with Redis-backed consent state management.

**Key Security Features**:

- Redis-cached consent state lookup
- Path-based consent requirement evaluation
- Learner-specific consent validation
- Audit logging for consent decisions

**Security Tests**:

- ✅ Privacy-sensitive path + no consent → 403 `CONSENT_REQUIRED`
- ✅ Consent state cached and validated
- ✅ Admin role bypass consent checks
- ✅ Consent granted → Access with audit headers

## JWT Security Test Matrix

| Test Case                  | JWT Status | Claims                    | Expected Result             |
| -------------------------- | ---------- | ------------------------- | --------------------------- |
| No Auth Header             | ❌ Missing | -                         | 401 MISSING_JWT             |
| Invalid JWT                | ❌ Invalid | -                         | 401 INVALID_JWT             |
| Valid JWT, No Context      | ✅ Valid   | Missing `dash_context`    | 401 MISSING_CONTEXT         |
| Valid JWT, Invalid Context | ✅ Valid   | `dash_context: "invalid"` | 403 INVALID_CONTEXT         |
| Valid JWT, Wrong Learner   | ✅ Valid   | `learner_uid: "other"`    | 403 LEARNER_SCOPE_VIOLATION |
| Valid JWT, No Consent      | ✅ Valid   | All valid                 | 403 CONSENT_REQUIRED        |
| Valid JWT + All Claims     | ✅ Valid   | Complete claims           | 200 OK                      |

## Consent Logging Requirements

### Append-Only Audit Trail

All consent decisions are logged to PostgreSQL with immutable audit records:

```sql
CREATE TABLE consent_audit_log (
    id SERIAL PRIMARY KEY,
    learner_id VARCHAR(255) NOT NULL,
    actor_user_id VARCHAR(255) NOT NULL,
    consent_key VARCHAR(255) NOT NULL,
    consent_value BOOLEAN NOT NULL,
    ts TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    ip_address INET,
    user_agent TEXT,
    metadata JSONB,
    correlation_id VARCHAR(255)
);
```

### Consent State Management

- **Redis Cache**: Fast consent lookups with 1-hour TTL
- **PostgreSQL**: Authoritative consent state with full audit history
- **Cache Invalidation**: Real-time consent updates invalidate Redis cache
- **Audit Retention**: 7-year retention (2555 days) for compliance

## PII Protection at Inference Edge

### PII Scrubbing Requirements

For AI inference requests, PII must be identified and scrubbed before model processing:

1. **Detection Patterns**:
   - Email addresses: `\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b`
   - Phone numbers: `\b\d{3}-?\d{3}-?\d{4}\b`
   - SSN: `\b\d{3}-?\d{2}-?\d{4}\b`
   - Names: NER model detection
   - Addresses: Pattern + NER detection

2. **Scrubbing Methods**:
   - **Redaction**: Replace with `[REDACTED]`
   - **Tokenization**: Replace with semantic tokens `[EMAIL]`, `[PHONE]`, `[NAME]`
   - **Hashing**: One-way hash for referential integrity

3. **Audit Requirements**:
   - Log PII detection events
   - Track scrubbing method applied
   - Maintain referential mapping for post-processing
   - Correlation with consent audit trail

### Inference Gateway PII Stub Implementation

```python
# Location: services/inference-svc/app/pii_scrubber.py
import re
import hashlib
from typing import Dict, List, Tuple

class PIIScrubber:
    """PII detection and scrubbing for AI inference requests"""

    def scrub_request(self, content: str, learner_id: str) -> Tuple[str, List[Dict]]:
        """Scrub PII from inference request content"""
        pii_findings = []
        scrubbed_content = content

        # Email detection and scrubbing
        email_pattern = r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b'
        emails = re.findall(email_pattern, content, re.IGNORECASE)
        for email in emails:
            token = f"[EMAIL_{hashlib.md5(email.encode()).hexdigest()[:8]}]"
            scrubbed_content = scrubbed_content.replace(email, token)
            pii_findings.append({
                'type': 'email',
                'original': email,
                'token': token,
                'position': content.find(email)
            })

        return scrubbed_content, pii_findings
```

## Security Testing Coverage Requirements

### Minimum Coverage Targets

- **Guard Coverage**: ≥ 80% of security validation paths
- **JWT Test Coverage**: 100% of authentication flows
- **Consent Test Coverage**: 100% of consent enforcement paths
- **PII Scrub Coverage**: ≥ 90% of PII detection patterns

### CI Regression Prevention

```yaml
# .github/workflows/security-tests.yml
name: Security & Privacy Tests
on: [push, pull_request]

jobs:
  security-tests:
    runs-on: ubuntu-latest
    steps:
      - name: Run Security Test Suite
        run: |
          npm run test:security
          python -m pytest tests/security/ --cov=80 --cov-fail-under=80

      - name: JWT Claims Validation
        run: |
          ./scripts/test-jwt-validation.sh

      - name: Consent Logging Tests
        run: |
          ./scripts/test-consent-logging.sh

      - name: PII Scrubbing Tests
        run: |
          python -m pytest tests/pii/ --cov=90 --cov-fail-under=90
```

## Security Monitoring & Alerts

### Metrics Collection

- JWT validation failure rate
- Scope violation attempts
- Consent bypass attempts
- PII detection rate
- Response time impact of security checks

### Alert Thresholds

- JWT failure rate > 5% → WARN
- Scope violations > 10/hour → ALERT
- Consent bypasses > 1/hour → CRITICAL
- PII in inference logs → CRITICAL

## Compliance & Audit

### Privacy Regulations

- **GDPR**: Right to erasure, consent management, audit trails
- **CCPA**: Consumer privacy rights, data minimization
- **FERPA**: Educational records protection
- **COPPA**: Children's privacy protection

### Audit Trail Requirements

1. All consent decisions logged with correlation IDs
2. Security policy violations tracked with context
3. PII scrubbing events recorded with findings
4. JWT validation failures monitored for attack patterns
5. 7-year retention for compliance audit trails

---

_Document Version: 1.0.0_  
_Last Updated: 2024-12-31_  
_Classification: Internal Security Documentation_
