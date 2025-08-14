# AIVO SEL Service - Authentication and Consent Management
# S2-12 Implementation - FERPA-compliant consent verification

import logging
from typing import Dict, Optional, Any
from datetime import datetime, timezone
import uuid

from fastapi import HTTPException, status, Depends, Header
from sqlalchemy.orm import Session
from sqlalchemy import and_

from .models import ConsentRecord, ConsentStatus

logger = logging.getLogger(__name__)


async def get_current_user(authorization: str = Header(None)) -> Dict[str, Any]:
    """
    Extract user information from authorization header.
    This is a simplified implementation for the demo.
    In production, this would validate JWT tokens and extract user claims.
    """
    if not authorization:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authorization header required"
        )
    
    # Simple implementation for demo - in production this would:
    # 1. Validate JWT token
    # 2. Extract user claims
    # 3. Verify token signature and expiration
    # 4. Return user information
    
    try:
        # Mock user extraction from token
        # Format expected: "Bearer <token>"
        if not authorization.startswith("Bearer "):
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid authorization header format"
            )
        
        token = authorization[7:]  # Remove "Bearer " prefix
        
        # Mock token validation and user extraction
        # In production, this would decode and validate the JWT
        if len(token) < 10:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid token"
            )
        
        # Mock user data - in production this would come from token claims
        mock_user = {
            "user_id": uuid.uuid4(),
            "tenant_id": uuid.uuid4(),
            "role": "educator",
            "permissions": ["sel_data_access", "student_data_read"],
            "sub": "user123@example.com",
            "iat": datetime.now(timezone.utc).timestamp(),
            "exp": (datetime.now(timezone.utc).timestamp()) + 3600  # 1 hour
        }
        
        return mock_user
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error extracting user from token: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid authorization token"
        )


async def require_consent(
    student_id: uuid.UUID,
    tenant_id: uuid.UUID,
    consent_type: str,
    db: Session,
    raise_on_missing: bool = True
) -> Optional[ConsentRecord]:
    """
    Verify that appropriate consent exists for the requested operation.
    
    Args:
        student_id: The student's UUID
        tenant_id: The tenant's UUID
        consent_type: Type of consent required (e.g., "data_collection", "data_sharing", "alert_notifications")
        db: Database session
        raise_on_missing: Whether to raise an exception if consent is missing
        
    Returns:
        ConsentRecord if found and valid, None if not found and raise_on_missing=False
        
    Raises:
        HTTPException: If consent is missing, expired, or insufficient
    """
    try:
        # Query for active consent record
        consent = db.query(ConsentRecord).filter(
            and_(
                ConsentRecord.student_id == student_id,
                ConsentRecord.tenant_id == tenant_id,
                ConsentRecord.status == ConsentStatus.GRANTED
            )
        ).first()
        
        if not consent:
            if raise_on_missing:
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail="No valid consent found for student data access"
                )
            return None
        
        # Check if consent has expired
        if consent.expiration_date and consent.expiration_date < datetime.now(timezone.utc):
            if raise_on_missing:
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail="Consent has expired"
                )
            return None
        
        # Check specific consent permissions based on type
        consent_permissions = {
            "data_collection": consent.data_collection_allowed,
            "data_sharing": consent.data_sharing_allowed,
            "alert_notifications": consent.alert_notifications_allowed,
            "ai_processing": consent.ai_processing_allowed,
            "research_participation": consent.research_participation_allowed
        }
        
        permission_required = consent_permissions.get(consent_type)
        if permission_required is False:
            if raise_on_missing:
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail=f"Consent not granted for {consent_type}"
                )
            return None
        
        # For minors, verify both parent/guardian consent and student assent
        if consent.parent_guardian_consent is False:
            if raise_on_missing:
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail="Parent/guardian consent required"
                )
            return None
        
        # Additional validation for specific consent types
        if consent_type == "alert_notifications":
            if not consent.alert_notifications_allowed:
                if raise_on_missing:
                    raise HTTPException(
                        status_code=status.HTTP_403_FORBIDDEN,
                        detail="Alert notifications not permitted by consent"
                    )
                return None
        
        logger.info(f"Consent verified for student {student_id}, type: {consent_type}")
        return consent
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error verifying consent: {str(e)}")
        if raise_on_missing:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Error verifying consent"
            )
        return None


async def check_data_access_permissions(
    user: Dict[str, Any],
    student_id: uuid.UUID,
    tenant_id: uuid.UUID,
    access_type: str = "read"
) -> bool:
    """
    Check if the current user has permission to access student data.
    
    Args:
        user: User information from token
        student_id: Student's UUID
        tenant_id: Tenant's UUID
        access_type: Type of access requested ("read", "write", "delete")
        
    Returns:
        Boolean indicating if access is permitted
    """
    try:
        # Verify tenant matching
        if user.get("tenant_id") != tenant_id:
            logger.warning(f"Tenant mismatch: user {user.get('user_id')} attempted access to tenant {tenant_id}")
            return False
        
        # Check user role and permissions
        user_role = user.get("role", "").lower()
        user_permissions = user.get("permissions", [])
        
        # Define permission requirements
        permission_map = {
            "read": ["sel_data_access", "student_data_read"],
            "write": ["sel_data_access", "student_data_write"],
            "delete": ["sel_data_access", "student_data_delete", "admin"]
        }
        
        required_permissions = permission_map.get(access_type, [])
        
        # Check if user has any of the required permissions
        has_permission = any(perm in user_permissions for perm in required_permissions)
        
        # Special role-based access
        if user_role in ["educator", "counselor", "administrator"]:
            if access_type in ["read", "write"]:
                has_permission = True
        
        if user_role == "administrator":
            has_permission = True
        
        if not has_permission:
            logger.warning(f"Insufficient permissions for user {user.get('user_id')}: {user_permissions}")
        
        return has_permission
        
    except Exception as e:
        logger.error(f"Error checking data access permissions: {str(e)}")
        return False


async def require_data_access_permission(
    user: Dict[str, Any],
    student_id: uuid.UUID,
    tenant_id: uuid.UUID,
    access_type: str = "read"
):
    """
    Require that the user has appropriate data access permissions.
    Raises HTTPException if access is denied.
    """
    has_access = await check_data_access_permissions(user, student_id, tenant_id, access_type)
    
    if not has_access:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=f"Insufficient permissions for {access_type} access to student data"
        )


def verify_ferpa_compliance(consent: ConsentRecord, operation: str) -> bool:
    """
    Verify that the requested operation complies with FERPA requirements.
    
    Args:
        consent: The consent record to check
        operation: The operation being performed
        
    Returns:
        Boolean indicating FERPA compliance
    """
    try:
        # FERPA requires explicit consent for certain operations
        ferpa_sensitive_operations = [
            "data_sharing_external",
            "research_participation",
            "third_party_access",
            "marketing_communications"
        ]
        
        # Check if operation requires explicit consent under FERPA
        if operation in ferpa_sensitive_operations:
            if not consent.data_sharing_allowed:
                return False
        
        # Verify consent is current and valid
        if consent.status != ConsentStatus.GRANTED:
            return False
        
        # Check expiration
        if consent.expiration_date and consent.expiration_date < datetime.now(timezone.utc):
            return False
        
        # For minors, verify both parent consent and student assent
        if consent.parent_guardian_consent is False:
            return False
        
        # Additional FERPA-specific checks could be added here
        
        return True
        
    except Exception as e:
        logger.error(f"Error verifying FERPA compliance: {str(e)}")
        return False


async def log_data_access(
    user: Dict[str, Any],
    student_id: uuid.UUID,
    tenant_id: uuid.UUID,
    operation: str,
    success: bool,
    additional_info: Optional[Dict] = None
):
    """
    Log data access for audit trail and compliance.
    
    Args:
        user: User performing the operation
        student_id: Student whose data was accessed
        tenant_id: Tenant ID
        operation: Operation performed
        success: Whether the operation succeeded
        additional_info: Additional context information
    """
    try:
        # In production, this would write to an audit log system
        audit_entry = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "user_id": user.get("user_id"),
            "user_role": user.get("role"),
            "tenant_id": tenant_id,
            "student_id": student_id,
            "operation": operation,
            "success": success,
            "ip_address": None,  # Would be extracted from request in production
            "user_agent": None,  # Would be extracted from request in production
            "additional_info": additional_info or {}
        }
        
        logger.info(f"Data access audit: {audit_entry}")
        
        # In production, this would:
        # 1. Write to secure audit log database
        # 2. Send to compliance monitoring system
        # 3. Alert on suspicious access patterns
        # 4. Maintain tamper-proof audit trail
        
    except Exception as e:
        logger.error(f"Error logging data access: {str(e)}")


class ConsentManager:
    """
    Centralized consent management for SEL service operations.
    """
    
    @staticmethod
    async def verify_operation_consent(
        student_id: uuid.UUID,
        tenant_id: uuid.UUID,
        operation: str,
        db: Session
    ) -> ConsentRecord:
        """
        Verify consent for a specific operation with detailed validation.
        """
        consent = await require_consent(student_id, tenant_id, operation, db)
        
        # Additional operation-specific validation
        operation_requirements = {
            "sel_checkin": ["data_collection_allowed"],
            "strategy_generation": ["data_collection_allowed", "ai_processing_allowed"],
            "alert_generation": ["alert_notifications_allowed"],
            "report_generation": ["data_sharing_allowed"],
            "ai_analysis": ["ai_processing_allowed"]
        }
        
        requirements = operation_requirements.get(operation, [])
        for requirement in requirements:
            if not getattr(consent, requirement, False):
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail=f"Consent not granted for {requirement}"
                )
        
        # Verify FERPA compliance
        if not verify_ferpa_compliance(consent, operation):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Operation does not comply with FERPA requirements"
            )
        
        return consent
    
    @staticmethod
    async def check_alert_consent(
        student_id: uuid.UUID,
        tenant_id: uuid.UUID,
        alert_level: str,
        db: Session
    ) -> bool:
        """
        Check if consent allows for the specific alert level.
        """
        try:
            consent = await require_consent(student_id, tenant_id, "alert_notifications", db, raise_on_missing=False)
            
            if not consent or not consent.alert_notifications_allowed:
                return False
            
            # Check custom thresholds if defined
            if consent.alert_thresholds:
                custom_settings = consent.alert_thresholds.get("alert_levels", {})
                if alert_level in custom_settings:
                    return custom_settings[alert_level]
            
            # Default: allow all alert levels if notifications are enabled
            return True
            
        except Exception as e:
            logger.error(f"Error checking alert consent: {str(e)}")
            return False
