"""
Analytics Service - Progress from Coursework Hooks (S5-10)

Hooks for merging coursework completion signals with lesson progress
to provide comprehensive mastery curve adjustments and analytics.
"""

import asyncio
import logging
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any
from uuid import UUID

import httpx
from sqlalchemy import text
from sqlalchemy.orm import Session

from ..database import get_db
from ..models import ProgressMetric, MasteryAggregate, PrivacyGuard
from ..orchestrator import EventListener, emit_event
from ..config import get_settings

logger = logging.getLogger(__name__)
settings = get_settings()


class CourseworkProgressHook:
    """
    Hook processor for integrating coursework completion signals
    with lesson progress analytics and mastery calculations.
    """
    
    def __init__(self):
        self.lesson_registry_client = httpx.AsyncClient(
            base_url=settings.LESSON_REGISTRY_URL,
            timeout=30.0
        )
    
    async def process_coursework_linked_event(self, event_data: Dict[str, Any]) -> bool:
        """
        Process COURSEWORK_LINKED events to establish progress tracking.
        
        Args:
            event_data: Event payload with coursework_id, lesson_id, etc.
            
        Returns:
            bool: True if processing succeeded
        """
        try:
            coursework_id = UUID(event_data.get("coursework_id"))
            lesson_id = UUID(event_data.get("lesson_id"))
            learner_id = event_data.get("learner_id")
            link_id = UUID(event_data.get("link_id"))
            mastery_weight = event_data.get("mastery_weight", 100)
            
            logger.info(f"Processing coursework link: {coursework_id} → {lesson_id}")
            
            # Validate lesson exists and get metadata
            lesson_data = await self._fetch_lesson_metadata(lesson_id)
            if not lesson_data:
                logger.error(f"Lesson {lesson_id} not found for coursework link")
                return False
            
            # Initialize progress tracking structures
            with next(get_db()) as db:
                await self._initialize_progress_tracking(
                    db, coursework_id, lesson_id, learner_id, 
                    mastery_weight, lesson_data
                )
                
                # Set up coursework completion monitoring
                await self._setup_completion_monitoring(
                    db, coursework_id, lesson_id, learner_id, link_id
                )
            
            # Emit progress updated event for orchestrator
            await emit_event("PROGRESS_UPDATED", {
                "type": "coursework_linked",
                "coursework_id": str(coursework_id),
                "lesson_id": str(lesson_id),
                "learner_id": learner_id,
                "link_id": str(link_id),
                "timestamp": datetime.utcnow().isoformat()
            })
            
            return True
            
        except Exception as e:
            logger.error(f"Failed to process coursework linked event: {e}")
            return False
    
    async def process_coursework_completion(self, completion_data: Dict[str, Any]) -> bool:
        """
        Process coursework completion signals to update mastery curves.
        
        Args:
            completion_data: Completion event with scores, timing, etc.
            
        Returns:
            bool: True if mastery update succeeded
        """
        try:
            coursework_id = UUID(completion_data.get("coursework_id"))
            learner_id = UUID(completion_data.get("learner_id"))
            completion_score = completion_data.get("score", 0.0)
            completion_time = completion_data.get("completion_time")
            
            logger.info(f"Processing coursework completion: {coursework_id} for learner {learner_id}")
            
            with next(get_db()) as db:
                # Find linked lessons for this coursework
                linked_lessons = await self._get_linked_lessons(db, coursework_id, learner_id)
                
                if not linked_lessons:
                    logger.warning(f"No lesson links found for coursework {coursework_id}")
                    return True
                
                # Update mastery for each linked lesson
                for lesson_link in linked_lessons:
                    await self._update_lesson_mastery(
                        db, lesson_link, completion_score, completion_time
                    )
                
                # Trigger mastery curve recalculation
                await self._recalculate_mastery_curves(db, learner_id, linked_lessons)
            
            return True
            
        except Exception as e:
            logger.error(f"Failed to process coursework completion: {e}")
            return False
    
    async def _fetch_lesson_metadata(self, lesson_id: UUID) -> Optional[Dict[str, Any]]:
        """Fetch lesson metadata from lesson registry service."""
        try:
            response = await self.lesson_registry_client.get(f"/lessons/{lesson_id}")
            if response.status_code == 200:
                return response.json()
            return None
        except Exception as e:
            logger.error(f"Failed to fetch lesson {lesson_id}: {e}")
            return None
    
    async def _initialize_progress_tracking(
        self, 
        db: Session, 
        coursework_id: UUID, 
        lesson_id: UUID,
        learner_id: Optional[str],
        mastery_weight: int,
        lesson_data: Dict[str, Any]
    ):
        """Initialize progress tracking structures for coursework-lesson link."""
        
        # Create progress metric entry for coursework → lesson mapping
        progress_metric = ProgressMetric(
            learner_id=learner_id,
            lesson_id=lesson_id,
            metric_type="coursework_linked",
            metric_value=0.0,  # Will be updated on completion
            metadata={
                "coursework_id": str(coursework_id),
                "mastery_weight": mastery_weight,
                "lesson_subject": lesson_data.get("subject"),
                "lesson_difficulty": lesson_data.get("difficulty_level", 0)
            },
            tenant_id=lesson_data.get("tenant_id"),
            created_at=datetime.utcnow()
        )
        
        db.add(progress_metric)
        
        # Initialize mastery aggregate if needed
        existing_mastery = db.query(MasteryAggregate).filter(
            MasteryAggregate.learner_id == learner_id,
            MasteryAggregate.lesson_id == lesson_id
        ).first()
        
        if not existing_mastery:
            mastery_aggregate = MasteryAggregate(
                learner_id=learner_id,
                lesson_id=lesson_id,
                subject=lesson_data.get("subject"),
                current_mastery=0.0,
                coursework_contributions=0,
                total_attempts=0,
                metadata={"coursework_links": [str(coursework_id)]},
                tenant_id=lesson_data.get("tenant_id"),
                updated_at=datetime.utcnow()
            )
            db.add(mastery_aggregate)
        else:
            # Add coursework link to existing aggregate
            coursework_links = existing_mastery.metadata.get("coursework_links", [])
            if str(coursework_id) not in coursework_links:
                coursework_links.append(str(coursework_id))
                existing_mastery.metadata["coursework_links"] = coursework_links
                existing_mastery.updated_at = datetime.utcnow()
        
        db.commit()
    
    async def _setup_completion_monitoring(
        self,
        db: Session,
        coursework_id: UUID,
        lesson_id: UUID,
        learner_id: Optional[str],
        link_id: UUID
    ):
        """Set up monitoring for coursework completion events."""
        
        # Register completion webhook/listener
        monitor_config = {
            "coursework_id": str(coursework_id),
            "lesson_id": str(lesson_id),
            "learner_id": learner_id,
            "link_id": str(link_id),
            "monitor_type": "completion",
            "created_at": datetime.utcnow().isoformat()
        }
        
        # Store monitoring configuration
        db.execute(
            text("""
                INSERT INTO coursework_monitors 
                (id, coursework_id, lesson_id, learner_id, config, created_at)
                VALUES (gen_random_uuid(), :coursework_id, :lesson_id, :learner_id, :config, NOW())
                ON CONFLICT (coursework_id, lesson_id, learner_id) 
                DO UPDATE SET config = :config, updated_at = NOW()
            """),
            {
                "coursework_id": str(coursework_id),
                "lesson_id": str(lesson_id),
                "learner_id": learner_id,
                "config": str(monitor_config)
            }
        )
        db.commit()
    
    async def _get_linked_lessons(
        self, 
        db: Session, 
        coursework_id: UUID, 
        learner_id: UUID
    ) -> List[Dict[str, Any]]:
        """Get all lessons linked to a coursework item for a learner."""
        
        # Query linked lessons through lesson registry service
        try:
            response = await self.lesson_registry_client.get(
                f"/linkback/coursework/{coursework_id}/links",
                params={"learner_id": str(learner_id) if learner_id else None}
            )
            
            if response.status_code == 200:
                return response.json().get("links", [])
            return []
            
        except Exception as e:
            logger.error(f"Failed to fetch linked lessons: {e}")
            return []
    
    async def _update_lesson_mastery(
        self,
        db: Session,
        lesson_link: Dict[str, Any],
        completion_score: float,
        completion_time: Optional[str]
    ):
        """Update lesson mastery based on coursework completion."""
        
        lesson_id = lesson_link["lesson_id"]
        learner_id = lesson_link.get("learner_id")
        mastery_weight = lesson_link.get("mastery_weight", 100)
        difficulty_adjustment = lesson_link.get("difficulty_adjustment", 0)
        
        # Calculate adjusted score
        adjusted_score = completion_score * (mastery_weight / 100.0)
        if difficulty_adjustment != 0:
            adjusted_score *= (1.0 + difficulty_adjustment / 100.0)
        
        # Update progress metric
        db.execute(
            text("""
                UPDATE progress_metrics 
                SET metric_value = :score,
                    completion_time = :completion_time,
                    updated_at = NOW()
                WHERE learner_id = :learner_id 
                AND lesson_id = :lesson_id 
                AND metric_type = 'coursework_linked'
                AND metadata->>'coursework_id' = :coursework_id
            """),
            {
                "score": adjusted_score,
                "completion_time": completion_time,
                "learner_id": learner_id,
                "lesson_id": lesson_id,
                "coursework_id": lesson_link["coursework_id"]
            }
        )
        
        # Update mastery aggregate
        db.execute(
            text("""
                UPDATE mastery_aggregates 
                SET coursework_contributions = coursework_contributions + 1,
                    current_mastery = LEAST(100.0, current_mastery + :score_contribution),
                    updated_at = NOW()
                WHERE learner_id = :learner_id AND lesson_id = :lesson_id
            """),
            {
                "score_contribution": adjusted_score * 0.1,  # Scale contribution
                "learner_id": learner_id,
                "lesson_id": lesson_id
            }
        )
        
        db.commit()
        logger.info(f"Updated mastery for lesson {lesson_id}: +{adjusted_score}")
    
    async def _recalculate_mastery_curves(
        self,
        db: Session,
        learner_id: UUID,
        linked_lessons: List[Dict[str, Any]]
    ):
        """Recalculate mastery curves with coursework contributions."""
        
        for lesson_link in linked_lessons:
            lesson_id = lesson_link["lesson_id"]
            
            # Aggregate all progress signals for this lesson
            result = db.execute(
                text("""
                    SELECT 
                        AVG(metric_value) as avg_score,
                        COUNT(*) as total_activities,
                        MAX(updated_at) as last_activity
                    FROM progress_metrics 
                    WHERE learner_id = :learner_id AND lesson_id = :lesson_id
                """),
                {"learner_id": str(learner_id), "lesson_id": lesson_id}
            ).fetchone()
            
            if result and result.avg_score is not None:
                # Update mastery curve with integrated signals
                db.execute(
                    text("""
                        UPDATE mastery_aggregates 
                        SET current_mastery = LEAST(100.0, :mastery_score),
                            total_attempts = :total_activities,
                            last_activity_at = :last_activity,
                            updated_at = NOW()
                        WHERE learner_id = :learner_id AND lesson_id = :lesson_id
                    """),
                    {
                        "mastery_score": result.avg_score,
                        "total_activities": result.total_activities,
                        "last_activity": result.last_activity,
                        "learner_id": str(learner_id),
                        "lesson_id": lesson_id
                    }
                )
        
        db.commit()
        logger.info(f"Recalculated mastery curves for learner {learner_id}")


# Initialize the hook processor
coursework_hook = CourseworkProgressHook()


# Event listener registration for orchestrator
@EventListener("COURSEWORK_LINKED")
async def handle_coursework_linked(event_data: Dict[str, Any]):
    """Handle COURSEWORK_LINKED events from lesson registry."""
    await coursework_hook.process_coursework_linked_event(event_data)


@EventListener("COURSEWORK_COMPLETED") 
async def handle_coursework_completed(event_data: Dict[str, Any]):
    """Handle COURSEWORK_COMPLETED events from coursework services."""
    await coursework_hook.process_coursework_completion(event_data)


# Direct API for manual progress updates
async def update_coursework_progress(
    coursework_id: UUID,
    learner_id: UUID,
    completion_data: Dict[str, Any]
) -> bool:
    """
    Manually update coursework progress for linked lessons.
    
    Args:
        coursework_id: UUID of completed coursework
        learner_id: UUID of the learner
        completion_data: Completion metrics and metadata
        
    Returns:
        bool: True if update succeeded
    """
    return await coursework_hook.process_coursework_completion({
        "coursework_id": str(coursework_id),
        "learner_id": str(learner_id),
        **completion_data
    })


# Analytics query functions
async def get_coursework_progress_analytics(
    learner_id: Optional[UUID] = None,
    lesson_id: Optional[UUID] = None,
    days_back: int = 30
) -> Dict[str, Any]:
    """
    Get analytics for coursework-lesson progress integration.
    
    Args:
        learner_id: Optional learner filter
        lesson_id: Optional lesson filter  
        days_back: Days of history to include
        
    Returns:
        Dict with progress analytics
    """
    with next(get_db()) as db:
        since_date = datetime.utcnow() - timedelta(days=days_back)
        
        # Base query filters
        filters = ["created_at >= :since_date", "metric_type = 'coursework_linked'"]
        params = {"since_date": since_date}
        
        if learner_id:
            filters.append("learner_id = :learner_id")
            params["learner_id"] = str(learner_id)
            
        if lesson_id:
            filters.append("lesson_id = :lesson_id")
            params["lesson_id"] = str(lesson_id)
        
        where_clause = " AND ".join(filters)
        
        # Get progress metrics
        result = db.execute(
            text(f"""
                SELECT 
                    COUNT(*) as total_completions,
                    AVG(metric_value) as avg_score,
                    COUNT(DISTINCT learner_id) as unique_learners,
                    COUNT(DISTINCT lesson_id) as unique_lessons,
                    COUNT(DISTINCT metadata->>'coursework_id') as unique_coursework
                FROM progress_metrics 
                WHERE {where_clause}
            """),
            params
        ).fetchone()
        
        return {
            "total_completions": result.total_completions or 0,
            "average_score": float(result.avg_score or 0),
            "unique_learners": result.unique_learners or 0,
            "unique_lessons": result.unique_lessons or 0,
            "unique_coursework": result.unique_coursework or 0,
            "period_days": days_back,
            "generated_at": datetime.utcnow().isoformat()
        }
