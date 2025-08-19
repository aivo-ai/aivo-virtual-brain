# Learner Namespace Operator

A Kubernetes operator that creates isolated namespaces for individual learners with strict security controls.

## Overview

The Learner Namespace Operator implements **per-learner namespace isolation** by managing `LearnerSpace` custom resources. Each learner receives a dedicated Kubernetes namespace with:

- **Network isolation** with egress deny-all policies
- **Resource quotas** to prevent resource exhaustion
- **Pod Security Standards** enforcement (restricted)
- **RBAC** with minimal permissions
- **Vault integration** for secret management
- **Tombstone tracking** for deleted namespaces

## Quick Start

### Prerequisites

- Kubernetes 1.24+
- Argo CD (for GitOps deployment)
- HashiCorp Vault (for secret management)
- Prometheus (for monitoring)

### Installation via Argo CD

```bash
# Apply the Argo CD application
kubectl apply -f ../../infra/argocd/apps/learner-ns-operator.yaml

# Wait for deployment
kubectl wait --for=condition=available --timeout=300s \
  deployment/learner-ns-operator -n aivo-system
```

### Manual Installation

```bash
# Install CRD
kubectl apply -f crd.yaml

# Install RBAC
kubectl apply -f rbac.yaml

# Deploy using Helm
helm install learner-ns-operator charts/learner-ns-operator \
  --namespace aivo-system \
  --create-namespace
```

## Usage

### Creating a Learner Namespace

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

Apply the resource:

```bash
kubectl apply -f learnerspace.yaml

# Check status
kubectl get learnerspace student-john-doe -n aivo-system

# View created namespace
kubectl get namespace aivo-learner-john-doe-a1b2c3d4
```

### Viewing Learner Namespaces

```bash
# List all LearnerSpaces
kubectl get learnerspace -n aivo-system

# List learner namespaces
kubectl get namespace -l aivo.dev/component=learner-namespace

# View detailed status
kubectl describe learnerspace student-john-doe -n aivo-system
```

### Deleting a Learner Namespace

```bash
# Delete the LearnerSpace (creates tombstone)
kubectl delete learnerspace student-john-doe -n aivo-system

# Verify namespace is deleted
kubectl get namespace aivo-learner-john-doe-a1b2c3d4

# Check tombstone
kubectl get configmap tombstone-john-doe -n aivo-system
```

## Architecture

### Namespace Naming

Namespaces are named using the pattern:
```
aivo-learner-{sanitized-learner-id}-{8-char-hash}
```

Examples:
- `john.doe` → `aivo-learner-john-doe-a1b2c3d4`
- `student_123` → `aivo-learner-student-123-e5f6g7h8`

### Security Controls

#### Network Isolation

**Default Policy: DENY ALL EGRESS**

- ✅ Intra-namespace communication allowed
- ✅ Communication to `aivo-system` namespace
- ✅ Communication to `aivo-shared` namespace  
- ✅ DNS resolution (`kube-system:53`)
- ❌ Internet egress blocked
- ❌ Cross-learner communication blocked

#### Resource Quotas

Default limits per namespace:
- **CPU**: 2 cores
- **Memory**: 4 GiB
- **Storage**: 10 GiB
- **Pods**: 10 pods
- **Services**: 5 services
- **Secrets**: 10 secrets
- **ConfigMaps**: 10 configmaps

#### Pod Security

- **Enforcement Level**: `restricted`
- **Non-root containers**: Required
- **Read-only root filesystem**: Recommended
- **No privilege escalation**: Enforced
- **Dropped capabilities**: All capabilities dropped

#### RBAC

Minimal permissions for learner service account:
```yaml
rules:
- apiGroups: [""]
  resources: ["pods", "pods/log", "pods/status"]
  verbs: ["get", "list", "watch"]
- apiGroups: [""]
  resources: ["configmaps", "secrets"]
  verbs: ["get", "list"]
```

## Configuration

### Operator Configuration

```yaml
operator:
  namespace: aivo-system
  logLevel: INFO
  defaultResourceQuota:
    cpu: "2"
    memory: "4Gi"
    storage: "10Gi"
    pods: 10
  defaultNetworkPolicy:
    egressDeny: true
    allowedNamespaces: ["aivo-system", "aivo-shared"]
  defaultVaultRole: "learner-default"
```

### Vault Integration

The operator integrates with HashiCorp Vault for secret management:

```yaml
podAnnotations:
  vault.hashicorp.com/agent-inject: "true"
  vault.hashicorp.com/role: "learner-ns-operator"
  vault.hashicorp.com/agent-inject-secret-config: "secret/data/operators/learner-ns"
```

Secret paths for learners:
- `secret/data/learners/{learner-id}/api-keys`
- `secret/data/learners/{learner-id}/database`
- `secret/data/learners/{learner-id}/external-services`

## Testing

### Unit Tests

```bash
# Run unit tests
python -m pytest tests/unit/

# Run with coverage
python -m pytest tests/unit/ --cov=handlers --cov=main
```

### End-to-End Tests

```bash
# Setup Kind cluster and run E2E tests
cd tests
chmod +x kind-test.sh
./kind-test.sh
```

### Manual Testing

```bash
# Create test LearnerSpace
kubectl apply -f tests/example-learnerspace.yaml

# Run connectivity tests
cd tests
python test_e2e.py

# Cleanup
kubectl delete learnerspace example-student -n aivo-system
```

## Monitoring and Observability

### Metrics

The operator exposes Prometheus metrics:

- `learner_namespaces_total`: Total number of learner namespaces
- `learner_namespace_creation_duration_seconds`: Time to create namespace
- `learner_namespace_deletion_duration_seconds`: Time to delete namespace
- `learner_spaces_by_phase`: Namespaces by phase

### Logging

Structured JSON logging with configurable levels:

```bash
# View operator logs
kubectl logs -n aivo-system deployment/learner-ns-operator -f

# Search for specific learner
kubectl logs -n aivo-system deployment/learner-ns-operator | grep "john.doe"
```

### Health Checks

```bash
# Check operator health
kubectl port-forward -n aivo-system deployment/learner-ns-operator 8080:8080
curl http://localhost:8080/healthz

# Check operator status
kubectl get deployment learner-ns-operator -n aivo-system
```

## Troubleshooting

### Common Issues

**LearnerSpace stuck in "Creating" phase:**

```bash
# Check operator logs
kubectl logs -n aivo-system deployment/learner-ns-operator

# Check events
kubectl get events -n aivo-system --field-selector involvedObject.name=student-name

# Check LearnerSpace status
kubectl describe learnerspace student-name -n aivo-system
```

**Network policy not working:**

```bash
# Verify policy exists
kubectl get networkpolicy -n aivo-learner-{id}

# Test connectivity
kubectl run test-pod --rm -i --tty --image=busybox:1.35 \
  --namespace=aivo-learner-{id} -- /bin/sh

# Inside pod, test connectivity
wget --timeout=5 --tries=1 google.com  # Should fail
nslookup kubernetes.default.svc.cluster.local  # Should work
```

**Resource quota exceeded:**

```bash
# Check quota usage
kubectl describe quota learner-quota -n aivo-learner-{id}

# View resource consumption
kubectl top pods -n aivo-learner-{id}
kubectl top nodes
```

### Debug Mode

Enable debug logging:

```bash
# Update deployment with debug level
kubectl set env deployment/learner-ns-operator \
  -n aivo-system KOPF_LOG_LEVEL=DEBUG

# Watch logs
kubectl logs -n aivo-system deployment/learner-ns-operator -f
```

## Development

### Local Development

```bash
# Install dependencies
pip install -r requirements.txt

# Run locally (requires kubeconfig)
python main.py

# Run with debug logging
KOPF_LOG_LEVEL=DEBUG python main.py
```

### Building Images

```bash
# Build image
docker build -t aivo/learner-ns-operator:dev .

# Test locally with Kind
kind load docker-image aivo/learner-ns-operator:dev --name aivo-test
```

### Contributing

1. Fork the repository
2. Create a feature branch
3. Make changes with tests
4. Run the test suite
5. Submit a pull request

## Security Considerations

### Principle of Least Privilege

- Operator runs as non-root user (10001)
- Minimal RBAC permissions
- Read-only root filesystem
- No privilege escalation

### Network Security

- Default deny-all egress policy
- Explicit allow lists for system communication
- DNS resolution restricted to cluster DNS

### Data Protection

- S3 data preserved on namespace deletion
- Tombstone tracking for audit compliance
- Vault integration for secret management

## License

This project is licensed under the MIT License - see the LICENSE file for details.

## Support

For support and questions:

- **Documentation**: [docs/security/namespace-isolation.md](../../docs/security/namespace-isolation.md)
- **Issues**: GitHub Issues
- **Chat**: AIVO Platform Slack #infrastructure
- **Email**: platform@aivo.dev
