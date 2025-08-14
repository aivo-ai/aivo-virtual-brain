# AIVO SEL Service - API Routes
# S2-12 Implementation - FastAPI endpoints for SEL workflows

import logging
from typing import Dict, List, Any, Optional
from datetime import datetime, timezone, timedelta
import uuid

from fastapi import APIRouter, Depends, HTTPException, status, Query, Path
from fastapi.responses import JSONResponse
from sqlalchemy.orm import Session
from sqlalchemy import and_, desc, func

from .database import get_db
from .models import (
    SELCheckIn, SELStrategy, SELAlert, ConsentRecord, StrategyUsage, SELReport,
    EmotionType, SELDomain, AlertLevel, StrategyType, GradeBand, ConsentStatus, AlertStatus
)
from .schemas import (
    CheckInRequest, CheckInResponse, CheckInFilter,
    StrategyRequest, StrategyResponse, StrategyFilter,
    ConsentRequest, ConsentResponse, ConsentFilter,
    AlertResponse, AlertFilter,
    ReportRequest, ReportResponse, ReportFilter,
    StrategyUsageRequest, StrategyUsageResponse
)
from .engine import SELEngine
from .auth import get_current_user, require_consent

logger = logging.getLogger(__name__)

# Initialize router
router = APIRouter(prefix="/api/v1", tags=["sel"])

# Initialize SEL engine (will be done in app startup)
sel_engine = SELEngine()


# Health check endpoint
@router.get("/health", status_code=200)
async def health_check():
    """Health check endpoint for the SEL service."""
    return {"status": "healthy", "service": "sel-svc", "timestamp": datetime.now(timezone.utc).isoformat()}


# SEL Check-in Endpoints

@router.post("/checkin", response_model=CheckInResponse, status_code=status.HTTP_201_CREATED)
async def create_checkin(
    request: CheckInRequest,
    db: Session = Depends(get_db),
    current_user: Dict = Depends(get_current_user)
):
    """
    Create a new SEL check-in and trigger processing pipeline.
    
    S2-12 Primary endpoint: POST /checkin
    """
    try:
        logger.info(f"Creating SEL check-in for student {request.student_id}")
        
        # Verify tenant access
        if request.tenant_id != current_user.get("tenant_id"):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Access denied to tenant data"
            )
        
        # Verify consent for data collection
        consent = await require_consent(request.student_id, request.tenant_id, "data_collection", db)
        
        # Create check-in record
        checkin = SELCheckIn(
            tenant_id=request.tenant_id,
            student_id=request.student_id,
            consent_record_id=consent.id,
            checkin_date=request.checkin_date or datetime.now(timezone.utc),
            grade_band=request.grade_band,
            primary_emotion=request.primary_emotion,
            emotion_intensity=request.emotion_intensity,
            secondary_emotions=request.secondary_emotions,
            triggers=request.triggers,
            current_situation=request.current_situation,
            location_context=request.location_context,
            social_context=request.social_context,
            self_awareness_rating=request.self_awareness_rating,
            self_management_rating=request.self_management_rating,
            social_awareness_rating=request.social_awareness_rating,
            relationship_skills_rating=request.relationship_skills_rating,
            decision_making_rating=request.decision_making_rating,
            energy_level=request.energy_level,
            stress_level=request.stress_level,
            confidence_level=request.confidence_level,
            support_needed=request.support_needed,
            additional_notes=request.additional_notes
        )
        
        db.add(checkin)
        db.commit()
        db.refresh(checkin)
        
        # Process check-in through SEL engine
        try:
            processing_results = await sel_engine.process_checkin(checkin, db)
            logger.info(f"Check-in {checkin.id} processed successfully")
        except Exception as e:
            logger.error(f"Error processing check-in {checkin.id}: {str(e)}")
            # Continue even if processing fails - the check-in is still recorded
            processing_results = {"error": "Processing failed", "message": str(e)}
        
        # Prepare response
        response_data = {
            "id": checkin.id,
            "tenant_id": checkin.tenant_id,
            "student_id": checkin.student_id,
            "checkin_date": checkin.checkin_date,
            "grade_band": checkin.grade_band,
            "primary_emotion": checkin.primary_emotion,
            "emotion_intensity": checkin.emotion_intensity,
            "secondary_emotions": checkin.secondary_emotions,
            "triggers": checkin.triggers,
            "current_situation": checkin.current_situation,
            "location_context": checkin.location_context,
            "social_context": checkin.social_context,
            "self_awareness_rating": checkin.self_awareness_rating,
            "self_management_rating": checkin.self_management_rating,
            "social_awareness_rating": checkin.social_awareness_rating,
            "relationship_skills_rating": checkin.relationship_skills_rating,
            "decision_making_rating": checkin.decision_making_rating,
            "energy_level": checkin.energy_level,
            "stress_level": checkin.stress_level,
            "confidence_level": checkin.confidence_level,
            "support_needed": checkin.support_needed,
            "additional_notes": checkin.additional_notes,
            "consent_verified": True,
            "processing_results": processing_results,
            "created_at": checkin.created_at
        }
        
        return CheckInResponse(**response_data)
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error creating check-in: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error creating check-in: {str(e)}"
        )


@router.get("/checkin", response_model=List[CheckInResponse])
async def get_checkins(
    student_id: uuid.UUID,
    tenant_id: uuid.UUID,
    limit: int = Query(20, ge=1, le=100),
    offset: int = Query(0, ge=0),
    start_date: Optional[datetime] = None,
    end_date: Optional[datetime] = None,
    db: Session = Depends(get_db),
    current_user: Dict = Depends(get_current_user)
):
    """Get SEL check-ins for a student."""
    try:
        # Verify tenant access
        if tenant_id != current_user.get("tenant_id"):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Access denied to tenant data"
            )
        
        # Verify consent for data sharing
        await require_consent(student_id, tenant_id, "data_sharing", db)
        
        # Build query
        query = db.query(SELCheckIn).filter(
            and_(
                SELCheckIn.student_id == student_id,
                SELCheckIn.tenant_id == tenant_id
            )
        )
        
        if start_date:
            query = query.filter(SELCheckIn.checkin_date >= start_date)
        if end_date:
            query = query.filter(SELCheckIn.checkin_date <= end_date)
        
        # Execute query
        checkins = query.order_by(desc(SELCheckIn.checkin_date)).offset(offset).limit(limit).all()
        
        # Convert to response format
        return [
            CheckInResponse(
                id=ci.id,
                tenant_id=ci.tenant_id,
                student_id=ci.student_id,
                checkin_date=ci.checkin_date,
                grade_band=ci.grade_band,
                primary_emotion=ci.primary_emotion,
                emotion_intensity=ci.emotion_intensity,
                secondary_emotions=ci.secondary_emotions,
                triggers=ci.triggers,
                current_situation=ci.current_situation,
                location_context=ci.location_context,
                social_context=ci.social_context,
                self_awareness_rating=ci.self_awareness_rating,
                self_management_rating=ci.self_management_rating,
                social_awareness_rating=ci.social_awareness_rating,
                relationship_skills_rating=ci.relationship_skills_rating,
                decision_making_rating=ci.decision_making_rating,
                energy_level=ci.energy_level,
                stress_level=ci.stress_level,
                confidence_level=ci.confidence_level,
                support_needed=ci.support_needed,
                additional_notes=ci.additional_notes,
                consent_verified=True,
                created_at=ci.created_at
            )
            for ci in checkins
        ]
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error retrieving check-ins: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error retrieving check-ins: {str(e)}"
        )


# SEL Strategy Endpoints

@router.get("/strategy/next", response_model=StrategyResponse)
async def get_next_strategy(
    student_id: uuid.UUID,
    tenant_id: uuid.UUID,
    target_emotion: Optional[EmotionType] = None,
    target_domain: Optional[SELDomain] = None,
    difficulty_preference: Optional[str] = Query("adaptive", regex="^(easy|adaptive|challenging)$"),
    max_duration: Optional[int] = Query(None, ge=1, le=60),
    db: Session = Depends(get_db),
    current_user: Dict = Depends(get_current_user)
):
    """
    Get the next personalized SEL strategy for a student.
    
    S2-12 Primary endpoint: GET /strategy/next
    """
    try:
        logger.info(f"Generating next strategy for student {student_id}")
        
        # Verify tenant access
        if tenant_id != current_user.get("tenant_id"):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Access denied to tenant data"
            )
        
        # Verify consent for data sharing and personalization
        await require_consent(student_id, tenant_id, "data_sharing", db)
        
        # Prepare request data for strategy generation
        request_data = {
            "student_id": student_id,
            "tenant_id": tenant_id,
            "target_emotion": target_emotion,
            "target_domain": target_domain,
            "difficulty_preference": difficulty_preference,
            "max_duration": max_duration
        }
        
        # Generate strategy using SEL engine
        strategy = await sel_engine.generate_personalized_strategy(request_data, db)
        
        # Prepare response
        response_data = {
            "id": strategy.id,
            "tenant_id": strategy.tenant_id,
            "student_id": strategy.student_id,
            "checkin_id": strategy.checkin_id,
            "strategy_type": strategy.strategy_type,
            "strategy_title": strategy.strategy_title,
            "strategy_description": strategy.strategy_description,
            "instructions": strategy.instructions,
            "grade_band": strategy.grade_band,
            "target_emotion": strategy.target_emotion,
            "target_domain": strategy.target_domain,
            "difficulty_level": strategy.difficulty_level,
            "estimated_duration": strategy.estimated_duration,
            "materials_needed": strategy.materials_needed,
            "step_by_step": strategy.step_by_step,
            "success_indicators": strategy.success_indicators,
            "video_url": strategy.video_url,
            "audio_url": strategy.audio_url,
            "image_urls": strategy.image_urls,
            "interactive_elements": strategy.interactive_elements,
            "times_used": strategy.times_used,
            "average_rating": strategy.average_rating,
            "success_rate": strategy.success_rate,
            "personalization_context": {
                "generated_for": "current_request",
                "based_on_recent_checkins": strategy.checkin_id is not None,
                "difficulty_adapted": difficulty_preference != "adaptive"
            },
            "created_at": strategy.created_at
        }
        
        return StrategyResponse(**response_data)
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error generating strategy: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error generating strategy: {str(e)}"
        )


@router.post("/strategy/{strategy_id}/usage", response_model=StrategyUsageResponse)
async def record_strategy_usage(
    strategy_id: uuid.UUID,
    request: StrategyUsageRequest,
    db: Session = Depends(get_db),
    current_user: Dict = Depends(get_current_user)
):
    """Record usage and effectiveness data for a strategy."""
    try:
        # Verify tenant access
        if request.tenant_id != current_user.get("tenant_id"):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Access denied to tenant data"
            )
        
        # Verify strategy exists and belongs to tenant
        strategy = db.query(SELStrategy).filter(
            and_(
                SELStrategy.id == strategy_id,
                SELStrategy.tenant_id == request.tenant_id
            )
        ).first()
        
        if not strategy:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Strategy not found"
            )
        
        # Prepare usage data
        usage_data = {
            "tenant_id": request.tenant_id,
            "student_id": request.student_id,
            "strategy_id": strategy_id,
            "duration_used": request.duration_used,
            "completion_status": request.completion_status,
            "pre_emotion_rating": request.pre_emotion_rating,
            "post_emotion_rating": request.post_emotion_rating,
            "helpfulness_rating": request.helpfulness_rating,
            "difficulty_rating": request.difficulty_rating,
            "liked_aspects": request.liked_aspects,
            "disliked_aspects": request.disliked_aspects,
            "suggestions": request.suggestions,
            "would_use_again": request.would_use_again,
            "usage_context": request.usage_context,
            "support_received": request.support_received
        }
        
        # Record usage through SEL engine
        usage = await sel_engine.record_strategy_usage(usage_data, db)
        
        return StrategyUsageResponse(
            id=usage.id,
            tenant_id=usage.tenant_id,
            student_id=usage.student_id,
            strategy_id=usage.strategy_id,
            duration_used=usage.duration_used,
            completion_status=usage.completion_status,
            pre_emotion_rating=usage.pre_emotion_rating,
            post_emotion_rating=usage.post_emotion_rating,
            helpfulness_rating=usage.helpfulness_rating,
            difficulty_rating=usage.difficulty_rating,
            liked_aspects=usage.liked_aspects,
            disliked_aspects=usage.disliked_aspects,
            suggestions=usage.suggestions,
            would_use_again=usage.would_use_again,
            usage_context=usage.usage_context,
            support_received=usage.support_received,
            effectiveness_score=usage.post_emotion_rating - usage.pre_emotion_rating if usage.post_emotion_rating and usage.pre_emotion_rating else None,
            used_at=usage.used_at
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error recording strategy usage: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error recording strategy usage: {str(e)}"
        )


# SEL Report Endpoints

@router.post("/report", response_model=ReportResponse, status_code=status.HTTP_201_CREATED)
async def generate_report(
    request: ReportRequest,
    db: Session = Depends(get_db),
    current_user: Dict = Depends(get_current_user)
):
    """
    Generate comprehensive SEL report for a student.
    
    S2-12 Primary endpoint: POST /report
    """
    try:
        logger.info(f"Generating SEL report for student {request.student_id}")
        
        # Verify tenant access
        if request.tenant_id != current_user.get("tenant_id"):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Access denied to tenant data"
            )
        
        # Verify consent for data sharing and reporting
        await require_consent(request.student_id, request.tenant_id, "data_sharing", db)
        
        # Prepare request data
        request_data = {
            "student_id": request.student_id,
            "tenant_id": request.tenant_id,
            "report_type": request.report_type,
            "start_date": request.start_date,
            "end_date": request.end_date,
            "report_audience": request.report_audience,
            "privacy_level": request.privacy_level,
            "include_strategies": request.include_strategies,
            "include_alerts": request.include_alerts,
            "include_trends": request.include_trends
        }
        
        # Generate report using SEL engine
        report = await sel_engine.generate_report(request_data, db)
        
        # Prepare response
        response_data = {
            "id": report.id,
            "tenant_id": report.tenant_id,
            "student_id": report.student_id,
            "report_type": report.report_type,
            "report_period_start": report.report_period_start,
            "report_period_end": report.report_period_end,
            "generated_for": report.generated_for,
            "total_checkins": report.total_checkins,
            "average_emotion_intensity": report.average_emotion_intensity,
            "most_common_emotion": report.most_common_emotion,
            "trend_direction": report.trend_direction,
            "domain_scores": report.domain_scores,
            "domain_trends": report.domain_trends,
            "growth_indicators": report.growth_indicators,
            "areas_for_support": report.areas_for_support,
            "strategies_used": report.strategies_used,
            "strategy_success_rate": report.strategy_success_rate,
            "preferred_strategies": report.preferred_strategies,
            "total_alerts": report.total_alerts,
            "alert_trends": report.alert_trends,
            "key_insights": report.key_insights,
            "recommendations": report.recommendations,
            "celebration_points": report.celebration_points,
            "narrative_summary": report.narrative_summary,
            "privacy_level": report.privacy_level,
            "consent_verified": report.consent_verified,
            "generated_at": report.generated_at
        }
        
        # Conditionally include detailed data based on request
        if request.include_detailed_data:
            response_data["report_data"] = report.report_data
        
        return ReportResponse(**response_data)
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error generating report: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error generating report: {str(e)}"
        )


# SEL Alert Endpoints

@router.get("/alerts", response_model=List[AlertResponse])
async def get_alerts(
    student_id: Optional[uuid.UUID] = None,
    tenant_id: uuid.UUID = Query(...),
    alert_level: Optional[AlertLevel] = None,
    status_filter: Optional[AlertStatus] = None,
    limit: int = Query(20, ge=1, le=100),
    offset: int = Query(0, ge=0),
    db: Session = Depends(get_db),
    current_user: Dict = Depends(get_current_user)
):
    """Get SEL alerts with filtering."""
    try:
        # Verify tenant access
        if tenant_id != current_user.get("tenant_id"):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Access denied to tenant data"
            )
        
        # Build query
        query = db.query(SELAlert).filter(SELAlert.tenant_id == tenant_id)
        
        if student_id:
            # Verify consent for specific student
            await require_consent(student_id, tenant_id, "alert_notifications", db)
            query = query.filter(SELAlert.student_id == student_id)
        
        if alert_level:
            query = query.filter(SELAlert.alert_level == alert_level)
        if status_filter:
            query = query.filter(SELAlert.status == status_filter)
        
        # Execute query
        alerts = query.order_by(desc(SELAlert.created_at)).offset(offset).limit(limit).all()
        
        return [
            AlertResponse(
                id=alert.id,
                tenant_id=alert.tenant_id,
                student_id=alert.student_id,
                checkin_id=alert.checkin_id,
                alert_type=alert.alert_type,
                alert_level=alert.alert_level,
                status=alert.status,
                title=alert.title,
                description=alert.description,
                trigger_domain=alert.trigger_domain,
                trigger_value=alert.trigger_value,
                threshold_value=alert.threshold_value,
                risk_score=alert.risk_score,
                risk_factors=alert.risk_factors,
                protective_factors=alert.protective_factors,
                consent_verified=alert.consent_verified,
                privacy_level=alert.privacy_level,
                created_at=alert.created_at,
                acknowledged_at=alert.acknowledged_at,
                resolved_at=alert.resolved_at
            )
            for alert in alerts
        ]
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error retrieving alerts: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error retrieving alerts: {str(e)}"
        )


@router.patch("/alerts/{alert_id}/acknowledge")
async def acknowledge_alert(
    alert_id: uuid.UUID,
    db: Session = Depends(get_db),
    current_user: Dict = Depends(get_current_user)
):
    """Acknowledge an SEL alert."""
    try:
        alert = db.query(SELAlert).filter(SELAlert.id == alert_id).first()
        
        if not alert:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Alert not found"
            )
        
        # Verify tenant access
        if alert.tenant_id != current_user.get("tenant_id"):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Access denied to tenant data"
            )
        
        # Update alert status
        alert.status = AlertStatus.ACKNOWLEDGED
        alert.acknowledged_at = datetime.now(timezone.utc)
        alert.acknowledged_by = current_user.get("user_id")
        
        db.commit()
        
        return {"message": "Alert acknowledged successfully", "alert_id": alert_id}
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error acknowledging alert: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error acknowledging alert: {str(e)}"
        )


# Consent Management Endpoints

@router.post("/consent", response_model=ConsentResponse)
async def create_consent_record(
    request: ConsentRequest,
    db: Session = Depends(get_db),
    current_user: Dict = Depends(get_current_user)
):
    """Create or update consent record for SEL data processing."""
    try:
        # Verify tenant access
        if request.tenant_id != current_user.get("tenant_id"):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Access denied to tenant data"
            )
        
        # Check for existing consent record
        existing_consent = db.query(ConsentRecord).filter(
            and_(
                ConsentRecord.student_id == request.student_id,
                ConsentRecord.tenant_id == request.tenant_id
            )
        ).first()
        
        if existing_consent:
            # Update existing record
            existing_consent.status = request.status
            existing_consent.data_collection_allowed = request.data_collection_allowed
            existing_consent.data_sharing_allowed = request.data_sharing_allowed
            existing_consent.alert_notifications_allowed = request.alert_notifications_allowed
            existing_consent.ai_processing_allowed = request.ai_processing_allowed
            existing_consent.research_participation_allowed = request.research_participation_allowed
            existing_consent.parent_guardian_consent = request.parent_guardian_consent
            existing_consent.student_assent = request.student_assent
            existing_consent.consent_date = request.consent_date or datetime.now(timezone.utc)
            existing_consent.expiration_date = request.expiration_date
            existing_consent.withdrawal_date = None if request.status == ConsentStatus.GRANTED else datetime.now(timezone.utc)
            existing_consent.alert_thresholds = request.alert_thresholds
            existing_consent.data_retention_preferences = request.data_retention_preferences
            existing_consent.special_circumstances = request.special_circumstances
            existing_consent.updated_at = datetime.now(timezone.utc)
            
            consent = existing_consent
        else:
            # Create new consent record
            consent = ConsentRecord(
                tenant_id=request.tenant_id,
                student_id=request.student_id,
                status=request.status,
                consent_type=request.consent_type,
                data_collection_allowed=request.data_collection_allowed,
                data_sharing_allowed=request.data_sharing_allowed,
                alert_notifications_allowed=request.alert_notifications_allowed,
                ai_processing_allowed=request.ai_processing_allowed,
                research_participation_allowed=request.research_participation_allowed,
                parent_guardian_consent=request.parent_guardian_consent,
                student_assent=request.student_assent,
                consent_date=request.consent_date or datetime.now(timezone.utc),
                expiration_date=request.expiration_date,
                consent_method=request.consent_method,
                consenting_party_name=request.consenting_party_name,
                consenting_party_relationship=request.consenting_party_relationship,
                alert_thresholds=request.alert_thresholds,
                data_retention_preferences=request.data_retention_preferences,
                special_circumstances=request.special_circumstances
            )
            db.add(consent)
        
        db.commit()
        db.refresh(consent)
        
        return ConsentResponse(
            id=consent.id,
            tenant_id=consent.tenant_id,
            student_id=consent.student_id,
            status=consent.status,
            consent_type=consent.consent_type,
            data_collection_allowed=consent.data_collection_allowed,
            data_sharing_allowed=consent.data_sharing_allowed,
            alert_notifications_allowed=consent.alert_notifications_allowed,
            ai_processing_allowed=consent.ai_processing_allowed,
            research_participation_allowed=consent.research_participation_allowed,
            parent_guardian_consent=consent.parent_guardian_consent,
            student_assent=consent.student_assent,
            consent_date=consent.consent_date,
            expiration_date=consent.expiration_date,
            withdrawal_date=consent.withdrawal_date,
            consent_method=consent.consent_method,
            consenting_party_name=consent.consenting_party_name,
            consenting_party_relationship=consent.consenting_party_relationship,
            alert_thresholds=consent.alert_thresholds,
            data_retention_preferences=consent.data_retention_preferences,
            special_circumstances=consent.special_circumstances,
            privacy_compliance=True,
            created_at=consent.created_at,
            updated_at=consent.updated_at
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error managing consent: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error managing consent: {str(e)}"
        )


@router.get("/consent/{student_id}", response_model=ConsentResponse)
async def get_consent_record(
    student_id: uuid.UUID,
    tenant_id: uuid.UUID = Query(...),
    db: Session = Depends(get_db),
    current_user: Dict = Depends(get_current_user)
):
    """Get consent record for a student."""
    try:
        # Verify tenant access
        if tenant_id != current_user.get("tenant_id"):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Access denied to tenant data"
            )
        
        consent = db.query(ConsentRecord).filter(
            and_(
                ConsentRecord.student_id == student_id,
                ConsentRecord.tenant_id == tenant_id
            )
        ).first()
        
        if not consent:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Consent record not found"
            )
        
        return ConsentResponse(
            id=consent.id,
            tenant_id=consent.tenant_id,
            student_id=consent.student_id,
            status=consent.status,
            consent_type=consent.consent_type,
            data_collection_allowed=consent.data_collection_allowed,
            data_sharing_allowed=consent.data_sharing_allowed,
            alert_notifications_allowed=consent.alert_notifications_allowed,
            ai_processing_allowed=consent.ai_processing_allowed,
            research_participation_allowed=consent.research_participation_allowed,
            parent_guardian_consent=consent.parent_guardian_consent,
            student_assent=consent.student_assent,
            consent_date=consent.consent_date,
            expiration_date=consent.expiration_date,
            withdrawal_date=consent.withdrawal_date,
            consent_method=consent.consent_method,
            consenting_party_name=consent.consenting_party_name,
            consenting_party_relationship=consent.consenting_party_relationship,
            alert_thresholds=consent.alert_thresholds,
            data_retention_preferences=consent.data_retention_preferences,
            special_circumstances=consent.special_circumstances,
            privacy_compliance=True,
            created_at=consent.created_at,
            updated_at=consent.updated_at
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error retrieving consent: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error retrieving consent: {str(e)}"
        )
