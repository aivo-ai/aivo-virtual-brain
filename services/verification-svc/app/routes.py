"""
API Routes for Guardian Identity Verification Service
COPPA-compliant verification endpoints with rate limiting and privacy controls
"""

import hashlib
from datetime import datetime, timedelta
from typing import List, Optional, Dict, Any
from fastapi import APIRouter, Depends, HTTPException, status, Request, BackgroundTasks
from fastapi.responses import JSONResponse
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, update, and_, or_, desc
from sqlalchemy.orm import selectinload
import structlog

from app.database import get_db_session
from app.config import settings
from app.models import (
    GuardianVerification, ChargeVerification, KBASession, 
    VerificationAuditLog, VerificationRateLimit, GeoPolicyRule,
    VerificationMethod, VerificationStatus, FailureReason
)
from app.schemas import (
    VerificationStartRequest, VerificationStartResponse,
    VerificationResultRequest, VerificationStatusResponse,
    GuardianVerificationSummary, BulkVerificationStatusRequest,
    BulkVerificationStatusResponse, RateLimitResponse,
    WebhookEventResponse, ErrorResponse
)
from app.providers.stripe_charge import stripe_charge_provider
from app.providers.kba_vendor import kba_vendor_provider

logger = structlog.get_logger(__name__)

router = APIRouter()


# Rate limiting dependency
async def check_rate_limit(
    request: Request,
    guardian_user_id: str,
    db: AsyncSession = Depends(get_db_session)
) -> None:
    """Check rate limits for verification attempts"""
    
    # Get IP address for additional rate limiting
    ip_address = request.client.host
    ip_hash = hashlib.sha256(ip_address.encode()).hexdigest() if ip_address else None
    
    # Check guardian-specific rate limit
    guardian_limit = await _check_guardian_rate_limit(db, guardian_user_id)
    if guardian_limit.rate_limited:
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail={
                "error": "Rate limit exceeded",
                "guardian_user_id": guardian_user_id,
                "attempts_used_today": guardian_limit.attempts_used_today,
                "lockout_until": guardian_limit.lockout_until.isoformat() if guardian_limit.lockout_until else None,
                "retry_after": int((guardian_limit.next_attempt_allowed_at - datetime.utcnow()).total_seconds()) if guardian_limit.next_attempt_allowed_at else None
            }
        )
    
    # Check IP-based rate limit
    if ip_hash:
        ip_limited = await _check_ip_rate_limit(db, ip_hash)
        if ip_limited:
            raise HTTPException(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                detail={
                    "error": "IP rate limit exceeded",
                    "retry_after": 3600  # 1 hour
                }
            )


# Geographic policy dependency
async def check_geo_policy(
    request: VerificationStartRequest,
    db: AsyncSession = Depends(get_db_session)
) -> None:
    """Check geographic policies for verification method"""
    
    if not settings.geo_restrictions_enabled:
        return
    
    country_code = request.country_code
    if not country_code:
        # Try to determine from IP if not provided
        # In production, this would use a GeoIP service
        country_code = "US"  # Default fallback
    
    # Check if country is allowed
    if not settings.is_allowed_country(country_code):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail={
                "error": "Verification not available in your region",
                "country_code": country_code,
                "supported_countries": settings.allowed_countries
            }
        )
    
    # Check method-specific restrictions
    geo_policy = await _get_geo_policy(db, country_code)
    if geo_policy:
        if request.method == VerificationMethod.MICRO_CHARGE and not geo_policy.micro_charge_allowed:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail={
                    "error": "Micro-charge verification not available in your region",
                    "country_code": country_code,
                    "available_methods": ["kba"] if geo_policy.kba_allowed else []
                }
            )
        
        if request.method == VerificationMethod.KBA and not geo_policy.kba_allowed:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail={
                    "error": "KBA verification not available in your region",
                    "country_code": country_code,
                    "available_methods": ["micro_charge"] if geo_policy.micro_charge_allowed else []
                }
            )


@router.post(
    "/verify/start",
    response_model=VerificationStartResponse,
    summary="Start Guardian Verification",
    description="Initiate guardian identity verification via micro-charge or KBA"
)
async def start_verification(
    request: VerificationStartRequest,
    background_tasks: BackgroundTasks,
    db: AsyncSession = Depends(get_db_session),
    _rate_limit: None = Depends(lambda req=Request, guardian_id=lambda: request.guardian_user_id: 
                                check_rate_limit(req, guardian_id, db)),
    _geo_check: None = Depends(check_geo_policy)
) -> VerificationStartResponse:
    """Start guardian identity verification process"""
    
    try:
        # Check if guardian already has active verification
        existing = await db.execute(
            select(GuardianVerification).where(
                and_(
                    GuardianVerification.guardian_user_id == request.guardian_user_id,
                    GuardianVerification.status.in_([
                        VerificationStatus.PENDING,
                        VerificationStatus.IN_PROGRESS
                    ]),
                    GuardianVerification.expires_at > datetime.utcnow()
                )
            )
        )
        
        existing_verification = existing.scalar_one_or_none()
        if existing_verification:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail={
                    "error": "Active verification already exists",
                    "verification_id": str(existing_verification.id),
                    "expires_at": existing_verification.expires_at.isoformat()
                }
            )
        
        # Create new verification record
        verification = GuardianVerification(
            guardian_user_id=request.guardian_user_id,
            tenant_id=request.metadata.get('tenant_id', 'default'),
            verification_method=request.method,
            verification_country=request.country_code,
            ip_country=request.country_code,  # Would be determined from IP in production
            consent_version=request.consent_version
        )
        
        db.add(verification)
        await db.flush()  # Get the ID
        
        # Initialize method-specific verification
        verification_data = {}
        
        if request.method == VerificationMethod.MICRO_CHARGE:
            if not stripe_charge_provider.is_available:
                raise HTTPException(
                    status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                    detail="Micro-charge verification currently unavailable"
                )
            
            micro_charge_response, charge_verification = await stripe_charge_provider.create_verification_intent(
                str(verification.id),
                request.guardian_user_id,
                request.metadata
            )
            
            # Add charge verification to session
            charge_verification.verification_id = verification.id
            db.add(charge_verification)
            
            verification_data["micro_charge"] = micro_charge_response
        
        elif request.method == VerificationMethod.KBA:
            if not kba_vendor_provider.is_available:
                raise HTTPException(
                    status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                    detail="KBA verification currently unavailable"
                )
            
            # Extract guardian info for KBA (minimal PII)
            guardian_info = {
                "first_name": request.metadata.get('first_name', ''),
                "last_name": request.metadata.get('last_name', ''),
                "zip_code": request.metadata.get('zip_code', ''),
                "state": request.metadata.get('state', ''),
                "city": request.metadata.get('city', ''),
                "country_code": request.country_code
            }
            
            kba_response, kba_session = await kba_vendor_provider.start_kba_session(
                str(verification.id),
                request.guardian_user_id,
                guardian_info,
                request.metadata
            )
            
            # Add KBA session to database
            kba_session.verification_id = verification.id
            db.add(kba_session)
            
            verification_data["kba"] = kba_response
        
        # Update verification status
        verification.status = VerificationStatus.IN_PROGRESS
        verification.attempt_count += 1
        verification.last_attempt_at = datetime.utcnow()
        
        # Create audit log
        audit_log = VerificationAuditLog(
            verification_id=verification.id,
            event_type="verification_started",
            event_description=f"Guardian verification started via {request.method.value}",
            success=True,
            metadata={
                "method": request.method.value,
                "country_code": request.country_code,
                "coppa_compliant": request.coppa_compliant
            }
        )
        db.add(audit_log)
        
        # Get rate limit info
        rate_limit = await _check_guardian_rate_limit(db, request.guardian_user_id)
        
        await db.commit()
        
        # Schedule background tasks
        background_tasks.add_task(
            _log_verification_attempt,
            str(verification.id),
            request.guardian_user_id,
            request.method.value,
            "started"
        )
        
        # Build response
        response = VerificationStartResponse(
            verification_id=str(verification.id),
            status=verification.status,
            method=verification.verification_method,
            expires_at=verification.expires_at,
            attempts_remaining=max(0, settings.max_attempts_per_day - rate_limit.attempts_used_today),
            next_attempt_at=rate_limit.next_attempt_allowed_at,
            **verification_data
        )
        
        logger.info("Guardian verification started",
                   verification_id=str(verification.id),
                   guardian_user_id=request.guardian_user_id,
                   method=request.method.value)
        
        return response
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error("Failed to start verification",
                    error=str(e),
                    guardian_user_id=request.guardian_user_id,
                    method=request.method.value,
                    exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to start verification process"
        )


@router.post(
    "/verify/result",
    response_model=WebhookEventResponse,
    summary="Process Verification Result",
    description="Process verification result from provider webhook/callback"
)
async def process_verification_result(
    request: VerificationResultRequest,
    background_tasks: BackgroundTasks,
    db: AsyncSession = Depends(get_db_session)
) -> WebhookEventResponse:
    """Process verification result from provider webhook or callback"""
    
    try:
        # Get verification record
        result = await db.execute(
            select(GuardianVerification).where(
                GuardianVerification.id == request.verification_id
            ).options(
                selectinload(GuardianVerification.charge_verifications),
                selectinload(GuardianVerification.kba_sessions)
            )
        )
        
        verification = result.scalar_one_or_none()
        if not verification:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Verification {request.verification_id} not found"
            )
        
        # Process based on provider
        success = False
        processed_data = {}
        
        if request.provider == "stripe":
            success, _, processed_data = await stripe_charge_provider.process_webhook_event(
                request.provider_data,
                request.signature or "",
                b""  # Raw body would be passed in production
            )
        
        elif request.provider in ["lexisnexis", "experian", "mock"]:
            success, _, processed_data = await kba_vendor_provider.process_kba_callback(
                request.provider_data.get('session_id', ''),
                request.provider_data
            )
        
        else:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Unsupported provider: {request.provider}"
            )
        
        if not success:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Failed to process verification result"
            )
        
        # Update verification status based on result
        new_status = VerificationStatus.VERIFIED if processed_data.get('status') == 'verified' else VerificationStatus.FAILED
        
        verification.status = new_status
        verification.updated_at = datetime.utcnow()
        
        if new_status == VerificationStatus.VERIFIED:
            verification.verified_at = datetime.utcnow()
        elif new_status == VerificationStatus.FAILED:
            failure_reason = processed_data.get('failure_reason')
            if failure_reason:
                verification.failure_reason = FailureReason(failure_reason)
            verification.failure_details = processed_data.get('error_message', '')
        
        # Create audit log
        audit_log = VerificationAuditLog(
            verification_id=verification.id,
            event_type="verification_completed",
            event_description=f"Verification {new_status.value} via {request.provider}",
            success=(new_status == VerificationStatus.VERIFIED),
            metadata=processed_data
        )
        db.add(audit_log)
        
        await db.commit()
        
        # Schedule background tasks
        background_tasks.add_task(
            _notify_verification_result,
            str(verification.id),
            verification.guardian_user_id,
            new_status.value
        )
        
        if new_status == VerificationStatus.VERIFIED:
            background_tasks.add_task(
                _update_consent_service,
                verification.guardian_user_id,
                True
            )
        
        logger.info("Verification result processed",
                   verification_id=request.verification_id,
                   provider=request.provider,
                   status=new_status.value,
                   success=success)
        
        return WebhookEventResponse(
            event_id=request.provider_data.get('id', 'unknown'),
            processed=True,
            verification_id=request.verification_id,
            status_updated=True,
            message=f"Verification {new_status.value}"
        )
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error("Failed to process verification result",
                    error=str(e),
                    verification_id=request.verification_id,
                    provider=request.provider,
                    exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to process verification result"
        )


@router.get(
    "/verify/{verification_id}/status",
    response_model=VerificationStatusResponse,
    summary="Get Verification Status",
    description="Get current status of a verification attempt"
)
async def get_verification_status(
    verification_id: str,
    db: AsyncSession = Depends(get_db_session)
) -> VerificationStatusResponse:
    """Get verification status by ID"""
    
    try:
        result = await db.execute(
            select(GuardianVerification).where(
                GuardianVerification.id == verification_id
            )
        )
        
        verification = result.scalar_one_or_none()
        if not verification:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Verification {verification_id} not found"
            )
        
        # Get rate limit info
        rate_limit = await _check_guardian_rate_limit(db, verification.guardian_user_id)
        
        response = VerificationStatusResponse(
            verification_id=str(verification.id),
            guardian_user_id=verification.guardian_user_id,
            status=verification.status,
            method=verification.verification_method,
            created_at=verification.created_at,
            updated_at=verification.updated_at,
            verified_at=verification.verified_at,
            expires_at=verification.expires_at,
            attempt_count=verification.attempt_count,
            attempts_remaining=max(0, settings.max_attempts_per_day - rate_limit.attempts_used_today),
            failure_reason=verification.failure_reason,
            can_retry=verification.can_retry and not rate_limit.rate_limited,
            next_retry_at=rate_limit.next_attempt_allowed_at,
            data_retention_until=verification.data_retention_until
        )
        
        return response
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error("Failed to get verification status",
                    error=str(e),
                    verification_id=verification_id,
                    exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to get verification status"
        )


@router.get(
    "/guardian/{guardian_user_id}/verification",
    response_model=GuardianVerificationSummary,
    summary="Get Guardian Verification Summary",
    description="Get guardian's overall verification status for consent gating"
)
async def get_guardian_verification_summary(
    guardian_user_id: str,
    db: AsyncSession = Depends(get_db_session)
) -> GuardianVerificationSummary:
    """Get guardian verification summary for consent system integration"""
    
    try:
        # Get most recent successful verification
        result = await db.execute(
            select(GuardianVerification).where(
                and_(
                    GuardianVerification.guardian_user_id == guardian_user_id,
                    GuardianVerification.status == VerificationStatus.VERIFIED
                )
            ).order_by(desc(GuardianVerification.verified_at)).limit(1)
        )
        
        verification = result.scalar_one_or_none()
        
        is_verified = verification is not None and verification.verified_at is not None
        
        # Check if verification is still valid (not expired)
        if is_verified and verification.expires_at < datetime.utcnow():
            is_verified = False
        
        summary = GuardianVerificationSummary(
            guardian_user_id=guardian_user_id,
            is_verified=is_verified,
            verification_method=verification.verification_method if verification else None,
            verified_at=verification.verified_at if verification else None,
            expires_at=verification.expires_at if verification else None,
            blocks_consent_toggles=not is_verified,  # Block toggles if not verified
            required_for_enrollment=True  # Always required for student enrollment
        )
        
        return summary
    
    except Exception as e:
        logger.error("Failed to get guardian verification summary",
                    error=str(e),
                    guardian_user_id=guardian_user_id,
                    exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to get guardian verification summary"
        )


@router.post(
    "/guardian/verification/bulk",
    response_model=BulkVerificationStatusResponse,
    summary="Bulk Guardian Verification Status",
    description="Get verification status for multiple guardians"
)
async def get_bulk_verification_status(
    request: BulkVerificationStatusRequest,
    db: AsyncSession = Depends(get_db_session)
) -> BulkVerificationStatusResponse:
    """Get verification status for multiple guardians"""
    
    try:
        # Get all verified guardians from the list
        query = select(GuardianVerification).where(
            and_(
                GuardianVerification.guardian_user_id.in_(request.guardian_user_ids),
                GuardianVerification.status == VerificationStatus.VERIFIED,
                GuardianVerification.expires_at > datetime.utcnow()
            )
        )
        
        if request.tenant_id:
            query = query.where(GuardianVerification.tenant_id == request.tenant_id)
        
        result = await db.execute(query)
        verified_records = result.scalars().all()
        
        # Create summary for each guardian
        results = []
        verified_user_ids = {v.guardian_user_id for v in verified_records}
        
        for guardian_user_id in request.guardian_user_ids:
            verification = next(
                (v for v in verified_records if v.guardian_user_id == guardian_user_id),
                None
            )
            
            is_verified = guardian_user_id in verified_user_ids
            
            summary = GuardianVerificationSummary(
                guardian_user_id=guardian_user_id,
                is_verified=is_verified,
                verification_method=verification.verification_method if verification else None,
                verified_at=verification.verified_at if verification else None,
                expires_at=verification.expires_at if verification else None,
                blocks_consent_toggles=not is_verified,
                required_for_enrollment=True
            )
            results.append(summary)
        
        verified_count = len(verified_user_ids)
        total_count = len(request.guardian_user_ids)
        
        return BulkVerificationStatusResponse(
            results=results,
            total_count=total_count,
            verified_count=verified_count,
            unverified_count=total_count - verified_count
        )
    
    except Exception as e:
        logger.error("Failed to get bulk verification status",
                    error=str(e),
                    guardian_count=len(request.guardian_user_ids),
                    exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to get bulk verification status"
        )


@router.get(
    "/guardian/{guardian_user_id}/rate-limit",
    response_model=RateLimitResponse,
    summary="Get Rate Limit Status",
    description="Get current rate limit status for a guardian"
)
async def get_rate_limit_status(
    guardian_user_id: str,
    db: AsyncSession = Depends(get_db_session)
) -> RateLimitResponse:
    """Get rate limit status for guardian"""
    
    rate_limit = await _check_guardian_rate_limit(db, guardian_user_id)
    return rate_limit


# Helper functions

async def _check_guardian_rate_limit(
    db: AsyncSession,
    guardian_user_id: str
) -> RateLimitResponse:
    """Check guardian-specific rate limits"""
    
    today_start = datetime.utcnow().replace(hour=0, minute=0, second=0, microsecond=0)
    
    # Count today's attempts
    result = await db.execute(
        select(GuardianVerification).where(
            and_(
                GuardianVerification.guardian_user_id == guardian_user_id,
                GuardianVerification.created_at >= today_start
            )
        )
    )
    
    attempts_today = len(result.scalars().all())
    attempts_remaining = max(0, settings.max_attempts_per_day - attempts_today)
    
    # Check for lockout
    lockout_result = await db.execute(
        select(VerificationRateLimit).where(
            and_(
                VerificationRateLimit.guardian_user_id == guardian_user_id,
                VerificationRateLimit.locked_out == True,
                VerificationRateLimit.lockout_until > datetime.utcnow()
            )
        )
    )
    
    lockout = lockout_result.scalar_one_or_none()
    
    rate_limited = (attempts_today >= settings.max_attempts_per_day) or (lockout is not None)
    
    next_attempt_at = None
    if rate_limited:
        if lockout:
            next_attempt_at = lockout.lockout_until
        else:
            # Next attempt allowed tomorrow
            next_attempt_at = today_start + timedelta(days=1)
    
    return RateLimitResponse(
        guardian_user_id=guardian_user_id,
        rate_limited=rate_limited,
        attempts_used_today=attempts_today,
        attempts_remaining_today=attempts_remaining,
        lockout_until=lockout.lockout_until if lockout else None,
        next_attempt_allowed_at=next_attempt_at
    )


async def _check_ip_rate_limit(db: AsyncSession, ip_hash: str) -> bool:
    """Check IP-based rate limits"""
    
    hour_ago = datetime.utcnow() - timedelta(hours=1)
    
    result = await db.execute(
        select(VerificationRateLimit).where(
            and_(
                VerificationRateLimit.ip_address_hash == ip_hash,
                VerificationRateLimit.window_start >= hour_ago,
                VerificationRateLimit.rate_limit_type == "hourly"
            )
        )
    )
    
    rate_limit = result.scalar_one_or_none()
    
    if rate_limit:
        return rate_limit.attempt_count >= settings.ip_rate_limit_per_hour
    
    return False


async def _get_geo_policy(db: AsyncSession, country_code: str) -> Optional[GeoPolicyRule]:
    """Get geographic policy for country"""
    
    result = await db.execute(
        select(GeoPolicyRule).where(
            and_(
                GeoPolicyRule.country_code == country_code,
                GeoPolicyRule.effective_date <= datetime.utcnow()
            )
        ).order_by(desc(GeoPolicyRule.effective_date)).limit(1)
    )
    
    return result.scalar_one_or_none()


# Background task functions

async def _log_verification_attempt(
    verification_id: str,
    guardian_user_id: str,
    method: str,
    event: str
):
    """Log verification attempt for analytics"""
    logger.info("Verification event logged",
               verification_id=verification_id,
               guardian_user_id=guardian_user_id,
               method=method,
               event=event)


async def _notify_verification_result(
    verification_id: str,
    guardian_user_id: str,
    status: str
):
    """Notify relevant services of verification result"""
    logger.info("Verification result notification",
               verification_id=verification_id,
               guardian_user_id=guardian_user_id,
               status=status)


async def _update_consent_service(
    guardian_user_id: str,
    verified: bool
):
    """Update consent service with verification status"""
    # In production, this would call the consent service API
    logger.info("Consent service notification",
               guardian_user_id=guardian_user_id,
               guardian_verified=verified)
