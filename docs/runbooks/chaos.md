# Chaos Engineering Runbook

## 🎯 S4-11 — Chaos & Isolation Tests

**GOAL**: Continuous chaos tests to prove **tenant isolation** and **graceful degradation**

### 📋 Overview

This runbook covers the chaos engineering infrastructure designed to continuously validate:

1. **Tenant Isolation**: Cross-namespace access denial
2. **Graceful Degradation**: Provider failover with meaningful error messages
3. **SRE Alerting**: ≤5 minute alert thresholds for critical failures

### 🔧 Infrastructure Components

#### Test Framework

- **Network Isolation Tests**: `tests/chaos/network-isolation.test.ts`
- **Service Outage Tests**: `tests/chaos/service-outage.test.ts`
- **Playwright Framework**: End-to-end testing with synthetic pod monitoring

#### Chaos Mesh Configurations

- **Tenant Isolation**: `infra/chaos/chaos-mesh/tenant-isolation-chaos.yaml`
- **Provider Outage**: `infra/chaos/chaos-mesh/provider-outage-chaos.yaml`
- **Continuous Schedule**: `infra/chaos/chaos-mesh/continuous-chaos-schedule.yaml`

### 🚀 Quick Start

#### 1. Deploy Chaos Infrastructure

```bash
# Deploy Chaos Mesh operator
kubectl apply -f https://mirrors.chaos-mesh.org/v2.5.1/crd.yaml
kubectl apply -f https://mirrors.chaos-mesh.org/v2.5.1/rbac.yaml
kubectl apply -f https://mirrors.chaos-mesh.org/v2.5.1/chaos-mesh.yaml

# Deploy our chaos experiments
kubectl apply -f infra/chaos/chaos-mesh/
```

#### 2. Run Manual Tests

```bash
# Run tenant isolation tests
cd tests/chaos
npx playwright test network-isolation.test.ts

# Run provider failover tests
npx playwright test service-outage.test.ts
```

#### 3. Monitor Continuous Tests

```bash
# Check chaos experiment status
kubectl get networkchaos,podchaos,httpchaos -n chaos-testing

# View chaos logs
kubectl logs -n chaos-testing -l app=chaos-controller-manager

# Check SRE alerts
kubectl logs -n chaos-testing -l app=sre-alerting
```

### 📊 Test Scenarios

#### Tenant Isolation Validation

**Frequency**: Every 30 minutes
**Duration**: 5-10 minutes per test
**Success Criteria**:

- Cross-tenant API calls return 401/403
- Network policies block inter-tenant traffic
- Synthetic pods cannot access other namespaces

```yaml
# Example chaos experiment
apiVersion: chaos-mesh.org/v1alpha1
kind: NetworkChaos
metadata:
  name: tenant-isolation-network-chaos
spec:
  action: partition
  mode: all
  selector:
    namespaces: [tenant-alice, tenant-bob]
  duration: "30m"
```

#### Provider Failover Testing

**Frequency**: Every 4 hours
**Duration**: 15-20 minutes per test
**Success Criteria**:

- Gateway fails over to secondary provider
- Users receive graceful error messages
- Response times remain under 30 seconds

```yaml
# Example provider outage
apiVersion: chaos-mesh.org/v1alpha1
kind: PodChaos
metadata:
  name: inference-provider-outage
spec:
  action: pod-kill
  mode: fixed-percent
  value: "50"
  selector:
    labelSelectors:
      app: openai-provider
```

### 🚨 Alert Thresholds

#### Critical Alerts (≤5 minutes)

- **Tenant Isolation Breach**: Cross-tenant access succeeds
- **No Provider Failover**: Primary provider down, no fallback
- **SRE System Down**: Chaos tests not running for >30 minutes

#### Warning Alerts (≤15 minutes)

- **Degraded Performance**: Response times >30 seconds
- **High Error Rate**: >20% failed requests
- **Resource Exhaustion**: CPU/memory >85%

### 📱 SRE Integration

#### PagerDuty Integration

```json
{
  "severity": "critical",
  "summary": "Tenant Isolation FAILURE Detected",
  "component": "chaos-engineering",
  "details": {
    "test": "cross-tenant-access-denial",
    "status": "FAILED",
    "escalation": "immediate"
  }
}
```

#### Slack Notifications

```bash
# Webhook URL for #sre-alerts channel
SRE_WEBHOOK_URL="https://hooks.slack.com/services/..."

# Alert message format
curl -X POST -H "Content-Type: application/json" \
  -d '{"text":"🚨 CHAOS TEST FAILED: Tenant isolation breach detected"}' \
  $SRE_WEBHOOK_URL
```

### 🔍 Monitoring & Observability

#### Key Metrics

- **Test Success Rate**: >95% for isolation tests
- **Failover Time**: <30 seconds average
- **Mean Time to Detection**: <5 minutes
- **Mean Time to Recovery**: <15 minutes

#### Grafana Dashboards

- **Chaos Engineering Overview**: Test success rates, alert trends
- **Tenant Isolation Health**: Cross-tenant access attempts, denials
- **Provider Failover Status**: Provider health, failover frequency

#### Prometheus Queries

```promql
# Tenant isolation test success rate
rate(chaos_tenant_isolation_success_total[5m]) / rate(chaos_tenant_isolation_total[5m])

# Provider failover detection
increase(chaos_provider_failover_total[1h])

# Alert response time
histogram_quantile(0.95, chaos_alert_response_time_seconds_bucket)
```

### 🛠️ Troubleshooting

#### Common Issues

**1. Chaos Mesh Not Starting**

```bash
# Check RBAC permissions
kubectl get clusterroles | grep chaos-mesh
kubectl describe clusterrolebinding chaos-mesh

# Verify CRDs installed
kubectl get crd | grep chaos-mesh.org
```

**2. Tests Not Running**

```bash
# Check scheduler status
kubectl get schedule -n chaos-testing
kubectl describe schedule continuous-chaos-schedule

# Check workflow execution
kubectl get workflow -n chaos-testing
kubectl logs -n chaos-testing workflow/tenant-isolation-validation-workflow
```

**3. SRE Alerts Not Firing**

```bash
# Verify webhook configuration
kubectl get secret sre-webhook-config -n chaos-testing -o yaml

# Test webhook manually
curl -X POST $SRE_WEBHOOK_URL -d '{"test":"manual"}'

# Check alert manager logs
kubectl logs -n monitoring alertmanager-0
```

#### Debugging Commands

```bash
# View all chaos experiments
kubectl get chaos --all-namespaces

# Check experiment status
kubectl describe networkchaos tenant-isolation-network-chaos -n chaos-testing

# View experiment logs
kubectl logs -n chaos-testing -l app=chaos-daemon

# Check target pod status
kubectl get pods -n tenant-alice -l app=synthetic-test-pod
```

### 📋 Maintenance Tasks

#### Daily

- [ ] Review chaos test results in Grafana
- [ ] Check SRE alert frequency (should be <5% failure rate)
- [ ] Verify synthetic pods are running

#### Weekly

- [ ] Update chaos experiment schedules if needed
- [ ] Review provider failover performance metrics
- [ ] Test manual alert escalation procedures

#### Monthly

- [ ] Update chaos scenarios based on new features
- [ ] Review and update SRE runbooks
- [ ] Conduct chaos engineering game days

### 🎮 Game Day Procedures

#### Quarterly Chaos Game Day

1. **Pre-Game** (30 min):
   - Announce game day to stakeholders
   - Verify monitoring systems
   - Prepare rollback procedures

2. **Game Execution** (2 hours):
   - Run manual chaos experiments
   - Test cross-team communication
   - Validate alert escalation

3. **Post-Game** (30 min):
   - Document lessons learned
   - Update runbooks
   - Schedule follow-up actions

#### Game Day Scenarios

- **Scenario 1**: Total provider outage (all inference providers down)
- **Scenario 2**: Network partition (50% of tenants isolated)
- **Scenario 3**: Database corruption (tenant data integrity)
- **Scenario 4**: Security breach simulation (lateral movement)

### 📚 Additional Resources

#### Documentation

- [Chaos Mesh Official Docs](https://chaos-mesh.org/docs/)
- [Playwright Testing Guide](https://playwright.dev/docs/intro)
- [SRE Best Practices](https://sre.google/books/)

#### Training Materials

- [Chaos Engineering Principles](https://principlesofchaos.org/)
- [AIVO Multi-Tenant Architecture](../docs/architecture/multi-tenant.md)
- [Provider Failover Design](../docs/architecture/inference-gateway.md)

#### Emergency Contacts

- **SRE On-Call**: +1-555-SRE-HELP
- **Engineering Manager**: eng-manager@aivo.com
- **Security Team**: security-incidents@aivo.com

---

**Last Updated**: $(date)
**Version**: 1.0.0
**Owner**: SRE Team
**Reviewers**: Security, Platform Engineering
