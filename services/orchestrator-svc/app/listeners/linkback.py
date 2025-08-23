"""
Orchestrator Event Listener for S5-10 Coursework→Lesson Linkback

Listens for COURSEWORK_LINKED events from lesson-registry-svc and
emits PROGRESS_UPDATED events to coordinate progress tracking.
"""

import asyncio
import logging
from datetime import datetime
from typing import Dict, Any
from uuid import UUID

from ..events import EventListener, emit_event
from ..config import get_settings

logger = logging.getLogger(__name__)
settings = get_settings()


@EventListener("COURSEWORK_LINKED")
async def handle_coursework_linked(event_data: Dict[str, Any]):
    """
    Handle COURSEWORK_LINKED events from lesson-registry-svc.
    
    Emits PROGRESS_UPDATED events to notify analytics and other services
    that new progress tracking has been established.
    """
    try:
        coursework_id = event_data.get("coursework_id")
        lesson_id = event_data.get("lesson_id")
        learner_id = event_data.get("learner_id")
        link_id = event_data.get("link_id")
        created_by = event_data.get("created_by")
        
        logger.info(f"Processing COURSEWORK_LINKED event: {coursework_id} → {lesson_id}")
        
        # Validate required fields
        if not all([coursework_id, lesson_id, link_id]):
            logger.error("Missing required fields in COURSEWORK_LINKED event")
            return
        
        # Emit PROGRESS_UPDATED event for analytics and other services
        progress_event = {
            "type": "coursework_linked",
            "coursework_id": coursework_id,
            "lesson_id": lesson_id,
            "learner_id": learner_id,
            "link_id": link_id,
            "created_by": created_by,
            "timestamp": datetime.utcnow().isoformat(),
            "source_service": "lesson-registry-svc",
            "event_version": "1.0"
        }
        
        # Emit to analytics service for progress tracking setup
        await emit_event("PROGRESS_UPDATED", progress_event, target_service="analytics-svc")
        
        # Emit to learner service for recommendation updates
        await emit_event("LEARNER_LINKBACK_CREATED", progress_event, target_service="learner-svc")
        
        # Emit to notification service for teacher/guardian alerts
        if learner_id:
            notification_event = {
                **progress_event,
                "notification_type": "linkback_created",
                "message": f"Coursework has been linked to lesson for progress tracking"
            }
            await emit_event("NOTIFICATION_REQUESTED", notification_event, target_service="notification-svc")
        
        logger.info(f"Successfully processed COURSEWORK_LINKED event {link_id}")
        
    except Exception as e:
        logger.error(f"Failed to process COURSEWORK_LINKED event: {e}")


@EventListener("COURSEWORK_UNLINKED") 
async def handle_coursework_unlinked(event_data: Dict[str, Any]):
    """
    Handle COURSEWORK_UNLINKED events from lesson-registry-svc.
    
    Emits events to clean up progress tracking and notify relevant services.
    """
    try:
        coursework_id = event_data.get("coursework_id")
        lesson_id = event_data.get("lesson_id")
        learner_id = event_data.get("learner_id") 
        link_id = event_data.get("link_id")
        deleted_by = event_data.get("deleted_by")
        
        logger.info(f"Processing COURSEWORK_UNLINKED event: {coursework_id} ↛ {lesson_id}")
        
        # Emit progress cleanup event
        cleanup_event = {
            "type": "coursework_unlinked",
            "coursework_id": coursework_id,
            "lesson_id": lesson_id,
            "learner_id": learner_id,
            "link_id": link_id,
            "deleted_by": deleted_by,
            "timestamp": datetime.utcnow().isoformat(),
            "source_service": "lesson-registry-svc",
            "event_version": "1.0"
        }
        
        # Notify analytics service to clean up progress tracking
        await emit_event("PROGRESS_TRACKING_REMOVED", cleanup_event, target_service="analytics-svc")
        
        # Notify learner service to update recommendations
        await emit_event("LEARNER_LINKBACK_REMOVED", cleanup_event, target_service="learner-svc")
        
        logger.info(f"Successfully processed COURSEWORK_UNLINKED event {link_id}")
        
    except Exception as e:
        logger.error(f"Failed to process COURSEWORK_UNLINKED event: {e}")


@EventListener("COURSEWORK_COMPLETED")
async def handle_coursework_completed(event_data: Dict[str, Any]):
    """
    Handle COURSEWORK_COMPLETED events and trigger progress updates.
    
    When coursework is completed, check for linked lessons and update
    their progress/mastery based on the completion data.
    """
    try:
        coursework_id = event_data.get("coursework_id")
        learner_id = event_data.get("learner_id")
        completion_score = event_data.get("score", 0.0)
        completion_time = event_data.get("completion_time")
        
        logger.info(f"Processing COURSEWORK_COMPLETED event: {coursework_id} by {learner_id}")
        
        # Emit event for analytics service to process linked lesson updates
        progress_update_event = {
            "type": "coursework_completed",
            "coursework_id": coursework_id,
            "learner_id": learner_id,
            "completion_score": completion_score,
            "completion_time": completion_time,
            "timestamp": datetime.utcnow().isoformat(),
            "source_service": "orchestrator",
            "event_version": "1.0"
        }
        
        # Analytics service will look up linked lessons and update mastery
        await emit_event("PROGRESS_UPDATED", progress_update_event, target_service="analytics-svc")
        
        # Notify orchestrator's own recommendation engine
        await emit_event("MASTERY_UPDATED", progress_update_event, target_service="orchestrator-svc")
        
        logger.info(f"Successfully processed COURSEWORK_COMPLETED event for {coursework_id}")
        
    except Exception as e:
        logger.error(f"Failed to process COURSEWORK_COMPLETED event: {e}")


# Health check for event listeners
async def linkback_listener_health_check() -> Dict[str, Any]:
    """Health check for linkback event listeners."""
    return {
        "status": "healthy",
        "listeners": [
            "COURSEWORK_LINKED",
            "COURSEWORK_UNLINKED", 
            "COURSEWORK_COMPLETED"
        ],
        "last_check": datetime.utcnow().isoformat(),
        "service": "orchestrator-linkback-listeners"
    }


# Register listeners on module import
logger.info("Registered S5-10 linkback event listeners: COURSEWORK_LINKED, COURSEWORK_UNLINKED, COURSEWORK_COMPLETED")
