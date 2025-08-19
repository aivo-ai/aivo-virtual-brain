# AIVO Platform Deployment Runbook

This runbook covers deployment procedures for the AIVO platform using GitOps with Argo CD, Helm charts, and Vault secret injection.

## Prerequisites

### Tools Required

- `kubectl` - Kubernetes CLI
- `helm` - Helm package manager
- `argocd` - Argo CD CLI
- `vault` - Vault CLI
- `git` - Git client

### Access Requirements

- Kubernetes cluster access with appropriate RBAC
- Argo CD web UI or CLI access
- Vault authentication (Kubernetes auth method)
- Git repository access for infra changes

## Architecture Overview

```
┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│   Git Repo      │    │   Argo CD       │    │   Kubernetes    │
│                 │    │                 │    │                 │
│ infra/argocd/   │───▶│ App-of-Apps     │───▶│ aivo-platform   │
│ infra/helm/     │    │                 │    │ aivo-services   │
│                 │    │ Applications    │    │ aivo-monitoring │
└─────────────────┘    └─────────────────┘    └─────────────────┘
                              │
                              ▼
                       ┌─────────────────┐
                       │   Vault         │
                       │ Secret Injection│
                       └─────────────────┘
```

## Initial Platform Setup

### 1. Bootstrap Argo CD

If Argo CD is not already installed:

```bash
# Install Argo CD
kubectl create namespace argocd
kubectl apply -n argocd -f https://raw.githubusercontent.com/argoproj/argo-cd/stable/manifests/install.yaml

# Wait for Argo CD to be ready
kubectl wait --for=condition=available --timeout=300s deployment/argocd-server -n argocd

# Get initial admin password
kubectl -n argocd get secret argocd-initial-admin-secret -o jsonpath="{.data.password}" | base64 -d
```

### 2. Configure Vault Authentication

```bash
# Enable Kubernetes auth method
vault auth enable kubernetes

# Configure Kubernetes auth
vault write auth/kubernetes/config \
    token_reviewer_jwt="$(cat /var/run/secrets/kubernetes.io/serviceaccount/token)" \
    kubernetes_host="https://kubernetes.default.svc.cluster.local" \
    kubernetes_ca_cert=@/var/run/secrets/kubernetes.io/serviceaccount/ca.crt

# Create service-specific policies and roles (see vault-kv-paths.md)
```

### 3. Deploy App-of-Apps

```bash
# Apply the app-of-apps to bootstrap the platform
kubectl apply -f infra/argocd/app-of-apps.yaml

# Verify app-of-apps is synced
argocd app get aivo-app-of-apps
```

## Service Deployment Procedures

### Standard Service Deployment

1. **Prepare Helm Chart**
   ```bash
   # Copy template to new service
   cp -r infra/helm/services/_template infra/helm/services/new-service-svc
   
   # Update Chart.yaml with service-specific information
   # Update values.yaml with service configuration
   ```

2. **Create Argo CD Application**
   ```bash
   # Create Argo CD app manifest
   cp infra/argocd/apps/auth-svc.yaml infra/argocd/apps/new-service-svc.yaml
   # Update with service-specific configuration
   ```

3. **Validate Helm Chart**
   ```bash
   # Template the chart locally
   helm template new-service-svc infra/helm/services/new-service-svc \
     --values infra/helm/services/new-service-svc/values.yaml \
     --dry-run
   
   # Validate Kubernetes manifests
   helm template new-service-svc infra/helm/services/new-service-svc | kubectl apply --dry-run=client -f -
   ```

4. **Commit and Push**
   ```bash
   git add infra/helm/services/new-service-svc infra/argocd/apps/new-service-svc.yaml
   git commit -m "feat(k8s): add new-service-svc helm chart and argocd app"
   git push origin main
   ```

5. **Monitor Deployment**
   ```bash
   # Check Argo CD sync status
   argocd app get new-service-svc
   argocd app sync new-service-svc
   
   # Monitor pod status
   kubectl get pods -n aivo-services -l app.kubernetes.io/name=new-service-svc
   
   # Check logs
   kubectl logs -n aivo-services -l app.kubernetes.io/name=new-service-svc
   ```

### Emergency Deployment (Fast-track)

For critical fixes that need immediate deployment:

```bash
# Temporarily disable auto-sync
argocd app patch service-name --patch '{"spec":{"syncPolicy":{"automated":null}}}'

# Apply specific change
kubectl patch deployment service-name -n aivo-services -p '{"spec":{"template":{"spec":{"containers":[{"name":"service-name","image":"new-image:tag"}]}}}}'

# Verify fix
kubectl rollout status deployment/service-name -n aivo-services

# Re-enable auto-sync and sync to git state
argocd app patch service-name --patch '{"spec":{"syncPolicy":{"automated":{"prune":true,"selfHeal":true}}}}'
argocd app sync service-name
```

## Troubleshooting Guide

### Common Issues

#### 1. Argo CD Application Out of Sync

**Symptoms**: Application shows "OutOfSync" status

**Diagnosis**:
```bash
argocd app get service-name
argocd app diff service-name
```

**Resolution**:
```bash
# Force sync
argocd app sync service-name --force

# If persistent, check for manual changes
kubectl get deployment service-name -n aivo-services -o yaml | grep -E "image:|replicas:"
```

#### 2. Vault Secret Injection Failures

**Symptoms**: Pods stuck in Init or have vault agent errors

**Diagnosis**:
```bash
# Check vault agent logs
kubectl logs pod-name -n aivo-services -c vault-agent-init

# Verify vault role and policy
vault read auth/kubernetes/role/service-name
vault policy read service-name-policy
```

**Resolution**:
```bash
# Test vault authentication
kubectl exec -it pod-name -n aivo-services -- vault auth -method=kubernetes role=service-name

# Update vault role if needed
vault write auth/kubernetes/role/service-name \
    bound_service_account_names=service-name \
    bound_service_account_namespaces=aivo-services \
    policies=service-name-policy \
    ttl=24h
```

#### 3. Pod Security Policy Violations

**Symptoms**: Pods fail to start with security context errors

**Diagnosis**:
```bash
kubectl describe pod pod-name -n aivo-services
kubectl get events -n aivo-services --field-selector involvedObject.name=pod-name
```

**Resolution**:
```bash
# Update security context in Helm values
# Ensure runAsNonRoot: true and appropriate user IDs
# Verify no privileged containers or capabilities
```

#### 4. Resource Constraints

**Symptoms**: Pods stuck in Pending state or frequent OOMKills

**Diagnosis**:
```bash
kubectl describe pod pod-name -n aivo-services
kubectl top pods -n aivo-services
kubectl get events -n aivo-services --sort-by=.metadata.creationTimestamp
```

**Resolution**:
```bash
# Adjust resource requests/limits in Helm values
# Check node capacity
kubectl describe nodes
kubectl get nodes -o custom-columns=NAME:.metadata.name,CPU-CAPACITY:.status.capacity.cpu,MEMORY-CAPACITY:.status.capacity.memory
```

### Health Checks

#### Platform Health

```bash
# Check all applications
argocd app list

# Check platform components
kubectl get pods -n aivo-platform
kubectl get pods -n aivo-services
kubectl get pods -n aivo-monitoring

# Check ingress
kubectl get ingress -n aivo-services
```

#### Service Health

```bash
# Check specific service
kubectl get pods -n aivo-services -l app.kubernetes.io/name=service-name
kubectl get svc -n aivo-services -l app.kubernetes.io/name=service-name
kubectl get hpa -n aivo-services -l app.kubernetes.io/name=service-name

# Test service endpoints
kubectl port-forward svc/service-name -n aivo-services 8080:8080
curl http://localhost:8080/health
```

## Scaling Procedures

### Manual Scaling

```bash
# Scale deployment
kubectl scale deployment service-name -n aivo-services --replicas=5

# Update HPA
kubectl patch hpa service-name -n aivo-services -p '{"spec":{"maxReplicas":20}}'
```

### Auto-scaling Configuration

Update HPA settings in Helm values:

```yaml
autoscaling:
  enabled: true
  minReplicas: 3
  maxReplicas: 20
  targetCPUUtilizationPercentage: 70
  targetMemoryUtilizationPercentage: 80
```

## Rollback Procedures

### Application Rollback

```bash
# Rollback to previous revision
kubectl rollout undo deployment/service-name -n aivo-services

# Rollback to specific revision
kubectl rollout undo deployment/service-name -n aivo-services --to-revision=2

# Check rollout status
kubectl rollout status deployment/service-name -n aivo-services
```

### Git-based Rollback

```bash
# Revert git commit
git revert commit-hash
git push origin main

# Sync Argo CD application
argocd app sync service-name
```

## Monitoring and Alerting

### Key Metrics to Monitor

- Application sync status in Argo CD
- Pod restart counts and failure rates
- Resource utilization (CPU, memory)
- HTTP response times and error rates
- Vault secret injection success rate

### Prometheus Queries

```promql
# Application deployment health
up{job="kubernetes-pods", namespace="aivo-services"}

# Pod restart rate
rate(kube_pod_container_status_restarts_total[5m])

# Memory usage
container_memory_usage_bytes{namespace="aivo-services"} / container_spec_memory_limit_bytes

# HTTP error rate
rate(http_requests_total{status=~"5.."}[5m]) / rate(http_requests_total[5m])
```

### Grafana Dashboards

- **Platform Overview**: Cluster resources, namespace status
- **Application Health**: Service availability, response times
- **GitOps Status**: Argo CD application sync status
- **Security**: Vault secret injection, pod security violations

## Security Considerations

### Regular Security Tasks

1. **Rotate Vault Secrets**: Monthly rotation of database passwords
2. **Update Base Images**: Weekly security updates
3. **Review RBAC**: Quarterly access review
4. **Audit Logs**: Daily review of Vault audit logs
5. **Network Policies**: Validate network segmentation

### Incident Response

1. **Security Incident**: Immediately rotate compromised secrets
2. **Breach Detection**: Isolate affected services via network policies
3. **Forensics**: Preserve logs and audit trails
4. **Recovery**: Restore from clean state, update security controls

## Backup and Recovery

### Backup Procedures

```bash
# Backup Argo CD applications
argocd app list -o json > argocd-applications-backup.json

# Backup Vault policies and roles
vault policy list | xargs -I {} vault policy read {} > vault-policies-backup.hcl

# Backup Kubernetes resources
kubectl get applications -n argocd -o yaml > k8s-applications-backup.yaml
```

### Recovery Procedures

```bash
# Restore Argo CD applications
kubectl apply -f argocd-applications-backup.yaml

# Restore Vault configuration
vault policy write policy-name vault-policies-backup.hcl

# Force sync all applications
argocd app list -o name | xargs -I {} argocd app sync {}
```

## Performance Tuning

### Argo CD Optimization

```yaml
# argocd-server configuration
spec:
  server:
    config:
      application.instanceLabelKey: argocd.argoproj.io/instance
      server.rbac.log.enforce.enable: true
    env:
      - name: ARGOCD_SERVER_INSECURE
        value: "false"
      - name: ARGOCD_APPLICATION_CONTROLLER_REPO_SERVER_TIMEOUT_SECONDS
        value: "120"
```

### Helm Performance

```bash
# Increase helm timeout for large charts
helm upgrade --timeout=600s service-name infra/helm/services/service-name

# Use --atomic for safer deployments
helm upgrade --atomic service-name infra/helm/services/service-name
```

## Maintenance Windows

### Planned Maintenance

1. **Pre-maintenance**: Scale up replicas for zero-downtime
2. **Maintenance**: Update infra components
3. **Post-maintenance**: Verify all services, scale back to normal
4. **Documentation**: Update runbooks with changes

### Emergency Maintenance

1. **Assessment**: Determine blast radius
2. **Communication**: Notify stakeholders
3. **Execution**: Apply minimal necessary changes
4. **Verification**: Confirm issue resolution
5. **Post-mortem**: Document lessons learned
