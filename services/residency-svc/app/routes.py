"""
API Routes for Data Residency Service
Handles region resolution, policy management, and compliance enforcement
"""

from datetime import datetime, timedelta
from typing import List, Optional, Dict, Any
from uuid import UUID
from fastapi import APIRouter, HTTPException, Depends, Header, Request, BackgroundTasks
from fastapi.responses import JSONResponse
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_, or_
from sqlalchemy.orm import selectinload
import structlog

from app.models import (
    ResidencyPolicy, RegionInfrastructure, DataAccessLog, EmergencyOverride,
    ResidencyPolicyRequest, ResidencyPolicyResponse, DataAccessRequest, 
    DataAccessResponse, EmergencyOverrideRequest, RegionCode
)
from app.config import settings, get_region_infrastructure, get_compliance_requirements, is_region_compliant
from app.database import get_db_session
from app.utils import generate_presigned_urls, check_emergency_override, audit_log_access

logger = structlog.get_logger()

# Router setup
router = APIRouter(prefix="/api/v1", tags=["residency"])


@router.post("/policies", response_model=ResidencyPolicyResponse)
async def create_residency_policy(
    policy_request: ResidencyPolicyRequest,
    db: AsyncSession = Depends(get_db_session),
    x_user_id: str = Header(..., alias="X-User-ID"),
    x_request_id: str = Header(..., alias="X-Request-ID")
):
    """Create a new data residency policy for a tenant/learner"""
    logger.info(
        "Creating residency policy",
        tenant_id=policy_request.tenant_id,
        learner_id=policy_request.learner_id,
        primary_region=policy_request.primary_region,
        user_id=x_user_id,
        request_id=x_request_id
    )
    
    # Validate regions
    invalid_regions = []
    all_regions = [policy_request.primary_region] + policy_request.allowed_regions + policy_request.prohibited_regions
    for region in all_regions:
        if region.value not in settings.supported_regions:
            invalid_regions.append(region.value)
    
    if invalid_regions:
        raise HTTPException(
            status_code=400,
            detail=f"Unsupported regions: {invalid_regions}"
        )
    
    # Check for conflicting regions
    allowed_set = set([r.value for r in policy_request.allowed_regions])
    prohibited_set = set([r.value for r in policy_request.prohibited_regions])
    conflicts = allowed_set.intersection(prohibited_set)
    
    if conflicts:
        raise HTTPException(
            status_code=400,
            detail=f"Regions cannot be both allowed and prohibited: {conflicts}"
        )
    
    # Validate compliance frameworks with primary region
    if policy_request.compliance_frameworks:
        frameworks = [f.value for f in policy_request.compliance_frameworks]
        if not is_region_compliant(policy_request.primary_region.value, frameworks):
            raise HTTPException(
                status_code=400,
                detail=f"Primary region {policy_request.primary_region.value} is not compliant with frameworks: {frameworks}"
            )
    
    # Check for existing policy
    existing_query = select(ResidencyPolicy).where(
        and_(
            ResidencyPolicy.tenant_id == policy_request.tenant_id,
            ResidencyPolicy.learner_id == policy_request.learner_id,
            ResidencyPolicy.is_active == True
        )
    )
    existing_policy = await db.scalar(existing_query)
    
    if existing_policy:
        # Deactivate existing policy
        existing_policy.is_active = False
        existing_policy.updated_at = datetime.utcnow()
        await db.commit()
        
        logger.info(
            "Deactivated existing policy",
            old_policy_id=str(existing_policy.policy_id),
            tenant_id=policy_request.tenant_id
        )
    
    # Create new policy
    new_policy = ResidencyPolicy(
        tenant_id=policy_request.tenant_id,
        learner_id=policy_request.learner_id,
        primary_region=policy_request.primary_region.value,
        allowed_regions=[r.value for r in policy_request.allowed_regions],
        prohibited_regions=[r.value for r in policy_request.prohibited_regions],
        compliance_frameworks=[f.value for f in policy_request.compliance_frameworks],
        data_classification=policy_request.data_classification,
        allow_cross_region_failover=policy_request.allow_cross_region_failover,
        require_encryption_at_rest=policy_request.require_encryption_at_rest,
        require_encryption_in_transit=policy_request.require_encryption_in_transit,
        data_retention_days=policy_request.data_retention_days,
        emergency_contact=policy_request.emergency_contact,
        created_by=x_user_id
    )
    
    db.add(new_policy)
    await db.commit()
    await db.refresh(new_policy)
    
    logger.info(
        "Created residency policy",
        policy_id=str(new_policy.policy_id),
        tenant_id=policy_request.tenant_id,
        primary_region=policy_request.primary_region.value
    )
    
    return ResidencyPolicyResponse(
        policy_id=str(new_policy.policy_id),
        tenant_id=new_policy.tenant_id,
        learner_id=new_policy.learner_id,
        primary_region=new_policy.primary_region,
        allowed_regions=new_policy.allowed_regions,
        prohibited_regions=new_policy.prohibited_regions,
        compliance_frameworks=new_policy.compliance_frameworks,
        allow_cross_region_failover=new_policy.allow_cross_region_failover,
        is_active=new_policy.is_active,
        created_at=new_policy.created_at,
        updated_at=new_policy.updated_at
    )


@router.get("/policies/{tenant_id}", response_model=List[ResidencyPolicyResponse])
async def get_tenant_policies(
    tenant_id: str,
    learner_id: Optional[str] = None,
    active_only: bool = True,
    db: AsyncSession = Depends(get_db_session),
    x_user_id: str = Header(..., alias="X-User-ID"),
    x_request_id: str = Header(..., alias="X-Request-ID")
):
    """Get residency policies for a tenant"""
    
    query = select(ResidencyPolicy).where(ResidencyPolicy.tenant_id == tenant_id)
    
    if learner_id:
        query = query.where(ResidencyPolicy.learner_id == learner_id)
    
    if active_only:
        query = query.where(ResidencyPolicy.is_active == True)
    
    query = query.order_by(ResidencyPolicy.created_at.desc())
    
    result = await db.execute(query)
    policies = result.scalars().all()
    
    logger.info(
        "Retrieved tenant policies",
        tenant_id=tenant_id,
        learner_id=learner_id,
        policy_count=len(policies),
        user_id=x_user_id
    )
    
    return [
        ResidencyPolicyResponse(
            policy_id=str(policy.policy_id),
            tenant_id=policy.tenant_id,
            learner_id=policy.learner_id,
            primary_region=policy.primary_region,
            allowed_regions=policy.allowed_regions,
            prohibited_regions=policy.prohibited_regions,
            compliance_frameworks=policy.compliance_frameworks,
            allow_cross_region_failover=policy.allow_cross_region_failover,
            is_active=policy.is_active,
            created_at=policy.created_at,
            updated_at=policy.updated_at
        )
        for policy in policies
    ]


@router.post("/access/resolve", response_model=DataAccessResponse)
async def resolve_data_access(
    access_request: DataAccessRequest,
    background_tasks: BackgroundTasks,
    db: AsyncSession = Depends(get_db_session),
    x_user_id: str = Header(..., alias="X-User-ID"),
    x_request_id: str = Header(..., alias="X-Request-ID"),
    x_region: Optional[str] = Header(None, alias="X-Region")
):
    """Resolve data access request and determine appropriate region/infrastructure"""
    
    logger.info(
        "Resolving data access",
        tenant_id=access_request.tenant_id,
        learner_id=access_request.learner_id,
        operation_type=access_request.operation_type,
        resource_type=access_request.resource_type,
        requested_region=access_request.requested_region,
        user_id=x_user_id,
        request_id=x_request_id
    )
    
    # Find applicable residency policy
    policy_query = select(ResidencyPolicy).where(
        and_(
            ResidencyPolicy.tenant_id == access_request.tenant_id,
            ResidencyPolicy.is_active == True
        )
    )
    
    # Try learner-specific policy first, then tenant-wide
    if access_request.learner_id:
        learner_policy_query = policy_query.where(ResidencyPolicy.learner_id == access_request.learner_id)
        learner_policy = await db.scalar(learner_policy_query)
        
        if learner_policy:
            policy = learner_policy
        else:
            # Fall back to tenant-wide policy
            tenant_policy_query = policy_query.where(ResidencyPolicy.learner_id.is_(None))
            policy = await db.scalar(tenant_policy_query)
    else:
        tenant_policy_query = policy_query.where(ResidencyPolicy.learner_id.is_(None))
        policy = await db.scalar(tenant_policy_query)
    
    if not policy:
        # No policy found - use default region with basic compliance
        logger.warning(
            "No residency policy found, using default",
            tenant_id=access_request.tenant_id,
            learner_id=access_request.learner_id
        )
        
        target_region = access_request.requested_region or settings.default_region
        infrastructure = get_region_infrastructure(target_region)
        
        # Log access attempt
        background_tasks.add_task(
            audit_log_access,
            db=db,
            policy_id=None,
            tenant_id=access_request.tenant_id,
            learner_id=access_request.learner_id,
            user_id=x_user_id,
            operation_type=access_request.operation_type,
            resource_type=access_request.resource_type,
            resource_id=access_request.resource_id,
            requested_region=access_request.requested_region or "none",
            actual_region=target_region,
            is_cross_region=False,
            compliance_check_result="allowed",
            request_id=x_request_id
        )
        
        return DataAccessResponse(
            allowed=True,
            target_region=target_region,
            infrastructure=infrastructure,
            compliance_notes=["No specific policy - using default region"],
            emergency_override_used=False
        )
    
    # Check compliance requirements
    compliance_requirements = get_compliance_requirements(policy.compliance_frameworks)
    
    # Determine target region
    target_region = policy.primary_region
    requested_region = access_request.requested_region or x_region
    
    # Check if requested region is allowed
    if requested_region and requested_region != policy.primary_region:
        # Check if cross-region access is prohibited by compliance
        if compliance_requirements["cross_region_prohibited"]:
            if not access_request.emergency_override:
                logger.warning(
                    "Cross-region access denied by compliance",
                    tenant_id=access_request.tenant_id,
                    requested_region=requested_region,
                    primary_region=policy.primary_region,
                    compliance_frameworks=policy.compliance_frameworks
                )
                
                # Log denied access
                background_tasks.add_task(
                    audit_log_access,
                    db=db,
                    policy_id=policy.policy_id,
                    tenant_id=access_request.tenant_id,
                    learner_id=access_request.learner_id,
                    user_id=x_user_id,
                    operation_type=access_request.operation_type,
                    resource_type=access_request.resource_type,
                    resource_id=access_request.resource_id,
                    requested_region=requested_region,
                    actual_region=policy.primary_region,
                    is_cross_region=True,
                    compliance_check_result="denied",
                    denial_reason="Cross-region access prohibited by compliance frameworks",
                    request_id=x_request_id
                )
                
                raise HTTPException(
                    status_code=403,
                    detail=f"Cross-region access prohibited by compliance frameworks: {policy.compliance_frameworks}"
                )
        
        # Check if region is explicitly prohibited
        if requested_region in policy.prohibited_regions:
            if not access_request.emergency_override:
                logger.warning(
                    "Access to prohibited region denied",
                    tenant_id=access_request.tenant_id,
                    requested_region=requested_region,
                    prohibited_regions=policy.prohibited_regions
                )
                
                background_tasks.add_task(
                    audit_log_access,
                    db=db,
                    policy_id=policy.policy_id,
                    tenant_id=access_request.tenant_id,
                    learner_id=access_request.learner_id,
                    user_id=x_user_id,
                    operation_type=access_request.operation_type,
                    resource_type=access_request.resource_type,
                    resource_id=access_request.resource_id,
                    requested_region=requested_region,
                    actual_region=policy.primary_region,
                    is_cross_region=True,
                    compliance_check_result="denied",
                    denial_reason=f"Region {requested_region} is explicitly prohibited",
                    request_id=x_request_id
                )
                
                raise HTTPException(
                    status_code=403,
                    detail=f"Access to region {requested_region} is explicitly prohibited"
                )
        
        # Check if region is in allowed list (if allowed list is not empty)
        if policy.allowed_regions and requested_region not in policy.allowed_regions:
            if not access_request.emergency_override:
                logger.warning(
                    "Access to non-allowed region denied",
                    tenant_id=access_request.tenant_id,
                    requested_region=requested_region,
                    allowed_regions=policy.allowed_regions
                )
                
                background_tasks.add_task(
                    audit_log_access,
                    db=db,
                    policy_id=policy.policy_id,
                    tenant_id=access_request.tenant_id,
                    learner_id=access_request.learner_id,
                    user_id=x_user_id,
                    operation_type=access_request.operation_type,
                    resource_type=access_request.resource_type,
                    resource_id=access_request.resource_id,
                    requested_region=requested_region,
                    actual_region=policy.primary_region,
                    is_cross_region=True,
                    compliance_check_result="denied",
                    denial_reason=f"Region {requested_region} is not in allowed regions list",
                    request_id=x_request_id
                )
                
                raise HTTPException(
                    status_code=403,
                    detail=f"Region {requested_region} is not in allowed regions list"
                )
        
        # If we get here, the requested region is allowed or emergency override is used
        target_region = requested_region
    
    # Handle emergency override
    emergency_override_used = False
    if access_request.emergency_override:
        override_result = await check_emergency_override(
            db=db,
            tenant_id=access_request.tenant_id,
            user_id=x_user_id,
            reason=access_request.override_reason
        )
        
        if not override_result["allowed"]:
            raise HTTPException(
                status_code=403,
                detail=f"Emergency override denied: {override_result['reason']}"
            )
        
        emergency_override_used = True
        logger.warning(
            "Emergency override used",
            tenant_id=access_request.tenant_id,
            user_id=x_user_id,
            reason=access_request.override_reason,
            target_region=target_region
        )
    
    # Get infrastructure for target region
    try:
        infrastructure = get_region_infrastructure(target_region)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    
    # Build compliance notes
    compliance_notes = []
    if policy.compliance_frameworks:
        compliance_notes.append(f"Subject to compliance frameworks: {', '.join(policy.compliance_frameworks)}")
    
    if compliance_requirements["data_retention_max_days"]:
        compliance_notes.append(f"Data retention limited to {compliance_requirements['data_retention_max_days']} days")
    
    if policy.require_encryption_at_rest:
        compliance_notes.append("Encryption at rest required")
    
    if policy.require_encryption_in_transit:
        compliance_notes.append("Encryption in transit required")
    
    for special_req in compliance_requirements["special_requirements"]:
        compliance_notes.append(f"Special requirement: {special_req}")
    
    # Log successful access
    background_tasks.add_task(
        audit_log_access,
        db=db,
        policy_id=policy.policy_id,
        tenant_id=access_request.tenant_id,
        learner_id=access_request.learner_id,
        user_id=x_user_id,
        operation_type=access_request.operation_type,
        resource_type=access_request.resource_type,
        resource_id=access_request.resource_id,
        requested_region=requested_region or "none",
        actual_region=target_region,
        is_cross_region=(requested_region is not None and requested_region != policy.primary_region),
        compliance_check_result="override" if emergency_override_used else "allowed",
        emergency_override=emergency_override_used,
        override_reason=access_request.override_reason if emergency_override_used else None,
        override_authorized_by=x_user_id if emergency_override_used else None,
        request_id=x_request_id
    )
    
    logger.info(
        "Data access resolved",
        tenant_id=access_request.tenant_id,
        target_region=target_region,
        emergency_override_used=emergency_override_used,
        compliance_frameworks=policy.compliance_frameworks
    )
    
    return DataAccessResponse(
        allowed=True,
        target_region=target_region,
        infrastructure=infrastructure,
        compliance_notes=compliance_notes,
        emergency_override_used=emergency_override_used,
        expires_at=datetime.utcnow() + timedelta(hours=1) if emergency_override_used else None
    )


@router.post("/emergency/override", response_model=Dict[str, Any])
async def request_emergency_override(
    override_request: EmergencyOverrideRequest,
    db: AsyncSession = Depends(get_db_session),
    x_user_id: str = Header(..., alias="X-User-ID"),
    x_request_id: str = Header(..., alias="X-Request-ID")
):
    """Request emergency override for cross-region data access"""
    
    logger.warning(
        "Emergency override requested",
        tenant_id=override_request.tenant_id,
        reason=override_request.reason,
        source_region=override_request.source_region,
        target_region=override_request.target_region,
        duration_hours=override_request.duration_hours,
        user_id=x_user_id,
        request_id=x_request_id
    )
    
    # Validate duration
    if override_request.duration_hours > settings.emergency_override_max_duration_hours:
        raise HTTPException(
            status_code=400,
            detail=f"Override duration cannot exceed {settings.emergency_override_max_duration_hours} hours"
        )
    
    # Create override request
    override = EmergencyOverride(
        tenant_id=override_request.tenant_id,
        reason=override_request.reason,
        requested_by=x_user_id,
        affected_learners=override_request.affected_learners,
        source_region=override_request.source_region,
        target_region=override_request.target_region,
        valid_from=datetime.utcnow(),
        valid_until=datetime.utcnow() + timedelta(hours=override_request.duration_hours)
    )
    
    # Auto-approve if configured, otherwise requires manual approval
    if not settings.emergency_override_approval_required:
        override.status = "approved"
        override.approved_by = "system"
        override.approved_at = datetime.utcnow()
        override.approval_notes = "Auto-approved by system configuration"
    
    db.add(override)
    await db.commit()
    await db.refresh(override)
    
    logger.warning(
        "Emergency override created",
        override_id=str(override.override_id),
        status=override.status,
        tenant_id=override_request.tenant_id
    )
    
    return {
        "override_id": str(override.override_id),
        "status": override.status,
        "valid_from": override.valid_from.isoformat(),
        "valid_until": override.valid_until.isoformat(),
        "requires_approval": settings.emergency_override_approval_required,
        "message": "Override created successfully" if override.status == "approved" else "Override pending approval"
    }


@router.get("/regions", response_model=List[Dict[str, Any]])
async def list_supported_regions():
    """List all supported regions with infrastructure details"""
    
    regions = []
    for region_code in settings.supported_regions:
        try:
            infrastructure = get_region_infrastructure(region_code)
            
            # Get compliance frameworks applicable to this region
            applicable_frameworks = []
            for framework, config in settings.compliance_frameworks.items():
                if not config.get("applicable_regions") or region_code in config["applicable_regions"]:
                    applicable_frameworks.append({
                        "framework": framework,
                        "name": config["name"]
                    })
            
            regions.append({
                "region_code": region_code,
                "infrastructure": infrastructure,
                "compliance_frameworks": applicable_frameworks,
                "is_default": region_code == settings.default_region
            })
        except Exception as e:
            logger.error(f"Failed to get infrastructure for region {region_code}", error=str(e))
            continue
    
    return regions


@router.get("/audit/access-logs/{tenant_id}")
async def get_access_logs(
    tenant_id: str,
    learner_id: Optional[str] = None,
    start_date: Optional[datetime] = None,
    end_date: Optional[datetime] = None,
    operation_type: Optional[str] = None,
    limit: int = 100,
    offset: int = 0,
    db: AsyncSession = Depends(get_db_session),
    x_user_id: str = Header(..., alias="X-User-ID"),
    x_request_id: str = Header(..., alias="X-Request-ID")
):
    """Get audit logs for data access (admin/compliance use)"""
    
    query = select(DataAccessLog).where(DataAccessLog.tenant_id == tenant_id)
    
    if learner_id:
        query = query.where(DataAccessLog.learner_id == learner_id)
    
    if start_date:
        query = query.where(DataAccessLog.timestamp >= start_date)
    
    if end_date:
        query = query.where(DataAccessLog.timestamp <= end_date)
    
    if operation_type:
        query = query.where(DataAccessLog.operation_type == operation_type)
    
    query = query.order_by(DataAccessLog.timestamp.desc()).offset(offset).limit(limit)
    
    result = await db.execute(query)
    logs = result.scalars().all()
    
    logger.info(
        "Retrieved access logs",
        tenant_id=tenant_id,
        log_count=len(logs),
        user_id=x_user_id
    )
    
    return [
        {
            "log_id": str(log.log_id),
            "tenant_id": log.tenant_id,
            "learner_id": log.learner_id,
            "user_id": log.user_id,
            "operation_type": log.operation_type,
            "resource_type": log.resource_type,
            "resource_id": log.resource_id,
            "requested_region": log.requested_region,
            "actual_region": log.actual_region,
            "is_cross_region": log.is_cross_region,
            "compliance_check_result": log.compliance_check_result,
            "emergency_override": log.emergency_override,
            "timestamp": log.timestamp.isoformat()
        }
        for log in logs
    ]
