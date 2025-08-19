# Namespace Isolation Architecture

## Overview

The AIVO platform implements **per-learner namespace isolation** to ensure strict security boundaries between learner environments. Each learner receives a dedicated Kubernetes namespace with comprehensive security controls.

## Architecture

### Learner Namespace Operator

The `learner-ns-operator` is a Kubernetes controller built with [Kopf](https://kopf.readthedocs.io/) that manages learner namespace lifecycle through the `LearnerSpace` Custom Resource Definition (CRD).

### Namespace Naming Convention

```
aivo-learner-{sanitized-learner-id}-{8-char-hash}
```

**Examples:**
- Learner ID: `student123` → Namespace: `aivo-learner-student123-a1b2c3d4`
- Learner ID: `John.Doe@school` → Namespace: `aivo-learner-john-doe-school-e5f6g7h8`

## Security Controls

### 1. Network Isolation

**Default Policy: DENY ALL EGRESS**

```yaml
apiVersion: networking.k8s.io/v1
kind: NetworkPolicy
metadata:
  name: learner-isolation
  namespace: aivo-learner-{id}
spec:
  podSelector: {}  # All pods
  policyTypes:
  - Ingress
  - Egress
  egress:
  - to:
    - namespaceSelector:
        matchLabels:
          name: aivo-system  # Control plane
  - to:
    - namespaceSelector:
        matchLabels:
          name: aivo-shared  # Shared services
  - to:
    - namespaceSelector:
        matchLabels:
          name: kube-system  # DNS only
    ports:
    - protocol: UDP
      port: 53
```

**Allowed Communications:**
- ✅ Same namespace (learner pods to learner pods)
- ✅ `aivo-system` (platform control plane)
- ✅ `aivo-shared` (shared platform services)
- ✅ DNS resolution (`kube-system:53`)
- ❌ **Internet egress (BLOCKED)**
- ❌ **Other learner namespaces (BLOCKED)**
- ❌ **External services (BLOCKED)**

### 2. Resource Quotas

**Default Limits per Learner:**

```yaml
apiVersion: v1
kind: ResourceQuota
metadata:
  name: learner-quota
spec:
  hard:
    requests.cpu: "2"
    requests.memory: "4Gi"
    requests.storage: "10Gi"
    persistentvolumeclaims: "5"
    pods: "10"
    services: "5"
    secrets: "10"
    configmaps: "10"
```

### 3. Pod Security Standards

**Enforcement Level: `restricted`**

```yaml
metadata:
  labels:
    pod-security.kubernetes.io/enforce: restricted
    pod-security.kubernetes.io/audit: restricted
    pod-security.kubernetes.io/warn: restricted
```

**Restrictions:**
- ❌ Root containers
- ❌ Privileged containers
- ❌ Host network/PID/IPC
- ❌ Privilege escalation
- ❌ Dangerous capabilities
- ✅ Read-only root filesystem (recommended)

### 4. RBAC (Role-Based Access Control)

**Minimal Permissions per Learner:**

```yaml
apiVersion: rbac.authorization.k8s.io/v1
kind: Role
metadata:
  name: learner-role
rules:
- apiGroups: [""]
  resources: ["pods", "pods/log", "pods/status"]
  verbs: ["get", "list", "watch"]
- apiGroups: [""]
  resources: ["configmaps", "secrets"]
  verbs: ["get", "list"]
- apiGroups: ["apps"]
  resources: ["deployments", "replicasets"]
  verbs: ["get", "list", "watch"]
```

### 5. Vault Secret Injection

**Automatic Secret Management:**

```yaml
metadata:
  annotations:
    vault.hashicorp.com/agent-inject: "true"
    vault.hashicorp.com/role: "learner-default"
    vault.hashicorp.com/agent-pre-populate-only: "true"
```

**Secret Paths:**
- `secret/data/learners/{learner-id}/api-keys`
- `secret/data/learners/{learner-id}/database`
- `secret/data/learners/{learner-id}/external-services`

## LearnerSpace CRD

### Resource Definition

```yaml
apiVersion: aivo.dev/v1
kind: LearnerSpace
metadata:
  name: student-john-doe
  namespace: aivo-system
spec:
  learnerId: "john.doe"
  subjects: ["mathematics", "science", "programming"]
  resourceQuota:
    cpu: "2"
    memory: "4Gi"
    storage: "10Gi"
    pods: 10
  networkPolicy:
    egressDeny: true
    allowedNamespaces: ["aivo-system", "aivo-shared"]
  vaultRole: "learner-default"
```

### Status Tracking

```yaml
status:
  phase: "Ready"  # Pending | Creating | Ready | Deleting | Failed
  namespace: "aivo-learner-john-doe-a1b2c3d4"
  conditions:
  - type: "Ready"
    status: "True"
    lastTransitionTime: "2025-01-15T10:30:00Z"
    reason: "NamespaceReady"
    message: "Learner namespace created and configured"
  createdAt: "2025-01-15T10:29:45Z"
  lastUpdated: "2025-01-15T10:30:00Z"
```

## Deletion and Cleanup

### Tombstone Strategy

When a `LearnerSpace` is deleted:

1. **Tombstone Creation**: Metadata stored in `aivo-system` namespace
2. **Namespace Deletion**: Kubernetes namespace removed (cascades all resources)
3. **S3 Preservation**: **Data artifacts are NOT deleted** by default
4. **Manual Cleanup**: S3 data requires explicit administrator action

### Tombstone ConfigMap

```yaml
apiVersion: v1
kind: ConfigMap
metadata:
  name: tombstone-john-doe
  namespace: aivo-system
  labels:
    aivo.dev/component: learner-tombstone
    aivo.dev/learner-id: john.doe
    aivo.dev/original-namespace: aivo-learner-john-doe-a1b2c3d4
data:
  learner-id: "john.doe"
  namespace: "aivo-learner-john-doe-a1b2c3d4"
  subjects: "mathematics,science,programming"
  deleted-at: "2025-01-15T15:45:30Z"
  note: "S3 data preserved - manual cleanup required if needed"
```

## Testing and Validation

### Cross-Namespace Connection Tests

**Test 1: Blocked Inter-Learner Communication**

```bash
# From learner A namespace, attempt to reach learner B
kubectl exec -n aivo-learner-a-12345678 test-pod -- \
  curl -m 5 http://service.aivo-learner-b-87654321.svc.cluster.local
# Expected: Timeout (connection blocked)
```

**Test 2: Allowed System Communication**

```bash
# From learner namespace, reach system services
kubectl exec -n aivo-learner-a-12345678 test-pod -- \
  curl -m 5 http://api.aivo-system.svc.cluster.local/health
# Expected: Success (200 OK)
```

**Test 3: DNS Resolution**

```bash
# DNS should work
kubectl exec -n aivo-learner-a-12345678 test-pod -- \
  nslookup kubernetes.default.svc.cluster.local
# Expected: Success
```

**Test 4: Internet Egress Blocked**

```bash
# Internet access should be denied
kubectl exec -n aivo-learner-a-12345678 test-pod -- \
  curl -m 5 https://google.com
# Expected: Timeout (egress blocked)
```

## Monitoring and Observability

### Metrics Collection

The operator exposes Prometheus metrics:

- `learner_namespaces_total`: Total number of learner namespaces
- `learner_namespace_creation_duration_seconds`: Time to create namespace
- `learner_namespace_deletion_duration_seconds`: Time to delete namespace
- `learner_spaces_by_phase`: Namespaces by phase (Ready, Creating, etc.)

### Log Aggregation

All operator logs are collected via:
- **Structured logging** with JSON format
- **Grafana Loki** integration
- **Alert rules** for failed namespace operations

### Alerting Rules

```yaml
groups:
- name: learner-namespace-alerts
  rules:
  - alert: LearnerNamespaceCreationFailed
    expr: rate(learner_namespace_creation_failures_total[5m]) > 0
    for: 1m
    labels:
      severity: warning
    annotations:
      summary: "Learner namespace creation failing"
      description: "{{ $value }} namespace creations failed in the last 5 minutes"
```

## Best Practices

### 1. Namespace Lifecycle

- **Create namespaces** via `LearnerSpace` CRD only
- **Never manually delete** learner namespaces
- **Use tombstones** to track deleted learners
- **Preserve S3 data** unless explicitly requested

### 2. Security Enforcement

- **Always apply** network policies before workloads
- **Validate resource quotas** before deployment
- **Use least-privilege** RBAC principles
- **Audit namespace access** regularly

### 3. Monitoring

- **Track resource usage** per learner
- **Monitor network policy violations**
- **Alert on quota exhaustion**
- **Log all operator actions**

## Compliance and Auditing

### Data Privacy (GDPR/FERPA)

- **Namespace isolation** prevents cross-learner data access
- **Tombstone records** provide deletion audit trail
- **S3 preservation** allows data recovery if needed
- **Encryption at rest** for all learner data

### Security Standards

- **Pod Security Standards**: Restricted enforcement
- **Network segmentation**: Zero-trust networking
- **RBAC**: Principle of least privilege
- **Secret management**: HashiCorp Vault integration

## Troubleshooting

### Common Issues

**Issue: Namespace stuck in "Creating" phase**

```bash
# Check operator logs
kubectl logs -n aivo-system deployment/learner-ns-operator

# Check LearnerSpace status
kubectl get learnerspace -n aivo-system student-name -o yaml
```

**Issue: Network policy not working**

```bash
# Verify policy exists
kubectl get networkpolicy -n aivo-learner-{id}

# Test connectivity
kubectl exec -n aivo-learner-{id} test-pod -- nc -zv target-service 80
```

**Issue: Resource quota exceeded**

```bash
# Check quota usage
kubectl describe quota -n aivo-learner-{id}

# View resource consumption
kubectl top pods -n aivo-learner-{id}
```

## Migration and Updates

### Operator Updates

1. **Rolling deployment** with zero downtime
2. **CRD versioning** with backward compatibility
3. **Graceful handling** of existing resources
4. **Validation** before applying changes

### Namespace Migration

```bash
# Backup existing namespace
kubectl get all -n aivo-learner-{old-id} -o yaml > backup.yaml

# Create new LearnerSpace
kubectl apply -f new-learnerspace.yaml

# Migrate data (manual process)
# Delete old namespace via LearnerSpace deletion
```

This architecture ensures **complete isolation** between learners while maintaining **operational simplicity** and **security compliance**.
