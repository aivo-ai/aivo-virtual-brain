"""
Chat Service Event Publishing
Kafka integration for publishing chat events
"""

import json
import asyncio
import logging
from typing import Optional, Dict, Any
from datetime import datetime
from uuid import UUID

try:
    from kafka import KafkaProducer
    from kafka.errors import KafkaError
    KAFKA_AVAILABLE = True
    KafkaProducerType = KafkaProducer
except ImportError:
    KAFKA_AVAILABLE = False
    KafkaProducerType = None
    KafkaError = Exception

from .config import settings, KAFKA_TOPICS
from .schemas import ChatMessageEvent, ChatThreadEvent

# Configure logging
logger = logging.getLogger(__name__)

# Global Kafka producer instance
kafka_producer: Optional[Any] = None


def get_kafka_producer() -> Optional[Any]:
    """
    Get or create Kafka producer instance
    Returns None if Kafka is not available or disabled
    """
    global kafka_producer
    
    if not KAFKA_AVAILABLE:
        logger.warning("Kafka not available - events will not be published")
        return None
    
    if kafka_producer is None:
        try:
            kafka_producer = KafkaProducerType(
                bootstrap_servers=settings.kafka_bootstrap_servers.split(','),
                client_id=settings.kafka_client_id,
                value_serializer=lambda x: json.dumps(x, default=str).encode('utf-8'),
                key_serializer=lambda x: x.encode('utf-8') if x else None,
                security_protocol=settings.kafka_security_protocol,
                retries=3,
                acks='all',  # Wait for all replicas to acknowledge
                batch_size=16384,
                linger_ms=10,  # Wait up to 10ms to batch messages
                buffer_memory=33554432,  # 32MB buffer
            )
            logger.info("Kafka producer initialized successfully")
        except Exception as e:
            logger.error(f"Failed to initialize Kafka producer: {e}")
            kafka_producer = None
    
    return kafka_producer


async def close_kafka_producer():
    """
    Close Kafka producer connection gracefully
    """
    global kafka_producer
    
    if kafka_producer:
        try:
            kafka_producer.flush()  # Ensure all messages are sent
            kafka_producer.close()
            kafka_producer = None
            logger.info("Kafka producer closed successfully")
        except Exception as e:
            logger.error(f"Error closing Kafka producer: {e}")


def publish_event(topic: str, event_data: Dict[str, Any], key: Optional[str] = None) -> bool:
    """
    Publish an event to Kafka
    Returns True if successful, False otherwise
    """
    producer = get_kafka_producer()
    
    if not producer:
        logger.warning(f"Cannot publish event to {topic} - Kafka producer not available")
        return False
    
    try:
        # Add metadata to event
        enriched_event = {
            **event_data,
            "service": settings.service_name,
            "version": settings.version,
            "timestamp": datetime.utcnow().isoformat(),
            "tenant_isolated": True,
        }
        
        # Send message
        future = producer.send(
            topic=topic,
            value=enriched_event,
            key=key
        )
        
        # Wait for confirmation (with timeout)
        record_metadata = future.get(timeout=10)
        
        logger.debug(f"Event published to {topic}: partition={record_metadata.partition}, offset={record_metadata.offset}")
        return True
        
    except KafkaError as e:
        logger.error(f"Kafka error publishing to {topic}: {e}")
        return False
    except Exception as e:
        logger.error(f"Unexpected error publishing to {topic}: {e}")
        return False


async def publish_message_created_event(
    message_id: UUID,
    thread_id: UUID,
    learner_id: str,
    tenant_id: str,
    role: str,
    message_type: str,
    created_by: str
) -> bool:
    """
    Publish CHAT_MESSAGE_CREATED event
    """
    event = ChatMessageEvent(
        event_type="CHAT_MESSAGE_CREATED",
        message_id=message_id,
        thread_id=thread_id,
        learner_id=learner_id,
        tenant_id=tenant_id,
        role=role,
        message_type=message_type,
        created_at=datetime.utcnow(),
        created_by=created_by
    )
    
    # Use learner_id as key for consistent partitioning
    key = f"{tenant_id}:{learner_id}"
    
    return publish_event(
        topic=KAFKA_TOPICS["chat_message_created"],
        event_data=event.model_dump(),
        key=key
    )


async def publish_message_updated_event(
    message_id: UUID,
    thread_id: UUID,
    learner_id: str,
    tenant_id: str,
    role: str,
    message_type: str,
    updated_by: str
) -> bool:
    """
    Publish CHAT_MESSAGE_UPDATED event
    """
    event = ChatMessageEvent(
        event_type="CHAT_MESSAGE_UPDATED",
        message_id=message_id,
        thread_id=thread_id,
        learner_id=learner_id,
        tenant_id=tenant_id,
        role=role,
        message_type=message_type,
        created_at=datetime.utcnow(),
        created_by=updated_by
    )
    
    key = f"{tenant_id}:{learner_id}"
    
    return publish_event(
        topic=KAFKA_TOPICS["chat_message_updated"],
        event_data=event.model_dump(),
        key=key
    )


async def publish_thread_created_event(
    thread_id: UUID,
    learner_id: str,
    tenant_id: str,
    subject: Optional[str],
    created_by: str
) -> bool:
    """
    Publish CHAT_THREAD_CREATED event
    """
    event = ChatThreadEvent(
        event_type="CHAT_THREAD_CREATED",
        thread_id=thread_id,
        learner_id=learner_id,
        tenant_id=tenant_id,
        subject=subject,
        created_by=created_by,
        created_at=datetime.utcnow()
    )
    
    key = f"{tenant_id}:{learner_id}"
    
    return publish_event(
        topic=KAFKA_TOPICS["chat_thread_created"],
        event_data=event.model_dump(),
        key=key
    )


async def publish_thread_archived_event(
    thread_id: UUID,
    learner_id: str,
    tenant_id: str,
    subject: Optional[str],
    archived_by: str
) -> bool:
    """
    Publish CHAT_THREAD_ARCHIVED event
    """
    event = ChatThreadEvent(
        event_type="CHAT_THREAD_ARCHIVED",
        thread_id=thread_id,
        learner_id=learner_id,
        tenant_id=tenant_id,
        subject=subject,
        created_by=archived_by,
        created_at=datetime.utcnow()
    )
    
    key = f"{tenant_id}:{learner_id}"
    
    return publish_event(
        topic=KAFKA_TOPICS["chat_thread_archived"],
        event_data=event.model_dump(),
        key=key
    )


async def publish_privacy_export_event(
    learner_id: str,
    tenant_id: str,
    export_type: str,
    requested_by: str,
    thread_count: int,
    message_count: int
) -> bool:
    """
    Publish privacy export event for compliance tracking
    """
    event_data = {
        "event_type": "PRIVACY_EXPORT_COMPLETED",
        "learner_id": learner_id,
        "tenant_id": tenant_id,
        "export_type": export_type,
        "requested_by": requested_by,
        "thread_count": thread_count,
        "message_count": message_count,
        "exported_at": datetime.utcnow().isoformat(),
        "service": "chat-svc"
    }
    
    key = f"{tenant_id}:{learner_id}"
    
    return publish_event(
        topic=KAFKA_TOPICS["privacy_export_requested"],
        event_data=event_data,
        key=key
    )


async def publish_privacy_deletion_event(
    learner_id: str,
    tenant_id: str,
    deletion_type: str,
    requested_by: str,
    thread_count: int,
    message_count: int,
    reason: Optional[str] = None
) -> bool:
    """
    Publish privacy deletion event for compliance tracking
    """
    event_data = {
        "event_type": "PRIVACY_DELETION_COMPLETED",
        "learner_id": learner_id,
        "tenant_id": tenant_id,
        "deletion_type": deletion_type,
        "requested_by": requested_by,
        "thread_count": thread_count,
        "message_count": message_count,
        "reason": reason,
        "deleted_at": datetime.utcnow().isoformat(),
        "service": "chat-svc"
    }
    
    key = f"{tenant_id}:{learner_id}"
    
    return publish_event(
        topic=KAFKA_TOPICS["privacy_deletion_requested"],
        event_data=event_data,
        key=key
    )


# Health check for Kafka

async def check_kafka_health() -> bool:
    """
    Check if Kafka is healthy and reachable
    Returns True if healthy, False otherwise
    """
    if not KAFKA_AVAILABLE:
        return False
    
    producer = get_kafka_producer()
    if not producer:
        return False
    
    try:
        # Try to get cluster metadata
        metadata = producer.list_topics()
        return True
    except Exception as e:
        logger.error(f"Kafka health check failed: {e}")
        return False


class EventPublisher:
    """
    Event publisher class that wraps all event publishing functionality
    """
    
    def __init__(self):
        self.producer = None
    
    async def init(self):
        """Initialize the event publisher"""
        self.producer = get_kafka_producer()
    
    async def close(self):
        """Close the event publisher"""
        await close_kafka_producer()
    
    async def publish_message_created(
        self,
        message_id: str,
        thread_id: str,
        tenant_id: str,
        learner_id: str,
        sender_id: str,
        content: str,
        message_type: str,
        metadata: Dict[str, Any] = None
    ) -> bool:
        """Publish message created event"""
        return await publish_message_created_event(
            message_id=message_id,
            thread_id=thread_id,
            tenant_id=tenant_id,
            learner_id=learner_id,
            sender_id=sender_id,
            content=content,
            message_type=message_type,
            metadata=metadata or {}
        )
    
    async def publish_thread_created(
        self,
        thread_id: str,
        tenant_id: str,
        learner_id: str,
        created_by: str,
        metadata: Dict[str, Any] = None
    ) -> bool:
        """Publish thread created event"""
        return await publish_thread_created_event(
            thread_id=thread_id,
            tenant_id=tenant_id,
            learner_id=learner_id,
            created_by=created_by,
            title="", # Will be filled by the event function
            metadata=metadata or {}
        )
    
    async def publish_thread_deleted(
        self,
        thread_id: str,
        tenant_id: str,
        learner_id: str,
        deleted_by: str
    ) -> bool:
        """Publish thread deleted event"""
        return await publish_thread_archived_event(
            thread_id=thread_id,
            tenant_id=tenant_id,
            learner_id=learner_id,
            archived_by=deleted_by,
            reason="deleted"
        )
    
    async def publish_privacy_export_requested(
        self,
        export_id: str,
        tenant_id: str,
        learner_id: str,
        requested_by: str,
        export_type: str
    ) -> bool:
        """Publish privacy export requested event"""
        return await publish_privacy_export_event(
            export_id=export_id,
            tenant_id=tenant_id,
            learner_id=learner_id,
            requested_by=requested_by,
            export_type=export_type,
            status="requested"
        )
    
    async def publish_privacy_deletion_requested(
        self,
        deletion_id: str,
        tenant_id: str,
        learner_id: str,
        requested_by: str,
        deletion_type: str
    ) -> bool:
        """Publish privacy deletion requested event"""
        return await publish_privacy_deletion_event(
            deletion_id=deletion_id,
            tenant_id=tenant_id,
            learner_id=learner_id,
            requested_by=requested_by,
            deletion_type=deletion_type,
            status="requested"
        )
