"""
Utility functions for data residency service
"""

import boto3
from datetime import datetime, timedelta
from typing import Dict, Any, List, Optional
from uuid import UUID
import structlog
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_

from app.config import settings
from app.models import DataAccessLog, EmergencyOverride

logger = structlog.get_logger()


async def generate_presigned_urls(
    region_code: str,
    bucket_name: str,
    object_keys: List[str],
    operation: str = "get_object",
    expires_in: int = 3600
) -> Dict[str, str]:
    """
    Generate presigned URLs for S3 objects in a specific region
    
    Args:
        region_code: Target region code
        bucket_name: S3 bucket name
        object_keys: List of object keys
        operation: S3 operation (get_object, put_object, delete_object)
        expires_in: URL expiration time in seconds
    
    Returns:
        Dictionary mapping object keys to presigned URLs
    """
    try:
        # Get region-specific S3 configuration
        from app.config import get_region_infrastructure
        infrastructure = get_region_infrastructure(region_code)
        s3_config = infrastructure["s3"]
        
        # Create S3 client for the specific region
        s3_client = boto3.client(
            's3',
            region_name=s3_config["region"],
            aws_access_key_id=settings.aws_access_key_id,
            aws_secret_access_key=settings.aws_secret_access_key
        )
        
        presigned_urls = {}
        
        for object_key in object_keys:
            try:
                url = s3_client.generate_presigned_url(
                    operation,
                    Params={'Bucket': bucket_name, 'Key': object_key},
                    ExpiresIn=expires_in
                )
                presigned_urls[object_key] = url
                
                logger.debug(
                    "Generated presigned URL",
                    region=region_code,
                    bucket=bucket_name,
                    object_key=object_key,
                    operation=operation
                )
                
            except Exception as e:
                logger.error(
                    "Failed to generate presigned URL",
                    region=region_code,
                    bucket=bucket_name,
                    object_key=object_key,
                    error=str(e)
                )
                continue
        
        return presigned_urls
        
    except Exception as e:
        logger.error(
            "Failed to generate presigned URLs",
            region=region_code,
            error=str(e)
        )
        return {}


async def check_emergency_override(
    db: AsyncSession,
    tenant_id: str,
    user_id: str,
    reason: Optional[str] = None
) -> Dict[str, Any]:
    """
    Check if user has valid emergency override for cross-region access
    
    Args:
        db: Database session
        tenant_id: Tenant ID
        user_id: User requesting override
        reason: Reason for override request
    
    Returns:
        Dictionary with override status and details
    """
    try:
        # Check for active emergency overrides
        query = select(EmergencyOverride).where(
            and_(
                EmergencyOverride.tenant_id == tenant_id,
                EmergencyOverride.status == "approved",
                EmergencyOverride.valid_from <= datetime.utcnow(),
                EmergencyOverride.valid_until > datetime.utcnow()
            )
        )
        
        result = await db.execute(query)
        active_overrides = result.scalars().all()
        
        if not active_overrides:
            logger.warning(
                "No active emergency overrides found",
                tenant_id=tenant_id,
                user_id=user_id
            )
            return {
                "allowed": False,
                "reason": "No active emergency override found",
                "override_id": None
            }
        
        # Use the most recent override
        active_override = sorted(active_overrides, key=lambda x: x.approved_at, reverse=True)[0]
        
        # Update usage count
        active_override.used_count += 1
        active_override.last_used_at = datetime.utcnow()
        await db.commit()
        
        logger.warning(
            "Emergency override used",
            override_id=str(active_override.override_id),
            tenant_id=tenant_id,
            user_id=user_id,
            used_count=active_override.used_count
        )
        
        return {
            "allowed": True,
            "reason": "Valid emergency override active",
            "override_id": str(active_override.override_id),
            "expires_at": active_override.valid_until.isoformat(),
            "usage_count": active_override.used_count
        }
        
    except Exception as e:
        logger.error(
            "Error checking emergency override",
            tenant_id=tenant_id,
            user_id=user_id,
            error=str(e)
        )
        return {
            "allowed": False,
            "reason": f"Error checking override: {str(e)}",
            "override_id": None
        }


async def audit_log_access(
    db: AsyncSession,
    policy_id: Optional[UUID],
    tenant_id: str,
    learner_id: Optional[str],
    user_id: str,
    operation_type: str,
    resource_type: str,
    resource_id: str,
    requested_region: str,
    actual_region: str,
    is_cross_region: bool,
    compliance_check_result: str,
    request_id: str,
    denial_reason: Optional[str] = None,
    emergency_override: bool = False,
    override_reason: Optional[str] = None,
    override_authorized_by: Optional[str] = None,
    response_status: int = 200,
    response_time_ms: Optional[int] = None,
    bytes_transferred: Optional[int] = None,
    request_headers: Optional[Dict[str, Any]] = None,
    ip_address: Optional[str] = None,
    user_agent: Optional[str] = None
):
    """
    Log data access for audit and compliance tracking
    
    Args:
        db: Database session
        policy_id: Related residency policy ID
        tenant_id: Tenant ID
        learner_id: Learner ID (optional)
        user_id: User performing the access
        operation_type: Type of operation (read, write, delete, inference)
        resource_type: Type of resource being accessed
        resource_id: Resource identifier
        requested_region: Originally requested region
        actual_region: Actual region used
        is_cross_region: Whether this was cross-region access
        compliance_check_result: Result of compliance check (allowed, denied, override)
        request_id: Request ID for tracing
        denial_reason: Reason for denial (if applicable)
        emergency_override: Whether emergency override was used
        override_reason: Reason for override
        override_authorized_by: Who authorized the override
        response_status: HTTP response status
        response_time_ms: Response time in milliseconds
        bytes_transferred: Number of bytes transferred
        request_headers: Request headers
        ip_address: Client IP address
        user_agent: Client user agent
    """
    try:
        access_log = DataAccessLog(
            policy_id=policy_id,
            tenant_id=tenant_id,
            learner_id=learner_id,
            user_id=user_id,
            operation_type=operation_type,
            resource_type=resource_type,
            resource_id=resource_id,
            requested_region=requested_region,
            actual_region=actual_region,
            is_cross_region=is_cross_region,
            compliance_check_result=compliance_check_result,
            denial_reason=denial_reason,
            emergency_override=emergency_override,
            override_reason=override_reason,
            override_authorized_by=override_authorized_by,
            request_id=request_id,
            request_headers=request_headers,
            ip_address=ip_address,
            user_agent=user_agent,
            response_status=response_status,
            response_time_ms=response_time_ms,
            bytes_transferred=bytes_transferred
        )
        
        db.add(access_log)
        await db.commit()
        
        logger.info(
            "Access logged for audit",
            log_id=str(access_log.log_id),
            tenant_id=tenant_id,
            operation_type=operation_type,
            compliance_check_result=compliance_check_result,
            is_cross_region=is_cross_region,
            emergency_override=emergency_override
        )
        
    except Exception as e:
        logger.error(
            "Failed to log access for audit",
            tenant_id=tenant_id,
            operation_type=operation_type,
            error=str(e)
        )
        # Don't raise exception here as audit logging shouldn't break the main flow
        pass


def validate_region_compliance(region_code: str, compliance_frameworks: List[str]) -> Dict[str, Any]:
    """
    Validate if a region meets compliance requirements
    
    Args:
        region_code: Region to validate
        compliance_frameworks: List of required compliance frameworks
    
    Returns:
        Dictionary with validation results
    """
    from app.config import is_region_compliant, get_compliance_requirements
    
    try:
        # Check basic region compliance
        is_compliant = is_region_compliant(region_code, compliance_frameworks)
        
        if not is_compliant:
            return {
                "valid": False,
                "reason": f"Region {region_code} does not meet compliance requirements for {compliance_frameworks}",
                "requirements": {}
            }
        
        # Get detailed compliance requirements
        requirements = get_compliance_requirements(compliance_frameworks)
        
        return {
            "valid": True,
            "reason": "Region meets all compliance requirements",
            "requirements": requirements
        }
        
    except Exception as e:
        logger.error(
            "Error validating region compliance",
            region_code=region_code,
            compliance_frameworks=compliance_frameworks,
            error=str(e)
        )
        return {
            "valid": False,
            "reason": f"Error validating compliance: {str(e)}",
            "requirements": {}
        }


def get_regional_inference_endpoints(region_code: str, model_type: Optional[str] = None) -> List[Dict[str, Any]]:
    """
    Get available inference endpoints for a specific region
    
    Args:
        region_code: Target region
        model_type: Optional model type filter
    
    Returns:
        List of available inference endpoints
    """
    try:
        from app.config import get_region_infrastructure
        infrastructure = get_region_infrastructure(region_code)
        inference_providers = infrastructure.get("inference", [])
        
        if model_type:
            # Filter providers that support the requested model type
            filtered_providers = []
            for provider in inference_providers:
                if model_type in provider.get("models", []):
                    filtered_providers.append(provider)
            return filtered_providers
        
        return inference_providers
        
    except Exception as e:
        logger.error(
            "Error getting regional inference endpoints",
            region_code=region_code,
            model_type=model_type,
            error=str(e)
        )
        return []


def calculate_data_retention_expiry(
    compliance_frameworks: List[str],
    data_classification: str = "standard",
    created_at: Optional[datetime] = None
) -> Optional[datetime]:
    """
    Calculate when data should expire based on compliance requirements
    
    Args:
        compliance_frameworks: List of applicable compliance frameworks
        data_classification: Data classification level
        created_at: When the data was created (defaults to now)
    
    Returns:
        Expiry datetime or None if no retention limit
    """
    from app.config import get_compliance_requirements
    
    try:
        if not created_at:
            created_at = datetime.utcnow()
        
        requirements = get_compliance_requirements(compliance_frameworks)
        max_retention_days = requirements.get("data_retention_max_days")
        
        if max_retention_days:
            # Apply stricter limits for sensitive data
            if data_classification in ["sensitive", "restricted"]:
                max_retention_days = min(max_retention_days, 180)  # 6 months max for sensitive data
            elif data_classification == "confidential":
                max_retention_days = min(max_retention_days, 90)   # 3 months max for confidential data
            
            expiry_date = created_at + timedelta(days=max_retention_days)
            
            logger.debug(
                "Calculated data retention expiry",
                compliance_frameworks=compliance_frameworks,
                data_classification=data_classification,
                max_retention_days=max_retention_days,
                expiry_date=expiry_date.isoformat()
            )
            
            return expiry_date
        
        return None
        
    except Exception as e:
        logger.error(
            "Error calculating data retention expiry",
            compliance_frameworks=compliance_frameworks,
            data_classification=data_classification,
            error=str(e)
        )
        return None


async def check_cross_region_policy_violations(
    db: AsyncSession,
    tenant_id: str,
    source_region: str,
    target_region: str,
    operation_type: str
) -> Dict[str, Any]:
    """
    Check for policy violations in cross-region operations
    
    Args:
        db: Database session
        tenant_id: Tenant ID
        source_region: Source region
        target_region: Target region
        operation_type: Type of operation
    
    Returns:
        Dictionary with violation check results
    """
    try:
        from app.models import ResidencyPolicy
        
        # Get active tenant policy
        query = select(ResidencyPolicy).where(
            and_(
                ResidencyPolicy.tenant_id == tenant_id,
                ResidencyPolicy.is_active == True,
                ResidencyPolicy.learner_id.is_(None)  # Tenant-wide policy
            )
        )
        
        policy = await db.scalar(query)
        
        if not policy:
            return {
                "violations": [],
                "allowed": True,
                "reason": "No policy found - default allow"
            }
        
        violations = []
        
        # Check if target region is prohibited
        if target_region in policy.prohibited_regions:
            violations.append(f"Target region {target_region} is explicitly prohibited")
        
        # Check if target region is in allowed list (if list is not empty)
        if policy.allowed_regions and target_region not in policy.allowed_regions:
            violations.append(f"Target region {target_region} is not in allowed regions list")
        
        # Check compliance framework restrictions
        if policy.compliance_frameworks:
            from app.config import get_compliance_requirements
            requirements = get_compliance_requirements(policy.compliance_frameworks)
            
            if requirements.get("cross_region_prohibited") and source_region != target_region:
                violations.append(f"Cross-region operations prohibited by compliance frameworks: {policy.compliance_frameworks}")
        
        # Check failover policy
        if not policy.allow_cross_region_failover and source_region != target_region:
            violations.append("Cross-region failover is disabled for this tenant")
        
        return {
            "violations": violations,
            "allowed": len(violations) == 0,
            "reason": "; ".join(violations) if violations else "No violations found"
        }
        
    except Exception as e:
        logger.error(
            "Error checking cross-region policy violations",
            tenant_id=tenant_id,
            source_region=source_region,
            target_region=target_region,
            error=str(e)
        )
        return {
            "violations": [f"Error checking policies: {str(e)}"],
            "allowed": False,
            "reason": f"Policy check failed: {str(e)}"
        }
