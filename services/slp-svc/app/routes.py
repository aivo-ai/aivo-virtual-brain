# AIVO SLP Service - API Routes
# S2-11 Implementation - REST API endpoints for SLP workflows

from fastapi import APIRouter, HTTPException, Depends, status, BackgroundTasks
from sqlalchemy.orm import Session
from sqlalchemy import and_
from datetime import datetime, timezone
from typing import List, Optional
import uuid
import logging

from .models import (
    ScreeningAssessment, TherapyPlan, ExerciseInstance, ExerciseSession, ProgressEvent,
    ScreeningStatus, TherapyPlanStatus, SessionStatus
)
from .schemas import (
    ScreeningRequest, ScreeningResponse, TherapyPlanRequest, TherapyPlanResponse,
    ExerciseRequest, ExerciseResponse, SessionSubmitRequest, SessionResponse,
    ProgressEventResponse, ErrorResponse, ScreeningFilters, TherapyPlanFilters
)
from .engine import SLPEngine
from .database import get_db

router = APIRouter(prefix="/api/v1/slp", tags=["SLP"])
logger = logging.getLogger(__name__)

# Initialize SLP engine
slp_engine = SLPEngine()


@router.post("/screen", response_model=ScreeningResponse, status_code=status.HTTP_201_CREATED)
async def create_screening_assessment(
    request_data: ScreeningRequest,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db)
):
    """
    Create and process a new screening assessment.
    Evaluates speech and language domains to determine therapy needs.
    """
    try:
        logger.info(f"Creating screening assessment for patient {request_data.patient_id}")
        
        # Create screening assessment
        assessment = ScreeningAssessment(
            tenant_id=request_data.tenant_id,
            patient_id=request_data.patient_id,
            patient_name=request_data.patient_name,
            patient_age=request_data.patient_age,
            date_of_birth=request_data.date_of_birth,
            assessment_type=request_data.assessment_type,
            assessment_data=request_data.assessment_data,
            status=ScreeningStatus.IN_PROGRESS.value
        )
        
        db.add(assessment)
        db.flush()  # Get the ID
        
        # Process assessment in background
        background_tasks.add_task(process_screening_background, assessment.id, db)
        
        db.commit()
        db.refresh(assessment)
        
        logger.info(f"Screening assessment {assessment.id} created successfully")
        return assessment
        
    except Exception as e:
        db.rollback()
        logger.error(f"Error creating screening assessment: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to create screening assessment: {str(e)}"
        )


@router.get("/screen/{assessment_id}", response_model=ScreeningResponse)
async def get_screening_assessment(
    assessment_id: uuid.UUID,
    tenant_id: uuid.UUID,
    db: Session = Depends(get_db)
):
    """Get screening assessment by ID."""
    assessment = db.query(ScreeningAssessment).filter(
        and_(
            ScreeningAssessment.id == assessment_id,
            ScreeningAssessment.tenant_id == tenant_id
        )
    ).first()
    
    if not assessment:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Screening assessment not found"
        )
    
    return assessment


@router.get("/screen", response_model=List[ScreeningResponse])
async def list_screening_assessments(
    filters: ScreeningFilters = Depends(),
    db: Session = Depends(get_db)
):
    """List screening assessments with filtering."""
    query = db.query(ScreeningAssessment).filter(
        ScreeningAssessment.tenant_id == filters.tenant_id
    )
    
    # Apply filters
    if filters.patient_id:
        query = query.filter(ScreeningAssessment.patient_id == filters.patient_id)
    if filters.status:
        query = query.filter(ScreeningAssessment.status == filters.status.value)
    if filters.assessment_type:
        query = query.filter(ScreeningAssessment.assessment_type == filters.assessment_type)
    if filters.date_from:
        query = query.filter(ScreeningAssessment.created_at >= filters.date_from)
    if filters.date_to:
        query = query.filter(ScreeningAssessment.created_at <= filters.date_to)
    
    # Pagination
    offset = (filters.page - 1) * filters.per_page
    assessments = query.offset(offset).limit(filters.per_page).all()
    
    return assessments


@router.post("/plan", response_model=TherapyPlanResponse, status_code=status.HTTP_201_CREATED)
async def create_therapy_plan(
    request_data: TherapyPlanRequest,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db)
):
    """
    Create individualized therapy plan based on screening results.
    Generates goals, objectives, and exercise sequences.
    """
    try:
        logger.info(f"Creating therapy plan for screening {request_data.screening_id}")
        
        # Verify screening exists and is completed
        screening = db.query(ScreeningAssessment).filter(
            and_(
                ScreeningAssessment.id == request_data.screening_id,
                ScreeningAssessment.tenant_id == request_data.tenant_id
            )
        ).first()
        
        if not screening:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Screening assessment not found"
            )
        
        if screening.status != ScreeningStatus.COMPLETED.value:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Screening assessment must be completed before creating therapy plan"
            )
        
        # Generate therapy plan using SLP engine
        plan_data = await slp_engine.generate_therapy_plan(screening, request_data.model_dump())
        
        # Create therapy plan
        therapy_plan = TherapyPlan(
            tenant_id=request_data.tenant_id,
            screening_id=request_data.screening_id,
            patient_id=screening.patient_id,
            plan_name=request_data.plan_name,
            priority_level=request_data.priority_level,
            goals=plan_data["goals"],
            objectives=plan_data["objectives"],
            exercise_sequence=plan_data["exercise_sequence"],
            sessions_per_week=request_data.sessions_per_week,
            session_duration=request_data.session_duration,
            estimated_duration_weeks=plan_data.get("estimated_duration_weeks"),
            progress_data=plan_data["progress_data"],
            current_phase=plan_data["current_phase"],
            status=TherapyPlanStatus.ACTIVE.value,
            started_at=datetime.now(timezone.utc)
        )
        
        db.add(therapy_plan)
        db.flush()
        
        # Emit progress event
        background_tasks.add_task(
            emit_progress_event,
            "SLP_PLAN_CREATED",
            "therapy_plan",
            therapy_plan.id,
            {"plan_name": therapy_plan.plan_name, "goals_count": len(plan_data["goals"])},
            therapy_plan.tenant_id,
            therapy_plan.patient_id,
            db
        )
        
        db.commit()
        db.refresh(therapy_plan)
        
        logger.info(f"Therapy plan {therapy_plan.id} created successfully")
        return therapy_plan
        
    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        logger.error(f"Error creating therapy plan: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to create therapy plan: {str(e)}"
        )


@router.get("/plan/{plan_id}", response_model=TherapyPlanResponse)
async def get_therapy_plan(
    plan_id: uuid.UUID,
    tenant_id: uuid.UUID,
    db: Session = Depends(get_db)
):
    """Get therapy plan by ID."""
    plan = db.query(TherapyPlan).filter(
        and_(
            TherapyPlan.id == plan_id,
            TherapyPlan.tenant_id == tenant_id
        )
    ).first()
    
    if not plan:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Therapy plan not found"
        )
    
    return plan


@router.get("/plan", response_model=List[TherapyPlanResponse])
async def list_therapy_plans(
    filters: TherapyPlanFilters = Depends(),
    db: Session = Depends(get_db)
):
    """List therapy plans with filtering."""
    query = db.query(TherapyPlan).filter(
        TherapyPlan.tenant_id == filters.tenant_id
    )
    
    # Apply filters
    if filters.patient_id:
        query = query.filter(TherapyPlan.patient_id == filters.patient_id)
    if filters.status:
        query = query.filter(TherapyPlan.status == filters.status.value)
    if filters.priority_level:
        query = query.filter(TherapyPlan.priority_level == filters.priority_level)
    
    # Pagination
    offset = (filters.page - 1) * filters.per_page
    plans = query.offset(offset).limit(filters.per_page).all()
    
    return plans


@router.post("/exercise/next", response_model=ExerciseResponse, status_code=status.HTTP_201_CREATED)
async def generate_next_exercise(
    request_data: ExerciseRequest,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db)
):
    """
    Generate next exercise in therapy sequence.
    Uses AI-powered content generation and adaptive difficulty.
    """
    try:
        logger.info(f"Generating next exercise for therapy plan {request_data.therapy_plan_id}")
        
        # Verify therapy plan exists
        therapy_plan = db.query(TherapyPlan).filter(
            and_(
                TherapyPlan.id == request_data.therapy_plan_id,
                TherapyPlan.tenant_id == request_data.tenant_id
            )
        ).first()
        
        if not therapy_plan:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Therapy plan not found"
            )
        
        if therapy_plan.status != TherapyPlanStatus.ACTIVE.value:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Therapy plan must be active to generate exercises"
            )
        
        # Generate exercise using SLP engine
        exercise = await slp_engine.generate_next_exercise(therapy_plan, request_data.model_dump())
        
        db.add(exercise)
        db.flush()
        
        # Update therapy plan progress
        background_tasks.add_task(
            update_plan_progress,
            therapy_plan.id,
            {"exercise_generated": exercise.exercise_name},
            db
        )
        
        db.commit()
        db.refresh(exercise)
        
        logger.info(f"Exercise {exercise.id} generated successfully")
        return exercise
        
    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        logger.error(f"Error generating exercise: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to generate exercise: {str(e)}"
        )


@router.get("/exercise/{exercise_id}", response_model=ExerciseResponse)
async def get_exercise(
    exercise_id: uuid.UUID,
    tenant_id: uuid.UUID,
    db: Session = Depends(get_db)
):
    """Get exercise by ID."""
    exercise = db.query(ExerciseInstance).filter(
        and_(
            ExerciseInstance.id == exercise_id,
            ExerciseInstance.tenant_id == tenant_id
        )
    ).first()
    
    if not exercise:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Exercise not found"
        )
    
    return exercise


@router.post("/session/submit", response_model=SessionResponse, status_code=status.HTTP_200_OK)
async def submit_session_results(
    request_data: SessionSubmitRequest,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db)
):
    """
    Submit session results and update progress.
    Processes performance data and generates next session recommendations.
    """
    try:
        logger.info(f"Submitting results for session {request_data.session_id}")
        
        # Verify session exists
        session = db.query(ExerciseSession).filter(
            and_(
                ExerciseSession.id == request_data.session_id,
                ExerciseSession.tenant_id == request_data.tenant_id
            )
        ).first()
        
        if not session:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Session not found"
            )
        
        if session.status == SessionStatus.COMPLETED.value:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Session already completed"
            )
        
        # Process session results using SLP engine
        results = await slp_engine.process_session_submission(session, request_data.model_dump())
        
        # Update session
        session.status = SessionStatus.COMPLETED.value
        session.completed_at = datetime.now(timezone.utc)
        session.actual_duration = request_data.actual_duration
        session.session_notes = request_data.session_notes
        session.exercises_completed = len(request_data.exercise_results)
        session.overall_score = results["session_metrics"].get("overall_score")
        session.engagement_score = results["session_metrics"].get("engagement_score")
        session.accuracy_rate = results["session_metrics"].get("accuracy_rate")
        session.completion_rate = results["session_metrics"].get("completion_rate")
        session.audio_recordings = request_data.audio_recordings
        session.voice_analysis = results.get("voice_analysis")
        
        # Emit progress event
        background_tasks.add_task(
            emit_progress_event,
            "SLP_SESSION_COMPLETED",
            "session",
            session.id,
            {
                "session_number": session.session_number,
                "overall_score": session.overall_score,
                "exercises_completed": session.exercises_completed
            },
            session.tenant_id,
            session.patient_id,
            db
        )
        
        db.commit()
        db.refresh(session)
        
        logger.info(f"Session {session.id} submitted successfully")
        return session
        
    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        logger.error(f"Error submitting session: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to submit session: {str(e)}"
        )


@router.get("/session/{session_id}", response_model=SessionResponse)
async def get_session(
    session_id: uuid.UUID,
    tenant_id: uuid.UUID,
    db: Session = Depends(get_db)
):
    """Get session by ID."""
    session = db.query(ExerciseSession).filter(
        and_(
            ExerciseSession.id == session_id,
            ExerciseSession.tenant_id == tenant_id
        )
    ).first()
    
    if not session:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Session not found"
        )
    
    return session


@router.post("/session", response_model=SessionResponse, status_code=status.HTTP_201_CREATED)
async def create_session(
    tenant_id: uuid.UUID,
    therapy_plan_id: uuid.UUID,
    session_type: str = "regular",
    db: Session = Depends(get_db)
):
    """Create a new exercise session."""
    try:
        # Verify therapy plan exists
        therapy_plan = db.query(TherapyPlan).filter(
            and_(
                TherapyPlan.id == therapy_plan_id,
                TherapyPlan.tenant_id == tenant_id
            )
        ).first()
        
        if not therapy_plan:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Therapy plan not found"
            )
        
        # Get next session number
        last_session = db.query(ExerciseSession).filter(
            ExerciseSession.therapy_plan_id == therapy_plan_id
        ).order_by(ExerciseSession.session_number.desc()).first()
        
        session_number = (last_session.session_number + 1) if last_session else 1
        
        # Create session
        session = ExerciseSession(
            tenant_id=tenant_id,
            therapy_plan_id=therapy_plan_id,
            patient_id=therapy_plan.patient_id,
            session_number=session_number,
            session_type=session_type,
            planned_duration=therapy_plan.session_duration,
            status=SessionStatus.ACTIVE.value,
            started_at=datetime.now(timezone.utc)
        )
        
        db.add(session)
        db.commit()
        db.refresh(session)
        
        logger.info(f"Session {session.id} created successfully")
        return session
        
    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        logger.error(f"Error creating session: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to create session: {str(e)}"
        )


@router.get("/progress/{patient_id}", response_model=List[ProgressEventResponse])
async def get_progress_events(
    patient_id: str,
    tenant_id: uuid.UUID,
    limit: int = 50,
    db: Session = Depends(get_db)
):
    """Get progress events for a patient."""
    events = db.query(ProgressEvent).filter(
        and_(
            ProgressEvent.patient_id == patient_id,
            ProgressEvent.tenant_id == tenant_id
        )
    ).order_by(ProgressEvent.created_at.desc()).limit(limit).all()
    
    return events


@router.get("/health")
async def health_check():
    """Health check endpoint."""
    return {
        "status": "healthy",
        "service": "slp-svc",
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "version": "1.0.0"
    }


# Background tasks
async def process_screening_background(assessment_id: uuid.UUID, db: Session):
    """Process screening assessment in background."""
    try:
        assessment = db.query(ScreeningAssessment).filter(
            ScreeningAssessment.id == assessment_id
        ).first()
        
        if not assessment:
            logger.error(f"Assessment {assessment_id} not found for background processing")
            return
        
        # Process assessment using SLP engine
        results = await slp_engine.process_screening(assessment)
        
        # Update assessment with results
        assessment.scores = results["scores"]
        assessment.risk_factors = results["risk_factors"]
        assessment.recommendations = results["recommendations"]
        assessment.overall_score = results["overall_score"]
        assessment.priority_areas = results["priority_areas"]
        assessment.therapy_recommended = results["therapy_recommended"]
        assessment.status = ScreeningStatus.COMPLETED.value
        assessment.completed_at = datetime.now(timezone.utc)
        
        # Emit progress event
        await emit_progress_event(
            "SLP_SCREENING_COMPLETED",
            "screening",
            assessment.id,
            {
                "overall_score": assessment.overall_score,
                "therapy_recommended": assessment.therapy_recommended,
                "priority_areas": assessment.priority_areas
            },
            assessment.tenant_id,
            assessment.patient_id,
            db
        )
        
        db.commit()
        logger.info(f"Screening assessment {assessment_id} processed successfully")
        
    except Exception as e:
        db.rollback()
        logger.error(f"Error processing screening assessment {assessment_id}: {str(e)}")


async def emit_progress_event(event_type: str, source: str, source_id: uuid.UUID,
                            event_data: dict, tenant_id: uuid.UUID, patient_id: str,
                            db: Session, triggered_by: Optional[str] = None):
    """Emit progress event."""
    try:
        event = await slp_engine.emit_progress_event(
            event_type, source, source_id, event_data, tenant_id, patient_id, triggered_by
        )
        
        db.add(event)
        db.commit()
        
        logger.info(f"Progress event emitted: {event_type}")
        
    except Exception as e:
        logger.error(f"Error emitting progress event: {str(e)}")


async def update_plan_progress(plan_id: uuid.UUID, progress_data: dict, db: Session):
    """Update therapy plan progress."""
    try:
        plan = db.query(TherapyPlan).filter(TherapyPlan.id == plan_id).first()
        if plan:
            # Update progress data
            current_progress = plan.progress_data or {}
            current_progress.update(progress_data)
            plan.progress_data = current_progress
            plan.updated_at = datetime.now(timezone.utc)
            
            db.commit()
            logger.info(f"Therapy plan {plan_id} progress updated")
        
    except Exception as e:
        logger.error(f"Error updating therapy plan progress: {str(e)}")
        db.rollback()
