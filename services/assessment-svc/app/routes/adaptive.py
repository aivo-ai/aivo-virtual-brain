"""
AIVO Assessment Service - Adaptive Assessment Routes
S2-08 Implementation - IRT-based Adaptive Testing Endpoints

Provides REST API endpoints for adaptive assessment using IRT:
- POST /adaptive/start - Initialize adaptive session
- POST /adaptive/answer - Submit answer and get next question  
- GET /adaptive/next - Get next question without answering
- GET /adaptive/report - Get final assessment report
- POST /admin/calibrate - Admin utility for item calibration
"""

from fastapi import APIRouter, Depends, HTTPException, status, Security
from sqlalchemy.orm import Session
from typing import List, Optional, Dict, Any
from datetime import datetime, timedelta
import uuid
import logging

from app.database import get_db
from app.models import (
    AssessmentSession, QuestionBank, AssessmentResponse, AssessmentResult,
    AssessmentStatus, AssessmentType
)
from app.schemas import (
    AdaptiveStartRequest, AdaptiveStartResponse, AdaptiveAnswerRequest, 
    AdaptiveAnswerResponse, NextQuestionResponse, AssessmentReportResponse,
    ItemCalibrationRequest, ItemCalibrationResponse, ErrorResponse
)
from app.logic_irt import IRTEngine, IRTParameters, ItemCalibration
from app.dependencies import get_current_user, get_admin_user
from app.events import publish_assessment_event

router = APIRouter(prefix="/adaptive", tags=["Adaptive Assessment"])
admin_router = APIRouter(prefix="/admin", tags=["Administration"])

logger = logging.getLogger(__name__)

# Initialize IRT engine
irt_engine = IRTEngine()
calibration_service = ItemCalibration()

@router.post("/start", response_model=AdaptiveStartResponse)
async def start_adaptive_assessment(
    request: AdaptiveStartRequest,
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user)
) -> AdaptiveStartResponse:
    """
    Start a new adaptive assessment session.
    
    Initializes IRT parameters and selects first question based on
    medium difficulty level (theta = 0).
    """
    try:
        # Validate request
        if not request.learner_id or not request.subject:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="learner_id and subject are required"
            )
        
        # Check for existing active session
        existing_session = db.query(AssessmentSession).filter(
            AssessmentSession.learner_id == request.learner_id,
            AssessmentSession.subject == request.subject,
            AssessmentSession.status.in_([AssessmentStatus.CREATED.value, AssessmentStatus.IN_PROGRESS.value])
        ).first()
        
        if existing_session:
            # Return existing session if found
            logger.info(f"Returning existing session {existing_session.id} for learner {request.learner_id}")
            
            # Get first/next question
            next_question = await get_next_question_internal(existing_session.id, db)
            
            return AdaptiveStartResponse(
                session_id=existing_session.id,
                status=existing_session.status,
                current_theta=existing_session.current_theta,
                standard_error=existing_session.standard_error,
                questions_answered=existing_session.questions_answered,
                first_question=next_question.question if next_question else None,
                estimated_total_questions=irt_engine.max_questions,
                message="Resumed existing session"
            )
        
        # Create new assessment session
        session = AssessmentSession(
            id=str(uuid.uuid4()),
            learner_id=request.learner_id,
            tenant_id=request.tenant_id,
            assessment_type=AssessmentType.ADAPTIVE.value,
            subject=request.subject,
            status=AssessmentStatus.CREATED.value,
            current_theta=0.0,  # Start at medium difficulty
            standard_error=irt_engine.default_se,
            session_data=request.metadata or {},
            started_at=datetime.utcnow(),
            expires_at=datetime.utcnow() + timedelta(hours=2)  # 2 hour session timeout
        )
        
        db.add(session)
        db.commit()
        db.refresh(session)
        
        logger.info(f"Created adaptive session {session.id} for learner {request.learner_id}, subject {request.subject}")
        
        # Select first question at medium difficulty (theta = 0)
        first_question = await select_next_question(session.id, db)
        
        # Update session status
        session.status = AssessmentStatus.IN_PROGRESS.value
        db.commit()
        
        return AdaptiveStartResponse(
            session_id=session.id,
            status=session.status,
            current_theta=session.current_theta,
            standard_error=session.standard_error,
            questions_answered=0,
            first_question=first_question,
            estimated_total_questions=irt_engine.max_questions,
            message="Adaptive session started successfully"
        )
        
    except Exception as e:
        logger.error(f"Error starting adaptive assessment: {str(e)}")
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to start adaptive assessment: {str(e)}"
        )

@router.post("/answer", response_model=AdaptiveAnswerResponse)
async def submit_answer(
    request: AdaptiveAnswerRequest,
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user)
) -> AdaptiveAnswerResponse:
    """
    Submit answer for current question and get next question.
    
    Updates ability estimate using IRT and selects optimal next item.
    """
    try:
        # Get assessment session
        session = db.query(AssessmentSession).filter(
            AssessmentSession.id == request.session_id
        ).first()
        
        if not session:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Assessment session not found"
            )
        
        if session.status not in [AssessmentStatus.IN_PROGRESS.value]:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Session is not active (status: {session.status})"
            )
        
        # Get current question
        current_question = db.query(QuestionBank).filter(
            QuestionBank.id == request.question_id
        ).first()
        
        if not current_question:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Question not found"
            )
        
        # Check if answer is correct
        is_correct = (request.user_answer.strip().lower() == 
                     current_question.correct_answer.strip().lower())
        
        # Store theta before this response
        theta_before = session.current_theta
        
        # Create response record
        response = AssessmentResponse(
            id=str(uuid.uuid4()),
            session_id=session.id,
            question_id=current_question.id,
            user_answer=request.user_answer,
            is_correct=is_correct,
            response_time_ms=request.response_time_ms,
            theta_before=theta_before,
            question_order=session.questions_answered + 1,
            response_metadata=request.metadata or {}
        )
        
        db.add(response)
        
        # Get all responses for ability estimation
        all_responses = db.query(AssessmentResponse).filter(
            AssessmentResponse.session_id == session.id
        ).all()
        all_responses.append(response)  # Include current response
        
        # Prepare response data for IRT estimation
        irt_responses = []
        for resp in all_responses:
            q = db.query(QuestionBank).filter(QuestionBank.id == resp.question_id).first()
            if q:
                item_params = IRTParameters(q.difficulty, q.discrimination, q.guessing)
                irt_responses.append((resp.is_correct, item_params))
        
        # Estimate new ability level
        new_theta, new_se = irt_engine.estimate_ability(irt_responses, theta_before)
        
        # Update response with new theta
        response.theta_after = new_theta
        response.information_value = irt_engine.information(
            new_theta, 
            IRTParameters(current_question.difficulty, current_question.discrimination, current_question.guessing)
        )
        
        # Update session
        session.current_theta = new_theta
        session.standard_error = new_se
        session.questions_answered = len(all_responses)
        session.correct_answers = sum(1 for r in all_responses if r.is_correct)
        session.theta_history = (session.theta_history or []) + [new_theta]
        
        db.commit()
        
        logger.info(f"Answer processed: session={session.id}, correct={is_correct}, new_theta={new_theta:.3f}, SE={new_se:.3f}")
        
        # Check stopping criteria
        should_stop = irt_engine.should_stop_assessment(new_se, session.questions_answered)
        
        next_question = None
        if not should_stop:
            # Select next question
            next_question = await select_next_question(session.id, db)
            if not next_question:
                should_stop = True  # No more questions available
        
        if should_stop:
            # Complete assessment
            await complete_assessment(session, db)
            
            return AdaptiveAnswerResponse(
                session_id=session.id,
                is_correct=is_correct,
                updated_theta=new_theta,
                standard_error=new_se,
                questions_answered=session.questions_answered,
                assessment_complete=True,
                next_question=None,
                stopping_reason="Target precision achieved" if new_se <= irt_engine.target_se else "Maximum questions reached",
                message="Assessment completed"
            )
        else:
            return AdaptiveAnswerResponse(
                session_id=session.id,
                is_correct=is_correct,
                updated_theta=new_theta,
                standard_error=new_se,
                questions_answered=session.questions_answered,
                assessment_complete=False,
                next_question=next_question,
                stopping_reason=None,
                message="Continue to next question"
            )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error processing answer: {str(e)}")
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to process answer: {str(e)}"
        )

@router.get("/next/{session_id}", response_model=NextQuestionResponse)
async def get_next_question(
    session_id: str,
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user)
) -> NextQuestionResponse:
    """Get next question without submitting an answer."""
    try:
        return await get_next_question_internal(session_id, db)
    except Exception as e:
        logger.error(f"Error getting next question: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get next question: {str(e)}"
        )

@router.get("/report/{session_id}", response_model=AssessmentReportResponse)
async def get_assessment_report(
    session_id: str,
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user)
) -> AssessmentReportResponse:
    """Get final assessment report with IRT results and level mapping."""
    try:
        # Get session and results
        session = db.query(AssessmentSession).filter(
            AssessmentSession.id == session_id
        ).first()
        
        if not session:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Assessment session not found"
            )
        
        # Get assessment result
        result = db.query(AssessmentResult).filter(
            AssessmentResult.session_id == session_id
        ).first()
        
        if not result:
            # Generate result if not exists
            if session.status == AssessmentStatus.COMPLETED.value:
                await complete_assessment(session, db)
                result = db.query(AssessmentResult).filter(
                    AssessmentResult.session_id == session_id
                ).first()
        
        if not result:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Assessment not completed or result not available"
            )
        
        # Get response history
        responses = db.query(AssessmentResponse).filter(
            AssessmentResponse.session_id == session_id
        ).order_by(AssessmentResponse.question_order).all()
        
        # Format response history
        response_history = []
        for resp in responses:
            question = db.query(QuestionBank).filter(QuestionBank.id == resp.question_id).first()
            response_history.append({
                "question_id": resp.question_id,
                "question_content": question.content if question else "N/A",
                "user_answer": resp.user_answer,
                "correct_answer": question.correct_answer if question else "N/A",
                "is_correct": resp.is_correct,
                "theta_before": resp.theta_before,
                "theta_after": resp.theta_after,
                "information_value": resp.information_value,
                "response_time_ms": resp.response_time_ms
            })
        
        return AssessmentReportResponse(
            session_id=session_id,
            learner_id=session.learner_id,
            subject=session.subject,
            assessment_type="adaptive",
            status=session.status,
            
            # IRT Results
            final_theta=result.final_theta,
            standard_error=result.standard_error,
            reliability=result.reliability,
            
            # Level Mapping
            proficiency_level=result.proficiency_level,
            level_confidence=result.level_confidence,
            
            # Performance Metrics
            total_questions=result.total_questions,
            correct_answers=result.correct_answers,
            accuracy_percentage=result.accuracy_percentage,
            average_response_time_ms=result.average_response_time_ms,
            
            # Detailed Results
            strengths=result.strengths,
            weaknesses=result.weaknesses,
            recommendations=result.recommendations,
            
            # Session Timeline
            theta_history=session.theta_history or [],
            response_history=response_history,
            
            # Timestamps
            started_at=session.started_at,
            completed_at=session.completed_at,
            total_time_minutes=((session.completed_at - session.started_at).total_seconds() / 60) if session.completed_at else None
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error generating assessment report: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to generate assessment report: {str(e)}"
        )

# Admin utilities
@admin_router.post("/calibrate", response_model=ItemCalibrationResponse)
async def calibrate_items(
    request: ItemCalibrationRequest,
    db: Session = Depends(get_db),
    admin_user: dict = Security(get_admin_user, scopes=["admin"])
) -> ItemCalibrationResponse:
    """
    Admin utility to calibrate item parameters from response data.
    
    Requires admin privileges. Updates question bank with new IRT parameters.
    """
    try:
        calibrated_count = 0
        failed_items = []
        
        for item_data in request.items:
            try:
                # Get item from database
                question = db.query(QuestionBank).filter(
                    QuestionBank.id == item_data.item_id
                ).first()
                
                if not question:
                    failed_items.append({
                        "item_id": item_data.item_id,
                        "error": "Item not found"
                    })
                    continue
                
                # Calibrate parameters
                params = calibration_service.estimate_item_parameters(item_data.responses)
                
                # Update question parameters
                question.difficulty = params.difficulty
                question.discrimination = params.discrimination
                question.guessing = params.guessing
                
                calibrated_count += 1
                
                logger.info(f"Calibrated item {item_data.item_id}: {params}")
                
            except Exception as e:
                failed_items.append({
                    "item_id": item_data.item_id,
                    "error": str(e)
                })
                logger.error(f"Failed to calibrate item {item_data.item_id}: {str(e)}")
        
        db.commit()
        
        return ItemCalibrationResponse(
            calibrated_items=calibrated_count,
            failed_items=failed_items,
            message=f"Successfully calibrated {calibrated_count} items"
        )
        
    except Exception as e:
        logger.error(f"Error in item calibration: {str(e)}")
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Item calibration failed: {str(e)}"
        )

# Helper functions
async def select_next_question(session_id: str, db: Session) -> Optional[Dict[str, Any]]:
    """Select optimal next question for adaptive assessment."""
    session = db.query(AssessmentSession).filter(AssessmentSession.id == session_id).first()
    if not session:
        return None
    
    # Get used question IDs
    used_questions = db.query(AssessmentResponse.question_id).filter(
        AssessmentResponse.session_id == session_id
    ).all()
    used_ids = [q[0] for q in used_questions]
    
    # Get available questions for this subject
    available_questions = db.query(QuestionBank).filter(
        QuestionBank.subject == session.subject,
        QuestionBank.is_active == True,
        ~QuestionBank.id.in_(used_ids)
    ).all()
    
    if not available_questions:
        return None
    
    # Convert to item pool format
    item_pool = []
    for q in available_questions:
        item_pool.append({
            'id': q.id,
            'difficulty': q.difficulty,
            'discrimination': q.discrimination,
            'guessing': q.guessing,
            'content': q.content,
            'options': q.options,
            'estimated_time_seconds': q.estimated_time_seconds
        })
    
    # Select optimal item
    optimal_item = irt_engine.select_next_item(session.current_theta, item_pool, used_ids)
    return optimal_item

async def get_next_question_internal(session_id: str, db: Session) -> NextQuestionResponse:
    """Internal function to get next question."""
    session = db.query(AssessmentSession).filter(AssessmentSession.id == session_id).first()
    
    if not session:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Assessment session not found"
        )
    
    if session.status == AssessmentStatus.COMPLETED.value:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Assessment already completed"
        )
    
    next_question = await select_next_question(session_id, db)
    
    if not next_question:
        return NextQuestionResponse(
            session_id=session_id,
            question=None,
            current_theta=session.current_theta,
            standard_error=session.standard_error,
            questions_answered=session.questions_answered,
            has_next_question=False,
            message="No more questions available"
        )
    
    return NextQuestionResponse(
        session_id=session_id,
        question=next_question,
        current_theta=session.current_theta,
        standard_error=session.standard_error,
        questions_answered=session.questions_answered,
        has_next_question=True,
        message="Next question ready"
    )

async def complete_assessment(session: AssessmentSession, db: Session):
    """Complete assessment and generate final results."""
    try:
        # Update session status
        session.status = AssessmentStatus.COMPLETED.value
        session.completed_at = datetime.utcnow()
        
        # Map theta to proficiency level
        level, confidence = irt_engine.map_theta_to_level(session.current_theta, session.standard_error)
        
        # Calculate performance metrics
        responses = db.query(AssessmentResponse).filter(
            AssessmentResponse.session_id == session.id
        ).all()
        
        total_questions = len(responses)
        correct_answers = sum(1 for r in responses if r.is_correct)
        accuracy = (correct_answers / total_questions) if total_questions > 0 else 0.0
        
        avg_response_time = None
        if responses and any(r.response_time_ms for r in responses):
            times = [r.response_time_ms for r in responses if r.response_time_ms]
            avg_response_time = sum(times) // len(times) if times else None
        
        # Generate recommendations based on performance
        recommendations = generate_recommendations(session.current_theta, level, accuracy)
        
        # Create assessment result
        result = AssessmentResult(
            id=str(uuid.uuid4()),
            session_id=session.id,
            learner_id=session.learner_id,
            subject=session.subject,
            final_theta=session.current_theta,
            standard_error=session.standard_error,
            reliability=calculate_reliability(responses),
            proficiency_level=level,
            level_confidence=confidence,
            total_questions=total_questions,
            correct_answers=correct_answers,
            accuracy_percentage=accuracy * 100,
            average_response_time_ms=avg_response_time,
            strengths=identify_strengths(responses, db),
            weaknesses=identify_weaknesses(responses, db),
            recommendations=recommendations
        )
        
        db.add(result)
        db.commit()
        
        # Publish assessment completion event
        await publish_assessment_event({
            "event_type": "ADAPTIVE_ASSESSMENT_COMPLETED",
            "session_id": session.id,
            "learner_id": session.learner_id,
            "subject": session.subject,
            "final_theta": session.current_theta,
            "proficiency_level": level,
            "total_questions": total_questions,
            "accuracy": accuracy
        })
        
        logger.info(f"Assessment completed: session={session.id}, theta={session.current_theta:.3f}, level={level}")
        
    except Exception as e:
        logger.error(f"Error completing assessment: {str(e)}")
        raise

def calculate_reliability(responses: List[AssessmentResponse]) -> float:
    """Calculate assessment reliability using information-based method."""
    if not responses:
        return 0.0
    
    total_info = sum(r.information_value or 0.0 for r in responses)
    if total_info <= 0:
        return 0.0
    
    # Reliability = Information / (1 + Information)
    reliability = total_info / (1 + total_info)
    return min(0.99, max(0.0, reliability))

def generate_recommendations(theta: float, level: str, accuracy: float) -> List[str]:
    """Generate learning recommendations based on assessment results."""
    recommendations = []
    
    if level in ["L0", "L1"]:
        recommendations.append("Focus on fundamental concepts and basic skills")
        recommendations.append("Practice regularly with guided exercises")
    elif level == "L2":
        recommendations.append("Work on intermediate problem-solving strategies")
        recommendations.append("Connect concepts to real-world applications")
    elif level in ["L3", "L4"]:
        recommendations.append("Challenge yourself with advanced problems")
        recommendations.append("Explore specialized topics in depth")
    
    if accuracy < 0.6:
        recommendations.append("Review basic concepts before moving forward")
        recommendations.append("Seek additional support or tutoring")
    elif accuracy > 0.9:
        recommendations.append("Consider accelerated or enrichment materials")
    
    return recommendations

def identify_strengths(responses: List[AssessmentResponse], db: Session) -> List[str]:
    """Identify learner strengths from response patterns."""
    # Placeholder - in real implementation, would analyze response patterns by topic/skill
    correct_responses = [r for r in responses if r.is_correct]
    if len(correct_responses) > len(responses) * 0.7:
        return ["Strong problem-solving skills", "Good conceptual understanding"]
    else:
        return ["Persistence", "Willingness to attempt difficult problems"]

def identify_weaknesses(responses: List[AssessmentResponse], db: Session) -> List[str]:
    """Identify areas needing improvement from response patterns."""
    # Placeholder - in real implementation, would analyze response patterns by topic/skill
    incorrect_responses = [r for r in responses if not r.is_correct]
    if len(incorrect_responses) > len(responses) * 0.4:
        return ["Needs more practice with basic concepts", "May benefit from additional instruction"]
    else:
        return ["Minor gaps in advanced topics"]

# Include admin router
router.include_router(admin_router)
