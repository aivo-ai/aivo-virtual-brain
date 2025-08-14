"""
Event Collector Service - Pydantic Schemas (S2-14)
Handles validation for batch event ingestion with JSON schema compliance
"""
from typing import List, Dict, Any, Optional, Union
from datetime import datetime
from enum import Enum
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, field_validator
from pydantic.types import PositiveInt


class EventType(str, Enum):
    """Supported event types for learner analytics."""
    GAME_STARTED = "game_started"
    GAME_COMPLETED = "game_completed"  
    GAME_PAUSED = "game_paused"
    GAME_RESUMED = "game_resumed"
    INTERACTION = "interaction"
    PROGRESS_UPDATE = "progress_update"
    ERROR_OCCURRED = "error_occurred"
    SESSION_START = "session_start"
    SESSION_END = "session_end"
    ACHIEVEMENT_UNLOCKED = "achievement_unlocked"


class EventPriority(str, Enum):
    """Event priority levels for processing."""
    LOW = "low"
    NORMAL = "normal"  
    HIGH = "high"
    CRITICAL = "critical"


class BaseEvent(BaseModel):
    """Base event schema with common fields."""
    model_config = ConfigDict(
        from_attributes=True,
        use_enum_values=True,
        validate_assignment=True,
        arbitrary_types_allowed=True
    )
    
    event_id: UUID = Field(..., description="Unique event identifier")
    learner_id: UUID = Field(..., description="Learner identifier for partitioning")
    tenant_id: UUID = Field(..., description="Tenant identifier")
    event_type: EventType = Field(..., description="Type of event")
    timestamp: datetime = Field(..., description="Event occurrence timestamp")
    priority: EventPriority = Field(EventPriority.NORMAL, description="Processing priority")
    session_id: Optional[UUID] = Field(None, description="Session identifier if applicable")
    game_id: Optional[UUID] = Field(None, description="Game identifier if applicable")
    source_service: str = Field(..., description="Service that generated the event")
    event_data: Dict[str, Any] = Field(default_factory=dict, description="Event-specific payload")
    metadata: Dict[str, Any] = Field(default_factory=dict, description="Additional metadata")

    @field_validator('event_data')
    @classmethod
    def validate_event_data_size(cls, v):
        """Limit event data size to prevent oversized messages."""
        if len(str(v)) > 10000:  # 10KB limit
            raise ValueError("Event data exceeds maximum size of 10KB")
        return v

    @field_validator('timestamp')
    @classmethod
    def validate_timestamp(cls, v):
        """Ensure timestamp is not too far in the future."""
        if v > datetime.utcnow().replace(microsecond=0):
            # Allow small clock skew (5 minutes)
            from datetime import timedelta
            max_future = datetime.utcnow() + timedelta(minutes=5)
            if v > max_future:
                raise ValueError("Event timestamp cannot be more than 5 minutes in the future")
        return v


class GameEvent(BaseEvent):
    """Game-specific event with required game_id."""
    game_id: UUID = Field(..., description="Game identifier (required for game events)")
    

class InteractionEvent(BaseEvent):
    """User interaction event with interaction details."""
    event_type: EventType = Field(EventType.INTERACTION, description="Fixed as interaction type")
    interaction_type: str = Field(..., description="Type of interaction (click, swipe, etc.)")
    element_id: Optional[str] = Field(None, description="UI element identifier")
    coordinates: Optional[Dict[str, float]] = Field(None, description="Interaction coordinates")


class ProgressEvent(BaseEvent):
    """Progress tracking event with completion metrics."""
    event_type: EventType = Field(EventType.PROGRESS_UPDATE, description="Fixed as progress type")
    completion_percentage: float = Field(..., ge=0.0, le=100.0, description="Progress completion %")
    score: Optional[float] = Field(None, ge=0.0, description="Current score if applicable")
    level: Optional[int] = Field(None, ge=1, description="Current level if applicable")


class ErrorEvent(BaseEvent):
    """Error event with error details."""
    event_type: EventType = Field(EventType.ERROR_OCCURRED, description="Fixed as error type")
    priority: EventPriority = Field(EventPriority.HIGH, description="Errors default to high priority")
    error_code: str = Field(..., description="Error code or identifier")
    error_message: str = Field(..., description="Human-readable error message")
    stack_trace: Optional[str] = Field(None, description="Technical stack trace")


# Request/Response schemas for batch operations
class EventBatchRequest(BaseModel):
    """Request schema for batch event ingestion."""
    model_config = ConfigDict(from_attributes=True)
    
    events: List[BaseEvent] = Field(..., min_length=1, max_length=1000, description="Batch of events")
    batch_id: Optional[UUID] = Field(None, description="Optional batch identifier for tracking")
    compress: bool = Field(True, description="Whether to compress before sending to Kafka")

    @field_validator('events')
    @classmethod
    def validate_batch_size(cls, v):
        """Ensure batch size is reasonable."""
        if len(v) == 0:
            raise ValueError("Event batch cannot be empty")
        if len(v) > 1000:
            raise ValueError("Event batch cannot contain more than 1000 events")
        return v


class EventBatchResponse(BaseModel):
    """Response schema for batch event processing."""
    model_config = ConfigDict(from_attributes=True)
    
    batch_id: UUID = Field(..., description="Batch processing identifier")
    accepted_count: int = Field(..., description="Number of events accepted")
    rejected_count: int = Field(0, description="Number of events rejected")
    processing_time_ms: float = Field(..., description="Processing time in milliseconds")
    kafka_partition: Optional[int] = Field(None, description="Kafka partition used")
    dlq_events: List[UUID] = Field(default_factory=list, description="Events sent to DLQ")
    warnings: List[str] = Field(default_factory=list, description="Processing warnings")


class HealthResponse(BaseModel):
    """Health check response schema."""
    model_config = ConfigDict(from_attributes=True)
    
    status: str = Field(..., description="Service health status")
    kafka_connected: bool = Field(..., description="Kafka connection status")
    buffer_status: Dict[str, Any] = Field(..., description="Disk buffer status")
    throughput_metrics: Dict[str, float] = Field(..., description="Performance metrics")
    uptime_seconds: float = Field(..., description="Service uptime")


class MetricsResponse(BaseModel):
    """Metrics response schema for monitoring."""
    model_config = ConfigDict(from_attributes=True)
    
    events_processed_total: int = Field(..., description="Total events processed")
    events_per_second: float = Field(..., description="Current throughput")
    kafka_writes_total: int = Field(..., description="Total Kafka writes")
    dlq_events_total: int = Field(..., description="Total DLQ events")
    buffer_events_count: int = Field(..., description="Events in disk buffer")
    avg_processing_time_ms: float = Field(..., description="Average processing time")
    p99_processing_time_ms: float = Field(..., description="99th percentile processing time")


# gRPC specific schemas
class StreamEventRequest(BaseModel):
    """Single event for gRPC streaming."""
    model_config = ConfigDict(from_attributes=True)
    
    event: BaseEvent = Field(..., description="Event to stream")
    stream_id: Optional[str] = Field(None, description="Client stream identifier")


class StreamEventResponse(BaseModel):
    """Response for gRPC streaming."""
    model_config = ConfigDict(from_attributes=True)
    
    event_id: UUID = Field(..., description="Processed event ID")
    status: str = Field(..., description="Processing status")
    partition: Optional[int] = Field(None, description="Kafka partition")
    timestamp: datetime = Field(..., description="Processing timestamp")


class ErrorResponse(BaseModel):
    """Standard error response format."""
    model_config = ConfigDict(from_attributes=True)
    
    error_code: str = Field(..., description="Machine-readable error code")
    error_message: str = Field(..., description="Human-readable error message") 
    timestamp: float = Field(..., description="Error timestamp (Unix)")
    request_id: str = Field(..., description="Request tracking identifier")
