#!/bin/bash
set -e

echo "🚀 Starting Kind cluster for learner namespace operator testing..."

# Create Kind cluster if it doesn't exist
if ! kind get clusters | grep -q "aivo-test"; then
    echo "Creating Kind cluster 'aivo-test'..."
    cat <<EOF | kind create cluster --name aivo-test --config=-
kind: Cluster
apiVersion: kind.x-k8s.io/v1alpha4
nodes:
- role: control-plane
  image: kindest/node:v1.28.0
  extraMounts:
  - hostPath: /tmp/aivo-test
    containerPath: /tmp/aivo-test
- role: worker
  image: kindest/node:v1.28.0
- role: worker
  image: kindest/node:v1.28.0
EOF
else
    echo "Using existing Kind cluster 'aivo-test'"
    kubectl config use-context kind-aivo-test
fi

echo "📦 Installing required namespaces..."
kubectl apply -f - <<EOF
apiVersion: v1
kind: Namespace
metadata:
  name: aivo-system
  labels:
    name: aivo-system
    pod-security.kubernetes.io/enforce: restricted
    pod-security.kubernetes.io/audit: restricted
    pod-security.kubernetes.io/warn: restricted
---
apiVersion: v1
kind: Namespace
metadata:
  name: aivo-shared
  labels:
    name: aivo-shared
    pod-security.kubernetes.io/enforce: restricted
    pod-security.kubernetes.io/audit: restricted
    pod-security.kubernetes.io/warn: restricted
EOF

echo "📋 Installing LearnerSpace CRD..."
kubectl apply -f ../crd.yaml

echo "🔐 Installing RBAC..."
kubectl apply -f ../rbac.yaml

echo "🏗️  Building operator image..."
cd ..
docker build -t aivo/learner-ns-operator:test .

echo "📤 Loading image into Kind..."
kind load docker-image aivo/learner-ns-operator:test --name aivo-test

echo "🚀 Deploying operator..."
kubectl apply -f - <<EOF
apiVersion: apps/v1
kind: Deployment
metadata:
  name: learner-ns-operator
  namespace: aivo-system
  labels:
    app.kubernetes.io/name: learner-ns-operator
spec:
  replicas: 1
  selector:
    matchLabels:
      app.kubernetes.io/name: learner-ns-operator
  template:
    metadata:
      labels:
        app.kubernetes.io/name: learner-ns-operator
    spec:
      serviceAccountName: learner-ns-operator
      securityContext:
        runAsNonRoot: true
        runAsUser: 10001
        runAsGroup: 10001
        fsGroup: 10001
      containers:
      - name: operator
        image: aivo/learner-ns-operator:test
        imagePullPolicy: Never
        env:
        - name: KOPF_LOG_LEVEL
          value: "INFO"
        - name: OPERATOR_NAMESPACE
          value: "aivo-system"
        ports:
        - name: health
          containerPort: 8080
          protocol: TCP
        livenessProbe:
          httpGet:
            path: /healthz
            port: health
          initialDelaySeconds: 30
          periodSeconds: 30
        readinessProbe:
          httpGet:
            path: /healthz
            port: health
          initialDelaySeconds: 5
          periodSeconds: 10
        securityContext:
          allowPrivilegeEscalation: false
          capabilities:
            drop:
            - ALL
          readOnlyRootFilesystem: true
          runAsNonRoot: true
          runAsUser: 10001
        resources:
          requests:
            cpu: 100m
            memory: 128Mi
          limits:
            cpu: 500m
            memory: 512Mi
        volumeMounts:
        - name: tmp
          mountPath: /tmp
      volumes:
      - name: tmp
        emptyDir: {}
EOF

echo "⏳ Waiting for operator to be ready..."
kubectl wait --for=condition=available --timeout=300s deployment/learner-ns-operator -n aivo-system

echo "🧪 Running E2E tests..."
cd tests
python3 test_e2e.py

echo "✅ All tests completed successfully!"
echo ""
echo "🔧 Useful commands:"
echo "  kubectl get learnerspaces -n aivo-system"
echo "  kubectl get namespaces | grep aivo-learner"
echo "  kubectl logs -n aivo-system deployment/learner-ns-operator"
echo ""
echo "🧹 To cleanup:"
echo "  kind delete cluster --name aivo-test"
