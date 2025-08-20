# Release Strategy Runbook

## Overview

This runbook provides operational procedures for managing progressive delivery with Argo Rollouts in the AIVO platform. It covers canary deployments, blue/green deployments, and automated rollback strategies.

## Release Strategies

### Canary Deployment Strategy

**When to Use:**

- High-traffic services (auth-svc, user-svc, inference-gateway-svc)
- New features with unknown performance impact
- Critical path services requiring gradual validation

**Traffic Split Pattern:**

```
10% → 25% → 50% → 75% → 100%
```

**SLO Gates:**

- Success Rate: ≥ 99.5%
- P95 Latency: ≤ 500ms
- Error Budget: < 10% burn rate

### Blue/Green Deployment Strategy

**When to Use:**

- Analytics and reporting services
- Background processing services
- Services with complex state transitions

**Pattern:**

```
Blue (Current) → Green (Preview) → Switch → Validate
```

**Validation Period:**

- Pre-promotion: 5 minutes
- Post-promotion: 10 minutes

## Operational Procedures

### 1. Pre-Release Checklist

```bash
# Verify Argo Rollouts health
kubectl get pods -n argo-rollouts
kubectl argo rollouts version

# Check analysis templates
kubectl get analysistemplate -n aivo-system

# Verify Prometheus connectivity
kubectl port-forward -n prometheus svc/prometheus 9090:9090 &
curl -s http://localhost:9090/-/healthy

# Validate service baseline metrics
kubectl argo rollouts get rollout <service-name> -n aivo-system
```

### 2. Initiating a Canary Release

```bash
# Method 1: Update image via kubectl
kubectl patch rollout <service-name> -n aivo-system \
  --type='merge' \
  -p='{"spec":{"template":{"spec":{"containers":[{"name":"<service-name>","image":"<service-name>:<new-version>"}]}}}}'

# Method 2: Update via Argo CD
argocd app set <app-name> --helm-set image.tag=<new-version>
argocd app sync <app-name>

# Method 3: Update rollout manifest
# Edit the rollout YAML and apply
kubectl apply -f rollouts/<service-name>-rollout.yaml
```

### 3. Monitoring Canary Progress

```bash
# Watch rollout status
kubectl argo rollouts get rollout <service-name> -n aivo-system --watch

# Check analysis results
kubectl get analysisrun -n aivo-system -l rollout=<service-name> --watch

# Monitor traffic split
kubectl get ingress <service-name>-canary -n aivo-system -o yaml | grep canary-weight

# View rollout events
kubectl get events -n aivo-system --field-selector involvedObject.name=<service-name>
```

### 4. Manual Canary Control

```bash
# Promote to next step
kubectl argo rollouts promote <service-name> -n aivo-system

# Skip analysis and promote
kubectl argo rollouts promote <service-name> -n aivo-system --skip-current-step

# Abort rollout (triggers rollback)
kubectl argo rollouts abort <service-name> -n aivo-system

# Pause rollout (manual intervention required)
kubectl argo rollouts pause <service-name> -n aivo-system

# Resume paused rollout
kubectl argo rollouts resume <service-name> -n aivo-system
```

### 5. Blue/Green Release Process

```bash
# Initiate blue/green deployment
kubectl patch rollout <service-name> -n aivo-system \
  --type='merge' \
  -p='{"spec":{"template":{"spec":{"containers":[{"name":"<service-name>","image":"<service-name>:<new-version>"}]}}}}'

# Monitor preview environment
kubectl port-forward service/<service-name>-preview 8080:80 -n aivo-system
curl http://localhost:8080/health

# Manual testing of preview
# Run integration tests against preview service

# Check pre-promotion analysis
kubectl get analysisrun -n aivo-system -l rollout=<service-name>

# Manual promotion (if analysis passes)
kubectl argo rollouts promote <service-name> -n aivo-system
```

### 6. Rollback Procedures

#### Automatic Rollback

- Triggered when SLO analysis fails
- No manual intervention required
- Traffic automatically returns to stable version

#### Manual Rollback

```bash
# Immediate rollback during active rollout
kubectl argo rollouts abort <service-name> -n aivo-system

# Rollback to previous stable version
kubectl argo rollouts undo <service-name> -n aivo-system

# Rollback to specific revision
kubectl argo rollouts undo <service-name> -n aivo-system --to-revision=3
```

## Incident Response

### Rollout Stuck in Degraded State

**Symptoms:**

- Analysis continuously failing
- Rollout not progressing
- High error rates in canary traffic

**Actions:**

1. Check analysis results
2. Review service logs
3. Abort rollout if needed
4. Investigate root cause

```bash
# Diagnose analysis failure
kubectl describe analysisrun $(kubectl get analysisrun -n aivo-system -l rollout=<service-name> -o name | head -1) -n aivo-system

# Check service logs
kubectl logs -l app=<service-name>,rollouts-pod-template-hash=<canary-hash> -n aivo-system

# Force abort if stuck
kubectl argo rollouts abort <service-name> -n aivo-system
```

### SLO Breach Detection

**Immediate Actions:**

1. Verify if automatic rollback triggered
2. Check Prometheus for metric accuracy
3. Investigate canary version issues
4. Communicate to stakeholders

```bash
# Check current rollout status
kubectl argo rollouts get rollout <service-name> -n aivo-system

# Verify metrics in Prometheus
kubectl port-forward -n prometheus svc/prometheus 9090:9090 &
# Navigate to: http://localhost:9090/graph
# Query: (sum(rate(http_requests_total{service="<service-name>",code!~"5.."}[5m])) / sum(rate(http_requests_total{service="<service-name>"}[5m]))) * 100
```

### Traffic Split Issues

**Symptoms:**

- Canary not receiving expected traffic
- Ingress annotations not updating
- Load balancer configuration problems

**Troubleshooting:**

```bash
# Check ingress configuration
kubectl get ingress <service-name>-canary -n aivo-system -o yaml

# Verify service endpoints
kubectl get endpoints <service-name>-canary -n aivo-system

# Test traffic routing
curl -H "X-Canary: true" https://<service-name>.aivo.dev/health
curl https://<service-name>.aivo.dev/health

# Check NGINX controller logs
kubectl logs -n ingress-nginx -l app.kubernetes.io/name=ingress-nginx
```

## Monitoring and Alerting

### Key Metrics to Monitor

1. **Rollout Success Rate**
   - Successful deployments vs. rollbacks
   - Time to complete rollout

2. **Service Health Metrics**
   - HTTP success rate
   - Response latency (P50, P95, P99)
   - Error rates by service

3. **Analysis Metrics**
   - Analysis success/failure rate
   - SLO breach frequency
   - Rollback trigger causes

### Alerting Rules

```yaml
# Example Prometheus alerting rules
groups:
  - name: argo-rollouts
    rules:
      - alert: RolloutFailed
        expr: |
          increase(rollout_phase_duration_seconds{phase="Aborted"}[5m]) > 0
        for: 0m
        labels:
          severity: critical
        annotations:
          summary: "Argo Rollout failed for {{ $labels.rollout }}"

      - alert: CanaryAnalysisFailed
        expr: |
          argo_rollouts_analysis_run_phase{phase="Failed"} > 0
        for: 0m
        labels:
          severity: warning
        annotations:
          summary: "Canary analysis failed for {{ $labels.analysisrun }}"
```

### Grafana Dashboards

1. **Argo Rollouts Overview**
   - Active rollouts status
   - Rollout success/failure rates
   - Analysis run results

2. **Service SLO Dashboard**
   - Success rate trends
   - Latency distributions
   - Error budget burn rates

3. **Release Timeline**
   - Deployment frequency
   - Lead time for changes
   - Recovery time metrics

## Best Practices

### Development Guidelines

1. **Service Readiness**
   - Implement proper health checks
   - Expose Prometheus metrics
   - Handle graceful shutdown

2. **Testing Strategy**
   - Automated smoke tests for canary
   - Load testing in staging
   - Chaos engineering validation

3. **Configuration Management**
   - Version rollout configurations
   - Test analysis templates in staging
   - Document SLO thresholds

### Operational Guidelines

1. **Release Timing**
   - Avoid releases during peak hours
   - Schedule blue/green during maintenance windows
   - Coordinate with on-call rotation

2. **Communication**
   - Notify stakeholders of releases
   - Document rollback procedures
   - Maintain release notes

3. **Continuous Improvement**
   - Review rollback incidents
   - Tune SLO thresholds based on data
   - Optimize analysis duration

## Emergency Procedures

### Service Down Scenario

```bash
# Quick rollback to last known good version
kubectl argo rollouts undo <service-name> -n aivo-system

# Scale up stable pods if needed
kubectl scale deployment <service-name> --replicas=5 -n aivo-system

# Bypass canary and go direct to stable
kubectl patch rollout <service-name> -n aivo-system \
  --type='merge' \
  -p='{"spec":{"strategy":{"canary":{"steps":[{"setWeight":100}]}}}}'
```

### Mass Rollback Scenario

```bash
# Script to rollback all active rollouts
for rollout in $(kubectl get rollouts -n aivo-system -o name); do
  echo "Rolling back $rollout"
  kubectl argo rollouts abort $rollout -n aivo-system
done
```

### Analysis Template Issues

```bash
# Disable analysis for emergency deployment
kubectl patch rollout <service-name> -n aivo-system \
  --type='merge' \
  -p='{"spec":{"strategy":{"canary":{"analysis":null}}}}'

# Re-enable after fixing
kubectl apply -f rollouts/<service-name>-rollout.yaml
```

## Support and Escalation

### L1 Support (Operations Team)

- Monitor rollout progress
- Execute standard runbook procedures
- Escalate if analysis consistently fails

### L2 Support (Platform Team)

- Investigate analysis template issues
- Troubleshoot traffic routing problems
- Tune SLO thresholds

### L3 Support (Development Team)

- Fix service-specific issues
- Update rollout configurations
- Investigate performance regressions

### Emergency Contacts

- Platform Team: #platform-engineering
- On-call Engineer: #incidents
- Service Owners: #service-teams

---

## Appendix

### Useful Commands Reference

```bash
# List all rollouts
kubectl argo rollouts list rollouts -A

# Get rollout history
kubectl argo rollouts history <service-name> -n aivo-system

# Describe analysis template
kubectl describe analysistemplate <template-name> -n aivo-system

# Watch all analysis runs
kubectl get analysisrun -A --watch

# Export rollout configuration
kubectl get rollout <service-name> -n aivo-system -o yaml > backup.yaml
```

### Configuration Examples

See `infra/rollouts/` directory for complete configuration examples:

- `canary-rollouts.yaml` - Canary deployment configurations
- `bluegreen-rollouts.yaml` - Blue/green deployment configurations
- `analysis-templates.yaml` - SLO analysis templates
- `ingress.yaml` - Traffic routing configurations
