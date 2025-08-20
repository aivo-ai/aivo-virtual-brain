# Edge Security Hardening Guide

## Overview

This document outlines the comprehensive edge security implementation for the AIVO platform, including Web Application Firewall (WAF), bot management, DDoS protection, and rate limiting strategies deployed at the Cloudflare edge and Kong Gateway.

## Architecture

```
Internet → Cloudflare Edge → Kong Gateway → Kubernetes Services
          ↓                  ↓              ↓
     [WAF Rules]        [Rate Limits]   [Service Mesh]
     [Bot Detection]    [Security Plugins] [Network Policies]
     [Geo Blocking]     [Auth Validation]   [RBAC]
```

## Cloudflare Edge Security

### Web Application Firewall (WAF)

Our WAF implementation provides multi-layered protection against common web attacks:

#### Attack Pattern Detection

- **SQL Injection**: Blocks patterns like `union select`, `drop table`, `' or 1=1`
- **XSS Protection**: Filters `<script>`, `javascript:`, event handlers
- **Command Injection**: Prevents path traversal, `/etc/passwd`, shell commands
- **File Upload Security**: Blocks dangerous file extensions (`.php`, `.jsp`, `.exe`)

#### Authentication Spray Protection

```javascript
// Cloudflare Rule Expression
(http.request.uri.path eq "/api/auth/login") and
(http.request.method eq "POST") and
(rate(1m) > 10)
```

#### Bot Score Protection

- **Block**: Bot score < 10 (likely malicious)
- **Challenge**: Bot score < 30 (suspicious)
- **Allow**: Bot score > 80 or verified bots (Google, Bing)

### Geographic Access Controls

#### Sensitive Route Geo-Fencing

- **Admin Routes** (`/admin/*`): Restricted to allowed countries only
- **Authentication** (`/api/auth/*`): Blocked from high-risk countries
- **Inference APIs** (`/api/inference/*`): Challenged from non-allowed regions
- **Payment APIs** (`/api/payment/*`): Blocked from high-risk jurisdictions

#### Configuration

```hcl
# Allowed Countries
allowed_countries = ["US", "CA", "GB", "DE", "FR", "AU", "JP", "SG"]

# Blocked Countries
blocked_countries = ["CN", "RU", "KP", "IR"]
```

### Rate Limiting at Edge

#### Per-Endpoint Limits

| Endpoint                  | Limit         | Window | Mitigation |
| ------------------------- | ------------- | ------ | ---------- |
| `/api/auth/login`         | 5 requests    | 60s    | 600s block |
| `/api/inference/generate` | 10 requests   | 60s    | 300s block |
| `/api/*` (general)        | 100 requests  | 60s    | 60s block  |
| Global                    | 1000 requests | 300s   | 300s block |

#### Identifier Strategies

- **IP-based**: Primary rate limiting by source IP
- **User-based**: Secondary limiting using JWT user ID
- **Credential-based**: Specific protection for login attempts

## Kong Gateway Security

### Rate Limiting Plugins

#### Login Protection

```yaml
# Per-IP rate limiting
- name: rate-limiting-advanced
  route: auth-login
  config:
    limit: [5, 15] # 5/min, 15/hour
    window_size: [60, 3600]
    identifier: ip
    strategy: redis
```

#### Inference Generation Limits

```yaml
# Per-IP and per-user limits
- name: rate-limiting-advanced
  route: inference-generate
  config:
    limit: [10, 100] # 10/min, 100/hour per IP
    window_size: [60, 3600]
    identifier: ip

# Per-user limits (higher allowance)
- name: rate-limiting-advanced
  route: inference-generate
  config:
    limit: [50, 500] # 50/hour, 500/day per user
    window_size: [3600, 86400]
    identifier: header
    header_name: X-User-ID
```

### Security Plugins

#### Bot Detection

```yaml
- name: bot-detection
  route: auth-login
  config:
    deny: ["sqlmap", "nikto", "nessus", "masscan", "zmap"]
    allow: ["googlebot", "bingbot"]
    message: "Bot access denied"
```

#### IP Restriction

```yaml
- name: ip-restriction
  route: auth-login
  config:
    deny:
      - 0.0.0.0/8 # Block local networks
      - 10.0.0.0/8 # Block RFC 1918
      - 172.16.0.0/12
      - 192.168.0.0/16
```

#### Security Headers

```yaml
- name: response-transformer
  config:
    add:
      headers:
        - "X-Frame-Options: DENY"
        - "X-Content-Type-Options: nosniff"
        - "X-XSS-Protection: 1; mode=block"
        - "Referrer-Policy: strict-origin-when-cross-origin"
```

## Security Monitoring

### Cloudflare Analytics

- **Firewall Events**: Real-time WAF rule triggers
- **Bot Requests**: Bot score distribution and blocked attempts
- **Rate Limit Events**: Edge rate limiting violations
- **Geographic Analysis**: Request patterns by country

### Kong Metrics

- **Request Rates**: Per-route and per-consumer metrics
- **Error Rates**: 4xx/5xx response tracking
- **Latency Metrics**: P50, P95, P99 response times
- **Plugin Performance**: Rate limiting and security plugin metrics

### Log Aggregation

```yaml
# Kong file logging
- name: file-log
  config:
    path: "/tmp/kong-access.log"
    custom_fields_by_lua:
      user_id: "return kong.request.get_header('X-User-ID')"
      bot_score: "return kong.request.get_header('CF-Bot-Score')"
```

## Incident Response

### Attack Detection

1. **Automated Blocking**: WAF rules trigger immediate blocks
2. **Rate Limit Violations**: Progressive throttling with increasing timeouts
3. **Bot Detection**: Score-based challenge/block decisions
4. **Geographic Violations**: Country-based access controls

### Alert Thresholds

- **High Rate of Blocks**: >100 WAF blocks in 5 minutes
- **Bot Attack**: >50 low-score bot requests in 1 minute
- **Rate Limit Breaches**: >10 users hitting limits simultaneously
- **Geographic Anomalies**: Requests from blocked countries

### Response Procedures

1. **Assess Threat Level**: Review attack patterns and volume
2. **Adjust WAF Rules**: Tighten rules for active attack patterns
3. **Update Rate Limits**: Temporarily reduce limits if needed
4. **Geographic Blocking**: Add new countries to block list
5. **Coordinate with Teams**: Notify security and platform teams

## Testing and Validation

### Synthetic Attack Tests

```bash
# SQL Injection Test
curl -X POST "https://api.aivo.dev/api/auth/login" \
  -d "username=admin' OR 1=1--&password=test"
# Expected: 403 Blocked by WAF

# Rate Limit Test
for i in {1..10}; do
  curl -X POST "https://api.aivo.dev/api/auth/login" \
    -d "username=test&password=test"
done
# Expected: 429 Rate Limited after 5 requests

# Bot Detection Test
curl -X GET "https://api.aivo.dev/" \
  -H "User-Agent: sqlmap/1.0"
# Expected: 403 Blocked by bot detection
```

### Geographic Access Validation

```bash
# Test from allowed country (US)
curl -X GET "https://admin.aivo.dev/" \
  -H "CF-IPCountry: US"
# Expected: 200 OK (or proper auth challenge)

# Test from blocked country (CN)
curl -X GET "https://admin.aivo.dev/" \
  -H "CF-IPCountry: CN"
# Expected: 403 Blocked
```

### Load Testing

```bash
# High-volume inference testing
k6 run --vus 50 --duration 60s inference-load-test.js
# Verify rate limits engage appropriately

# Authentication spray simulation
k6 run --vus 20 --duration 30s auth-spray-test.js
# Verify progressive blocking and challenges
```

## Configuration Management

### Terraform Deployment

```bash
# Deploy Cloudflare WAF rules
cd infra/edge
terraform init
terraform plan -var-file="prod.tfvars"
terraform apply

# Variables
cloudflare_zone_id = "your-zone-id"
allowed_countries = ["US", "CA", "GB", "DE", "FR", "AU", "JP", "SG"]
blocked_countries = ["CN", "RU", "KP", "IR"]
```

### Kong Configuration

```bash
# Apply Kong configuration
kubectl apply -f apps/gateway/kong.yml

# Validate configuration
kong config parse apps/gateway/kong.yml

# Test rate limiting
kong health
```

### Cloudflare Workers

```bash
# Deploy edge worker
wrangler deploy infra/edge/cf-workers.js

# Configure KV namespaces
wrangler kv:namespace create "RATE_LIMIT_KV"
wrangler kv:namespace create "SECURITY_LOGS_KV"
```

## Performance Impact

### Cloudflare Edge

- **WAF Processing**: < 1ms additional latency
- **Bot Detection**: < 0.5ms for score lookup
- **Rate Limiting**: < 0.1ms for counter updates
- **Geographic Filtering**: No measurable impact

### Kong Gateway

- **Rate Limiting Plugin**: 1-3ms per request
- **Bot Detection**: 0.5-1ms user agent parsing
- **Security Headers**: < 0.1ms response modification
- **IP Restriction**: < 0.1ms IP lookup

### Optimization Strategies

1. **Redis Clustering**: Distribute rate limit counters
2. **Plugin Ordering**: Place fast plugins first
3. **Caching**: Cache WAF decisions for repeated patterns
4. **Geographic Edge**: Deploy Kong at edge locations

## Compliance and Auditing

### Security Standards

- **OWASP Top 10**: Protection against all major web vulnerabilities
- **PCI DSS**: Payment route protection with geo-fencing
- **GDPR**: Geographic controls for EU data protection
- **SOC 2**: Comprehensive logging and monitoring

### Audit Trails

- **WAF Events**: All blocks and challenges logged to S3
- **Kong Access Logs**: Detailed request/response logging
- **Rate Limit Events**: Stored in Redis with TTL
- **Geographic Decisions**: Logged with country codes

### Regular Reviews

- **Monthly**: WAF rule effectiveness analysis
- **Quarterly**: Rate limit threshold optimization
- **Bi-annually**: Geographic restriction review
- **Annually**: Full security posture assessment

## Troubleshooting

### Common Issues

#### False Positives

```bash
# Review WAF logs for legitimate blocks
curl -X GET "https://api.cloudflare.com/client/v4/zones/{zone_id}/firewall/events" \
  -H "Authorization: Bearer {api_token}"

# Whitelist specific patterns if needed
# Add to WAF rule: and not (http.request.uri.query contains "legitimate_pattern")
```

#### Rate Limit Tuning

```bash
# Monitor rate limit violations
kubectl logs -l app=kong -n aivo-system | grep "rate-limit"

# Adjust limits in kong.yml and redeploy
# Consider user behavior patterns and business requirements
```

#### Geographic Access Issues

```bash
# Check country detection accuracy
curl -H "CF-Connecting-IP: {test_ip}" https://api.aivo.dev/

# Verify IP geolocation database
# Update allowed/blocked country lists as needed
```

### Emergency Procedures

#### Disable WAF (Emergency Only)

```bash
# Temporarily disable WAF rules
terraform apply -var="enable_waf=false"

# Or use Cloudflare dashboard:
# Security > WAF > Custom Rules > Disable specific rules
```

#### Increase Rate Limits

```bash
# Emergency rate limit increase
kubectl patch configmap kong-config -n aivo-system --patch '
data:
  rate_limit_emergency: "true"
  emergency_multiplier: "5"
'
kubectl rollout restart deployment kong -n aivo-system
```

#### Geographic Emergency Access

```bash
# Temporarily allow all countries
terraform apply -var="emergency_access=true"

# Restore restrictions after incident
terraform apply -var="emergency_access=false"
```

## Future Enhancements

### Planned Improvements

1. **Machine Learning WAF**: Adaptive rules based on attack patterns
2. **Behavioral Analysis**: User behavior anomaly detection
3. **Advanced Bot Management**: CAPTCHA integration and device fingerprinting
4. **Zero Trust Network**: Complete request verification pipeline

### Integration Roadmap

- **Q1**: Enhanced bot detection with device fingerprinting
- **Q2**: ML-based anomaly detection for rate limiting
- **Q3**: Advanced geographic analysis with VPN detection
- **Q4**: Zero-trust architecture implementation

---

## References

- [Cloudflare WAF Documentation](https://developers.cloudflare.com/waf/)
- [Kong Rate Limiting Plugin](https://docs.konghq.com/hub/kong-inc/rate-limiting-advanced/)
- [OWASP Security Guidelines](https://owasp.org/www-project-top-ten/)
- [AIVO Security Architecture](../architecture/security-overview.md)
