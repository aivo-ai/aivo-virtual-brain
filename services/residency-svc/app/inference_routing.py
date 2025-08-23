"""
Integration with Inference Gateway for Regional Routing
Provides regional routing policies for model inference
"""

from typing import Dict, List, Optional, Any
from fastapi import APIRouter, HTTPException, Depends, Header
from sqlalchemy.ext.asyncio import AsyncSession
import structlog

from app.database import get_db_session
from app.models import ResidencyPolicy
from app.config import settings, get_region_infrastructure, get_compliance_requirements
from app.utils import get_regional_inference_endpoints, validate_region_compliance

logger = structlog.get_logger()

# Router for inference gateway integration
inference_router = APIRouter(prefix="/api/v1/inference", tags=["inference"])


@inference_router.post("/route")
async def route_inference_request(
    request_data: Dict[str, Any],
    db: AsyncSession = Depends(get_db_session),
    x_user_id: str = Header(..., alias="X-User-ID"),
    x_tenant_id: str = Header(..., alias="X-Tenant-ID"),
    x_request_id: str = Header(..., alias="X-Request-ID"),
    x_region: Optional[str] = Header(None, alias="X-Region")
):
    """
    Route inference request to appropriate regional endpoint
    
    Request data should include:
    - model_type: Type of model requested (e.g., "claude-3-haiku", "gpt-4")
    - learner_id: Optional learner ID
    - operation_type: Type of operation ("inference", "training", "fine-tuning")
    - data_classification: Data sensitivity level
    """
    
    model_type = request_data.get("model_type")
    learner_id = request_data.get("learner_id")
    operation_type = request_data.get("operation_type", "inference")
    data_classification = request_data.get("data_classification", "standard")
    
    if not model_type:
        raise HTTPException(status_code=400, detail="model_type is required")
    
    logger.info(
        "Routing inference request",
        tenant_id=x_tenant_id,
        learner_id=learner_id,
        model_type=model_type,
        operation_type=operation_type,
        user_id=x_user_id,
        request_id=x_request_id
    )
    
    # Get applicable residency policy
    from sqlalchemy import select, and_
    
    policy_query = select(ResidencyPolicy).where(
        and_(
            ResidencyPolicy.tenant_id == x_tenant_id,
            ResidencyPolicy.is_active == True
        )
    )
    
    # Try learner-specific policy first
    if learner_id:
        learner_policy_query = policy_query.where(ResidencyPolicy.learner_id == learner_id)
        policy = await db.scalar(learner_policy_query)
        
        if not policy:
            # Fall back to tenant-wide policy
            tenant_policy_query = policy_query.where(ResidencyPolicy.learner_id.is_(None))
            policy = await db.scalar(tenant_policy_query)
    else:
        tenant_policy_query = policy_query.where(ResidencyPolicy.learner_id.is_(None))
        policy = await db.scalar(tenant_policy_query)
    
    # Determine target region
    if policy:
        target_region = policy.primary_region
        compliance_frameworks = policy.compliance_frameworks
        
        # Check if requested region is allowed
        if x_region and x_region != policy.primary_region:
            # Validate cross-region request
            if x_region in policy.prohibited_regions:
                raise HTTPException(
                    status_code=403,
                    detail=f"Inference in region {x_region} is prohibited"
                )
            
            if policy.allowed_regions and x_region not in policy.allowed_regions:
                raise HTTPException(
                    status_code=403,
                    detail=f"Inference in region {x_region} is not allowed"
                )
            
            # Check compliance restrictions
            compliance_requirements = get_compliance_requirements(compliance_frameworks)
            if compliance_requirements.get("cross_region_prohibited"):
                raise HTTPException(
                    status_code=403,
                    detail=f"Cross-region inference prohibited by compliance: {compliance_frameworks}"
                )
            
            target_region = x_region
    else:
        # No policy - use default region
        target_region = x_region or settings.default_region
        compliance_frameworks = []
    
    # Get available inference endpoints for the target region
    inference_endpoints = get_regional_inference_endpoints(target_region, model_type)
    
    if not inference_endpoints:
        # Try fallback regions if cross-region failover is allowed
        if policy and policy.allow_cross_region_failover:
            fallback_regions = policy.allowed_regions or []
            
            for fallback_region in fallback_regions:
                fallback_endpoints = get_regional_inference_endpoints(fallback_region, model_type)
                if fallback_endpoints:
                    target_region = fallback_region
                    inference_endpoints = fallback_endpoints
                    
                    logger.warning(
                        "Using fallback region for inference",
                        original_region=policy.primary_region,
                        fallback_region=target_region,
                        tenant_id=x_tenant_id
                    )
                    break
        
        if not inference_endpoints:
            raise HTTPException(
                status_code=404,
                detail=f"No inference endpoints available for model {model_type} in region {target_region}"
            )
    
    # Select best endpoint based on availability and compliance
    selected_endpoint = select_best_inference_endpoint(
        inference_endpoints,
        compliance_frameworks,
        data_classification
    )
    
    # Get regional infrastructure details
    infrastructure = get_region_infrastructure(target_region)
    
    # Build routing response
    routing_response = {
        "target_region": target_region,
        "selected_endpoint": selected_endpoint,
        "infrastructure": infrastructure,
        "compliance_frameworks": compliance_frameworks,
        "routing_metadata": {
            "policy_id": str(policy.policy_id) if policy else None,
            "fallback_used": target_region != (policy.primary_region if policy else settings.default_region),
            "cross_region": x_region is not None and x_region != target_region,
            "data_classification": data_classification
        }
    }
    
    logger.info(
        "Inference request routed",
        tenant_id=x_tenant_id,
        target_region=target_region,
        endpoint_provider=selected_endpoint["provider"],
        model_type=model_type,
        compliance_frameworks=compliance_frameworks
    )
    
    return routing_response


@inference_router.get("/endpoints/{region_code}")
async def list_inference_endpoints(
    region_code: str,
    model_type: Optional[str] = None,
    x_user_id: str = Header(..., alias="X-User-ID"),
    x_request_id: str = Header(..., alias="X-Request-ID")
):
    """List available inference endpoints for a specific region"""
    
    if region_code not in settings.supported_regions:
        raise HTTPException(
            status_code=400,
            detail=f"Unsupported region: {region_code}"
        )
    
    try:
        endpoints = get_regional_inference_endpoints(region_code, model_type)
        
        logger.info(
            "Listed inference endpoints",
            region_code=region_code,
            model_type=model_type,
            endpoint_count=len(endpoints),
            user_id=x_user_id
        )
        
        return {
            "region_code": region_code,
            "model_type": model_type,
            "endpoints": endpoints,
            "total_count": len(endpoints)
        }
        
    except Exception as e:
        logger.error(
            "Failed to list inference endpoints",
            region_code=region_code,
            error=str(e)
        )
        raise HTTPException(status_code=500, detail=str(e))


@inference_router.post("/validate-routing")
async def validate_inference_routing(
    validation_request: Dict[str, Any],
    db: AsyncSession = Depends(get_db_session),
    x_user_id: str = Header(..., alias="X-User-ID"),
    x_request_id: str = Header(..., alias="X-Request-ID")
):
    """
    Validate inference routing configuration for a tenant
    
    Request should include:
    - tenant_id: Tenant to validate
    - target_regions: List of regions to validate
    - model_types: List of model types to validate
    - compliance_frameworks: List of compliance frameworks to check
    """
    
    tenant_id = validation_request.get("tenant_id")
    target_regions = validation_request.get("target_regions", [])
    model_types = validation_request.get("model_types", [])
    compliance_frameworks = validation_request.get("compliance_frameworks", [])
    
    if not tenant_id:
        raise HTTPException(status_code=400, detail="tenant_id is required")
    
    validation_results = {
        "tenant_id": tenant_id,
        "overall_valid": True,
        "validation_details": [],
        "warnings": [],
        "errors": []
    }
    
    # Get tenant policy
    from sqlalchemy import select, and_
    
    policy_query = select(ResidencyPolicy).where(
        and_(
            ResidencyPolicy.tenant_id == tenant_id,
            ResidencyPolicy.is_active == True,
            ResidencyPolicy.learner_id.is_(None)  # Tenant-wide policy
        )
    )
    
    policy = await db.scalar(policy_query)
    
    if not policy:
        validation_results["warnings"].append("No residency policy found for tenant - using default settings")
        effective_compliance = compliance_frameworks
        allowed_regions = target_regions
    else:
        effective_compliance = policy.compliance_frameworks + compliance_frameworks
        allowed_regions = [policy.primary_region] + (policy.allowed_regions or [])
    
    # Validate each region
    for region in target_regions:
        region_validation = {
            "region_code": region,
            "valid": True,
            "issues": []
        }
        
        # Check if region is supported
        if region not in settings.supported_regions:
            region_validation["valid"] = False
            region_validation["issues"].append(f"Region {region} is not supported")
            validation_results["overall_valid"] = False
            
        # Check compliance requirements
        compliance_check = validate_region_compliance(region, effective_compliance)
        if not compliance_check["valid"]:
            region_validation["valid"] = False
            region_validation["issues"].append(compliance_check["reason"])
            validation_results["overall_valid"] = False
        
        # Check policy restrictions
        if policy:
            if region in policy.prohibited_regions:
                region_validation["valid"] = False
                region_validation["issues"].append(f"Region {region} is prohibited by policy")
                validation_results["overall_valid"] = False
            
            if region not in allowed_regions:
                region_validation["valid"] = False
                region_validation["issues"].append(f"Region {region} is not in allowed regions")
                validation_results["overall_valid"] = False
        
        # Check model availability
        for model_type in model_types:
            endpoints = get_regional_inference_endpoints(region, model_type)
            if not endpoints:
                region_validation["issues"].append(f"Model {model_type} not available in region {region}")
                validation_results["warnings"].append(f"Model {model_type} unavailable in {region}")
        
        validation_results["validation_details"].append(region_validation)
    
    # Overall compliance check
    if effective_compliance:
        compliance_requirements = get_compliance_requirements(effective_compliance)
        
        if compliance_requirements.get("cross_region_prohibited"):
            cross_region_count = len([r for r in target_regions if r != (policy.primary_region if policy else settings.default_region)])
            if cross_region_count > 0:
                validation_results["warnings"].append(f"Compliance frameworks {effective_compliance} restrict cross-region operations")
        
        if compliance_requirements.get("data_retention_max_days"):
            validation_results["warnings"].append(f"Data retention limited to {compliance_requirements['data_retention_max_days']} days")
    
    logger.info(
        "Validated inference routing",
        tenant_id=tenant_id,
        overall_valid=validation_results["overall_valid"],
        regions_count=len(target_regions),
        models_count=len(model_types),
        user_id=x_user_id
    )
    
    return validation_results


def select_best_inference_endpoint(
    endpoints: List[Dict[str, Any]],
    compliance_frameworks: List[str],
    data_classification: str
) -> Dict[str, Any]:
    """
    Select the best inference endpoint based on compliance and classification
    
    Args:
        endpoints: List of available endpoints
        compliance_frameworks: Required compliance frameworks
        data_classification: Data sensitivity level
    
    Returns:
        Selected endpoint configuration
    """
    
    if not endpoints:
        raise ValueError("No endpoints available")
    
    # Score endpoints based on compliance and capabilities
    scored_endpoints = []
    
    for endpoint in endpoints:
        score = 0
        
        # Prefer endpoints with better compliance support
        endpoint_compliance = endpoint.get("compliance_features", [])
        if "encryption_at_rest" in endpoint_compliance:
            score += 10
        if "encryption_in_transit" in endpoint_compliance:
            score += 10
        if "audit_logging" in endpoint_compliance:
            score += 5
        
        # Prefer managed services for sensitive data
        if data_classification in ["sensitive", "confidential", "restricted"]:
            if endpoint["provider"] in ["aws-bedrock", "azure-openai"]:
                score += 20
        
        # Prefer regional providers for GDPR compliance
        if "gdpr" in compliance_frameworks:
            if "eu" in endpoint.get("region", ""):
                score += 15
            if endpoint["provider"] in ["anthropic-eu"]:
                score += 10
        
        # Prefer high-availability endpoints
        if endpoint.get("high_availability", False):
            score += 5
        
        # Consider model variety
        score += len(endpoint.get("models", [])) * 2
        
        scored_endpoints.append((score, endpoint))
    
    # Sort by score (highest first) and return best endpoint
    scored_endpoints.sort(key=lambda x: x[0], reverse=True)
    
    selected = scored_endpoints[0][1]
    
    logger.debug(
        "Selected inference endpoint",
        provider=selected["provider"],
        region=selected.get("region"),
        score=scored_endpoints[0][0],
        compliance_frameworks=compliance_frameworks,
        data_classification=data_classification
    )
    
    return selected


# Health check for inference routing
@inference_router.get("/health")
async def inference_routing_health():
    """Health check for inference routing capability"""
    
    health_status = {
        "status": "healthy",
        "regions_available": 0,
        "total_endpoints": 0,
        "issues": []
    }
    
    try:
        for region in settings.supported_regions:
            try:
                endpoints = get_regional_inference_endpoints(region)
                if endpoints:
                    health_status["regions_available"] += 1
                    health_status["total_endpoints"] += len(endpoints)
                else:
                    health_status["issues"].append(f"No endpoints available in region {region}")
            except Exception as e:
                health_status["issues"].append(f"Error checking region {region}: {str(e)}")
        
        if health_status["regions_available"] == 0:
            health_status["status"] = "unhealthy"
        elif health_status["issues"]:
            health_status["status"] = "degraded"
        
    except Exception as e:
        health_status["status"] = "unhealthy"
        health_status["issues"].append(f"Health check failed: {str(e)}")
    
    return health_status
