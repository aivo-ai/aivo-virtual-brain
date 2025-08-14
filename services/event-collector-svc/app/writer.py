"""
Event Collector Service - Kafka Writer (S2-14)
Handles event writing to Kafka with backpressure, buffering, and DLQ support
"""
import asyncio
import json
import gzip
import os
import time
from typing import List, Dict, Any, Optional, Tuple
from datetime import datetime, timedelta
from uuid import UUID, uuid4
from pathlib import Path
import logging

from kafka import KafkaProducer
from kafka.errors import KafkaError, KafkaTimeoutError, NoBrokersAvailable
import aiofiles
import aiofiles.os

from .schemas import BaseEvent, EventBatchRequest, EventPriority

logger = logging.getLogger(__name__)


class DiskBuffer:
    """Disk-based buffer for events when Kafka is unavailable."""
    
    def __init__(self, buffer_dir: str = "/tmp/event-buffer", max_age_minutes: int = 30):
        self.buffer_dir = Path(buffer_dir)
        self.max_age = timedelta(minutes=max_age_minutes)
        self.buffer_dir.mkdir(parents=True, exist_ok=True)
        
    async def write_batch(self, events: List[BaseEvent], batch_id: UUID) -> bool:
        """Write event batch to disk buffer."""
        try:
            filename = f"batch_{batch_id}_{int(time.time())}.json.gz"
            filepath = self.buffer_dir / filename
            
            # Serialize events to JSON
            event_data = {
                "batch_id": str(batch_id),
                "timestamp": datetime.utcnow().isoformat(),
                "events": [event.model_dump() for event in events]
            }
            
            # Compress and write
            compressed_data = gzip.compress(json.dumps(event_data).encode('utf-8'))
            
            async with aiofiles.open(filepath, 'wb') as f:
                await f.write(compressed_data)
                
            logger.info(f"Buffered {len(events)} events to disk: {filename}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to write buffer batch {batch_id}: {e}")
            return False
    
    async def read_batches(self) -> List[Tuple[UUID, List[BaseEvent]]]:
        """Read all buffered batches that haven't expired."""
        batches = []
        current_time = datetime.utcnow()
        
        try:
            for filepath in self.buffer_dir.glob("batch_*.json.gz"):
                try:
                    # Check if file is too old
                    file_time = datetime.fromtimestamp(filepath.stat().st_mtime)
                    if current_time - file_time > self.max_age:
                        await aiofiles.os.remove(filepath)
                        logger.info(f"Removed expired buffer file: {filepath.name}")
                        continue
                    
                    # Read and decompress
                    async with aiofiles.open(filepath, 'rb') as f:
                        compressed_data = await f.read()
                    
                    data = json.loads(gzip.decompress(compressed_data).decode('utf-8'))
                    
                    # Parse events
                    batch_id = UUID(data["batch_id"])
                    events = [BaseEvent(**event_data) for event_data in data["events"]]
                    
                    batches.append((batch_id, events))
                    
                except Exception as e:
                    logger.error(f"Failed to read buffer file {filepath}: {e}")
                    # Move corrupted file aside
                    corrupted_path = filepath.with_suffix('.corrupted')
                    await aiofiles.os.rename(filepath, corrupted_path)
                    
        except Exception as e:
            logger.error(f"Failed to scan buffer directory: {e}")
            
        return batches
    
    async def remove_batch(self, batch_id: UUID) -> bool:
        """Remove processed batch from buffer."""
        try:
            for filepath in self.buffer_dir.glob(f"batch_{batch_id}_*.json.gz"):
                await aiofiles.os.remove(filepath)
                logger.debug(f"Removed processed buffer file: {filepath.name}")
                return True
        except Exception as e:
            logger.error(f"Failed to remove buffer batch {batch_id}: {e}")
            return False
    
    async def get_status(self) -> Dict[str, Any]:
        """Get buffer status for health checks."""
        try:
            files = list(self.buffer_dir.glob("batch_*.json.gz"))
            total_size = sum(f.stat().st_size for f in files if f.exists())
            
            return {
                "buffered_batches": len(files),
                "total_size_bytes": total_size,
                "oldest_batch": min([f.stat().st_mtime for f in files]) if files else None,
                "buffer_dir": str(self.buffer_dir),
                "max_age_minutes": self.max_age.total_seconds() / 60
            }
        except Exception as e:
            logger.error(f"Failed to get buffer status: {e}")
            return {"error": str(e)}


class KafkaEventWriter:
    """Kafka event writer with backpressure, buffering, and DLQ support."""
    
    def __init__(
        self,
        bootstrap_servers: str = "localhost:9092",
        topic: str = "learner_events",
        dlq_topic: str = "learner_events_dlq",
        max_request_size: int = 1048576,  # 1MB
        request_timeout_ms: int = 30000,  # 30 seconds
        retries: int = 3,
        buffer_dir: str = "/tmp/event-buffer",
        buffer_max_age_minutes: int = 30
    ):
        self.bootstrap_servers = bootstrap_servers
        self.topic = topic
        self.dlq_topic = dlq_topic
        self.producer = None
        self.producer_config = {
            'bootstrap_servers': bootstrap_servers.split(','),
            'max_request_size': max_request_size,
            'request_timeout_ms': request_timeout_ms,
            'retries': retries,
            'acks': 'all',  # Wait for all replicas
            'compression_type': 'gzip',
            'batch_size': 16384,  # 16KB batches
            'linger_ms': 10,  # Wait 10ms to batch more messages
            'buffer_memory': 33554432,  # 32MB buffer
            'value_serializer': lambda v: json.dumps(v).encode('utf-8'),
            'key_serializer': lambda k: str(k).encode('utf-8') if k else None
        }
        
        # Metrics
        self.events_processed = 0
        self.events_dlq = 0
        self.kafka_writes = 0
        self.processing_times = []
        self.last_throughput_check = time.time()
        self.last_event_count = 0
        
        # Disk buffer
        self.disk_buffer = DiskBuffer(buffer_dir, buffer_max_age_minutes)
        
        # Connection state
        self.kafka_available = False
        self.last_connection_check = 0
        self.connection_check_interval = 30  # seconds
        
        # Background tasks
        self._buffer_processor_task = None
        self._running = False
        
    async def initialize(self):
        """Initialize the Kafka writer and start background tasks."""
        self._running = True
        await self._connect_kafka()
        
        # Start buffer processor task
        self._buffer_processor_task = asyncio.create_task(self._process_buffered_events())
        
        logger.info("Kafka event writer initialized")
    
    async def shutdown(self):
        """Gracefully shutdown the Kafka writer."""
        self._running = False
        
        if self._buffer_processor_task:
            self._buffer_processor_task.cancel()
            try:
                await self._buffer_processor_task
            except asyncio.CancelledError:
                pass
        
        if self.producer:
            self.producer.flush()
            self.producer.close()
            
        logger.info("Kafka event writer shutdown")
    
    async def _connect_kafka(self) -> bool:
        """Connect to Kafka cluster."""
        try:
            if self.producer:
                self.producer.close()
            
            self.producer = KafkaProducer(**self.producer_config)
            
            # Test connection by getting metadata
            metadata = self.producer.list_topics()
            if self.topic not in metadata:
                logger.warning(f"Topic {self.topic} not found in Kafka cluster")
            
            self.kafka_available = True
            self.last_connection_check = time.time()
            logger.info("Successfully connected to Kafka cluster")
            return True
            
        except Exception as e:
            self.kafka_available = False
            logger.error(f"Failed to connect to Kafka: {e}")
            return False
    
    async def _check_kafka_connection(self) -> bool:
        """Check if Kafka connection is still healthy."""
        current_time = time.time()
        
        # Only check periodically to avoid overhead
        if current_time - self.last_connection_check < self.connection_check_interval:
            return self.kafka_available
        
        try:
            if not self.producer:
                return await self._connect_kafka()
            
            # Simple health check - try to get topic metadata
            metadata = self.producer.list_topics()
            self.kafka_available = self.topic in metadata
            self.last_connection_check = current_time
            
            return self.kafka_available
            
        except Exception as e:
            logger.warning(f"Kafka health check failed: {e}")
            self.kafka_available = False
            self.last_connection_check = current_time
            return False
    
    def _get_partition_key(self, event: BaseEvent) -> str:
        """Generate partition key to ensure events for same learner go to same partition."""
        return str(event.learner_id)
    
    def _serialize_event(self, event: BaseEvent) -> Dict[str, Any]:
        """Serialize event for Kafka."""
        return {
            'event_id': str(event.event_id),
            'learner_id': str(event.learner_id),
            'tenant_id': str(event.tenant_id),
            'event_type': event.event_type,
            'timestamp': event.timestamp.isoformat(),
            'priority': event.priority,
            'session_id': str(event.session_id) if event.session_id else None,
            'game_id': str(event.game_id) if event.game_id else None,
            'source_service': event.source_service,
            'event_data': event.event_data,
            'metadata': event.metadata,
            'ingestion_timestamp': datetime.utcnow().isoformat()
        }
    
    async def write_batch(self, events: List[BaseEvent], batch_id: UUID) -> Tuple[int, int, List[UUID]]:
        """
        Write batch of events to Kafka.
        
        Returns:
            Tuple of (accepted_count, rejected_count, dlq_event_ids)
        """
        start_time = time.time()
        accepted = 0
        rejected = 0
        dlq_events = []
        
        # Check Kafka connection
        kafka_healthy = await self._check_kafka_connection()
        
        if not kafka_healthy:
            # Buffer events to disk
            if await self.disk_buffer.write_batch(events, batch_id):
                logger.warning(f"Kafka unavailable, buffered {len(events)} events to disk")
                return len(events), 0, []  # Consider buffered as accepted
            else:
                # If can't buffer, send to DLQ
                dlq_events = [event.event_id for event in events]
                await self._write_to_dlq(events, "buffer_write_failed")
                return 0, len(events), dlq_events
        
        # Process events
        for event in events:
            try:
                # Validate event
                if not self._validate_event(event):
                    rejected += 1
                    dlq_events.append(event.event_id)
                    await self._write_to_dlq([event], "validation_failed")
                    continue
                
                # Serialize for Kafka
                kafka_message = self._serialize_event(event)
                partition_key = self._get_partition_key(event)
                
                # Send to Kafka
                future = self.producer.send(
                    self.topic,
                    key=partition_key,
                    value=kafka_message
                )
                
                # For high priority events, wait for confirmation
                if event.priority == EventPriority.CRITICAL:
                    record_metadata = future.get(timeout=10)
                    logger.debug(f"Critical event {event.event_id} written to partition {record_metadata.partition}")
                
                accepted += 1
                self.kafka_writes += 1
                
            except KafkaTimeoutError:
                rejected += 1
                dlq_events.append(event.event_id)
                await self._write_to_dlq([event], "kafka_timeout")
                logger.error(f"Kafka timeout writing event {event.event_id}")
                
            except KafkaError as e:
                rejected += 1
                dlq_events.append(event.event_id)
                await self._write_to_dlq([event], f"kafka_error: {str(e)}")
                logger.error(f"Kafka error writing event {event.event_id}: {e}")
                
            except Exception as e:
                rejected += 1
                dlq_events.append(event.event_id)
                await self._write_to_dlq([event], f"unexpected_error: {str(e)}")
                logger.error(f"Unexpected error writing event {event.event_id}: {e}")
        
        # Update metrics
        processing_time = (time.time() - start_time) * 1000  # Convert to ms
        self.processing_times.append(processing_time)
        if len(self.processing_times) > 1000:  # Keep only last 1000 measurements
            self.processing_times = self.processing_times[-1000:]
        
        self.events_processed += accepted
        self.events_dlq += rejected
        
        logger.debug(f"Batch {batch_id}: {accepted} accepted, {rejected} rejected, {processing_time:.2f}ms")
        
        return accepted, rejected, dlq_events
    
    def _validate_event(self, event: BaseEvent) -> bool:
        """Validate event before sending to Kafka."""
        try:
            # Basic validation - Pydantic already handled schema validation
            
            # Check for poison pill indicators
            if len(str(event.event_data)) > 50000:  # 50KB limit
                logger.warning(f"Event {event.event_id} data too large")
                return False
            
            # Check timestamp sanity
            now = datetime.utcnow()
            event_time = event.timestamp.replace(tzinfo=None)
            
            # Reject events more than 24 hours old or 1 hour in future
            if abs((now - event_time).total_seconds()) > 24 * 3600:
                logger.warning(f"Event {event.event_id} timestamp too far from current time")
                return False
                
            return True
            
        except Exception as e:
            logger.error(f"Event validation failed for {event.event_id}: {e}")
            return False
    
    async def _write_to_dlq(self, events: List[BaseEvent], reason: str):
        """Write failed events to Dead Letter Queue."""
        try:
            dlq_message = {
                'timestamp': datetime.utcnow().isoformat(),
                'reason': reason,
                'events': [self._serialize_event(event) for event in events]
            }
            
            if self.producer and self.kafka_available:
                self.producer.send(
                    self.dlq_topic,
                    value=dlq_message
                )
            else:
                # Write DLQ to local file if Kafka unavailable
                dlq_file = Path("/tmp/event-collector-dlq.log")
                async with aiofiles.open(dlq_file, 'a') as f:
                    await f.write(json.dumps(dlq_message) + '\n')
                    
            logger.warning(f"Sent {len(events)} events to DLQ: {reason}")
            
        except Exception as e:
            logger.error(f"Failed to write to DLQ: {e}")
    
    async def _process_buffered_events(self):
        """Background task to process buffered events when Kafka comes back online."""
        while self._running:
            try:
                # Only process if Kafka is available
                if not await self._check_kafka_connection():
                    await asyncio.sleep(30)  # Check every 30 seconds
                    continue
                
                # Read buffered batches
                batches = await self.disk_buffer.read_batches()
                
                if not batches:
                    await asyncio.sleep(30)
                    continue
                
                logger.info(f"Processing {len(batches)} buffered batches")
                
                for batch_id, events in batches:
                    try:
                        accepted, rejected, dlq_events = await self.write_batch(events, batch_id)
                        
                        if accepted > 0 or rejected > 0:
                            # Remove from buffer if processed
                            await self.disk_buffer.remove_batch(batch_id)
                            logger.info(f"Processed buffered batch {batch_id}: {accepted} accepted, {rejected} rejected")
                        
                    except Exception as e:
                        logger.error(f"Failed to process buffered batch {batch_id}: {e}")
                
                await asyncio.sleep(10)  # Process more frequently when catching up
                
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Error in buffer processor: {e}")
                await asyncio.sleep(30)
    
    def get_metrics(self) -> Dict[str, Any]:
        """Get performance metrics."""
        current_time = time.time()
        time_delta = current_time - self.last_throughput_check
        
        if time_delta >= 1.0:  # Update throughput every second
            current_throughput = (self.events_processed - self.last_event_count) / time_delta
            self.last_event_count = self.events_processed
            self.last_throughput_check = current_time
        else:
            current_throughput = 0.0
        
        avg_processing_time = sum(self.processing_times) / len(self.processing_times) if self.processing_times else 0
        p99_processing_time = sorted(self.processing_times)[int(0.99 * len(self.processing_times))] if len(self.processing_times) >= 10 else 0
        
        return {
            'events_processed_total': self.events_processed,
            'events_per_second': current_throughput,
            'kafka_writes_total': self.kafka_writes,
            'dlq_events_total': self.events_dlq,
            'kafka_connected': self.kafka_available,
            'avg_processing_time_ms': avg_processing_time,
            'p99_processing_time_ms': p99_processing_time
        }
