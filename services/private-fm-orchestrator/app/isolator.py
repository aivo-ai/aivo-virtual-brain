"""
Isolation and namespace management for Private Foundation Model Orchestrator.
"""

import asyncio
import hashlib
import json
import os
import time
from datetime import datetime, timezone, timedelta
from typing import Dict, List, Optional, Any, Tuple
from uuid import UUID, uuid4

import structlog
from cryptography.fernet import Fernet
from sqlalchemy import select, and_, desc
from sqlalchemy.ext.asyncio import AsyncSession
from tenacity import retry, stop_after_attempt, wait_exponential

from .models import (
    LearnerNamespace, 
    MergeOperation,
    EventLog,
    NamespaceStatus,
    MergeStatus,
    FallbackReason,
    CheckpointInfo,
    NamespaceHealth
)

logger = structlog.get_logger()


class NamespaceIsolator:
    """Manages namespace isolation and lifecycle operations."""
    
    def __init__(self, db_session: AsyncSession, redis_client, fm_store_client, encryption_key: str):
        self.db = db_session
        self.redis = redis_client
        self.fm_store = fm_store_client
        self.cipher_suite = Fernet(encryption_key.encode() if isinstance(encryption_key, str) else encryption_key)
        self.logger = logger.bind(component="isolator")
        
        # Configuration
        self.max_version_lag = int(os.getenv("MAX_VERSION_LAG", "3"))
        self.checkpoint_retention_days = int(os.getenv("CHECKPOINT_RETENTION_DAYS", "30"))
        self.max_namespace_size_gb = float(os.getenv("MAX_NAMESPACE_SIZE_GB", "10.0"))

    async def create_namespace(
        self, 
        learner_id: UUID, 
        subjects: List[str], 
        base_fm_version: str,
        isolation_config: Optional[Dict[str, Any]] = None,
        merge_config: Optional[Dict[str, Any]] = None
    ) -> LearnerNamespace:
        """Create a new isolated namespace for a learner."""
        self.logger.info("Creating namespace", learner_id=str(learner_id), subjects=subjects)
        
        # Generate unique namespace identifier
        ns_uid = self._generate_namespace_uid(learner_id, subjects)
        
        # Default configurations
        default_isolation_config = {
            "memory_limit_mb": 2048,
            "cpu_limit_cores": 2.0,
            "storage_limit_gb": self.max_namespace_size_gb,
            "network_isolation": True,
            "encryption_enabled": True
        }
        
        default_merge_config = {
            "merge_strategy": "incremental",
            "batch_size": 1000,
            "learning_rate": 0.0001,
            "adapter_rank": 8,
            "validation_steps": 100
        }
        
        isolation_config = {**default_isolation_config, **(isolation_config or {})}
        merge_config = {**default_merge_config, **(merge_config or {})}
        
        # Create namespace record
        namespace = LearnerNamespace(
            learner_id=learner_id,
            ns_uid=ns_uid,
            status=NamespaceStatus.INITIALIZING,
            subjects=subjects,
            base_fm_version=base_fm_version,
            isolation_config=isolation_config,
            merge_config=merge_config
        )
        
        self.db.add(namespace)
        await self.db.flush()  # Get the ID
        
        # Log creation event
        await self._log_event(
            namespace.id,
            learner_id,
            "namespace_created",
            {
                "ns_uid": ns_uid,
                "subjects": subjects,
                "base_fm_version": base_fm_version,
                "isolation_config": isolation_config
            }
        )
        
        # Initialize namespace resources
        await self._initialize_namespace_resources(namespace)
        
        # Set status to active
        namespace.status = NamespaceStatus.ACTIVE
        
        await self.db.commit()
        
        self.logger.info("Namespace created successfully", 
                        namespace_id=str(namespace.id), 
                        ns_uid=ns_uid)
        
        return namespace

    async def get_namespace(self, learner_id: UUID) -> Optional[LearnerNamespace]:
        """Get namespace for a learner."""
        result = await self.db.execute(
            select(LearnerNamespace).where(LearnerNamespace.learner_id == learner_id)
        )
        return result.scalar_one_or_none()

    async def delete_namespace(self, learner_id: UUID, guardian_key: str) -> bool:
        """Delete a namespace (guardian only operation)."""
        self.logger.info("Attempting namespace deletion", learner_id=str(learner_id))
        
        # Verify guardian authorization (simplified - in production would verify JWT/API key)
        expected_guardian_key = os.getenv("GUARDIAN_API_KEY")
        if not expected_guardian_key or guardian_key != expected_guardian_key:
            self.logger.warning("Unauthorized namespace deletion attempt", 
                              learner_id=str(learner_id))
            return False
        
        namespace = await self.get_namespace(learner_id)
        if not namespace:
            return False
        
        # Log deletion event
        await self._log_event(
            namespace.id,
            learner_id,
            "namespace_deleted",
            {"guardian_authorized": True},
            created_by="guardian"
        )
        
        # Cleanup resources
        await self._cleanup_namespace_resources(namespace)
        
        # Mark as deleted (soft delete for audit trail)
        namespace.status = NamespaceStatus.DELETED
        namespace.updated_at = datetime.now(timezone.utc)
        
        await self.db.commit()
        
        self.logger.info("Namespace deleted", namespace_id=str(namespace.id))
        return True

    async def trigger_merge(
        self,
        learner_id: UUID,
        operation_type: str = "manual",
        target_fm_version: Optional[str] = None,
        force: bool = False
    ) -> MergeOperation:
        """Trigger a merge operation for a namespace."""
        namespace = await self.get_namespace(learner_id)
        if not namespace:
            raise ValueError(f"Namespace not found for learner {learner_id}")
        
        if namespace.status != NamespaceStatus.ACTIVE and not force:
            raise ValueError(f"Namespace not in active state: {namespace.status}")
        
        # Check for recent merge operations
        if not force:
            recent_merge = await self._get_recent_merge_operation(namespace.id)
            if recent_merge and (datetime.now(timezone.utc) - recent_merge.created_at).hours < 1:
                raise ValueError("Recent merge operation found, use force=True to override")
        
        # Use current FM version if not specified
        if not target_fm_version:
            target_fm_version = await self._get_latest_fm_version()
        
        # Create merge operation
        merge_op = MergeOperation(
            namespace_id=namespace.id,
            learner_id=learner_id,
            status=MergeStatus.PENDING,
            operation_type=operation_type,
            source_checkpoint_hash=namespace.current_checkpoint_hash,
            fm_version=target_fm_version,
            scheduled_at=datetime.now(timezone.utc)
        )
        
        self.db.add(merge_op)
        await self.db.flush()
        
        # Log merge initiation
        await self._log_event(
            namespace.id,
            learner_id,
            "merge_initiated",
            {
                "operation_id": str(merge_op.id),
                "operation_type": operation_type,
                "target_fm_version": target_fm_version,
                "source_checkpoint": namespace.current_checkpoint_hash
            }
        )
        
        # Queue merge operation
        await self._queue_merge_operation(merge_op.id)
        
        await self.db.commit()
        return merge_op

    @retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, min=4, max=10))
    async def execute_merge(self, merge_op_id: UUID) -> bool:
        """Execute a merge operation."""
        merge_op = await self._get_merge_operation(merge_op_id)
        if not merge_op:
            self.logger.error("Merge operation not found", operation_id=str(merge_op_id))
            return False
        
        namespace = await self.get_namespace(merge_op.learner_id)
        if not namespace:
            self.logger.error("Namespace not found for merge", learner_id=str(merge_op.learner_id))
            return False
        
        self.logger.info("Starting merge execution", 
                        operation_id=str(merge_op_id),
                        namespace_id=str(namespace.id))
        
        try:
            # Update status
            merge_op.status = MergeStatus.RUNNING
            merge_op.started_at = datetime.now(timezone.utc)
            namespace.status = NamespaceStatus.MERGING
            await self.db.commit()
            
            # Simulate merge process with stages
            stages = [
                ("Loading foundation model", 20),
                ("Loading namespace adapters", 40), 
                ("Performing merge", 70),
                ("Generating checkpoint", 90),
                ("Finalizing", 100)
            ]
            
            merge_stats = {"start_time": time.time()}
            
            for stage_name, progress in stages:
                merge_op.stage = stage_name
                merge_op.progress_percent = progress
                await self.db.commit()
                
                # Simulate work
                await asyncio.sleep(2)
                
                self.logger.debug("Merge progress", 
                                stage=stage_name, 
                                progress=progress,
                                operation_id=str(merge_op_id))
            
            # Generate new checkpoint
            new_checkpoint_hash = self._generate_checkpoint_hash(
                namespace.id, 
                merge_op.fm_version, 
                namespace.version_count + 1
            )
            
            # Simulate storing checkpoint
            checkpoint_size = await self._simulate_checkpoint_storage(
                namespace.id, 
                new_checkpoint_hash,
                merge_op.fm_version
            )
            
            merge_stats.update({
                "end_time": time.time(),
                "checkpoint_size_bytes": checkpoint_size,
                "adapters_merged": len(namespace.subjects) * 10,  # Simulated
                "parameters_updated": 1250000  # Simulated
            })
            
            # Update operation and namespace
            merge_op.status = MergeStatus.COMPLETED
            merge_op.target_checkpoint_hash = new_checkpoint_hash
            merge_op.completed_at = datetime.now(timezone.utc)
            merge_op.merge_stats = merge_stats
            merge_op.progress_percent = 100
            
            namespace.current_checkpoint_hash = new_checkpoint_hash
            namespace.version_count += 1
            namespace.last_merge_at = datetime.now(timezone.utc)
            namespace.status = NamespaceStatus.ACTIVE
            namespace.updated_at = datetime.now(timezone.utc)
            
            # Log successful merge
            await self._log_event(
                namespace.id,
                namespace.learner_id,
                "merge_completed",
                {
                    "operation_id": str(merge_op.id),
                    "new_checkpoint_hash": new_checkpoint_hash,
                    "version": namespace.version_count,
                    "merge_stats": merge_stats
                },
                checkpoint_hash=new_checkpoint_hash
            )
            
            await self.db.commit()
            
            self.logger.info("Merge completed successfully",
                           operation_id=str(merge_op_id),
                           new_checkpoint=new_checkpoint_hash,
                           version=namespace.version_count)
            
            return True
            
        except Exception as e:
            self.logger.error("Merge operation failed", 
                            operation_id=str(merge_op_id),
                            error=str(e))
            
            # Update operation status
            merge_op.status = MergeStatus.FAILED
            merge_op.error_message = str(e)
            merge_op.completed_at = datetime.now(timezone.utc)
            namespace.status = NamespaceStatus.ACTIVE  # Return to active state
            
            await self._log_event(
                namespace.id,
                namespace.learner_id,
                "merge_failed",
                {
                    "operation_id": str(merge_op.id),
                    "error": str(e)
                }
            )
            
            await self.db.commit()
            return False

    async def check_namespace_health(self, learner_id: UUID) -> NamespaceHealth:
        """Check the health status of a namespace."""
        namespace = await self.get_namespace(learner_id)
        if not namespace:
            raise ValueError(f"Namespace not found for learner {learner_id}")
        
        issues = []
        recommendations = []
        
        # Check version lag
        latest_fm_version = await self._get_latest_fm_version()
        version_lag = await self._calculate_version_lag(namespace.base_fm_version, latest_fm_version)
        
        if version_lag > self.max_version_lag:
            issues.append(f"Version lag of {version_lag} exceeds maximum of {self.max_version_lag}")
            recommendations.append("Consider triggering fallback recovery")
        
        # Check last merge time
        last_merge_ago_hours = None
        if namespace.last_merge_at:
            last_merge_ago_hours = int((datetime.now(timezone.utc) - namespace.last_merge_at).total_seconds() / 3600)
            if last_merge_ago_hours > 48:  # 48 hours
                issues.append(f"No merge in {last_merge_ago_hours} hours")
                recommendations.append("Schedule a merge operation")
        
        # Check checkpoint integrity
        integrity_score = 1.0
        if namespace.current_checkpoint_hash:
            integrity_verified = await self._verify_checkpoint_integrity(namespace.current_checkpoint_hash)
            if not integrity_verified:
                integrity_score = 0.0
                issues.append("Checkpoint integrity verification failed")
                recommendations.append("Immediate fallback recovery required")
        
        # Determine overall health
        is_healthy = (
            len(issues) == 0 and
            namespace.status == NamespaceStatus.ACTIVE and
            version_lag <= self.max_version_lag
        )
        
        return NamespaceHealth(
            namespace_id=namespace.id,
            learner_id=learner_id,
            status=namespace.status,
            is_healthy=is_healthy,
            last_merge_ago_hours=last_merge_ago_hours,
            version_lag=version_lag,
            integrity_score=integrity_score,
            issues=issues,
            recommendations=recommendations
        )

    async def initiate_fallback_recovery(
        self,
        learner_id: UUID,
        reason: FallbackReason,
        target_fm_version: Optional[str] = None
    ) -> UUID:
        """Initiate fallback recovery for a corrupted or lagged namespace."""
        namespace = await self.get_namespace(learner_id)
        if not namespace:
            raise ValueError(f"Namespace not found for learner {learner_id}")
        
        self.logger.info("Initiating fallback recovery",
                        learner_id=str(learner_id),
                        reason=reason.value)
        
        # Generate operation ID
        operation_id = uuid4()
        
        # Use latest FM version if not specified
        if not target_fm_version:
            target_fm_version = await self._get_latest_fm_version()
        
        # Count events to replay
        events_to_replay = await self._count_events_for_replay(namespace.id)
        
        # Update namespace status
        namespace.status = NamespaceStatus.FALLBACK
        namespace.last_fallback_at = datetime.now(timezone.utc)
        namespace.updated_at = datetime.now(timezone.utc)
        
        # Log fallback initiation
        await self._log_event(
            namespace.id,
            learner_id,
            "fallback_initiated",
            {
                "operation_id": str(operation_id),
                "reason": reason.value,
                "target_fm_version": target_fm_version,
                "events_to_replay": events_to_replay
            }
        )
        
        # Queue fallback operation
        await self._queue_fallback_operation(operation_id, namespace.id, target_fm_version, reason)
        
        await self.db.commit()
        
        return operation_id

    # Private helper methods
    
    def _generate_namespace_uid(self, learner_id: UUID, subjects: List[str]) -> str:
        """Generate unique namespace identifier."""
        data = f"{learner_id}:{':'.join(sorted(subjects))}:{int(time.time())}"
        return hashlib.sha256(data.encode()).hexdigest()[:16]
    
    def _generate_checkpoint_hash(self, namespace_id: UUID, fm_version: str, version: int) -> str:
        """Generate checkpoint hash."""
        data = f"{namespace_id}:{fm_version}:{version}:{int(time.time())}"
        return hashlib.sha256(data.encode()).hexdigest()
    
    async def _initialize_namespace_resources(self, namespace: LearnerNamespace) -> None:
        """Initialize namespace resources (simulated)."""
        # In a real implementation, this would:
        # - Allocate compute resources
        # - Set up network isolation
        # - Initialize storage volumes
        # - Configure security policies
        
        resource_key = f"namespace:{namespace.ns_uid}:resources"
        resources = {
            "cpu_quota": namespace.isolation_config.get("cpu_limit_cores", 2.0),
            "memory_limit": namespace.isolation_config.get("memory_limit_mb", 2048),
            "storage_quota": namespace.isolation_config.get("storage_limit_gb", 10.0),
            "network_isolated": namespace.isolation_config.get("network_isolation", True),
            "created_at": datetime.now(timezone.utc).isoformat()
        }
        
        await self.redis.hset(resource_key, mapping={
            k: json.dumps(v) if not isinstance(v, str) else v 
            for k, v in resources.items()
        })
        await self.redis.expire(resource_key, 86400 * 7)  # 7 days
    
    async def _cleanup_namespace_resources(self, namespace: LearnerNamespace) -> None:
        """Cleanup namespace resources."""
        resource_key = f"namespace:{namespace.ns_uid}:resources"
        await self.redis.delete(resource_key)
        
        # Cleanup checkpoints (simulated)
        checkpoint_pattern = f"checkpoint:{namespace.id}:*"
        keys = await self.redis.keys(checkpoint_pattern)
        if keys:
            await self.redis.delete(*keys)
    
    async def _log_event(
        self,
        namespace_id: UUID,
        learner_id: UUID,
        event_type: str,
        event_data: Dict[str, Any],
        checkpoint_hash: Optional[str] = None,
        correlation_id: Optional[str] = None,
        created_by: str = "system"
    ) -> None:
        """Log an event for audit and replay purposes."""
        # Get next sequence number
        sequence_number = await self._get_next_sequence_number(namespace_id)
        
        event_log = EventLog(
            namespace_id=namespace_id,
            learner_id=learner_id,
            event_type=event_type,
            event_data=event_data,
            checkpoint_hash=checkpoint_hash,
            sequence_number=sequence_number,
            correlation_id=correlation_id or str(uuid4()),
            created_by=created_by
        )
        
        self.db.add(event_log)
    
    async def _get_next_sequence_number(self, namespace_id: UUID) -> int:
        """Get the next sequence number for a namespace."""
        result = await self.db.execute(
            select(EventLog.sequence_number)
            .where(EventLog.namespace_id == namespace_id)
            .order_by(desc(EventLog.sequence_number))
            .limit(1)
        )
        last_seq = result.scalar_one_or_none()
        return (last_seq or 0) + 1
    
    async def _get_recent_merge_operation(self, namespace_id: UUID) -> Optional[MergeOperation]:
        """Get the most recent merge operation for a namespace."""
        result = await self.db.execute(
            select(MergeOperation)
            .where(MergeOperation.namespace_id == namespace_id)
            .order_by(desc(MergeOperation.created_at))
            .limit(1)
        )
        return result.scalar_one_or_none()
    
    async def _get_merge_operation(self, merge_op_id: UUID) -> Optional[MergeOperation]:
        """Get a merge operation by ID."""
        result = await self.db.execute(
            select(MergeOperation).where(MergeOperation.id == merge_op_id)
        )
        return result.scalar_one_or_none()
    
    async def _get_latest_fm_version(self) -> str:
        """Get the latest foundation model version."""
        # Simulated - in real implementation would query model registry
        return "fm-v2.3.1"
    
    async def _calculate_version_lag(self, current_version: str, latest_version: str) -> int:
        """Calculate version lag between current and latest versions."""
        # Simplified version comparison - in real implementation would use semantic versioning
        try:
            current_parts = [int(x) for x in current_version.split('-v')[1].split('.')]
            latest_parts = [int(x) for x in latest_version.split('-v')[1].split('.')]
            
            # Simple version difference calculation
            return sum(latest_parts) - sum(current_parts)
        except (IndexError, ValueError):
            return 0
    
    async def _verify_checkpoint_integrity(self, checkpoint_hash: str) -> bool:
        """Verify checkpoint integrity."""
        # Simulated integrity check
        checkpoint_key = f"checkpoint:{checkpoint_hash}:integrity"
        integrity_data = await self.redis.get(checkpoint_key)
        return integrity_data is not None
    
    async def _simulate_checkpoint_storage(self, namespace_id: UUID, checkpoint_hash: str, fm_version: str) -> int:
        """Simulate storing a checkpoint."""
        checkpoint_data = {
            "namespace_id": str(namespace_id),
            "hash": checkpoint_hash,
            "fm_version": fm_version,
            "created_at": datetime.now(timezone.utc).isoformat(),
            "size_bytes": 1024 * 1024 * 50  # Simulate 50MB checkpoint
        }
        
        checkpoint_key = f"checkpoint:{checkpoint_hash}"
        await self.redis.hset(checkpoint_key, mapping=checkpoint_data)
        await self.redis.expire(checkpoint_key, 86400 * self.checkpoint_retention_days)
        
        # Store integrity marker
        integrity_key = f"checkpoint:{checkpoint_hash}:integrity"
        await self.redis.set(integrity_key, "verified", ex=86400 * self.checkpoint_retention_days)
        
        return checkpoint_data["size_bytes"]
    
    async def _count_events_for_replay(self, namespace_id: UUID) -> int:
        """Count events that would need to be replayed."""
        result = await self.db.execute(
            select(EventLog.id)
            .where(EventLog.namespace_id == namespace_id)
        )
        return len(result.all())
    
    async def _queue_merge_operation(self, merge_op_id: UUID) -> None:
        """Queue a merge operation for execution."""
        # In a real implementation, this would use Celery or similar
        await self.redis.lpush("merge_queue", str(merge_op_id))
    
    async def _queue_fallback_operation(
        self,
        operation_id: UUID,
        namespace_id: UUID,
        target_fm_version: str,
        reason: FallbackReason
    ) -> None:
        """Queue a fallback operation for execution."""
        fallback_data = {
            "operation_id": str(operation_id),
            "namespace_id": str(namespace_id),
            "target_fm_version": target_fm_version,
            "reason": reason.value
        }
        await self.redis.lpush("fallback_queue", json.dumps(fallback_data))

    # Adapter Reset Methods (S5-08)
    async def delete_subject_adapter(self, learner_id: UUID, subject: str) -> bool:
        """
        Delete the existing adapter for a specific subject.
        
        Args:
            learner_id: The learner's unique identifier
            subject: The subject to delete the adapter for
            
        Returns:
            bool: True if deletion was successful
        """
        try:
            self.logger.info(
                "Deleting subject adapter",
                learner_id=str(learner_id),
                subject=subject
            )
            
            # Get namespace
            namespace = await self.get_namespace(learner_id)
            if not namespace:
                raise ValueError(f"Namespace not found for learner {learner_id}")
            
            # Delete subject-specific model files and checkpoints
            adapter_key = f"adapter:{namespace.ns_uid}:{subject}"
            checkpoint_pattern = f"checkpoint:{namespace.ns_uid}:{subject}:*"
            
            # Remove from foundation model store
            await self.fm_store.delete(adapter_key)
            
            # Clean up checkpoints
            checkpoint_keys = await self.fm_store.list_keys(checkpoint_pattern)
            for key in checkpoint_keys:
                await self.fm_store.delete(key)
            
            # Remove from Redis cache
            cache_key = f"model_cache:{learner_id}:{subject}"
            await self.redis.delete(cache_key)
            
            self.logger.info(
                "Subject adapter deleted successfully",
                learner_id=str(learner_id),
                subject=subject,
                files_deleted=len(checkpoint_keys) + 1
            )
            
            return True
            
        except Exception as e:
            self.logger.error(
                "Failed to delete subject adapter",
                learner_id=str(learner_id),
                subject=subject,
                error=str(e)
            )
            raise

    async def clone_base_model_for_subject(self, learner_id: UUID, subject: str) -> bool:
        """
        Re-clone the base foundation model for a specific subject.
        
        Args:
            learner_id: The learner's unique identifier
            subject: The subject to clone the base model for
            
        Returns:
            bool: True if cloning was successful
        """
        try:
            self.logger.info(
                "Cloning base foundation model",
                learner_id=str(learner_id),
                subject=subject
            )
            
            # Get namespace
            namespace = await self.get_namespace(learner_id)
            if not namespace:
                raise ValueError(f"Namespace not found for learner {learner_id}")
            
            # Get the base foundation model for this subject
            base_model_key = f"base_fm:{namespace.base_fm_version}:{subject}"
            
            # Clone to subject-specific adapter location
            adapter_key = f"adapter:{namespace.ns_uid}:{subject}"
            
            # Copy base model to adapter location
            base_model_data = await self.fm_store.get(base_model_key)
            if not base_model_data:
                raise ValueError(f"Base model not found for subject {subject}")
            
            await self.fm_store.put(adapter_key, base_model_data)
            
            # Initialize training metadata
            training_metadata = {
                "created_at": datetime.now(timezone.utc).isoformat(),
                "base_fm_version": namespace.base_fm_version,
                "subject": subject,
                "learner_id": str(learner_id),
                "training_steps": 0,
                "last_checkpoint": None
            }
            
            metadata_key = f"metadata:{namespace.ns_uid}:{subject}"
            await self.fm_store.put(metadata_key, json.dumps(training_metadata))
            
            # Clear any cached data
            cache_key = f"model_cache:{learner_id}:{subject}"
            await self.redis.delete(cache_key)
            
            self.logger.info(
                "Base foundation model cloned successfully",
                learner_id=str(learner_id),
                subject=subject,
                base_fm_version=namespace.base_fm_version
            )
            
            return True
            
        except Exception as e:
            self.logger.error(
                "Failed to clone base foundation model",
                learner_id=str(learner_id),
                subject=subject,
                error=str(e)
            )
            raise

    async def replay_event(self, learner_id: UUID, subject: str, event: EventLog) -> bool:
        """
        Replay a single learner event for model training.
        
        Args:
            learner_id: The learner's unique identifier
            subject: The subject being trained
            event: The event data to replay
            
        Returns:
            bool: True if replay was successful
        """
        try:
            # Get namespace
            namespace = await self.get_namespace(learner_id)
            if not namespace:
                raise ValueError(f"Namespace not found for learner {learner_id}")
            
            # Load current adapter
            adapter_key = f"adapter:{namespace.ns_uid}:{subject}"
            
            # Apply the learning update based on event type
            update_applied = await self._apply_learning_update(
                adapter_key,
                event.event_type,
                event.event_data,
                subject
            )
            
            if update_applied:
                # Update training metadata
                metadata_key = f"metadata:{namespace.ns_uid}:{subject}"
                metadata_str = await self.fm_store.get(metadata_key)
                
                if metadata_str:
                    metadata = json.loads(metadata_str)
                    metadata["training_steps"] = metadata.get("training_steps", 0) + 1
                    metadata["last_event_replayed"] = event.id
                    metadata["last_update"] = datetime.now(timezone.utc).isoformat()
                    
                    await self.fm_store.put(metadata_key, json.dumps(metadata))
            
            return update_applied
            
        except Exception as e:
            self.logger.error(
                "Failed to replay event",
                learner_id=str(learner_id),
                subject=subject,
                event_id=str(event.id),
                error=str(e)
            )
            raise

    async def _apply_learning_update(
        self, 
        adapter_key: str, 
        event_type: str, 
        event_data: Dict[str, Any],
        subject: str
    ) -> bool:
        """
        Apply a learning update to the model based on event data.
        
        Args:
            adapter_key: Key for the adapter in storage
            event_type: Type of learning event
            event_data: Event data to apply
            subject: Subject being trained
            
        Returns:
            bool: True if update was applied
        """
        try:
            # Simulate learning update application
            # In a real implementation, this would:
            # 1. Load the current model weights
            # 2. Apply the learning update based on event_type
            # 3. Update the model parameters
            # 4. Save the updated model
            
            supported_events = [
                "PROBLEM_SOLVED",
                "ANSWER_SUBMITTED", 
                "HINT_REQUESTED",
                "MISTAKE_MADE",
                "CONCEPT_MASTERED",
                "SKILL_PRACTICED"
            ]
            
            if event_type in supported_events:
                # Simulate processing time based on event complexity
                processing_time = 0.1 if event_type in ["HINT_REQUESTED"] else 0.3
                await asyncio.sleep(processing_time)
                
                self.logger.debug(
                    "Learning update applied",
                    adapter_key=adapter_key,
                    event_type=event_type,
                    subject=subject
                )
                
                return True
            else:
                self.logger.debug(
                    "Event type not applicable for learning update",
                    event_type=event_type,
                    subject=subject
                )
                return False
                
        except Exception as e:
            self.logger.error(
                "Failed to apply learning update",
                adapter_key=adapter_key,
                event_type=event_type,
                error=str(e)
            )
            return False
