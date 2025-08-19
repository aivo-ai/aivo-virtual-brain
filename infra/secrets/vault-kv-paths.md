# Vault KV Secret Paths for AIVO Platform

This document outlines the Vault KV secret paths used by AIVO services for secret injection via Vault Agent Injector.

## Vault Configuration

- **Vault Address**: `https://vault.aivo.ai`
- **Auth Method**: Kubernetes auth
- **KV Mount**: `secret/`
- **Kubernetes Role Prefix**: Service name (e.g., `auth-svc`, `user-svc`)

## Service Secret Paths

### Auth Service (`auth-svc`)

**Path**: `secret/data/aivo/auth-svc`

```json
{
  "database_url": "postgres://auth_user:password@postgres.aivo.ai:5432/auth_db",
  "jwt_secret": "base64-encoded-jwt-secret-256-bits",
  "jwt_refresh_secret": "base64-encoded-refresh-secret-256-bits",
  "bcrypt_rounds": "12",
  "session_secret": "base64-encoded-session-secret-256-bits",
  "oauth_google_client_id": "google-oauth-client-id",
  "oauth_google_client_secret": "google-oauth-client-secret",
  "oauth_microsoft_client_id": "microsoft-oauth-client-id",
  "oauth_microsoft_client_secret": "microsoft-oauth-client-secret"
}
```

### User Service (`user-svc`)

**Path**: `secret/data/aivo/user-svc`

```json
{
  "database_url": "postgres://user_user:password@postgres.aivo.ai:5432/user_db",
  "redis_url": "redis://redis.aivo.ai:6379/0",
  "s3_access_key": "aws-s3-access-key",
  "s3_secret_key": "aws-s3-secret-key",
  "s3_bucket": "aivo-user-uploads",
  "encryption_key": "base64-encoded-aes-256-key"
}
```

### Inference Gateway Service (`inference-gateway-svc`)

**Path**: `secret/data/aivo/inference-gateway-svc`

```json
{
  "database_url": "postgres://inference_user:password@postgres.aivo.ai:5432/inference_db",
  "redis_url": "redis://redis.aivo.ai:6379/1",
  "openai_api_key": "sk-openai-api-key",
  "anthropic_api_key": "sk-ant-anthropic-api-key",
  "huggingface_api_key": "hf_huggingface-api-key",
  "model_registry_url": "https://models.aivo.ai",
  "model_registry_auth": "bearer-token-for-model-registry",
  "rate_limit_redis_url": "redis://redis.aivo.ai:6379/2"
}
```

### Analytics Service (`analytics-svc`)

**Path**: `secret/data/aivo/analytics-svc`

```json
{
  "database_url": "postgres://analytics_user:password@postgres.aivo.ai:5432/analytics_db",
  "clickhouse_url": "https://clickhouse.aivo.ai:8443",
  "clickhouse_user": "analytics_user",
  "clickhouse_password": "clickhouse-password",
  "s3_analytics_bucket": "aivo-analytics-data",
  "prometheus_bearer_token": "prometheus-bearer-token"
}
```

### Assessment Service (`assessment-svc`)

**Path**: `secret/data/aivo/assessment-svc`

```json
{
  "database_url": "postgres://assessment_user:password@postgres.aivo.ai:5432/assessment_db",
  "redis_url": "redis://redis.aivo.ai:6379/3",
  "ai_grading_api_key": "api-key-for-ai-grading",
  "s3_assessment_bucket": "aivo-assessments"
}
```

### Learner Service (`learner-svc`)

**Path**: `secret/data/aivo/learner-svc`

```json
{
  "database_url": "postgres://learner_user:password@postgres.aivo.ai:5432/learner_db",
  "redis_url": "redis://redis.aivo.ai:6379/4",
  "vector_db_url": "https://pinecone.aivo.ai",
  "vector_db_api_key": "pinecone-api-key",
  "learning_analytics_key": "learning-analytics-secret"
}
```

### Payment Service (`payment-svc`)

**Path**: `secret/data/aivo/payment-svc`

```json
{
  "database_url": "postgres://payment_user:password@postgres.aivo.ai:5432/payment_db",
  "stripe_secret_key": "sk_live_stripe-secret-key",
  "stripe_webhook_secret": "whsec_stripe-webhook-secret",
  "paypal_client_id": "paypal-client-id",
  "paypal_client_secret": "paypal-client-secret",
  "encryption_key": "base64-encoded-payment-encryption-key"
}
```

### Notification Service (`notification-svc`)

**Path**: `secret/data/aivo/notification-svc`

```json
{
  "database_url": "postgres://notification_user:password@postgres.aivo.ai:5432/notification_db",
  "sendgrid_api_key": "SG.sendgrid-api-key",
  "twilio_account_sid": "twilio-account-sid",
  "twilio_auth_token": "twilio-auth-token",
  "slack_webhook_url": "https://hooks.slack.com/services/webhook-url",
  "firebase_admin_key": "firebase-admin-service-account-json"
}
```

## Vault Policies

### Service-Specific Policy Template

```hcl
# Policy for {service-name}
path "secret/data/aivo/{service-name}" {
  capabilities = ["read"]
}

path "secret/metadata/aivo/{service-name}" {
  capabilities = ["read"]
}
```

### Platform Policy (for shared secrets)

```hcl
# Platform-wide shared secrets
path "secret/data/aivo/platform/*" {
  capabilities = ["read"]
}

path "secret/metadata/aivo/platform/*" {
  capabilities = ["read"]
}
```

## Kubernetes Auth Configuration

### Role Binding Template

```hcl
# Vault role for {service-name}
vault write auth/kubernetes/role/{service-name} \
    bound_service_account_names={service-name} \
    bound_service_account_namespaces=aivo-services \
    policies={service-name}-policy \
    ttl=24h
```

## Secret Rotation

- **Database passwords**: Rotated monthly via Vault database secrets engine
- **API keys**: Rotated quarterly or when compromised
- **Encryption keys**: Rotated annually with versioning support
- **OAuth secrets**: Rotated when providers require or annually

## Security Considerations

1. **Least Privilege**: Each service only has access to its own secrets
2. **Audit Logging**: All secret access is logged in Vault audit logs
3. **TTL Management**: Secrets have appropriate TTL based on sensitivity
4. **Encryption in Transit**: All Vault communication uses TLS
5. **Secret Versioning**: KV v2 engine provides secret versioning and rollback capabilities

## Emergency Procedures

### Secret Compromise Response

1. Immediately rotate the compromised secret in Vault
2. Update the secret value at the appropriate path
3. Restart affected pods to inject new secrets
4. Audit logs to determine scope of compromise
5. Update monitoring alerts for unusual access patterns

### Vault Unavailability

1. Pods will continue running with cached secrets
2. New deployments will fail until Vault is restored
3. Emergency break-glass procedures documented in runbook
4. Backup static secrets for critical services (encrypted at rest)
