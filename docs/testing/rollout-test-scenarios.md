# Argo Rollouts Progressive Delivery Test Scenarios

This document outlines test scenarios for validating canary and blue/green deployments with automated rollback capabilities.

## Test Environment Setup

```bash
# Deploy Argo Rollouts infrastructure
kubectl apply -f infra/rollouts/rollouts-crds.yaml
kubectl apply -f infra/rollouts/argo-rollouts.yaml
kubectl apply -f infra/rollouts/analysis-templates.yaml
kubectl apply -f infra/rollouts/services.yaml
kubectl apply -f infra/rollouts/ingress.yaml

# Wait for controller to be ready
kubectl wait --for=condition=Available deployment/argo-rollouts -n argo-rollouts --timeout=300s
```

## Scenario 1: Successful Canary Deployment

### Test Case: auth-svc Healthy Canary

```bash
# Deploy initial stable version
kubectl patch rollout auth-svc -n aivo-system --type='merge' -p='{"spec":{"template":{"spec":{"containers":[{"name":"auth-svc","image":"auth-svc:v1.0.0"}]}}}}'

# Wait for stable rollout
kubectl argo rollouts get rollout auth-svc -n aivo-system --watch

# Deploy canary version with good metrics
kubectl patch rollout auth-svc -n aivo-system --type='merge' -p='{"spec":{"template":{"spec":{"containers":[{"name":"auth-svc","image":"auth-svc:v1.1.0"}]}}}}'

# Monitor progression through 5 steps
kubectl argo rollouts get rollout auth-svc -n aivo-system --watch

# Verify traffic split progression
# Step 1: 10% canary traffic
curl -H "X-Canary: true" https://auth.aivo.dev/health
# Step 2: 25% canary traffic
# Step 3: 50% canary traffic
# Step 4: 75% canary traffic
# Step 5: 100% canary traffic

# Expected: Automatic progression with SLO validation at each step
```

### Expected Behavior:

- ✅ Canary starts at 10% traffic
- ✅ Analysis runs for 2 minutes at each step
- ✅ Progression to 25%, 50%, 75%, 100% based on SLO success
- ✅ Final promotion to stable version

## Scenario 2: Failed Canary with Automatic Rollback

### Test Case: auth-svc Bad Version Triggers Rollback

```bash
# Deploy canary version that violates SLOs
kubectl patch rollout auth-svc -n aivo-system --type='merge' -p='{"spec":{"template":{"spec":{"containers":[{"name":"auth-svc","image":"auth-svc:v1.2.0-broken"}]}}}}'

# Monitor rollout status
kubectl argo rollouts get rollout auth-svc -n aivo-system --watch

# Simulate bad metrics (high error rate)
# This would be done by the broken version itself
# curl https://auth.aivo.dev/simulate-errors

# Expected: Automatic pause and rollback
```

### Expected Behavior:

- ✅ Canary starts at 10% traffic
- ❌ Analysis detects SLO violation (success rate < 99.5%)
- ⏸️ Rollout pauses automatically
- 🔄 Automatic rollback to stable version
- ✅ Traffic returns to stable service

## Scenario 3: Manual Canary Testing

### Test Case: Header-Based Canary Testing

```bash
# Deploy canary version
kubectl patch rollout user-svc -n aivo-system --type='merge' -p='{"spec":{"template":{"spec":{"containers":[{"name":"user-svc","image":"user-svc:v2.0.0"}]}}}}'

# Test canary version directly
curl -H "X-Canary: true" https://users.aivo.dev/api/users/profile

# Test stable version
curl https://users.aivo.dev/api/users/profile

# Promote if satisfied
kubectl argo rollouts promote user-svc -n aivo-system

# Or abort if issues found
kubectl argo rollouts abort user-svc -n aivo-system
```

## Scenario 4: Blue/Green Deployment

### Test Case: analytics-svc Blue/Green Switch

```bash
# Deploy new version to preview
kubectl patch rollout analytics-svc -n aivo-system --type='merge' -p='{"spec":{"template":{"spec":{"containers":[{"name":"analytics-svc","image":"analytics-svc:v3.0.0"}]}}}}'

# Monitor blue/green rollout
kubectl argo rollouts get rollout analytics-svc -n aivo-system --watch

# Test preview environment
kubectl port-forward service/analytics-svc-preview 8080:80 -n aivo-system
curl http://localhost:8080/health

# Analysis validates metrics
# Automatic promotion after 5 minutes if SLOs pass
```

### Expected Behavior:

- 🔵 New version deploys to preview (blue)
- 📊 Pre-promotion analysis runs for 5 minutes
- ✅ If SLOs pass, traffic switches to blue
- 📊 Post-promotion analysis validates for 10 minutes
- 🟢 Preview becomes new active environment

## Scenario 5: SLO Violation During Blue/Green

### Test Case: Latency Regression Triggers Rollback

```bash
# Deploy version with high latency
kubectl patch rollout notification-svc -n aivo-system --type='merge' -p='{"spec":{"template":{"spec":{"containers":[{"name":"notification-svc","image":"notification-svc:v1.5.0-slow"}]}}}}'

# Monitor analysis
kubectl get analysisrun -n aivo-system -l rollout=notification-svc --watch

# Expected: Rollback due to P95 latency > 500ms
```

## Scenario 6: Load Testing Integration

### Test Case: Canary Under Load

```bash
# Start load test
kubectl apply -f - <<EOF
apiVersion: batch/v1
kind: Job
metadata:
  name: load-test-auth
  namespace: aivo-system
spec:
  template:
    spec:
      containers:
      - name: load-test
        image: fortio/fortio
        args:
        - load
        - -c
        - "10"
        - -qps
        - "100"
        - -t
        - "10m"
        - https://auth.aivo.dev/api/health
      restartPolicy: Never
EOF

# Deploy canary during load
kubectl patch rollout auth-svc -n aivo-system --type='merge' -p='{"spec":{"template":{"spec":{"containers":[{"name":"auth-svc","image":"auth-svc:v1.3.0"}]}}}}'

# Monitor metrics during load
kubectl argo rollouts get rollout auth-svc -n aivo-system --watch
```

## Monitoring and Observability

### Key Metrics to Monitor:

```bash
# Rollout status
kubectl argo rollouts list rollouts -n aivo-system

# Analysis results
kubectl get analysisrun -n aivo-system

# Rollout events
kubectl get events -n aivo-system --field-selector involvedObject.kind=Rollout

# Service metrics
kubectl port-forward -n prometheus svc/prometheus 9090:9090
# Visit: http://localhost:9090/graph
# Query: sum(rate(http_requests_total[5m])) by (version, service)
```

### Grafana Dashboards:

- Argo Rollouts Overview
- Service SLO Dashboard
- Canary Analysis Dashboard
- Blue/Green Deployment Status

## Troubleshooting

### Common Issues:

1. **Analysis Template Not Found**

```bash
kubectl get analysistemplate -n aivo-system
kubectl describe analysistemplate success-rate-slo -n aivo-system
```

2. **Prometheus Queries Failing**

```bash
# Test query manually
curl -G 'http://prometheus:9090/api/v1/query' \
  --data-urlencode 'query=sum(rate(http_requests_total{service="auth-svc"}[5m]))'
```

3. **Ingress Traffic Not Splitting**

```bash
kubectl get ingress -n aivo-system
kubectl describe ingress auth-svc-canary -n aivo-system
```

4. **Rollout Stuck in Paused State**

```bash
kubectl argo rollouts get rollout auth-svc -n aivo-system
kubectl argo rollouts promote auth-svc -n aivo-system  # Manual promotion
kubectl argo rollouts abort auth-svc -n aivo-system    # Manual abort
```

## Success Criteria

### Canary Deployments:

- ✅ 5-step progression (10→25→50→75→100%)
- ✅ SLO validation at each step
- ✅ Automatic rollback on SLO breach
- ✅ Manual promotion/abort capability

### Blue/Green Deployments:

- ✅ Preview environment validation
- ✅ Instant traffic switching
- ✅ Post-promotion validation
- ✅ Rollback capability

### Analysis & Monitoring:

- ✅ Success rate ≥ 99.5%
- ✅ P95 latency ≤ 500ms
- ✅ Error budget burn rate monitoring
- ✅ Real-time rollout status visibility
