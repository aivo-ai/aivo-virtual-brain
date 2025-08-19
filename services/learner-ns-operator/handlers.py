"""
Kubernetes event handlers for LearnerSpace CRD operations.
Implements namespace creation, security policies, and cleanup.
"""

import hashlib
import json
import logging
import re
from datetime import datetime, timezone
from typing import Dict, Any, Optional, List

import kopf
from kubernetes import client
from kubernetes.client.rest import ApiException

logger = logging.getLogger(__name__)

# Import global clients from main
from main import v1, apps_v1, rbac_v1, custom_objects_api


def generate_namespace_name(learner_id: str) -> str:
    """Generate a consistent namespace name for a learner."""
    # Create a deterministic hash for consistent naming
    hash_obj = hashlib.sha256(learner_id.encode())
    hash_suffix = hash_obj.hexdigest()[:8]
    
    # Ensure namespace name is valid (lowercase, alphanumeric + hyphens)
    safe_learner_id = re.sub(r'[^a-z0-9\-]', '-', learner_id.lower())
    safe_learner_id = re.sub(r'-+', '-', safe_learner_id).strip('-')
    
    namespace_name = f"aivo-learner-{safe_learner_id}-{hash_suffix}"
    
    # Kubernetes namespace names must be <= 63 characters
    if len(namespace_name) > 63:
        namespace_name = f"aivo-learner-{hash_suffix}"
    
    return namespace_name


def create_namespace(learner_space: Dict[str, Any], namespace_name: str) -> client.V1Namespace:
    """Create namespace with proper labels and annotations."""
    learner_id = learner_space['spec']['learnerId']
    subjects = learner_space['spec']['subjects']
    
    namespace = client.V1Namespace(
        metadata=client.V1ObjectMeta(
            name=namespace_name,
            labels={
                'aivo.dev/component': 'learner-namespace',
                'aivo.dev/learner-id': learner_id,
                'aivo.dev/managed-by': 'learner-ns-operator',
                'name': namespace_name,
                'pod-security.kubernetes.io/enforce': 'restricted',
                'pod-security.kubernetes.io/audit': 'restricted',
                'pod-security.kubernetes.io/warn': 'restricted'
            },
            annotations={
                'aivo.dev/learner-id': learner_id,
                'aivo.dev/subjects': ','.join(subjects),
                'aivo.dev/created-by': 'learner-ns-operator',
                'aivo.dev/created-at': datetime.now(timezone.utc).isoformat(),
                'vault.hashicorp.com/agent-inject': 'true',
                'vault.hashicorp.com/role': learner_space['spec'].get('vaultRole', 'learner-default'),
                'vault.hashicorp.com/agent-pre-populate-only': 'true'
            }
        )
    )
    
    try:
        created_namespace = v1.create_namespace(namespace)
        logger.info(f"Created namespace {namespace_name} for learner {learner_id}")
        return created_namespace
    except ApiException as e:
        if e.status == 409:  # Already exists
            logger.info(f"Namespace {namespace_name} already exists")
            return v1.read_namespace(namespace_name)
        else:
            logger.error(f"Failed to create namespace {namespace_name}: {e}")
            raise


def create_network_policy(namespace_name: str, learner_space: Dict[str, Any]) -> client.V1NetworkPolicy:
    """Create network policy with egress deny and selective ingress."""
    allowed_namespaces = learner_space['spec'].get('networkPolicy', {}).get('allowedNamespaces', ['aivo-system', 'aivo-shared'])
    
    # Build namespace selector for allowed namespaces
    namespace_selectors = []
    for ns in allowed_namespaces:
        namespace_selectors.append({
            'namespaceSelector': {
                'matchLabels': {
                    'name': ns
                }
            }
        })
    
    network_policy = client.V1NetworkPolicy(
        metadata=client.V1ObjectMeta(
            name='learner-isolation',
            namespace=namespace_name,
            labels={
                'aivo.dev/component': 'learner-network-policy',
                'aivo.dev/managed-by': 'learner-ns-operator'
            }
        ),
        spec=client.V1NetworkPolicySpec(
            pod_selector=client.V1LabelSelector(),  # Apply to all pods
            policy_types=['Ingress', 'Egress'],
            ingress=[
                # Allow ingress from same namespace
                client.V1NetworkPolicyIngressRule(
                    _from=[
                        client.V1NetworkPolicyPeer(
                            namespace_selector=client.V1LabelSelector(
                                match_labels={'name': namespace_name}
                            )
                        )
                    ]
                ),
                # Allow ingress from allowed namespaces
                client.V1NetworkPolicyIngressRule(
                    _from=[
                        client.V1NetworkPolicyPeer(
                            namespace_selector=client.V1LabelSelector(
                                match_labels={'name': ns}
                            )
                        ) for ns in allowed_namespaces
                    ]
                )
            ],
            egress=[
                # Allow egress to same namespace
                client.V1NetworkPolicyEgressRule(
                    to=[
                        client.V1NetworkPolicyPeer(
                            namespace_selector=client.V1LabelSelector(
                                match_labels={'name': namespace_name}
                            )
                        )
                    ]
                ),
                # Allow egress to allowed namespaces only
                client.V1NetworkPolicyEgressRule(
                    to=[
                        client.V1NetworkPolicyPeer(
                            namespace_selector=client.V1LabelSelector(
                                match_labels={'name': ns}
                            )
                        ) for ns in allowed_namespaces
                    ]
                ),
                # Allow DNS resolution
                client.V1NetworkPolicyEgressRule(
                    to=[
                        client.V1NetworkPolicyPeer(
                            namespace_selector=client.V1LabelSelector(
                                match_labels={'name': 'kube-system'}
                            )
                        )
                    ],
                    ports=[
                        client.V1NetworkPolicyPort(port=53, protocol='UDP'),
                        client.V1NetworkPolicyPort(port=53, protocol='TCP')
                    ]
                )
            ]
        )
    )
    
    try:
        from kubernetes.client import NetworkingV1Api
        networking_v1 = NetworkingV1Api()
        created_policy = networking_v1.create_namespaced_network_policy(
            namespace=namespace_name,
            body=network_policy
        )
        logger.info(f"Created network policy for namespace {namespace_name}")
        return created_policy
    except ApiException as e:
        if e.status == 409:  # Already exists
            logger.info(f"Network policy already exists in namespace {namespace_name}")
            return networking_v1.read_namespaced_network_policy(
                name='learner-isolation',
                namespace=namespace_name
            )
        else:
            logger.error(f"Failed to create network policy in {namespace_name}: {e}")
            raise


def create_resource_quota(namespace_name: str, learner_space: Dict[str, Any]) -> client.V1ResourceQuota:
    """Create resource quota to limit resource consumption."""
    quota_spec = learner_space['spec'].get('resourceQuota', {})
    
    resource_quota = client.V1ResourceQuota(
        metadata=client.V1ObjectMeta(
            name='learner-quota',
            namespace=namespace_name,
            labels={
                'aivo.dev/component': 'learner-resource-quota',
                'aivo.dev/managed-by': 'learner-ns-operator'
            }
        ),
        spec=client.V1ResourceQuotaSpec(
            hard={
                'requests.cpu': quota_spec.get('cpu', '2'),
                'requests.memory': quota_spec.get('memory', '4Gi'),
                'requests.storage': quota_spec.get('storage', '10Gi'),
                'persistentvolumeclaims': '5',
                'pods': str(quota_spec.get('pods', 10)),
                'services': '5',
                'secrets': '10',
                'configmaps': '10'
            }
        )
    )
    
    try:
        created_quota = v1.create_namespaced_resource_quota(
            namespace=namespace_name,
            body=resource_quota
        )
        logger.info(f"Created resource quota for namespace {namespace_name}")
        return created_quota
    except ApiException as e:
        if e.status == 409:  # Already exists
            logger.info(f"Resource quota already exists in namespace {namespace_name}")
            return v1.read_namespaced_resource_quota(
                name='learner-quota',
                namespace=namespace_name
            )
        else:
            logger.error(f"Failed to create resource quota in {namespace_name}: {e}")
            raise


def create_service_account_and_rbac(namespace_name: str, learner_id: str) -> tuple:
    """Create service account and minimal RBAC for learner namespace."""
    # Service Account
    service_account = client.V1ServiceAccount(
        metadata=client.V1ObjectMeta(
            name='learner-sa',
            namespace=namespace_name,
            labels={
                'aivo.dev/component': 'learner-service-account',
                'aivo.dev/managed-by': 'learner-ns-operator'
            },
            annotations={
                'vault.hashicorp.com/role': 'learner-default',
                'vault.hashicorp.com/agent-inject': 'true'
            }
        )
    )
    
    # Role with minimal permissions
    role = client.V1Role(
        metadata=client.V1ObjectMeta(
            name='learner-role',
            namespace=namespace_name,
            labels={
                'aivo.dev/component': 'learner-role',
                'aivo.dev/managed-by': 'learner-ns-operator'
            }
        ),
        rules=[
            client.V1PolicyRule(
                api_groups=[''],
                resources=['pods', 'pods/log', 'pods/status'],
                verbs=['get', 'list', 'watch']
            ),
            client.V1PolicyRule(
                api_groups=[''],
                resources=['configmaps', 'secrets'],
                verbs=['get', 'list']
            ),
            client.V1PolicyRule(
                api_groups=['apps'],
                resources=['deployments', 'replicasets'],
                verbs=['get', 'list', 'watch']
            )
        ]
    )
    
    # RoleBinding
    role_binding = client.V1RoleBinding(
        metadata=client.V1ObjectMeta(
            name='learner-role-binding',
            namespace=namespace_name,
            labels={
                'aivo.dev/component': 'learner-role-binding',
                'aivo.dev/managed-by': 'learner-ns-operator'
            }
        ),
        subjects=[
            client.V1Subject(
                kind='ServiceAccount',
                name='learner-sa',
                namespace=namespace_name
            )
        ],
        role_ref=client.V1RoleRef(
            api_group='rbac.authorization.k8s.io',
            kind='Role',
            name='learner-role'
        )
    )
    
    try:
        # Create ServiceAccount
        created_sa = v1.create_namespaced_service_account(
            namespace=namespace_name,
            body=service_account
        )
        
        # Create Role
        created_role = rbac_v1.create_namespaced_role(
            namespace=namespace_name,
            body=role
        )
        
        # Create RoleBinding
        created_rb = rbac_v1.create_namespaced_role_binding(
            namespace=namespace_name,
            body=role_binding
        )
        
        logger.info(f"Created RBAC resources for namespace {namespace_name}")
        return created_sa, created_role, created_rb
        
    except ApiException as e:
        if e.status == 409:  # Already exists
            logger.info(f"RBAC resources already exist in namespace {namespace_name}")
            return None, None, None
        else:
            logger.error(f"Failed to create RBAC resources in {namespace_name}: {e}")
            raise


def update_learner_space_status(name: str, namespace: str, status_update: Dict[str, Any]):
    """Update the status of a LearnerSpace resource."""
    try:
        # Get current resource
        current = custom_objects_api.get_namespaced_custom_object(
            group="aivo.dev",
            version="v1",
            namespace=namespace,
            plural="learnerspaces",
            name=name
        )
        
        # Update status
        if 'status' not in current:
            current['status'] = {}
        
        current['status'].update(status_update)
        current['status']['lastUpdated'] = datetime.now(timezone.utc).isoformat()
        
        # Patch the resource
        custom_objects_api.patch_namespaced_custom_object_status(
            group="aivo.dev",
            version="v1",
            namespace=namespace,
            plural="learnerspaces",
            name=name,
            body=current
        )
        
        logger.info(f"Updated LearnerSpace {name} status: {status_update}")
        
    except ApiException as e:
        logger.error(f"Failed to update LearnerSpace {name} status: {e}")


@kopf.on.create('aivo.dev', 'v1', 'learnerspaces')
async def create_learner_space(spec: Dict[str, Any], name: str, namespace: str, **kwargs):
    """Handle LearnerSpace creation."""
    logger.info(f"Creating LearnerSpace {name} for learner {spec['learnerId']}")
    
    learner_space = {'spec': spec}
    learner_id = spec['learnerId']
    
    try:
        # Update status to Creating
        update_learner_space_status(name, namespace, {
            'phase': 'Creating',
            'conditions': [{
                'type': 'Creating',
                'status': 'True',
                'lastTransitionTime': datetime.now(timezone.utc).isoformat(),
                'reason': 'NamespaceCreation',
                'message': 'Creating learner namespace and resources'
            }]
        })
        
        # Generate namespace name
        namespace_name = generate_namespace_name(learner_id)
        
        # Create namespace
        create_namespace(learner_space, namespace_name)
        
        # Create network policy (egress deny)
        create_network_policy(namespace_name, learner_space)
        
        # Create resource quota
        create_resource_quota(namespace_name, learner_space)
        
        # Create service account and RBAC
        create_service_account_and_rbac(namespace_name, learner_id)
        
        # Update status to Ready
        update_learner_space_status(name, namespace, {
            'phase': 'Ready',
            'namespace': namespace_name,
            'conditions': [{
                'type': 'Ready',
                'status': 'True',
                'lastTransitionTime': datetime.now(timezone.utc).isoformat(),
                'reason': 'NamespaceReady',
                'message': f'Learner namespace {namespace_name} created and configured'
            }],
            'createdAt': datetime.now(timezone.utc).isoformat()
        })
        
        logger.info(f"Successfully created LearnerSpace {name} with namespace {namespace_name}")
        
        return {'namespace': namespace_name, 'status': 'Ready'}
        
    except Exception as e:
        logger.error(f"Failed to create LearnerSpace {name}: {e}")
        
        # Update status to Failed
        update_learner_space_status(name, namespace, {
            'phase': 'Failed',
            'conditions': [{
                'type': 'Failed',
                'status': 'True',
                'lastTransitionTime': datetime.now(timezone.utc).isoformat(),
                'reason': 'CreationFailed',
                'message': f'Failed to create learner namespace: {str(e)}'
            }]
        })
        
        raise kopf.PermanentError(f"Failed to create LearnerSpace: {e}")


@kopf.on.update('aivo.dev', 'v1', 'learnerspaces')
async def update_learner_space(spec: Dict[str, Any], status: Dict[str, Any], name: str, namespace: str, **kwargs):
    """Handle LearnerSpace updates."""
    logger.info(f"Updating LearnerSpace {name}")
    
    namespace_name = status.get('namespace')
    if not namespace_name:
        logger.warning(f"LearnerSpace {name} has no namespace in status, skipping update")
        return
    
    try:
        # Update resource quota if changed
        learner_space = {'spec': spec}
        create_resource_quota(namespace_name, learner_space)
        
        # Update network policy if changed
        create_network_policy(namespace_name, learner_space)
        
        logger.info(f"Successfully updated LearnerSpace {name}")
        
    except Exception as e:
        logger.error(f"Failed to update LearnerSpace {name}: {e}")
        raise


@kopf.on.delete('aivo.dev', 'v1', 'learnerspaces')
async def delete_learner_space(spec: Dict[str, Any], status: Dict[str, Any], name: str, namespace: str, **kwargs):
    """Handle LearnerSpace deletion with tombstoning."""
    logger.info(f"Deleting LearnerSpace {name}")
    
    learner_id = spec['learnerId']
    namespace_name = status.get('namespace')
    
    if not namespace_name:
        logger.warning(f"LearnerSpace {name} has no namespace in status, nothing to clean up")
        return
    
    try:
        # Update status to Deleting
        update_learner_space_status(name, namespace, {
            'phase': 'Deleting',
            'conditions': [{
                'type': 'Deleting',
                'status': 'True',
                'lastTransitionTime': datetime.now(timezone.utc).isoformat(),
                'reason': 'NamespaceDeletion',
                'message': 'Deleting learner namespace and resources'
            }]
        })
        
        # Create tombstone ConfigMap with metadata before deletion
        tombstone_data = {
            'learner-id': learner_id,
            'namespace': namespace_name,
            'subjects': ','.join(spec.get('subjects', [])),
            'deleted-at': datetime.now(timezone.utc).isoformat(),
            'note': 'S3 data preserved - manual cleanup required if needed'
        }
        
        tombstone_cm = client.V1ConfigMap(
            metadata=client.V1ObjectMeta(
                name=f'tombstone-{learner_id}',
                namespace='aivo-system',  # Store in system namespace
                labels={
                    'aivo.dev/component': 'learner-tombstone',
                    'aivo.dev/learner-id': learner_id,
                    'aivo.dev/original-namespace': namespace_name
                }
            ),
            data=tombstone_data
        )
        
        try:
            v1.create_namespaced_config_map(
                namespace='aivo-system',
                body=tombstone_cm
            )
            logger.info(f"Created tombstone for learner {learner_id}")
        except ApiException as e:
            if e.status != 409:  # Ignore if already exists
                logger.warning(f"Failed to create tombstone for learner {learner_id}: {e}")
        
        # Delete the namespace (this will cascade delete all resources)
        try:
            v1.delete_namespace(name=namespace_name)
            logger.info(f"Initiated deletion of namespace {namespace_name}")
        except ApiException as e:
            if e.status != 404:  # Ignore if already deleted
                logger.error(f"Failed to delete namespace {namespace_name}: {e}")
                raise
        
        logger.info(f"Successfully deleted LearnerSpace {name}, S3 data preserved")
        
    except Exception as e:
        logger.error(f"Failed to delete LearnerSpace {name}: {e}")
        raise
