"""
Event Collector Service - HTTP Router (S2-14)
Handles HTTP batch event ingestion with gzip support and validation
"""
import gzip
import time
from typing import List
from uuid import uuid4
import logging

from fastapi import APIRouter, HTTPException, Request, Depends
from fastapi.responses import JSONResponse

from ..schemas import (
    EventBatchRequest, EventBatchResponse, BaseEvent,
    HealthResponse, MetricsResponse
)
from ..writer import KafkaEventWriter

logger = logging.getLogger(__name__)

router = APIRouter()

# Global writer instance (will be injected)
kafka_writer: KafkaEventWriter = None


def get_kafka_writer() -> KafkaEventWriter:
    """Dependency to get Kafka writer instance."""
    if kafka_writer is None:
        raise HTTPException(status_code=503, detail="Kafka writer not initialized")
    return kafka_writer


@router.post("/collect", response_model=EventBatchResponse)
async def collect_events(
    request: Request,
    writer: KafkaEventWriter = Depends(get_kafka_writer)
):
    """
    Collect batch of events for ingestion into Kafka.
    
    Supports both JSON and gzipped JSON payloads.
    Events are validated and written to Kafka with learner_id partitioning.
    """
    start_time = time.time()
    batch_id = uuid4()
    
    try:
        # Handle content encoding
        content_encoding = request.headers.get('content-encoding', '').lower()
        raw_body = await request.body()
        
        if not raw_body:
            raise HTTPException(status_code=400, detail="Request body is empty")
        
        # Decompress if gzipped
        if content_encoding == 'gzip':
            try:
                decompressed_body = gzip.decompress(raw_body)
                body_str = decompressed_body.decode('utf-8')
            except Exception as e:
                logger.error(f"Failed to decompress gzip content: {e}")
                raise HTTPException(status_code=400, detail="Invalid gzip content")
        else:
            body_str = raw_body.decode('utf-8')
        
        # Parse JSON
        try:
            import json
            body_data = json.loads(body_str)
        except json.JSONDecodeError as e:
            logger.error(f"Invalid JSON in request body: {e}")
            raise HTTPException(status_code=400, detail="Invalid JSON format")
        
        # Validate batch request schema
        try:
            if isinstance(body_data, dict) and 'events' in body_data:
                # Full batch request format
                batch_request = EventBatchRequest(**body_data)
                events = batch_request.events
                if batch_request.batch_id:
                    batch_id = batch_request.batch_id
            elif isinstance(body_data, list):
                # Simple list of events format
                events = [BaseEvent(**event_data) for event_data in body_data]
            else:
                raise HTTPException(status_code=400, detail="Invalid request format")
                
        except Exception as e:
            logger.error(f"Event validation failed: {e}")
            raise HTTPException(status_code=400, detail=f"Event validation failed: {str(e)}")
        
        # Rate limiting check (simple in-memory)
        if len(events) > 1000:
            raise HTTPException(status_code=413, detail="Batch size too large (max 1000 events)")
        
        # Write to Kafka
        try:
            accepted, rejected, dlq_events = await writer.write_batch(events, batch_id)
            processing_time = (time.time() - start_time) * 1000  # Convert to ms
            
            # Determine partition (simplified - use first event's learner_id)
            partition = None
            if accepted > 0 and events:
                # This is approximate since events might go to different partitions
                # In real implementation, we'd track this per event
                partition = hash(str(events[0].learner_id)) % 3  # Assume 3 partitions
            
            warnings = []
            if rejected > 0:
                warnings.append(f"{rejected} events were rejected and sent to DLQ")
            
            response = EventBatchResponse(
                batch_id=batch_id,
                accepted_count=accepted,
                rejected_count=rejected,
                processing_time_ms=processing_time,
                kafka_partition=partition,
                dlq_events=dlq_events,
                warnings=warnings
            )
            
            # Log processing result
            logger.info(f"Processed batch {batch_id}: {accepted} accepted, {rejected} rejected, {processing_time:.2f}ms")
            
            # Return appropriate status code
            if rejected == 0:
                return response
            elif accepted == 0:
                return JSONResponse(
                    status_code=422,
                    content=response.model_dump()
                )
            else:
                return JSONResponse(
                    status_code=207,  # Multi-Status
                    content=response.model_dump()
                )
                
        except Exception as e:
            logger.error(f"Failed to process event batch: {e}")
            raise HTTPException(status_code=500, detail="Internal processing error")
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Unexpected error processing batch: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")


@router.get("/health", response_model=HealthResponse)
async def health_check(writer: KafkaEventWriter = Depends(get_kafka_writer)):
    """Health check endpoint for monitoring."""
    try:
        # Get buffer status
        buffer_status = await writer.disk_buffer.get_status()
        
        # Get metrics for throughput
        metrics = writer.get_metrics()
        
        # Calculate uptime (simplified)
        uptime = time.time() - getattr(writer, '_start_time', time.time())
        
        health_status = "healthy" if writer.kafka_available else "degraded"
        
        return HealthResponse(
            status=health_status,
            kafka_connected=writer.kafka_available,
            buffer_status=buffer_status,
            throughput_metrics={
                "events_per_second": metrics.get("events_per_second", 0),
                "avg_processing_time_ms": metrics.get("avg_processing_time_ms", 0)
            },
            uptime_seconds=uptime
        )
        
    except Exception as e:
        logger.error(f"Health check failed: {e}")
        raise HTTPException(status_code=500, detail="Health check failed")


@router.get("/metrics", response_model=MetricsResponse)
async def get_metrics(writer: KafkaEventWriter = Depends(get_kafka_writer)):
    """Get processing metrics for monitoring."""
    try:
        metrics = writer.get_metrics()
        buffer_status = await writer.disk_buffer.get_status()
        
        return MetricsResponse(
            events_processed_total=metrics["events_processed_total"],
            events_per_second=metrics["events_per_second"],
            kafka_writes_total=metrics["kafka_writes_total"],
            dlq_events_total=metrics["dlq_events_total"],
            buffer_events_count=buffer_status.get("buffered_batches", 0),
            avg_processing_time_ms=metrics["avg_processing_time_ms"],
            p99_processing_time_ms=metrics["p99_processing_time_ms"]
        )
        
    except Exception as e:
        logger.error(f"Metrics retrieval failed: {e}")
        raise HTTPException(status_code=500, detail="Metrics unavailable")


@router.post("/test/events")
async def generate_test_events(
    count: int = 100,
    writer: KafkaEventWriter = Depends(get_kafka_writer)
):
    """Generate test events for load testing (development only)."""
    try:
        from uuid import uuid4
        from datetime import datetime
        from ..schemas import EventType, BaseEvent
        
        # Generate test events
        events = []
        for i in range(count):
            event = BaseEvent(
                event_id=uuid4(),
                learner_id=uuid4(),
                tenant_id=uuid4(),
                event_type=EventType.INTERACTION,
                timestamp=datetime.utcnow(),
                source_service="test-generator",
                event_data={"test_index": i, "action": "click", "element": "button"},
                metadata={"generated": True, "batch_size": count}
            )
            events.append(event)
        
        # Process batch
        batch_id = uuid4()
        start_time = time.time()
        accepted, rejected, dlq_events = await writer.write_batch(events, batch_id)
        processing_time = (time.time() - start_time) * 1000
        
        return {
            "generated": count,
            "accepted": accepted,
            "rejected": rejected,
            "processing_time_ms": processing_time,
            "throughput_eps": count / (processing_time / 1000) if processing_time > 0 else 0
        }
        
    except Exception as e:
        logger.error(f"Test event generation failed: {e}")
        raise HTTPException(status_code=500, detail="Test generation failed")
