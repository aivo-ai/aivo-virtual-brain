#!/usr/bin/env python3
"""
AIVO Learner Namespace Operator
Creates isolated namespaces per learner with strict security policies.
"""

import asyncio
import logging
import os
import sys
from pathlib import Path

import kopf
import kubernetes
from kubernetes import client, config

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Global Kubernetes clients
api_client = None
v1 = None
apps_v1 = None
rbac_v1 = None
custom_objects_api = None


def setup_kubernetes():
    """Initialize Kubernetes clients."""
    global api_client, v1, apps_v1, rbac_v1, custom_objects_api
    
    try:
        # Load in-cluster config if running in pod, otherwise use kubeconfig
        if Path("/var/run/secrets/kubernetes.io/serviceaccount").exists():
            config.load_incluster_config()
            logger.info("Loaded in-cluster Kubernetes configuration")
        else:
            config.load_kube_config()
            logger.info("Loaded kubeconfig from local environment")
        
        api_client = client.ApiClient()
        v1 = client.CoreV1Api()
        apps_v1 = client.AppsV1Api()
        rbac_v1 = client.RbacAuthorizationV1Api()
        custom_objects_api = client.CustomObjectsApi()
        
        logger.info("Kubernetes clients initialized successfully")
    except Exception as e:
        logger.error(f"Failed to initialize Kubernetes clients: {e}")
        sys.exit(1)


@kopf.on.startup()
async def startup_handler(settings: kopf.OperatorSettings, **kwargs):
    """Operator startup configuration."""
    logger.info("Starting AIVO Learner Namespace Operator")
    
    # Initialize Kubernetes clients
    setup_kubernetes()
    
    # Configure kopf settings
    settings.posting.level = logging.INFO
    settings.watching.reconnect_backoff = 1.0
    settings.networking.connect_timeout = 10.0
    settings.networking.request_timeout = 30.0
    
    logger.info("Operator startup completed")


@kopf.on.cleanup()
async def cleanup_handler(**kwargs):
    """Operator shutdown cleanup."""
    logger.info("AIVO Learner Namespace Operator shutting down")


if __name__ == "__main__":
    # Import handlers after clients are available
    from handlers import *
    
    logger.info("Starting operator main loop")
    kopf.run(
        clusterwide=True,
        liveness_endpoint="http://0.0.0.0:8080/healthz"
    )
