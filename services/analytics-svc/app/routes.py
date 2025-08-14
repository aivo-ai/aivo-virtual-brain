"""
Analytics Service - API Routes (S2-15)
Privacy-aware metrics endpoints for tenant and learner analytics
"""
import logging
from datetime import datetime, date, timedelta
from typing import List, Optional, Dict, Any
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, Path
from sqlalchemy.orm import Session
from sqlalchemy import and_, func, desc

from .models import (
    SessionAggregate, MasteryAggregate, WeeklyActiveAggregate,
    IEPProgressAggregate, ETLJobRun, AggregationLevel, PrivacyLevel,
    TenantAnalyticsSummary, LearnerAnalyticsSummary, SessionMetrics,
    MasteryMetrics, WeeklyActivityMetrics, IEPProgressMetrics, ETLJobStatus
)
from .etl import ETLOrchestrator, PrivacyAnonimizer

logger = logging.getLogger(__name__)

router = APIRouter()

# Dependency for database session
def get_db() -> Session:
    """Get database session (to be implemented with actual DB connection)."""
    # In production, this would return actual SQLAlchemy session
    pass

# Privacy checker
class PrivacyGuard:
    """Ensures privacy requirements are met for data access."""
    
    @staticmethod
    def check_tenant_access(tenant_id: UUID, requesting_user_tenant: UUID) -> bool:
        """Check if user can access tenant analytics."""
        return tenant_id == requesting_user_tenant
    
    @staticmethod
    def check_learner_access(learner_id_hash: str, requesting_user_id: UUID, 
                           requesting_user_role: str) -> bool:
        """Check if user can access learner-specific analytics."""
        # Only allow access to own data or if educator/admin role
        anonymizer = PrivacyAnonimizer()
        user_hash = anonymizer.hash_learner_id(requesting_user_id)
        
        return (learner_id_hash == user_hash or 
                requesting_user_role in ["educator", "admin", "parent"])
    
    @staticmethod
    def apply_privacy_filter(data: Dict[str, Any], privacy_level: PrivacyLevel) -> Dict[str, Any]:
        """Apply privacy filtering to response data."""
        if privacy_level == PrivacyLevel.NONE:
            return data
        
        # Remove/mask sensitive fields based on privacy level
        filtered = data.copy()
        
        if privacy_level.name.startswith("DP"):
            # Add privacy metadata for DP-protected data
            filtered["_privacy_notice"] = "Data protected with differential privacy"
            if "epsilon" in data:
                filtered["_privacy_epsilon"] = data["epsilon"]
        
        # Always remove raw counts below threshold for k-anonymity
        for key, value in filtered.items():
            if isinstance(value, int) and key.endswith("_count") and value < 5:
                filtered[key] = "<5"  # Suppress small counts
        
        return filtered


@router.get("/metrics/tenant/{tenant_id}", response_model=TenantAnalyticsSummary)
async def get_tenant_analytics(
    tenant_id: UUID = Path(..., description="Tenant identifier"),
    start_date: Optional[date] = Query(None, description="Report start date"),
    end_date: Optional[date] = Query(None, description="Report end date"),
    privacy_level: PrivacyLevel = Query(PrivacyLevel.ANONYMIZED, description="Privacy protection level"),
    db: Session = Depends(get_db)
):
    """
    Get comprehensive analytics summary for a tenant.
    
    Returns aggregated metrics with appropriate privacy protections:
    - Session duration and engagement metrics
    - Weekly active learner trends  
    - Subject mastery progress
    - IEP progress summary (if applicable)
    
    Privacy levels:
    - ANONYMIZED: PII removed, aggregated data
    - DP_LOW/MEDIUM/HIGH: Differential privacy with varying noise levels
    """
    # Default to last 30 days if no date range specified
    if not end_date:
        end_date = date.today()
    if not start_date:
        start_date = end_date - timedelta(days=30)
    
    # Validate date range
    if start_date > end_date:
        raise HTTPException(status_code=400, detail="Start date must be before end date")
    if (end_date - start_date).days > 365:
        raise HTTPException(status_code=400, detail="Date range cannot exceed 365 days")
    
    try:
        # TODO: In production, add authentication and authorization checks
        # if not PrivacyGuard.check_tenant_access(tenant_id, requesting_user_tenant):
        #     raise HTTPException(status_code=403, detail="Access denied")
        
        # Get session metrics
        session_data = db.query(SessionAggregate).filter(
            and_(
                SessionAggregate.tenant_id == tenant_id,
                SessionAggregate.date_bucket.between(start_date, end_date),
                SessionAggregate.aggregation_level == AggregationLevel.TENANT,
                SessionAggregate.privacy_level == privacy_level
            )
        ).all()
        
        if not session_data:
            # Trigger ETL if no data available
            logger.warning(f"No session data found for tenant {tenant_id}, triggering ETL")
            orchestrator = ETLOrchestrator(db)
            orchestrator.run_daily_etl(end_date, tenant_id, privacy_level)
            
            # Retry query
            session_data = db.query(SessionAggregate).filter(
                and_(
                    SessionAggregate.tenant_id == tenant_id,
                    SessionAggregate.date_bucket == end_date,
                    SessionAggregate.aggregation_level == AggregationLevel.TENANT,
                    SessionAggregate.privacy_level == privacy_level
                )
            ).all()
        
        # Aggregate session metrics
        if session_data:
            total_sessions = sum(s.total_sessions for s in session_data)
            total_duration = sum(s.total_duration_minutes for s in session_data)
            avg_duration = total_duration / max(1, total_sessions)
            
            session_metrics = SessionMetrics(
                total_sessions=total_sessions,
                avg_duration_minutes=round(avg_duration, 2),
                median_duration_minutes=round(sum(s.median_duration_minutes for s in session_data) / len(session_data), 2),
                total_hours=round(total_duration / 60.0, 2),
                trend_direction="stable",  # TODO: Calculate actual trend
                privacy_level=privacy_level.value,
                data_points=len(session_data)
            )
        else:
            session_metrics = SessionMetrics(
                total_sessions=0, avg_duration_minutes=0, median_duration_minutes=0,
                total_hours=0, trend_direction="no_data", privacy_level=privacy_level.value,
                data_points=0
            )
        
        # Get weekly activity data
        weekly_data = db.query(WeeklyActiveAggregate).filter(
            and_(
                WeeklyActiveAggregate.tenant_id == tenant_id,
                WeeklyActiveAggregate.week_start_date.between(start_date, end_date),
                WeeklyActiveAggregate.privacy_level == privacy_level
            )
        ).order_by(WeeklyActiveAggregate.week_start_date).all()
        
        weekly_metrics = []
        for week in weekly_data:
            weekly_metrics.append(WeeklyActivityMetrics(
                week_start=week.week_start_date,
                active_learners=week.total_active_learners,
                new_learners=week.new_learners,
                engagement_rate=float(week.engagement_rate),
                avg_sessions_per_learner=week.avg_sessions_per_learner,
                avg_time_per_learner=week.avg_time_per_learner_minutes,
                demographics={
                    "age_distribution": week.age_distribution or {},
                    "grade_distribution": week.grade_distribution or {},
                    "special_needs_percentage": week.special_needs_percentage
                },
                privacy_level=privacy_level.value
            ))
        
        # Get top subjects by mastery
        top_subjects_data = db.query(MasteryAggregate).filter(
            and_(
                MasteryAggregate.tenant_id == tenant_id,
                MasteryAggregate.date_bucket.between(start_date, end_date),
                MasteryAggregate.privacy_level == privacy_level
            )
        ).order_by(desc(MasteryAggregate.avg_mastery_score)).limit(10).all()
        
        top_subjects = []
        for subject in top_subjects_data:
            top_subjects.append(MasteryMetrics(
                subject_id=subject.subject_id,
                subject_category=subject.subject_category or "Unknown",
                current_mastery=float(subject.current_mastery_score),
                mastery_improvement=float(subject.mastery_improvement or 0),
                assessments_completed=subject.assessments_completed,
                time_to_mastery_hours=subject.time_to_mastery_hours,
                privacy_level=privacy_level.value,
                aggregation_level=subject.aggregation_level.value
            ))
        
        # IEP progress summary (aggregated)
        iep_data = db.query(IEPProgressAggregate).filter(
            and_(
                IEPProgressAggregate.tenant_id == tenant_id,
                IEPProgressAggregate.date_bucket.between(start_date, end_date),
                IEPProgressAggregate.privacy_level == privacy_level
            )
        ).all()
        
        iep_summary = None
        if iep_data:
            on_track_count = sum(1 for iep in iep_data if iep.is_on_track)
            avg_progress = sum(float(iep.progress_percentage) for iep in iep_data) / len(iep_data)
            
            iep_summary = {
                "total_iep_learners": len(set(iep.learner_id_hash for iep in iep_data)),
                "on_track_percentage": round(on_track_count / len(iep_data), 3),
                "average_progress_percentage": round(avg_progress, 3),
                "goal_categories": list(set(iep.iep_goal_category for iep in iep_data))
            }
        
        # Calculate high-level metrics
        total_active = weekly_data[-1].total_active_learners if weekly_data else 0
        total_hours = session_metrics.total_hours
        avg_engagement = sum(w.engagement_rate for w in weekly_metrics) / len(weekly_metrics) if weekly_metrics else 0
        
        # Apply privacy filtering
        response_data = {
            "tenant_id": tenant_id,
            "reporting_period_start": start_date,
            "reporting_period_end": end_date,
            "total_active_learners": total_active,
            "total_learning_hours": total_hours,
            "average_engagement_rate": round(avg_engagement, 3),
            "session_metrics": session_metrics,
            "weekly_activity": weekly_metrics,
            "top_subjects": top_subjects,
            "iep_progress_summary": iep_summary,
            "privacy_level": privacy_level.value,
            "last_updated": datetime.utcnow()
        }
        
        filtered_data = PrivacyGuard.apply_privacy_filter(response_data, privacy_level)
        
        return TenantAnalyticsSummary(**filtered_data)
        
    except Exception as e:
        logger.error(f"Failed to get tenant analytics: {e}")
        raise HTTPException(status_code=500, detail="Failed to retrieve analytics data")


@router.get("/metrics/learner/{learner_id_hash}", response_model=LearnerAnalyticsSummary)
async def get_learner_analytics(
    learner_id_hash: str = Path(..., description="Hashed learner identifier"),
    start_date: Optional[date] = Query(None, description="Report start date"),
    end_date: Optional[date] = Query(None, description="Report end date"),
    privacy_level: PrivacyLevel = Query(PrivacyLevel.ANONYMIZED, description="Privacy protection level"),
    db: Session = Depends(get_db)
):
    """
    Get privacy-aware analytics for a specific learner.
    
    Returns individual learning metrics with strong privacy protections:
    - Session activity and engagement
    - Subject mastery progress
    - IEP goal progress (if applicable)
    
    Privacy features:
    - Learner ID is hashed (irreversible)
    - Minimum cohort size enforced for k-anonymity
    - Differential privacy noise applied to sensitive metrics
    - PII completely removed from responses
    """
    # Default to last 60 days for individual learner data
    if not end_date:
        end_date = date.today()
    if not start_date:
        start_date = end_date - timedelta(days=60)
    
    # Validate learner hash format
    if len(learner_id_hash) != 16 or not all(c in '0123456789abcdef' for c in learner_id_hash.lower()):
        raise HTTPException(status_code=400, detail="Invalid learner ID hash format")
    
    try:
        # TODO: In production, add authorization checks
        # if not PrivacyGuard.check_learner_access(learner_id_hash, requesting_user_id, requesting_user_role):
        #     raise HTTPException(status_code=403, detail="Access denied")
        
        # Get learner session data
        session_data = db.query(SessionAggregate).filter(
            and_(
                SessionAggregate.learner_id_hash == learner_id_hash,
                SessionAggregate.date_bucket.between(start_date, end_date),
                SessionAggregate.aggregation_level == AggregationLevel.INDIVIDUAL,
                SessionAggregate.privacy_level == privacy_level
            )
        ).all()
        
        # Aggregate session metrics
        if session_data:
            total_sessions = sum(s.total_sessions for s in session_data)
            total_duration = sum(s.total_duration_minutes for s in session_data)
            avg_duration = total_duration / max(1, total_sessions)
            
            session_metrics = SessionMetrics(
                total_sessions=total_sessions,
                avg_duration_minutes=round(avg_duration, 2),
                median_duration_minutes=round(sum(s.median_duration_minutes for s in session_data) / len(session_data), 2),
                total_hours=round(total_duration / 60.0, 2),
                trend_direction="stable",
                privacy_level=privacy_level.value,
                data_points=len(session_data)
            )
        else:
            session_metrics = SessionMetrics(
                total_sessions=0, avg_duration_minutes=0, median_duration_minutes=0,
                total_hours=0, trend_direction="no_data", privacy_level=privacy_level.value,
                data_points=0
            )
        
        # Get subject progress
        mastery_data = db.query(MasteryAggregate).filter(
            and_(
                MasteryAggregate.learner_id_hash == learner_id_hash,
                MasteryAggregate.date_bucket.between(start_date, end_date),
                MasteryAggregate.privacy_level == privacy_level
            )
        ).order_by(desc(MasteryAggregate.current_mastery_score)).all()
        
        subject_progress = []
        for mastery in mastery_data:
            subject_progress.append(MasteryMetrics(
                subject_id=mastery.subject_id,
                subject_category=mastery.subject_category or "Unknown",
                current_mastery=float(mastery.current_mastery_score),
                mastery_improvement=float(mastery.mastery_improvement or 0),
                assessments_completed=mastery.assessments_completed,
                time_to_mastery_hours=mastery.time_to_mastery_hours,
                privacy_level=privacy_level.value,
                aggregation_level=mastery.aggregation_level.value
            ))
        
        # Get IEP progress (if applicable)
        iep_data = db.query(IEPProgressAggregate).filter(
            and_(
                IEPProgressAggregate.learner_id_hash == learner_id_hash,
                IEPProgressAggregate.date_bucket.between(start_date, end_date),
                IEPProgressAggregate.privacy_level == privacy_level
            )
        ).all()
        
        iep_progress = []
        for iep in iep_data:
            iep_progress.append(IEPProgressMetrics(
                goal_category=iep.iep_goal_category,
                baseline_score=float(iep.baseline_score),
                current_score=float(iep.current_score),
                target_score=float(iep.target_score),
                progress_percentage=float(iep.progress_percentage),
                is_on_track=iep.is_on_track,
                days_since_baseline=iep.days_since_baseline,
                projected_completion=iep.projected_days_to_goal,
                support_level=iep.support_level,
                interventions_used=iep.intervention_count,
                privacy_level=privacy_level.value
            ))
        
        # Privacy metadata
        min_cohort_size = min((s.cohort_size for s in session_data if s.cohort_size), default=1)
        dp_epsilon = session_data[0].noise_epsilon if session_data and session_data[0].noise_epsilon else None
        
        # Data completeness score (0-1)
        expected_days = (end_date - start_date).days + 1
        actual_days = len(set(s.date_bucket for s in session_data))
        completeness = actual_days / expected_days if expected_days > 0 else 0
        
        response_data = {
            "learner_id_hash": learner_id_hash,
            "reporting_period_start": start_date,
            "reporting_period_end": end_date,
            "session_metrics": session_metrics,
            "subject_progress": subject_progress,
            "iep_progress": iep_progress if iep_progress else None,
            "privacy_level": privacy_level.value,
            "minimum_cohort_size": min_cohort_size,
            "differential_privacy_epsilon": dp_epsilon,
            "last_updated": datetime.utcnow(),
            "data_completeness": round(completeness, 3)
        }
        
        filtered_data = PrivacyGuard.apply_privacy_filter(response_data, privacy_level)
        
        return LearnerAnalyticsSummary(**filtered_data)
        
    except Exception as e:
        logger.error(f"Failed to get learner analytics: {e}")
        raise HTTPException(status_code=500, detail="Failed to retrieve learner analytics")


@router.get("/etl/jobs", response_model=List[ETLJobStatus])
async def get_etl_jobs(
    limit: int = Query(50, le=100, description="Maximum number of jobs to return"),
    status_filter: Optional[str] = Query(None, description="Filter by job status"),
    db: Session = Depends(get_db)
):
    """Get ETL job execution history and status."""
    try:
        query = db.query(ETLJobRun).order_by(desc(ETLJobRun.started_at))
        
        if status_filter:
            query = query.filter(ETLJobRun.status == status_filter)
        
        jobs = query.limit(limit).all()
        
        job_statuses = []
        for job in jobs:
            job_statuses.append(ETLJobStatus(
                job_id=job.id,
                job_name=job.job_name,
                status=job.status,
                started_at=job.started_at,
                completed_at=job.completed_at,
                records_processed=job.records_processed,
                records_created=job.records_created,
                processing_time_seconds=job.processing_time_seconds,
                privacy_level=job.privacy_level_used.value,
                epsilon_used=job.epsilon_budget_used,
                error_message=job.error_message
            ))
        
        return job_statuses
        
    except Exception as e:
        logger.error(f"Failed to get ETL jobs: {e}")
        raise HTTPException(status_code=500, detail="Failed to retrieve ETL job status")


@router.post("/etl/trigger/{tenant_id}")
async def trigger_etl(
    tenant_id: UUID = Path(..., description="Tenant identifier"),
    target_date: Optional[date] = Query(None, description="Date to process (default: yesterday)"),
    privacy_level: PrivacyLevel = Query(PrivacyLevel.ANONYMIZED, description="Privacy protection level"),
    db: Session = Depends(get_db)
):
    """
    Trigger ETL processing for a specific tenant and date.
    
    This endpoint allows manual triggering of ETL jobs for data processing.
    Useful for backfilling data or reprocessing with different privacy levels.
    """
    if not target_date:
        target_date = date.today() - timedelta(days=1)  # Default to yesterday
    
    try:
        orchestrator = ETLOrchestrator(db)
        
        # Run daily ETL jobs
        daily_jobs = orchestrator.run_daily_etl(target_date, tenant_id, privacy_level)
        
        # Run weekly ETL if it's a Monday (start of week)
        weekly_job = None
        if target_date.weekday() == 0:  # Monday
            weekly_job = orchestrator.run_weekly_etl(target_date, tenant_id, privacy_level)
        
        result = {
            "message": "ETL jobs triggered successfully",
            "tenant_id": tenant_id,
            "target_date": target_date,
            "privacy_level": privacy_level.value,
            "daily_jobs": len(daily_jobs),
            "weekly_job": weekly_job is not None,
            "job_ids": [str(job.id) for job in daily_jobs] + ([str(weekly_job.id)] if weekly_job else [])
        }
        
        return result
        
    except Exception as e:
        logger.error(f"Failed to trigger ETL: {e}")
        raise HTTPException(status_code=500, detail="Failed to trigger ETL processing")


@router.get("/health")
async def health_check():
    """Health check endpoint."""
    return {
        "status": "healthy",
        "service": "analytics-svc",
        "version": "1.0.0",
        "stage": "S2-15"
    }


@router.get("/privacy/levels")
async def get_privacy_levels():
    """Get available privacy protection levels."""
    return {
        "privacy_levels": [
            {
                "level": "none",
                "description": "No privacy protection (admin only)",
                "suitable_for": "Internal analytics, admin dashboards"
            },
            {
                "level": "anonymized", 
                "description": "PII removed, data aggregated",
                "suitable_for": "Educator dashboards, tenant analytics"
            },
            {
                "level": "dp_low",
                "description": "Low differential privacy noise (ε=2.0)",
                "suitable_for": "Research, cohort analytics"
            },
            {
                "level": "dp_medium",
                "description": "Medium differential privacy noise (ε=1.0)", 
                "suitable_for": "Public reports, cross-tenant analytics"
            },
            {
                "level": "dp_high",
                "description": "High differential privacy noise (ε=0.5)",
                "suitable_for": "Published research, external sharing"
            }
        ]
    }
