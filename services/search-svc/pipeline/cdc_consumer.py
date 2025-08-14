"""
CDC Consumer for Search Pipeline

Consumes change data capture events from PostgreSQL outbox pattern
and processes them for OpenSearch indexing with RBAC filtering.
"""
import asyncio
import json
import logging
from datetime import datetime
from typing import Dict, List, Optional, Any, Set
from dataclasses import dataclass
from enum import Enum
import asyncpg
from opensearchpy import AsyncOpenSearch, helpers
from .transform import DataTransformer, RBACFilter
from .analyzers import AnalyzerManager

logger = logging.getLogger(__name__)


class EventType(str, Enum):
    """Change data capture event types."""
    INSERT = "INSERT"
    UPDATE = "UPDATE" 
    DELETE = "DELETE"


@dataclass
class OutboxEvent:
    """Represents an outbox event from PostgreSQL."""
    id: str
    aggregate_id: str
    aggregate_type: str
    event_type: EventType
    event_data: Dict[str, Any]
    created_at: datetime
    processed_at: Optional[datetime] = None


class CDCConsumer:
    """
    Change Data Capture consumer for search indexing pipeline.
    
    Consumes events from PostgreSQL outbox table, transforms data with RBAC,
    and indexes to OpenSearch with subject-specific analyzers.
    """
    
    def __init__(
        self,
        postgres_url: str,
        opensearch_config: Dict[str, Any],
        batch_size: int = 100,
        poll_interval: int = 5
    ):
        self.postgres_url = postgres_url
        self.opensearch_config = opensearch_config
        self.batch_size = batch_size
        self.poll_interval = poll_interval
        
        # Components
        self.transformer = DataTransformer()
        self.rbac_filter = RBACFilter()
        self.analyzer_manager = AnalyzerManager()
        
        # Client connections
        self.pg_pool: Optional[asyncpg.Pool] = None
        self.opensearch: Optional[AsyncOpenSearch] = None
        
        # Processing state
        self.last_processed_id: Optional[str] = None
        self.running = False
        
        # Metrics tracking
        self.events_processed = 0
        self.events_failed = 0
        self.batches_processed = 0
        
    async def initialize(self):
        """Initialize database connections and OpenSearch indices."""
        try:
            # Initialize PostgreSQL connection pool
            self.pg_pool = await asyncpg.create_pool(
                self.postgres_url,
                min_size=2,
                max_size=10,
                command_timeout=60
            )
            
            # Initialize OpenSearch client
            self.opensearch = AsyncOpenSearch(
                hosts=self.opensearch_config.get("hosts", ["localhost:9200"]),
                http_auth=self.opensearch_config.get("auth"),
                use_ssl=self.opensearch_config.get("use_ssl", False),
                verify_certs=self.opensearch_config.get("verify_certs", False),
                timeout=30
            )
            
            # Setup indices and analyzers
            await self.setup_indices()
            
            # Load last processed position
            await self.load_checkpoint()
            
            logger.info("CDC Consumer initialized successfully")
            
        except Exception as e:
            logger.error(f"Failed to initialize CDC Consumer: {e}")
            raise
    
    async def setup_indices(self):
        """Setup OpenSearch indices with subject-specific analyzers."""
        indices_config = {
            "learners": {
                "mappings": {
                    "properties": {
                        "id": {"type": "keyword"},
                        "name": {
                            "type": "text",
                            "analyzer": "standard_analyzer",
                            "fields": {
                                "suggest": {
                                    "type": "completion",
                                    "analyzer": "edge_ngram_analyzer"
                                }
                            }
                        },
                        "email": {"type": "keyword"},
                        "grade_level": {"type": "keyword"},
                        "status": {"type": "keyword"},
                        "subjects": {"type": "keyword"},
                        "school_id": {"type": "keyword"},
                        "tenant_id": {"type": "keyword"},
                        "created_at": {"type": "date"},
                        "updated_at": {"type": "date"},
                        # RBAC fields
                        "visible_to_roles": {"type": "keyword"},
                        "restricted_fields": {"type": "keyword"}
                    }
                },
                "settings": self.analyzer_manager.get_index_settings("general")
            },
            
            "lessons": {
                "mappings": {
                    "properties": {
                        "id": {"type": "keyword"},
                        "title": {
                            "type": "text",
                            "analyzer": "standard_analyzer",
                            "fields": {
                                "suggest": {
                                    "type": "completion",
                                    "analyzer": "edge_ngram_analyzer"
                                }
                            }
                        },
                        "description": {"type": "text", "analyzer": "standard_analyzer"},
                        "subject": {"type": "keyword"},
                        "grade_level": {"type": "keyword"},
                        "topics": {"type": "keyword"},
                        "content": {
                            "type": "text",
                            "analyzer": "subject_analyzer"  # Dynamic based on subject
                        },
                        "difficulty": {"type": "keyword"},
                        "duration_minutes": {"type": "integer"},
                        "status": {"type": "keyword"},
                        "created_by": {"type": "keyword"},
                        "tenant_id": {"type": "keyword"},
                        "created_at": {"type": "date"},
                        "updated_at": {"type": "date"},
                        # RBAC fields
                        "visible_to_roles": {"type": "keyword"},
                        "access_level": {"type": "keyword"}
                    }
                },
                "settings": self.analyzer_manager.get_index_settings("general")
            },
            
            "assessments": {
                "mappings": {
                    "properties": {
                        "id": {"type": "keyword"},
                        "title": {
                            "type": "text", 
                            "analyzer": "standard_analyzer",
                            "fields": {
                                "suggest": {"type": "completion"}
                            }
                        },
                        "description": {"type": "text"},
                        "subject": {"type": "keyword"},
                        "questions": {
                            "type": "nested",
                            "properties": {
                                "id": {"type": "keyword"},
                                "text": {"type": "text", "analyzer": "subject_analyzer"},
                                "type": {"type": "keyword"},
                                "difficulty": {"type": "keyword"}
                            }
                        },
                        "grade_levels": {"type": "keyword"},
                        "standards": {"type": "keyword"},
                        "status": {"type": "keyword"},
                        "tenant_id": {"type": "keyword"},
                        "created_at": {"type": "date"},
                        "updated_at": {"type": "date"},
                        # RBAC fields
                        "visible_to_roles": {"type": "keyword"},
                        "data_sensitivity": {"type": "keyword"}
                    }
                },
                "settings": self.analyzer_manager.get_index_settings("general")
            }
        }
        
        # Create indices if they don't exist
        for index_name, config in indices_config.items():
            try:
                if not await self.opensearch.indices.exists(index=index_name):
                    await self.opensearch.indices.create(
                        index=index_name,
                        body=config
                    )
                    logger.info(f"Created OpenSearch index: {index_name}")
                else:
                    # Update settings and mappings
                    await self.opensearch.indices.put_settings(
                        index=index_name,
                        body={"settings": config["settings"]}
                    )
                    await self.opensearch.indices.put_mapping(
                        index=index_name,
                        body=config["mappings"]
                    )
                    logger.info(f"Updated OpenSearch index: {index_name}")
                    
            except Exception as e:
                logger.error(f"Failed to setup index {index_name}: {e}")
                raise
    
    async def load_checkpoint(self):
        """Load the last processed event ID from checkpoint table."""
        if not self.pg_pool:
            return
            
        try:
            async with self.pg_pool.acquire() as conn:
                result = await conn.fetchval(
                    """
                    SELECT last_processed_id FROM cdc_checkpoint 
                    WHERE consumer_name = $1
                    """,
                    "search-indexer"
                )
                self.last_processed_id = result
                logger.info(f"Loaded checkpoint: {self.last_processed_id}")
                
        except Exception as e:
            logger.warning(f"Failed to load checkpoint: {e}")
            self.last_processed_id = None
    
    async def save_checkpoint(self, event_id: str):
        """Save the last processed event ID to checkpoint table."""
        if not self.pg_pool:
            return
            
        try:
            async with self.pg_pool.acquire() as conn:
                await conn.execute(
                    """
                    INSERT INTO cdc_checkpoint (consumer_name, last_processed_id, updated_at)
                    VALUES ($1, $2, NOW())
                    ON CONFLICT (consumer_name) 
                    DO UPDATE SET last_processed_id = $2, updated_at = NOW()
                    """,
                    "search-indexer",
                    event_id
                )
                self.last_processed_id = event_id
                
        except Exception as e:
            logger.error(f"Failed to save checkpoint: {e}")
    
    async def start(self):
        """Start the CDC consumer loop."""
        if self.running:
            logger.warning("CDC Consumer is already running")
            return
            
        self.running = True
        logger.info("Starting CDC Consumer")
        
        try:
            while self.running:
                try:
                    # Fetch batch of events
                    events = await self.fetch_events()
                    
                    if events:
                        # Process batch
                        await self.process_batch(events)
                        
                        # Update checkpoint
                        last_event = events[-1]
                        await self.save_checkpoint(last_event.id)
                        
                        self.batches_processed += 1
                        logger.info(f"Processed batch of {len(events)} events")
                    else:
                        # No events, wait before polling again
                        await asyncio.sleep(self.poll_interval)
                        
                except Exception as e:
                    logger.error(f"Error in CDC consumer loop: {e}")
                    await asyncio.sleep(self.poll_interval * 2)  # Back-off
                    
        finally:
            self.running = False
            logger.info("CDC Consumer stopped")
    
    async def stop(self):
        """Stop the CDC consumer."""
        self.running = False
        logger.info("Stopping CDC Consumer")
    
    async def fetch_events(self) -> List[OutboxEvent]:
        """Fetch unprocessed events from outbox table."""
        if not self.pg_pool:
            return []
        
        query = """
            SELECT id, aggregate_id, aggregate_type, event_type, event_data, created_at
            FROM outbox_events 
            WHERE processed_at IS NULL
        """
        params = []
        
        if self.last_processed_id:
            query += " AND id > $1"
            params.append(self.last_processed_id)
        
        query += " ORDER BY id LIMIT $" + str(len(params) + 1)
        params.append(self.batch_size)
        
        try:
            async with self.pg_pool.acquire() as conn:
                rows = await conn.fetch(query, *params)
                
                events = []
                for row in rows:
                    event = OutboxEvent(
                        id=row["id"],
                        aggregate_id=row["aggregate_id"],
                        aggregate_type=row["aggregate_type"],
                        event_type=EventType(row["event_type"]),
                        event_data=json.loads(row["event_data"]),
                        created_at=row["created_at"]
                    )
                    events.append(event)
                
                return events
                
        except Exception as e:
            logger.error(f"Failed to fetch events: {e}")
            return []
    
    async def process_batch(self, events: List[OutboxEvent]):
        """Process a batch of outbox events."""
        if not self.opensearch:
            return
        
        # Group events by aggregate type for efficient processing
        events_by_type: Dict[str, List[OutboxEvent]] = {}
        for event in events:
            if event.aggregate_type not in events_by_type:
                events_by_type[event.aggregate_type] = []
            events_by_type[event.aggregate_type].append(event)
        
        # Process each aggregate type
        for aggregate_type, type_events in events_by_type.items():
            try:
                await self.process_events_by_type(aggregate_type, type_events)
                
            except Exception as e:
                logger.error(f"Failed to process {aggregate_type} events: {e}")
                self.events_failed += len(type_events)
                # Continue processing other types
    
    async def process_events_by_type(self, aggregate_type: str, events: List[OutboxEvent]):
        """Process events for a specific aggregate type."""
        index_name = self.get_index_name(aggregate_type)
        if not index_name:
            logger.warning(f"No index mapping for aggregate type: {aggregate_type}")
            return
        
        # Prepare bulk operations
        bulk_ops = []
        
        for event in events:
            try:
                # Transform data based on event type
                if event.event_type == EventType.DELETE:
                    # Delete document
                    bulk_ops.append({
                        "_op_type": "delete",
                        "_index": index_name,
                        "_id": event.aggregate_id
                    })
                else:
                    # Transform and filter data
                    transformed_data = await self.transform_event_data(
                        aggregate_type, 
                        event.event_data
                    )
                    
                    if transformed_data:  # May be None if filtered out by RBAC
                        # Apply subject-specific analyzers
                        analyzed_data = self.analyzer_manager.enhance_document(
                            transformed_data,
                            aggregate_type
                        )
                        
                        bulk_ops.append({
                            "_op_type": "index",
                            "_index": index_name,
                            "_id": event.aggregate_id,
                            "_source": analyzed_data
                        })
                
                self.events_processed += 1
                
            except Exception as e:
                logger.error(f"Failed to process event {event.id}: {e}")
                self.events_failed += 1
        
        # Execute bulk operations
        if bulk_ops:
            try:
                response = await helpers.async_bulk(
                    self.opensearch,
                    bulk_ops,
                    refresh=True
                )
                
                # Check for errors
                if response[1]:  # Errors occurred
                    logger.warning(f"Bulk operation had {len(response[1])} errors")
                    for error in response[1][:5]:  # Log first 5 errors
                        logger.error(f"Bulk error: {error}")
                
                logger.info(f"Bulk indexed {len(bulk_ops)} documents to {index_name}")
                
            except Exception as e:
                logger.error(f"Bulk indexing failed: {e}")
                raise
    
    async def transform_event_data(self, aggregate_type: str, event_data: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Transform and filter event data for indexing."""
        try:
            # Apply data transformations
            transformed = self.transformer.transform(aggregate_type, event_data)
            
            # Apply RBAC filtering
            filtered = await self.rbac_filter.filter_document(
                aggregate_type,
                transformed
            )
            
            return filtered
            
        except Exception as e:
            logger.error(f"Data transformation failed: {e}")
            return None
    
    def get_index_name(self, aggregate_type: str) -> Optional[str]:
        """Map aggregate type to OpenSearch index name."""
        mapping = {
            "learner": "learners",
            "lesson": "lessons", 
            "assessment": "assessments",
            "user": "learners",  # Users go to learners index
            "course": "lessons"   # Courses go to lessons index
        }
        return mapping.get(aggregate_type.lower())
    
    async def health_check(self) -> Dict[str, Any]:
        """Return health status and metrics."""
        pg_healthy = self.pg_pool is not None and not self.pg_pool._closed
        
        opensearch_healthy = False
        try:
            if self.opensearch:
                await self.opensearch.ping()
                opensearch_healthy = True
        except:
            pass
        
        return {
            "status": "healthy" if (pg_healthy and opensearch_healthy) else "unhealthy",
            "components": {
                "postgresql": "healthy" if pg_healthy else "unhealthy",
                "opensearch": "healthy" if opensearch_healthy else "unhealthy"
            },
            "metrics": {
                "events_processed": self.events_processed,
                "events_failed": self.events_failed,
                "batches_processed": self.batches_processed,
                "last_processed_id": self.last_processed_id
            },
            "running": self.running
        }
    
    async def close(self):
        """Clean up resources."""
        self.running = False
        
        if self.opensearch:
            await self.opensearch.close()
        
        if self.pg_pool:
            await self.pg_pool.close()
