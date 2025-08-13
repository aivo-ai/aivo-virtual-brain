"""
AIVO Orchestrator Service - Event Consumer
S1-14 Implementation

Consumes educational events from various services and triggers orchestration logic.
"""

import json
import logging
import asyncio
from typing import Dict, List, Any, Optional
from datetime import datetime, timedelta
from dataclasses import dataclass, asdict
from enum import Enum

import redis.asyncio as redis
import httpx
from pydantic import BaseModel, Field

logger = logging.getLogger(__name__)


class EventType(str, Enum):
    """Supported input event types"""
    BASELINE_COMPLETE = "BASELINE_COMPLETE"
    SLP_UPDATED = "SLP_UPDATED"
    SEL_ALERT = "SEL_ALERT"
    COURSEWORK_ANALYZED = "COURSEWORK_ANALYZED"
    
    # Additional event types for comprehensive orchestration
    ASSESSMENT_COMPLETE = "ASSESSMENT_COMPLETE"
    IEP_UPDATED = "IEP_UPDATED"
    LEARNER_PROGRESS = "LEARNER_PROGRESS"
    ENGAGEMENT_LOW = "ENGAGEMENT_LOW"
    ACHIEVEMENT_MILESTONE = "ACHIEVEMENT_MILESTONE"


class ActionType(str, Enum):
    """Output action types"""
    LEVEL_SUGGESTED = "LEVEL_SUGGESTED"
    GAME_BREAK = "GAME_BREAK"
    SEL_INTERVENTION = "SEL_INTERVENTION"
    LEARNING_PATH_UPDATE = "LEARNING_PATH_UPDATE"
    ACHIEVEMENT_CELEBRATION = "ACHIEVEMENT_CELEBRATION"


@dataclass
class Event:
    """Event data structure"""
    id: str
    type: EventType
    source_service: str
    tenant_id: str
    learner_id: str
    timestamp: datetime
    data: Dict[str, Any]
    correlation_id: Optional[str] = None
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'Event':
        """Create Event from dictionary"""
        return cls(
            id=data.get("id", ""),
            type=EventType(data.get("type", "")),
            source_service=data.get("source_service", ""),
            tenant_id=data.get("tenant_id", ""),
            learner_id=data.get("learner_id", ""),
            timestamp=datetime.fromisoformat(data.get("timestamp", datetime.utcnow().isoformat())),
            data=data.get("data", {}),
            correlation_id=data.get("correlation_id")
        )


@dataclass
class OrchestrationAction:
    """Orchestration action result"""
    id: str
    type: ActionType
    target_service: str
    learner_id: str
    tenant_id: str
    action_data: Dict[str, Any]
    scheduled_time: Optional[datetime] = None
    created_at: datetime = None
    
    def __post_init__(self):
        if self.created_at is None:
            self.created_at = datetime.utcnow()


class EventConsumerConfig(BaseModel):
    """Event consumer configuration"""
    redis_url: str = "redis://localhost:6379"
    event_channels: List[str] = Field(default_factory=lambda: [
        "aivo.events.baseline",
        "aivo.events.slp",
        "aivo.events.sel",
        "aivo.events.coursework",
        "aivo.events.assessment",
        "aivo.events.learner"
    ])
    consumer_group: str = "orchestrator-consumer-group"
    consumer_name: str = "orchestrator-consumer-1"
    batch_size: int = 10
    poll_timeout: float = 1.0
    max_retry_attempts: int = 3
    
    # Service endpoints for actions
    learner_service_url: str = "http://learner-svc:8001"
    notification_service_url: str = "http://notification-svc:8003"
    
    class Config:
        env_prefix = "ORCHESTRATOR_"


class EventConsumer:
    """Redis-based event consumer with orchestration logic"""
    
    def __init__(self, orchestration_engine):
        self.config = EventConsumerConfig()
        self.orchestration_engine = orchestration_engine
        self.redis_client: Optional[redis.Redis] = None
        self.is_running = False
        
        # Statistics tracking
        self.stats = {
            "total_events_processed": 0,
            "events_by_type": {},
            "processing_errors": 0,
            "last_event_time": None,
            "start_time": datetime.utcnow()
        }
        
    async def initialize(self):
        """Initialize Redis connection and consumer groups"""
        try:
            self.redis_client = redis.from_url(self.config.redis_url)
            
            # Test connection
            await self.redis_client.ping()
            logger.info("Connected to Redis for event consumption")
            
            # Create consumer groups for each channel
            for channel in self.config.event_channels:
                try:
                    await self.redis_client.xgroup_create(
                        channel,
                        self.config.consumer_group,
                        id="0",
                        mkstream=True
                    )
                    logger.info(f"Created consumer group for channel: {channel}")
                except redis.ResponseError as e:
                    if "BUSYGROUP" not in str(e):
                        logger.warning(f"Failed to create consumer group for {channel}: {e}")
                        
        except Exception as e:
            logger.error(f"Failed to initialize event consumer: {e}")
            raise
            
    async def start_consuming(self):
        """Start consuming events from Redis streams"""
        if not self.redis_client:
            await self.initialize()
            
        self.is_running = True
        logger.info("Starting event consumption...")
        
        try:
            while self.is_running:
                await self._consume_batch()
                await asyncio.sleep(0.1)  # Small delay to prevent tight loop
                
        except asyncio.CancelledError:
            logger.info("Event consumption cancelled")
        except Exception as e:
            logger.error(f"Event consumption error: {e}")
            self.is_running = False
        finally:
            await self._cleanup()
            
    async def stop_consuming(self):
        """Stop event consumption"""
        logger.info("Stopping event consumption...")
        self.is_running = False
        
    async def _consume_batch(self):
        """Consume a batch of events from all channels"""
        try:
            # Read from multiple streams
            streams = {channel: ">" for channel in self.config.event_channels}
            
            messages = await self.redis_client.xreadgroup(
                self.config.consumer_group,
                self.config.consumer_name,
                streams,
                count=self.config.batch_size,
                block=int(self.config.poll_timeout * 1000)  # Convert to milliseconds
            )
            
            for channel, channel_messages in messages:
                for message_id, fields in channel_messages:
                    await self._process_message(channel.decode(), message_id.decode(), fields)
                    
        except redis.ResponseError as e:
            logger.error(f"Redis stream read error: {e}")
        except Exception as e:
            logger.error(f"Batch consumption error: {e}")
            
    async def _process_message(self, channel: str, message_id: str, fields: Dict[bytes, bytes]):
        """Process a single event message"""
        try:
            # Decode message fields
            decoded_fields = {
                k.decode(): v.decode() for k, v in fields.items()
            }
            
            # Parse event data
            event_data = json.loads(decoded_fields.get("data", "{}"))
            event = Event.from_dict(event_data)
            
            logger.info(f"Processing event {event.type} for learner {event.learner_id}")
            
            # Process through orchestration engine
            actions = await self.orchestration_engine.process_event(event)
            
            # Execute orchestration actions
            for action in actions:
                await self._execute_action(action)
                
            # Update statistics
            self._update_stats(event)
            
            # Acknowledge message
            await self.redis_client.xack(channel, self.config.consumer_group, message_id)
            
        except Exception as e:
            logger.error(f"Message processing error: {e}")
            self.stats["processing_errors"] += 1
            
            # For now, acknowledge failed messages to prevent infinite retry
            # In production, you might want to implement a dead letter queue
            try:
                await self.redis_client.xack(channel, self.config.consumer_group, message_id)
            except:
                pass
                
    async def _execute_action(self, action: OrchestrationAction):
        """Execute an orchestration action"""
        try:
            if action.type == ActionType.LEVEL_SUGGESTED:
                await self._send_level_suggestion(action)
            elif action.type == ActionType.GAME_BREAK:
                await self._schedule_game_break(action)
            elif action.type == ActionType.SEL_INTERVENTION:
                await self._trigger_sel_intervention(action)
            elif action.type == ActionType.LEARNING_PATH_UPDATE:
                await self._update_learning_path(action)
            else:
                logger.warning(f"Unknown action type: {action.type}")
                
        except Exception as e:
            logger.error(f"Action execution failed for {action.type}: {e}")
            
    async def _send_level_suggestion(self, action: OrchestrationAction):
        """Send level suggestion to learner service"""
        try:
            async with httpx.AsyncClient() as client:
                response = await client.put(
                    f"{self.config.learner_service_url}/api/v1/learners/{action.learner_id}/level",
                    json={
                        "suggested_level": action.action_data.get("level"),
                        "reason": action.action_data.get("reason"),
                        "confidence": action.action_data.get("confidence", 0.8),
                        "metadata": {
                            "orchestrator_action_id": action.id,
                            "suggested_at": action.created_at.isoformat()
                        }
                    },
                    timeout=10.0
                )
                
                if response.status_code == 200:
                    logger.info(f"Level suggestion sent for learner {action.learner_id}")
                else:
                    logger.error(f"Failed to send level suggestion: {response.status_code}")
                    
        except Exception as e:
            logger.error(f"Level suggestion API call failed: {e}")
            
    async def _schedule_game_break(self, action: OrchestrationAction):
        """Schedule game break via notification service"""
        try:
            async with httpx.AsyncClient() as client:
                notification_data = {
                    "title": "Time for a Brain Break!",
                    "message": action.action_data.get("message", "Let's take a quick break and recharge."),
                    "notification_type": "game_break",
                    "priority": "high",
                    "channels": ["websocket", "push"],
                    "action_url": action.action_data.get("game_url", "/games/break"),
                    "metadata": {
                        "orchestrator_action_id": action.id,
                        "break_duration_minutes": action.action_data.get("duration", 5),
                        "break_type": action.action_data.get("break_type", "mindfulness")
                    }
                }
                
                # Schedule notification if needed
                if action.scheduled_time:
                    notification_data["scheduled_time"] = action.scheduled_time.isoformat()
                
                response = await client.post(
                    f"{self.config.notification_service_url}/internal/broadcast",
                    json={
                        "user_id": action.learner_id,
                        "tenant_id": action.tenant_id,
                        **notification_data
                    },
                    timeout=10.0
                )
                
                if response.status_code == 200:
                    logger.info(f"Game break scheduled for learner {action.learner_id}")
                else:
                    logger.error(f"Failed to schedule game break: {response.status_code}")
                    
        except Exception as e:
            logger.error(f"Game break scheduling failed: {e}")
            
    async def _trigger_sel_intervention(self, action: OrchestrationAction):
        """Trigger social-emotional learning intervention"""
        try:
            # This would integrate with a specialized SEL service
            # For now, we'll send a notification
            async with httpx.AsyncClient() as client:
                notification_data = {
                    "title": "SEL Support Available",
                    "message": action.action_data.get("message", "We're here to help with social-emotional support."),
                    "notification_type": "sel_intervention",
                    "priority": "high",
                    "channels": ["websocket", "in_app"],
                    "action_url": action.action_data.get("intervention_url", "/sel/support"),
                    "metadata": {
                        "orchestrator_action_id": action.id,
                        "intervention_type": action.action_data.get("intervention_type", "general"),
                        "urgency": action.action_data.get("urgency", "moderate")
                    }
                }
                
                response = await client.post(
                    f"{self.config.notification_service_url}/internal/broadcast",
                    json={
                        "user_id": action.learner_id,
                        "tenant_id": action.tenant_id,
                        **notification_data
                    },
                    timeout=10.0
                )
                
                if response.status_code == 200:
                    logger.info(f"SEL intervention triggered for learner {action.learner_id}")
                else:
                    logger.error(f"Failed to trigger SEL intervention: {response.status_code}")
                    
        except Exception as e:
            logger.error(f"SEL intervention trigger failed: {e}")
            
    async def _update_learning_path(self, action: OrchestrationAction):
        """Update learning path in learner service"""
        try:
            async with httpx.AsyncClient() as client:
                response = await client.put(
                    f"{self.config.learner_service_url}/api/v1/learners/{action.learner_id}/learning-path",
                    json={
                        "path_updates": action.action_data.get("path_updates", {}),
                        "reason": action.action_data.get("reason", "Orchestrator optimization"),
                        "metadata": {
                            "orchestrator_action_id": action.id,
                            "updated_at": action.created_at.isoformat()
                        }
                    },
                    timeout=10.0
                )
                
                if response.status_code == 200:
                    logger.info(f"Learning path updated for learner {action.learner_id}")
                else:
                    logger.error(f"Failed to update learning path: {response.status_code}")
                    
        except Exception as e:
            logger.error(f"Learning path update failed: {e}")
            
    def _update_stats(self, event: Event):
        """Update processing statistics"""
        self.stats["total_events_processed"] += 1
        self.stats["last_event_time"] = datetime.utcnow()
        
        event_type = event.type.value
        if event_type not in self.stats["events_by_type"]:
            self.stats["events_by_type"][event_type] = 0
        self.stats["events_by_type"][event_type] += 1
        
    async def get_stats(self) -> Dict[str, Any]:
        """Get consumer statistics"""
        uptime = datetime.utcnow() - self.stats["start_time"]
        
        return {
            **self.stats,
            "uptime_seconds": int(uptime.total_seconds()),
            "events_per_minute": self._calculate_events_per_minute(),
            "is_running": self.is_running
        }
        
    def _calculate_events_per_minute(self) -> float:
        """Calculate events processed per minute"""
        uptime = datetime.utcnow() - self.stats["start_time"]
        if uptime.total_seconds() < 60:
            return 0.0
            
        minutes = uptime.total_seconds() / 60
        return round(self.stats["total_events_processed"] / minutes, 2)
        
    async def _cleanup(self):
        """Cleanup resources"""
        if self.redis_client:
            await self.redis_client.close()
            logger.info("Redis connection closed")


# Mock event publisher for testing
class EventPublisher:
    """Event publisher for testing orchestration"""
    
    def __init__(self, redis_url: str = "redis://localhost:6379"):
        self.redis_url = redis_url
        self.redis_client: Optional[redis.Redis] = None
        
    async def initialize(self):
        """Initialize Redis connection"""
        self.redis_client = redis.from_url(self.redis_url)
        await self.redis_client.ping()
        
    async def publish_event(self, channel: str, event: Event):
        """Publish an event to Redis stream"""
        if not self.redis_client:
            await self.initialize()
            
        event_data = {
            "data": json.dumps(asdict(event), default=str)
        }
        
        message_id = await self.redis_client.xadd(channel, event_data)
        logger.info(f"Published event {event.type} to {channel}: {message_id}")
        
        return message_id
