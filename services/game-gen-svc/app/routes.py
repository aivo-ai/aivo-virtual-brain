# AIVO Game Generation Service - FastAPI Routes
# S2-13 Implementation - REST API endpoints for game generation

import logging
import uuid
from typing import List, Optional, Dict, Any
from datetime import datetime, timezone
from fastapi import APIRouter, Depends, HTTPException, Query, Path, BackgroundTasks
from fastapi.responses import JSONResponse
from sqlalchemy.orm import Session
from sqlalchemy import and_, or_, desc, asc

from .database import get_db
from .models import (
    GameManifest, LearnerProfile, GameTemplate, GameSession, GameAnalytics,
    GameType, GameDifficulty, GameStatus, SubjectArea, GradeBand
)
from .schemas import (
    GameGenerationRequest, GameGenerationResponse, GameManifestResponse,
    LearnerProfileRequest, LearnerProfileResponse, GameSessionCreate,
    GameSessionUpdate, GameSessionResponse, GameAnalyticsResponse,
    GameTemplateResponse, GameListResponse, GameListFilter,
    GameEventRequest, EventEmissionResponse, ValidationResponse,
    GameCompletionRequest
)
from .engine import GameGenerationEngine

logger = logging.getLogger(__name__)

# Initialize router
router = APIRouter(prefix="/api/v1/games", tags=["Game Generation"])

# Initialize game engine (will be injected in main.py)
game_engine: Optional[GameGenerationEngine] = None


def get_game_engine() -> GameGenerationEngine:
    """Dependency to get the game generation engine."""
    if game_engine is None:
        raise HTTPException(status_code=500, detail="Game engine not initialized")
    return game_engine


def get_tenant_id() -> uuid.UUID:
    """
    Extract tenant ID from request context.
    In production, this would come from JWT token or auth middleware.
    For now, using a default tenant.
    """
    # TODO: Extract from JWT token in production
    return uuid.UUID("550e8400-e29b-41d4-a716-446655440000")


@router.post("/generate", 
             response_model=GameGenerationResponse,
             summary="Generate Personalized Reset Game",
             description="Generate a personalized reset game based on learner profile and request parameters. Returns immediately with generation status; game content is generated asynchronously.")
async def generate_game(
    request: GameGenerationRequest,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db),
    engine: GameGenerationEngine = Depends(get_game_engine),
    tenant_id: uuid.UUID = Depends(get_tenant_id)
):
    """
    Generate a personalized reset game for a specific learner.
    
    The game generation process:
    1. Analyzes learner profile and preferences
    2. Selects optimal game type and difficulty
    3. Generates content using AI or templates
    4. Creates interactive game manifest
    5. Emits GAME_READY event when complete
    
    **Duration Management:**
    - Respects requested duration (1-60 minutes)
    - Adapts to learner's attention span
    - Ensures content fits time constraints
    
    **Events Emitted:**
    - GAME_READY: When generation completes successfully
    - GAME_FAILED: If generation encounters critical errors
    """
    try:
        logger.info(f"Generating game for learner {request.learner_id}")
        
        # Validate request parameters
        if request.minutes < 1 or request.minutes > 60:
            raise HTTPException(
                status_code=400,
                detail="Game duration must be between 1 and 60 minutes"
            )
        
        # Start game generation process
        manifest = await engine.generate_game(request, tenant_id, db)
        
        response = GameGenerationResponse(
            success=True,
            message="Game generation started successfully",
            game_manifest_id=manifest.id,
            estimated_completion_seconds=30,
            status=manifest.status,
            expected_ready_at=manifest.generation_started_at
        )
        
        return response
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Game generation failed: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail=f"Game generation failed: {str(e)}"
        )


@router.get("/manifest/{game_id}",
            response_model=GameManifestResponse,
            summary="Get Game Manifest",
            description="Retrieve the complete game manifest including scenes, assets, and rules.")
async def get_game_manifest(
    game_id: uuid.UUID = Path(..., description="Game manifest ID"),
    db: Session = Depends(get_db),
    tenant_id: uuid.UUID = Depends(get_tenant_id)
):
    """Get complete game manifest with all content and metadata."""
    try:
        manifest = db.query(GameManifest).filter(
            and_(
                GameManifest.id == game_id,
                GameManifest.tenant_id == tenant_id
            )
        ).first()
        
        if not manifest:
            raise HTTPException(status_code=404, detail="Game manifest not found")
        
        # Check if manifest has expired
        if manifest.expires_at and manifest.expires_at < datetime.now(timezone.utc):
            raise HTTPException(status_code=410, detail="Game manifest has expired")
        
        return GameManifestResponse.from_orm(manifest)
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error retrieving game manifest: {str(e)}")
        raise HTTPException(status_code=500, detail="Failed to retrieve game manifest")


@router.get("/",
            response_model=GameListResponse,
            summary="List Games",
            description="List games with filtering and pagination support.")
async def list_games(
    learner_id: Optional[uuid.UUID] = Query(None, description="Filter by learner ID"),
    game_type: Optional[GameType] = Query(None, description="Filter by game type"),
    subject_area: Optional[SubjectArea] = Query(None, description="Filter by subject"),
    status: Optional[GameStatus] = Query(None, description="Filter by status"),
    grade_band: Optional[GradeBand] = Query(None, description="Filter by grade band"),
    created_after: Optional[datetime] = Query(None, description="Filter by creation date"),
    limit: int = Query(50, ge=1, le=100, description="Number of results per page"),
    offset: int = Query(0, ge=0, description="Results offset for pagination"),
    db: Session = Depends(get_db),
    tenant_id: uuid.UUID = Depends(get_tenant_id)
):
    """List games with filtering and pagination."""
    try:
        # Build query
        query = db.query(GameManifest).filter(GameManifest.tenant_id == tenant_id)
        
        # Apply filters
        if learner_id:
            query = query.filter(GameManifest.learner_id == learner_id)
        if game_type:
            query = query.filter(GameManifest.game_type == game_type)
        if subject_area:
            query = query.filter(GameManifest.subject_area == subject_area)
        if status:
            query = query.filter(GameManifest.status == status)
        if grade_band:
            query = query.filter(GameManifest.grade_band == grade_band)
        if created_after:
            query = query.filter(GameManifest.created_at >= created_after)
        
        # Get total count
        total_count = query.count()
        
        # Apply pagination and ordering
        games = query.order_by(desc(GameManifest.created_at)).offset(offset).limit(limit).all()
        
        return GameListResponse(
            games=[GameManifestResponse.from_orm(game) for game in games],
            total_count=total_count,
            page_size=limit,
            page_offset=offset,
            has_more=offset + limit < total_count
        )
        
    except Exception as e:
        logger.error(f"Error listing games: {str(e)}")
        raise HTTPException(status_code=500, detail="Failed to list games")


@router.post("/sessions",
             response_model=GameSessionResponse,
             summary="Start Game Session",
             description="Start a new game session for a specific game manifest.")
async def start_game_session(
    request: GameSessionCreate,
    db: Session = Depends(get_db),
    tenant_id: uuid.UUID = Depends(get_tenant_id)
):
    """Start a new game session."""
    try:
        # Verify game manifest exists and is ready
        manifest = db.query(GameManifest).filter(
            and_(
                GameManifest.id == request.game_manifest_id,
                GameManifest.tenant_id == tenant_id,
                GameManifest.status == GameStatus.READY
            )
        ).first()
        
        if not manifest:
            raise HTTPException(
                status_code=404, 
                detail="Game manifest not found or not ready"
            )
        
        # Check if manifest has expired
        if manifest.expires_at and manifest.expires_at < datetime.now(timezone.utc):
            raise HTTPException(status_code=410, detail="Game manifest has expired")
        
        # Create game session
        session = GameSession(
            tenant_id=tenant_id,
            learner_id=request.learner_id,
            game_manifest_id=request.game_manifest_id,
            session_started_at=datetime.now(timezone.utc),
            session_status="active",
            progress_data=request.initial_progress or {},
            device_info=request.device_info or {}
        )
        
        db.add(session)
        db.commit()
        db.refresh(session)
        
        logger.info(f"Started game session {session.id} for learner {request.learner_id}")
        
        return GameSessionResponse.from_orm(session)
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error starting game session: {str(e)}")
        raise HTTPException(status_code=500, detail="Failed to start game session")


@router.put("/sessions/{session_id}",
            response_model=GameSessionResponse,
            summary="Update Game Session",
            description="Update game session progress and status.")
async def update_game_session(
    session_id: uuid.UUID,
    request: GameSessionUpdate,
    db: Session = Depends(get_db),
    engine: GameGenerationEngine = Depends(get_game_engine),
    tenant_id: uuid.UUID = Depends(get_tenant_id)
):
    """Update game session progress and status."""
    try:
        # Get session
        session = db.query(GameSession).filter(
            and_(
                GameSession.id == session_id,
                GameSession.tenant_id == tenant_id
            )
        ).first()
        
        if not session:
            raise HTTPException(status_code=404, detail="Game session not found")
        
        # Update session fields
        if request.progress_percentage is not None:
            session.progress_percentage = request.progress_percentage
        if request.score is not None:
            session.score = request.score
        if request.progress_data:
            session.progress_data = {**session.progress_data, **request.progress_data}
        if request.engagement_metrics:
            session.engagement_metrics = {**session.engagement_metrics, **request.engagement_metrics}
        if request.performance_data:
            session.performance_data = {**session.performance_data, **request.performance_data}
        if request.completion_reason:
            session.completion_reason = request.completion_reason
        if request.learner_satisfaction is not None:
            session.learner_satisfaction = request.learner_satisfaction
        if request.session_notes:
            session.session_notes = request.session_notes
        
        # Calculate engagement score
        if request.engagement_metrics:
            session.engagement_score = _calculate_engagement_score(request.engagement_metrics)
        
        session.updated_at = datetime.now(timezone.utc)
        
        # If session is being marked as completed, handle completion
        if (request.progress_percentage and request.progress_percentage >= 100) or \
           (request.completion_reason in ["completed", "finished"]):
            await engine.complete_game_session(session, db)
        
        db.commit()
        db.refresh(session)
        
        return GameSessionResponse.from_orm(session)
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error updating game session: {str(e)}")
        raise HTTPException(status_code=500, detail="Failed to update game session")


@router.post("/sessions/{session_id}/complete",
             response_model=GameSessionResponse,
             summary="Complete Game Session",
             description="Mark a game session as completed and emit completion event.")
async def complete_game_session(
    session_id: uuid.UUID,
    request: GameCompletionRequest,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db),
    engine: GameGenerationEngine = Depends(get_game_engine),
    tenant_id: uuid.UUID = Depends(get_tenant_id)
):
    """Complete a game session and emit GAME_COMPLETED event."""
    try:
        # Get session
        session = db.query(GameSession).filter(
            and_(
                GameSession.id == session_id,
                GameSession.tenant_id == tenant_id
            )
        ).first()
        
        if not session:
            raise HTTPException(status_code=404, detail="Game session not found")
        
        # Update completion data
        session.completion_reason = request.completion_reason
        session.learner_satisfaction = request.satisfaction
        session.session_notes = request.notes
        if request.final_score is not None:
            session.score = request.final_score
        
        # Complete the session
        await engine.complete_game_session(session, db)
        
        return GameSessionResponse.from_orm(session)
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error completing game session: {str(e)}")
        raise HTTPException(status_code=500, detail="Failed to complete game session")


@router.get("/sessions/{session_id}",
            response_model=GameSessionResponse,
            summary="Get Game Session",
            description="Retrieve game session details and progress.")
async def get_game_session(
    session_id: uuid.UUID,
    db: Session = Depends(get_db),
    tenant_id: uuid.UUID = Depends(get_tenant_id)
):
    """Get game session details."""
    try:
        session = db.query(GameSession).filter(
            and_(
                GameSession.id == session_id,
                GameSession.tenant_id == tenant_id
            )
        ).first()
        
        if not session:
            raise HTTPException(status_code=404, detail="Game session not found")
        
        return GameSessionResponse.from_orm(session)
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error retrieving game session: {str(e)}")
        raise HTTPException(status_code=500, detail="Failed to retrieve game session")


@router.post("/profiles",
             response_model=LearnerProfileResponse,
             summary="Create Learner Profile",
             description="Create or update a learner's gaming profile for personalization.")
async def create_learner_profile(
    request: LearnerProfileRequest,
    db: Session = Depends(get_db),
    tenant_id: uuid.UUID = Depends(get_tenant_id)
):
    """Create or update learner profile."""
    try:
        # Check if profile already exists
        existing_profile = db.query(LearnerProfile).filter(
            and_(
                LearnerProfile.learner_id == request.learner_id,
                LearnerProfile.tenant_id == tenant_id
            )
        ).first()
        
        if existing_profile:
            # Update existing profile
            for field, value in request.dict(exclude_unset=True).items():
                if field != "learner_id" and hasattr(existing_profile, field):
                    setattr(existing_profile, field, value)
            
            existing_profile.updated_at = datetime.now(timezone.utc)
            db.commit()
            db.refresh(existing_profile)
            
            return LearnerProfileResponse.from_orm(existing_profile)
        else:
            # Create new profile
            profile = LearnerProfile(
                tenant_id=tenant_id,
                **request.dict()
            )
            
            db.add(profile)
            db.commit()
            db.refresh(profile)
            
            logger.info(f"Created learner profile for {request.learner_id}")
            
            return LearnerProfileResponse.from_orm(profile)
        
    except Exception as e:
        logger.error(f"Error managing learner profile: {str(e)}")
        raise HTTPException(status_code=500, detail="Failed to manage learner profile")


@router.get("/profiles/{learner_id}",
            response_model=LearnerProfileResponse,
            summary="Get Learner Profile",
            description="Retrieve a learner's gaming profile and preferences.")
async def get_learner_profile(
    learner_id: uuid.UUID,
    db: Session = Depends(get_db),
    tenant_id: uuid.UUID = Depends(get_tenant_id)
):
    """Get learner profile."""
    try:
        profile = db.query(LearnerProfile).filter(
            and_(
                LearnerProfile.learner_id == learner_id,
                LearnerProfile.tenant_id == tenant_id
            )
        ).first()
        
        if not profile:
            raise HTTPException(status_code=404, detail="Learner profile not found")
        
        return LearnerProfileResponse.from_orm(profile)
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error retrieving learner profile: {str(e)}")
        raise HTTPException(status_code=500, detail="Failed to retrieve learner profile")


@router.get("/analytics/{learner_id}",
            response_model=GameAnalyticsResponse,
            summary="Get Game Analytics",
            description="Get comprehensive game analytics and learning insights for a learner.")
async def get_game_analytics(
    learner_id: uuid.UUID,
    days: int = Query(30, ge=1, le=365, description="Number of days to analyze"),
    include_recommendations: bool = Query(True, description="Include AI-generated recommendations"),
    db: Session = Depends(get_db),
    tenant_id: uuid.UUID = Depends(get_tenant_id)
):
    """Get comprehensive game analytics for a learner."""
    try:
        # Get or create analytics record
        analytics = db.query(GameAnalytics).filter(
            and_(
                GameAnalytics.learner_id == learner_id,
                GameAnalytics.tenant_id == tenant_id
            )
        ).first()
        
        if not analytics:
            # Create analytics record
            analytics = GameAnalytics(
                tenant_id=tenant_id,
                learner_id=learner_id,
                total_games_played=0,
                total_time_played_minutes=0.0,
                average_completion_rate=0.0,
                favorite_game_types=[],
                performance_trends={},
                learning_insights={},
                improvement_suggestions=[]
            )
            db.add(analytics)
            db.commit()
            db.refresh(analytics)
        
        # Update analytics with recent data
        await _update_analytics_data(analytics, learner_id, tenant_id, days, db)
        
        return GameAnalyticsResponse.from_orm(analytics)
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error retrieving game analytics: {str(e)}")
        raise HTTPException(status_code=500, detail="Failed to retrieve game analytics")


@router.post("/validate/manifest",
             response_model=ValidationResponse,
             summary="Validate Game Manifest",
             description="Validate a game manifest for completeness, correctness, and duration adherence.")
async def validate_game_manifest(
    game_id: uuid.UUID,
    db: Session = Depends(get_db),
    tenant_id: uuid.UUID = Depends(get_tenant_id)
):
    """Validate game manifest for compliance and quality."""
    try:
        manifest = db.query(GameManifest).filter(
            and_(
                GameManifest.id == game_id,
                GameManifest.tenant_id == tenant_id
            )
        ).first()
        
        if not manifest:
            raise HTTPException(status_code=404, detail="Game manifest not found")
        
        validation_result = _validate_manifest_structure(manifest)
        
        return ValidationResponse(
            is_valid=validation_result["is_valid"],
            validation_score=validation_result["score"],
            issues=validation_result["issues"],
            recommendations=validation_result["recommendations"],
            duration_compliance=validation_result["duration_compliance"]
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error validating manifest: {str(e)}")
        raise HTTPException(status_code=500, detail="Failed to validate manifest")


@router.get("/templates",
            response_model=List[GameTemplateResponse],
            summary="List Game Templates",
            description="List available game generation templates.")
async def list_game_templates(
    game_type: Optional[GameType] = Query(None, description="Filter by game type"),
    subject_area: Optional[SubjectArea] = Query(None, description="Filter by subject"),
    grade_band: Optional[GradeBand] = Query(None, description="Filter by grade band"),
    db: Session = Depends(get_db),
    tenant_id: uuid.UUID = Depends(get_tenant_id)
):
    """List available game templates."""
    try:
        query = db.query(GameTemplate).filter(GameTemplate.tenant_id == tenant_id)
        
        if game_type:
            query = query.filter(GameTemplate.game_type == game_type)
        if subject_area:
            query = query.filter(GameTemplate.subject_area == subject_area)
        if grade_band:
            query = query.filter(GameTemplate.grade_band == grade_band)
        
        templates = query.order_by(GameTemplate.template_name).all()
        
        return [GameTemplateResponse.from_orm(template) for template in templates]
        
    except Exception as e:
        logger.error(f"Error listing game templates: {str(e)}")
        raise HTTPException(status_code=500, detail="Failed to list game templates")


@router.get("/health",
            summary="Service Health Check",
            description="Check the health and status of the game generation service.")
async def health_check(
    engine: GameGenerationEngine = Depends(get_game_engine),
    db: Session = Depends(get_db)
):
    """Health check endpoint."""
    try:
        # Test database connection
        db.execute("SELECT 1")
        
        # Check if game engine is operational
        if not engine:
            raise Exception("Game engine not available")
        
        return {
            "status": "healthy",
            "service": "game-gen-svc",
            "version": "1.0.0",
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "database": "connected",
            "game_engine": "operational"
        }
        
    except Exception as e:
        logger.error(f"Health check failed: {str(e)}")
        return JSONResponse(
            status_code=503,
            content={
                "status": "unhealthy",
                "service": "game-gen-svc",
                "error": str(e),
                "timestamp": datetime.now(timezone.utc).isoformat()
            }
        )


# Helper functions

def _calculate_engagement_score(metrics: Dict[str, Any]) -> float:
    """Calculate engagement score from metrics."""
    score = 70.0  # Base score
    
    if "time_on_task" in metrics:
        # Higher time on task increases engagement (up to optimal point)
        time_ratio = min(metrics["time_on_task"] / 300, 1.0)  # 5 minutes optimal
        score += time_ratio * 15
    
    if "interaction_frequency" in metrics:
        # More interactions suggest higher engagement
        interaction_score = min(metrics["interaction_frequency"] / 10, 1.0)
        score += interaction_score * 10
    
    if "completion_attempts" in metrics:
        # Reasonable number of attempts suggests persistence
        attempts = metrics["completion_attempts"]
        if attempts <= 3:
            score += 5
        elif attempts > 5:
            score -= 5
    
    return min(max(score, 0), 100)


async def _update_analytics_data(
    analytics: GameAnalytics, 
    learner_id: uuid.UUID, 
    tenant_id: uuid.UUID,
    days: int,
    db: Session
):
    """Update analytics with recent data."""
    try:
        # Get recent sessions
        cutoff_date = datetime.now(timezone.utc) - timedelta(days=days)
        
        recent_sessions = db.query(GameSession).filter(
            and_(
                GameSession.learner_id == learner_id,
                GameSession.tenant_id == tenant_id,
                GameSession.session_started_at >= cutoff_date
            )
        ).all()
        
        if not recent_sessions:
            return
        
        # Calculate updated metrics
        total_games = len(recent_sessions)
        completed_games = len([s for s in recent_sessions if s.session_status == "completed"])
        total_time = sum(s.actual_duration_minutes or 0 for s in recent_sessions)
        
        # Update analytics
        analytics.total_games_played = total_games
        analytics.total_time_played_minutes = total_time
        analytics.average_completion_rate = (completed_games / total_games) * 100 if total_games > 0 else 0
        
        # Calculate favorite game types
        game_type_counts = {}
        for session in recent_sessions:
            manifest = db.query(GameManifest).filter(
                GameManifest.id == session.game_manifest_id
            ).first()
            if manifest:
                game_type = manifest.game_type.value
                game_type_counts[game_type] = game_type_counts.get(game_type, 0) + 1
        
        analytics.favorite_game_types = sorted(
            game_type_counts.keys(), 
            key=game_type_counts.get, 
            reverse=True
        )[:3]  # Top 3
        
        # Simple performance trends
        analytics.performance_trends = {
            "average_score": sum(s.score or 0 for s in recent_sessions) / len(recent_sessions),
            "average_engagement": sum(s.engagement_score or 0 for s in recent_sessions) / len(recent_sessions),
            "completion_rate": analytics.average_completion_rate
        }
        
        # Basic learning insights
        analytics.learning_insights = {
            "most_played_duration": _most_common_duration(recent_sessions),
            "preferred_subjects": _most_common_subjects(recent_sessions, db),
            "peak_performance_time": "Not calculated",  # Would need time-of-day data
            "improvement_areas": []
        }
        
        analytics.updated_at = datetime.now(timezone.utc)
        db.commit()
        
    except Exception as e:
        logger.error(f"Error updating analytics data: {str(e)}")


def _most_common_duration(sessions: List[GameSession]) -> str:
    """Find most common game duration."""
    duration_ranges = {"short": 0, "medium": 0, "long": 0}
    
    for session in sessions:
        if session.actual_duration_minutes:
            if session.actual_duration_minutes < 10:
                duration_ranges["short"] += 1
            elif session.actual_duration_minutes < 20:
                duration_ranges["medium"] += 1
            else:
                duration_ranges["long"] += 1
    
    return max(duration_ranges, key=duration_ranges.get)


def _most_common_subjects(sessions: List[GameSession], db: Session) -> List[str]:
    """Find most common subjects played."""
    subject_counts = {}
    
    for session in sessions:
        manifest = db.query(GameManifest).filter(
            GameManifest.id == session.game_manifest_id
        ).first()
        if manifest:
            subject = manifest.subject_area.value
            subject_counts[subject] = subject_counts.get(subject, 0) + 1
    
    return sorted(subject_counts.keys(), key=subject_counts.get, reverse=True)[:3]


def _validate_manifest_structure(manifest: GameManifest) -> Dict[str, Any]:
    """Validate game manifest structure and content."""
    issues = []
    recommendations = []
    score = 100.0
    
    # Check required fields
    if not manifest.game_title or len(manifest.game_title.strip()) < 3:
        issues.append("Game title is missing or too short")
        score -= 20
    
    if not manifest.game_scenes:
        issues.append("No game scenes defined")
        score -= 30
    else:
        # Validate scenes
        total_scene_duration = 0
        for scene_data in manifest.game_scenes:
            if "duration_minutes" in scene_data:
                total_scene_duration += scene_data["duration_minutes"]
            
            if not scene_data.get("content"):
                issues.append(f"Scene {scene_data.get('scene_id', 'unknown')} missing content")
                score -= 10
    
    # Check duration compliance
    duration_compliance = {
        "target_duration": manifest.target_duration_minutes,
        "estimated_duration": manifest.estimated_duration_minutes,
        "within_tolerance": True,
        "deviation_percentage": 0.0
    }
    
    if manifest.estimated_duration_minutes and manifest.target_duration_minutes:
        deviation = abs(manifest.estimated_duration_minutes - manifest.target_duration_minutes)
        deviation_pct = (deviation / manifest.target_duration_minutes) * 100
        
        duration_compliance["deviation_percentage"] = deviation_pct
        
        if deviation_pct > 20:  # More than 20% deviation
            duration_compliance["within_tolerance"] = False
            issues.append(f"Duration deviation too high: {deviation_pct:.1f}%")
            score -= 15
        elif deviation_pct > 10:  # 10-20% deviation
            recommendations.append("Consider adjusting content to better match target duration")
            score -= 5
    
    # Check content quality
    if not manifest.game_assets:
        recommendations.append("Consider adding visual or audio assets to improve engagement")
        score -= 10
    
    if not manifest.expected_learning_outcomes:
        recommendations.append("Define clear learning outcomes for better educational value")
        score -= 5
    
    return {
        "is_valid": len(issues) == 0,
        "score": max(score, 0),
        "issues": issues,
        "recommendations": recommendations,
        "duration_compliance": duration_compliance
    }
