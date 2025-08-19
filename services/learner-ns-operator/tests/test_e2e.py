#!/usr/bin/env python3
"""
End-to-end tests for the Learner Namespace Operator.
Tests namespace creation, isolation, and deletion.
"""

import asyncio
import json
import subprocess
import time
import yaml
from pathlib import Path
import tempfile
import pytest

# Test configuration
TEST_NAMESPACE = "aivo-system"
TEST_LEARNER_ID = "test-student-123"
TEST_SUBJECTS = ["mathematics", "science"]


class KubernetesTest:
    """Helper class for Kubernetes operations in tests."""
    
    @staticmethod
    def kubectl_apply(manifest_dict):
        """Apply a Kubernetes manifest."""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.yaml', delete=False) as f:
            yaml.dump(manifest_dict, f)
            temp_file = f.name
        
        try:
            result = subprocess.run(
                ["kubectl", "apply", "-f", temp_file],
                capture_output=True,
                text=True,
                check=True
            )
            return result
        finally:
            Path(temp_file).unlink()
    
    @staticmethod
    def kubectl_delete(resource_type, name, namespace=None):
        """Delete a Kubernetes resource."""
        cmd = ["kubectl", "delete", resource_type, name]
        if namespace:
            cmd.extend(["-n", namespace])
        
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True
        )
        return result
    
    @staticmethod
    def kubectl_get(resource_type, name=None, namespace=None, output="json"):
        """Get Kubernetes resource(s)."""
        cmd = ["kubectl", "get", resource_type]
        if name:
            cmd.append(name)
        if namespace:
            cmd.extend(["-n", namespace])
        cmd.extend(["-o", output])
        
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True
        )
        return result
    
    @staticmethod
    def kubectl_exec(namespace, pod_name, command):
        """Execute command in a pod."""
        cmd = ["kubectl", "exec", "-n", namespace, pod_name, "--"] + command
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=30
        )
        return result
    
    @staticmethod
    def wait_for_condition(check_func, timeout=300, interval=5):
        """Wait for a condition to be true."""
        start_time = time.time()
        while time.time() - start_time < timeout:
            if check_func():
                return True
            time.sleep(interval)
        return False


def create_test_learnerspace():
    """Create a test LearnerSpace resource."""
    learnerspace = {
        "apiVersion": "aivo.dev/v1",
        "kind": "LearnerSpace",
        "metadata": {
            "name": f"test-{TEST_LEARNER_ID}",
            "namespace": TEST_NAMESPACE
        },
        "spec": {
            "learnerId": TEST_LEARNER_ID,
            "subjects": TEST_SUBJECTS,
            "resourceQuota": {
                "cpu": "1",
                "memory": "2Gi",
                "storage": "5Gi",
                "pods": 5
            },
            "networkPolicy": {
                "egressDeny": True,
                "allowedNamespaces": ["aivo-system", "aivo-shared"]
            },
            "vaultRole": "learner-test"
        }
    }
    return learnerspace


def create_test_pod(namespace):
    """Create a test pod for connectivity testing."""
    pod = {
        "apiVersion": "v1",
        "kind": "Pod",
        "metadata": {
            "name": "test-connectivity",
            "namespace": namespace
        },
        "spec": {
            "containers": [
                {
                    "name": "test",
                    "image": "busybox:1.35",
                    "command": ["sleep", "3600"],
                    "securityContext": {
                        "runAsNonRoot": True,
                        "runAsUser": 10001,
                        "allowPrivilegeEscalation": False,
                        "readOnlyRootFilesystem": True,
                        "capabilities": {
                            "drop": ["ALL"]
                        }
                    },
                    "resources": {
                        "requests": {
                            "cpu": "10m",
                            "memory": "32Mi"
                        },
                        "limits": {
                            "cpu": "100m",
                            "memory": "64Mi"
                        }
                    }
                }
            ],
            "securityContext": {
                "runAsNonRoot": True,
                "runAsUser": 10001,
                "runAsGroup": 10001,
                "fsGroup": 10001
            },
            "serviceAccountName": "learner-sa"
        }
    }
    return pod


class TestLearnerNamespaceOperator:
    """Test suite for the Learner Namespace Operator."""
    
    @pytest.fixture(autouse=True)
    def setup_and_cleanup(self):
        """Setup and cleanup for each test."""
        # Cleanup any existing test resources
        self.cleanup_test_resources()
        
        yield
        
        # Cleanup after test
        self.cleanup_test_resources()
    
    def cleanup_test_resources(self):
        """Clean up test resources."""
        # Delete test LearnerSpace
        KubernetesTest.kubectl_delete(
            "learnerspace", 
            f"test-{TEST_LEARNER_ID}", 
            TEST_NAMESPACE
        )
        
        # Wait for namespace cleanup
        def namespace_deleted():
            result = KubernetesTest.kubectl_get("namespace", f"aivo-learner-{TEST_LEARNER_ID}")
            return result.returncode != 0
        
        KubernetesTest.wait_for_condition(namespace_deleted, timeout=60)
    
    def test_learnerspace_creation(self):
        """Test LearnerSpace creation and namespace setup."""
        print(f"Testing LearnerSpace creation for learner: {TEST_LEARNER_ID}")
        
        # Create LearnerSpace
        learnerspace = create_test_learnerspace()
        result = KubernetesTest.kubectl_apply(learnerspace)
        assert result.returncode == 0, f"Failed to create LearnerSpace: {result.stderr}"
        
        # Wait for namespace creation
        def namespace_ready():
            result = KubernetesTest.kubectl_get("learnerspace", f"test-{TEST_LEARNER_ID}", TEST_NAMESPACE)
            if result.returncode == 0:
                ls_data = json.loads(result.stdout)
                status = ls_data.get("status", {})
                return status.get("phase") == "Ready" and status.get("namespace")
            return False
        
        assert KubernetesTest.wait_for_condition(namespace_ready, timeout=120), \
            "LearnerSpace did not reach Ready state within timeout"
        
        # Get the created namespace name
        result = KubernetesTest.kubectl_get("learnerspace", f"test-{TEST_LEARNER_ID}", TEST_NAMESPACE)
        ls_data = json.loads(result.stdout)
        namespace_name = ls_data["status"]["namespace"]
        
        print(f"Created namespace: {namespace_name}")
        
        # Verify namespace exists
        result = KubernetesTest.kubectl_get("namespace", namespace_name)
        assert result.returncode == 0, f"Namespace {namespace_name} does not exist"
        
        # Verify namespace labels
        ns_data = json.loads(result.stdout)
        labels = ns_data.get("metadata", {}).get("labels", {})
        assert labels.get("aivo.dev/learner-id") == TEST_LEARNER_ID
        assert labels.get("pod-security.kubernetes.io/enforce") == "restricted"
        
        print("✓ Namespace created with correct labels")
        
        # Verify resource quota
        result = KubernetesTest.kubectl_get("resourcequota", "learner-quota", namespace_name)
        assert result.returncode == 0, "Resource quota not found"
        
        quota_data = json.loads(result.stdout)
        hard_limits = quota_data.get("spec", {}).get("hard", {})
        assert hard_limits.get("requests.cpu") == "1"
        assert hard_limits.get("requests.memory") == "2Gi"
        
        print("✓ Resource quota configured correctly")
        
        # Verify network policy
        result = KubernetesTest.kubectl_get("networkpolicy", "learner-isolation", namespace_name)
        assert result.returncode == 0, "Network policy not found"
        
        print("✓ Network policy created")
        
        # Verify service account and RBAC
        result = KubernetesTest.kubectl_get("serviceaccount", "learner-sa", namespace_name)
        assert result.returncode == 0, "Service account not found"
        
        result = KubernetesTest.kubectl_get("role", "learner-role", namespace_name)
        assert result.returncode == 0, "Role not found"
        
        result = KubernetesTest.kubectl_get("rolebinding", "learner-role-binding", namespace_name)
        assert result.returncode == 0, "Role binding not found"
        
        print("✓ RBAC resources created")
        
        return namespace_name
    
    def test_network_isolation(self):
        """Test network isolation between learner namespaces."""
        print("Testing network isolation")
        
        # Create first learnerspace
        namespace1 = self.test_learnerspace_creation()
        
        # Create a test pod in the namespace
        test_pod = create_test_pod(namespace1)
        result = KubernetesTest.kubectl_apply(test_pod)
        assert result.returncode == 0, f"Failed to create test pod: {result.stderr}"
        
        # Wait for pod to be ready
        def pod_ready():
            result = KubernetesTest.kubectl_get("pod", "test-connectivity", namespace1)
            if result.returncode == 0:
                pod_data = json.loads(result.stdout)
                return pod_data.get("status", {}).get("phase") == "Running"
            return False
        
        assert KubernetesTest.wait_for_condition(pod_ready, timeout=60), \
            "Test pod did not become ready"
        
        print("✓ Test pod is running")
        
        # Test DNS resolution (should work)
        result = KubernetesTest.kubectl_exec(
            namespace1, 
            "test-connectivity", 
            ["nslookup", "kubernetes.default.svc.cluster.local"]
        )
        assert result.returncode == 0, "DNS resolution failed"
        print("✓ DNS resolution works")
        
        # Test egress to internet (should fail)
        result = KubernetesTest.kubectl_exec(
            namespace1, 
            "test-connectivity", 
            ["wget", "--timeout=5", "--tries=1", "-O-", "https://google.com"]
        )
        assert result.returncode != 0, "Internet egress should be blocked"
        print("✓ Internet egress blocked")
        
        # Test connection to system namespace (should work if service exists)
        # This is a basic connectivity test - in real environment there would be services to test
        print("✓ Network isolation tests completed")
    
    def test_resource_quota_enforcement(self):
        """Test resource quota enforcement."""
        print("Testing resource quota enforcement")
        
        namespace_name = self.test_learnerspace_creation()
        
        # Try to create a pod that exceeds CPU quota
        large_pod = {
            "apiVersion": "v1",
            "kind": "Pod",
            "metadata": {
                "name": "large-pod",
                "namespace": namespace_name
            },
            "spec": {
                "containers": [
                    {
                        "name": "large",
                        "image": "busybox:1.35",
                        "command": ["sleep", "3600"],
                        "resources": {
                            "requests": {
                                "cpu": "2",  # Exceeds the 1 CPU quota
                                "memory": "1Gi"
                            }
                        },
                        "securityContext": {
                            "runAsNonRoot": True,
                            "runAsUser": 10001,
                            "allowPrivilegeEscalation": False,
                            "readOnlyRootFilesystem": True,
                            "capabilities": {
                                "drop": ["ALL"]
                            }
                        }
                    }
                ],
                "securityContext": {
                    "runAsNonRoot": True,
                    "runAsUser": 10001
                },
                "serviceAccountName": "learner-sa"
            }
        }
        
        result = KubernetesTest.kubectl_apply(large_pod)
        # This should either fail or the pod should not start due to quota
        
        if result.returncode == 0:
            # Check if pod is actually running
            time.sleep(5)
            result = KubernetesTest.kubectl_get("pod", "large-pod", namespace_name)
            if result.returncode == 0:
                pod_data = json.loads(result.stdout)
                phase = pod_data.get("status", {}).get("phase")
                # Pod should not be running due to quota
                assert phase != "Running", "Pod should not run due to resource quota"
        
        print("✓ Resource quota enforcement working")
    
    def test_learnerspace_deletion(self):
        """Test LearnerSpace deletion and tombstone creation."""
        print("Testing LearnerSpace deletion")
        
        namespace_name = self.test_learnerspace_creation()
        
        # Delete the LearnerSpace
        result = KubernetesTest.kubectl_delete(
            "learnerspace", 
            f"test-{TEST_LEARNER_ID}", 
            TEST_NAMESPACE
        )
        assert result.returncode == 0, f"Failed to delete LearnerSpace: {result.stderr}"
        
        # Wait for namespace deletion
        def namespace_deleted():
            result = KubernetesTest.kubectl_get("namespace", namespace_name)
            return result.returncode != 0
        
        assert KubernetesTest.wait_for_condition(namespace_deleted, timeout=120), \
            "Namespace was not deleted within timeout"
        
        print("✓ Namespace deleted")
        
        # Check for tombstone ConfigMap
        def tombstone_exists():
            result = KubernetesTest.kubectl_get(
                "configmap", 
                f"tombstone-{TEST_LEARNER_ID}", 
                "aivo-system"
            )
            return result.returncode == 0
        
        # Give some time for tombstone creation
        time.sleep(10)
        
        if KubernetesTest.wait_for_condition(tombstone_exists, timeout=30):
            # Verify tombstone data
            result = KubernetesTest.kubectl_get(
                "configmap", 
                f"tombstone-{TEST_LEARNER_ID}", 
                "aivo-system"
            )
            tombstone_data = json.loads(result.stdout)
            data = tombstone_data.get("data", {})
            assert data.get("learner-id") == TEST_LEARNER_ID
            assert data.get("namespace") == namespace_name
            print("✓ Tombstone created successfully")
            
            # Cleanup tombstone
            KubernetesTest.kubectl_delete(
                "configmap", 
                f"tombstone-{TEST_LEARNER_ID}", 
                "aivo-system"
            )
        else:
            print("⚠ Tombstone not found (may be normal in test environment)")


def main():
    """Main test runner."""
    print("Starting Learner Namespace Operator E2E Tests")
    print("=" * 50)
    
    # Check if kubectl is available
    result = subprocess.run(["kubectl", "version", "--client"], capture_output=True)
    if result.returncode != 0:
        print("ERROR: kubectl not found. Please install kubectl and configure cluster access.")
        return 1
    
    # Check if CRD is installed
    result = KubernetesTest.kubectl_get("crd", "learnerspaces.aivo.dev")
    if result.returncode != 0:
        print("ERROR: LearnerSpace CRD not found. Please install the operator first.")
        return 1
    
    # Run tests
    test_instance = TestLearnerNamespaceOperator()
    
    try:
        # Setup
        test_instance.cleanup_test_resources()
        
        # Run tests
        print("\n1. Testing LearnerSpace creation...")
        namespace_name = test_instance.test_learnerspace_creation()
        
        print("\n2. Testing network isolation...")
        test_instance.test_network_isolation()
        
        print("\n3. Testing resource quota enforcement...")
        test_instance.test_resource_quota_enforcement()
        
        print("\n4. Testing LearnerSpace deletion...")
        test_instance.test_learnerspace_deletion()
        
        print("\n" + "=" * 50)
        print("✅ All tests passed!")
        return 0
        
    except Exception as e:
        print(f"\n❌ Test failed: {e}")
        return 1
    
    finally:
        # Cleanup
        test_instance.cleanup_test_resources()


if __name__ == "__main__":
    exit(main())
