"""
Cron jobs and scheduled tasks for Private Foundation Model Orchestrator.
"""

import asyncio
import json
import os
from datetime import datetime, timezone, timedelta
from typing import List, Dict, Any
from uuid import UUID

import structlog
from sqlalchemy import select, and_, or_
from sqlalchemy.ext.asyncio import AsyncSession

from .models import (
    LearnerNamespace,
    MergeOperation,
    NamespaceStatus,
    MergeStatus,
    FallbackReason
)
from .isolator import NamespaceIsolator

logger = structlog.get_logger()


class CronScheduler:
    """Handles scheduled tasks for namespace management."""
    
    def __init__(self, db_session: AsyncSession, isolator: NamespaceIsolator, redis_client):
        self.db = db_session
        self.isolator = isolator
        self.redis = redis_client
        self.logger = logger.bind(component="cron")
        
        # Configuration
        self.nightly_merge_enabled = os.getenv("NIGHTLY_MERGE_ENABLED", "true").lower() == "true"
        self.cleanup_enabled = os.getenv("CLEANUP_ENABLED", "true").lower() == "true"
        self.health_check_enabled = os.getenv("HEALTH_CHECK_ENABLED", "true").lower() == "true"
        
        # Timing configuration
        self.merge_batch_size = int(os.getenv("MERGE_BATCH_SIZE", "10"))
        self.merge_delay_seconds = int(os.getenv("MERGE_DELAY_SECONDS", "30"))
        self.cleanup_retention_days = int(os.getenv("CLEANUP_RETENTION_DAYS", "30"))

    async def run_nightly_merge_job(self) -> Dict[str, Any]:
        """Run the nightly merge job for all active namespaces."""
        if not self.nightly_merge_enabled:
            self.logger.info("Nightly merge job disabled")
            return {"status": "disabled"}
        
        self.logger.info("Starting nightly merge job")
        start_time = datetime.now(timezone.utc)
        
        stats = {
            "namespaces_processed": 0,
            "merges_initiated": 0,
            "merges_skipped": 0,
            "errors": 0,
            "start_time": start_time.isoformat()
        }
        
        try:
            # Get active namespaces that need merging
            namespaces_to_merge = await self._get_namespaces_needing_merge()
            stats["namespaces_found"] = len(namespaces_to_merge)
            
            # Process in batches to avoid overwhelming the system
            for i in range(0, len(namespaces_to_merge), self.merge_batch_size):
                batch = namespaces_to_merge[i:i + self.merge_batch_size]
                
                # Process batch concurrently
                tasks = []
                for namespace in batch:
                    task = self._process_namespace_merge(namespace)
                    tasks.append(task)
                
                batch_results = await asyncio.gather(*tasks, return_exceptions=True)
                
                # Process results
                for result in batch_results:
                    if isinstance(result, Exception):
                        stats["errors"] += 1
                        self.logger.error("Batch merge error", error=str(result))
                    else:
                        stats["namespaces_processed"] += 1
                        if result.get("merge_initiated"):
                            stats["merges_initiated"] += 1
                        else:
                            stats["merges_skipped"] += 1
                
                # Delay between batches
                if i + self.merge_batch_size < len(namespaces_to_merge):
                    await asyncio.sleep(self.merge_delay_seconds)
            
            end_time = datetime.now(timezone.utc)
            stats["end_time"] = end_time.isoformat()
            stats["duration_minutes"] = (end_time - start_time).total_seconds() / 60
            
            self.logger.info("Nightly merge job completed", stats=stats)
            
            # Store job statistics
            await self._store_job_stats("nightly_merge", stats)
            
            return {"status": "completed", "stats": stats}
            
        except Exception as e:
            self.logger.error("Nightly merge job failed", error=str(e))
            stats["fatal_error"] = str(e)
            await self._store_job_stats("nightly_merge", stats)
            return {"status": "failed", "error": str(e), "stats": stats}

    async def run_health_check_job(self) -> Dict[str, Any]:
        """Run health checks on all namespaces and initiate fallback if needed."""
        if not self.health_check_enabled:
            self.logger.info("Health check job disabled")
            return {"status": "disabled"}
        
        self.logger.info("Starting health check job")
        start_time = datetime.now(timezone.utc)
        
        stats = {
            "namespaces_checked": 0,
            "healthy_namespaces": 0,
            "unhealthy_namespaces": 0,
            "fallbacks_initiated": 0,
            "errors": 0,
            "start_time": start_time.isoformat()
        }
        
        try:
            # Get all active namespaces
            result = await self.db.execute(
                select(LearnerNamespace)
                .where(LearnerNamespace.status.in_([
                    NamespaceStatus.ACTIVE,
                    NamespaceStatus.MERGING
                ]))
            )
            namespaces = result.scalars().all()
            
            for namespace in namespaces:
                try:
                    stats["namespaces_checked"] += 1
                    
                    # Check namespace health
                    health = await self.isolator.check_namespace_health(namespace.learner_id)
                    
                    if health.is_healthy:
                        stats["healthy_namespaces"] += 1
                    else:
                        stats["unhealthy_namespaces"] += 1
                        
                        # Determine if fallback is needed
                        needs_fallback = await self._evaluate_fallback_necessity(health)
                        
                        if needs_fallback:
                            fallback_reason = self._determine_fallback_reason(health)
                            
                            try:
                                operation_id = await self.isolator.initiate_fallback_recovery(
                                    namespace.learner_id,
                                    fallback_reason
                                )
                                stats["fallbacks_initiated"] += 1
                                
                                self.logger.warning("Fallback initiated for unhealthy namespace",
                                                  namespace_id=str(namespace.id),
                                                  learner_id=str(namespace.learner_id),
                                                  reason=fallback_reason.value,
                                                  operation_id=str(operation_id))
                            except Exception as fb_error:
                                self.logger.error("Failed to initiate fallback",
                                                namespace_id=str(namespace.id),
                                                error=str(fb_error))
                                stats["errors"] += 1
                    
                except Exception as ns_error:
                    self.logger.error("Error checking namespace health",
                                    namespace_id=str(namespace.id),
                                    error=str(ns_error))
                    stats["errors"] += 1
            
            end_time = datetime.now(timezone.utc)
            stats["end_time"] = end_time.isoformat()
            stats["duration_minutes"] = (end_time - start_time).total_seconds() / 60
            
            self.logger.info("Health check job completed", stats=stats)
            await self._store_job_stats("health_check", stats)
            
            return {"status": "completed", "stats": stats}
            
        except Exception as e:
            self.logger.error("Health check job failed", error=str(e))
            stats["fatal_error"] = str(e)
            await self._store_job_stats("health_check", stats)
            return {"status": "failed", "error": str(e), "stats": stats}

    async def run_cleanup_job(self) -> Dict[str, Any]:
        """Run cleanup job to remove old data."""
        if not self.cleanup_enabled:
            self.logger.info("Cleanup job disabled")
            return {"status": "disabled"}
        
        self.logger.info("Starting cleanup job")
        start_time = datetime.now(timezone.utc)
        
        stats = {
            "merge_operations_cleaned": 0,
            "event_logs_cleaned": 0,
            "checkpoints_cleaned": 0,
            "errors": 0,
            "start_time": start_time.isoformat()
        }
        
        try:
            cutoff_date = datetime.now(timezone.utc) - timedelta(days=self.cleanup_retention_days)
            
            # Clean up old completed merge operations
            merge_result = await self.db.execute(
                select(MergeOperation)
                .where(and_(
                    MergeOperation.status.in_([MergeStatus.COMPLETED, MergeStatus.FAILED]),
                    MergeOperation.completed_at < cutoff_date
                ))
            )
            old_merge_ops = merge_result.scalars().all()
            
            for merge_op in old_merge_ops:
                await self.db.delete(merge_op)
                stats["merge_operations_cleaned"] += 1
            
            # Clean up old event logs (keep more recent ones for audit)
            event_cutoff = datetime.now(timezone.utc) - timedelta(days=self.cleanup_retention_days * 2)
            
            from .models import EventLog
            event_result = await self.db.execute(
                select(EventLog)
                .where(EventLog.created_at < event_cutoff)
            )
            old_events = event_result.scalars().all()
            
            for event in old_events:
                await self.db.delete(event)
                stats["event_logs_cleaned"] += 1
            
            # Clean up Redis checkpoint data
            checkpoint_keys = await self.redis.keys("checkpoint:*")
            for key in checkpoint_keys:
                ttl = await self.redis.ttl(key)
                if ttl == -1:  # No expiration set
                    await self.redis.expire(key, 86400 * self.cleanup_retention_days)
                elif ttl <= 0:  # Expired
                    await self.redis.delete(key)
                    stats["checkpoints_cleaned"] += 1
            
            await self.db.commit()
            
            end_time = datetime.now(timezone.utc)
            stats["end_time"] = end_time.isoformat()
            stats["duration_minutes"] = (end_time - start_time).total_seconds() / 60
            
            self.logger.info("Cleanup job completed", stats=stats)
            await self._store_job_stats("cleanup", stats)
            
            return {"status": "completed", "stats": stats}
            
        except Exception as e:
            self.logger.error("Cleanup job failed", error=str(e))
            stats["fatal_error"] = str(e)
            await self._store_job_stats("cleanup", stats)
            return {"status": "failed", "error": str(e), "stats": stats}

    async def process_merge_queue(self) -> Dict[str, Any]:
        """Process pending merge operations from the queue."""
        stats = {
            "operations_processed": 0,
            "successful": 0,
            "failed": 0,
            "start_time": datetime.now(timezone.utc).isoformat()
        }
        
        try:
            # Process merge queue
            while True:
                # Get next merge operation from queue (blocking with timeout)
                queue_item = await self.redis.brpop("merge_queue", timeout=5)
                if not queue_item:
                    break  # No more items in queue
                
                merge_op_id = UUID(queue_item[1].decode())
                stats["operations_processed"] += 1
                
                try:
                    success = await self.isolator.execute_merge(merge_op_id)
                    if success:
                        stats["successful"] += 1
                    else:
                        stats["failed"] += 1
                except Exception as e:
                    self.logger.error("Failed to process merge operation",
                                    operation_id=str(merge_op_id),
                                    error=str(e))
                    stats["failed"] += 1
            
            stats["end_time"] = datetime.now(timezone.utc).isoformat()
            return {"status": "completed", "stats": stats}
            
        except Exception as e:
            self.logger.error("Merge queue processing failed", error=str(e))
            return {"status": "failed", "error": str(e), "stats": stats}

    async def process_fallback_queue(self) -> Dict[str, Any]:
        """Process pending fallback operations from the queue."""
        stats = {
            "operations_processed": 0,
            "successful": 0,
            "failed": 0,
            "start_time": datetime.now(timezone.utc).isoformat()
        }
        
        try:
            # Process fallback queue
            while True:
                # Get next fallback operation from queue
                queue_item = await self.redis.brpop("fallback_queue", timeout=5)
                if not queue_item:
                    break  # No more items in queue
                
                fallback_data = json.loads(queue_item[1].decode())
                stats["operations_processed"] += 1
                
                try:
                    success = await self._execute_fallback_recovery(fallback_data)
                    if success:
                        stats["successful"] += 1
                    else:
                        stats["failed"] += 1
                except Exception as e:
                    self.logger.error("Failed to process fallback operation",
                                    operation_data=fallback_data,
                                    error=str(e))
                    stats["failed"] += 1
            
            stats["end_time"] = datetime.now(timezone.utc).isoformat()
            return {"status": "completed", "stats": stats}
            
        except Exception as e:
            self.logger.error("Fallback queue processing failed", error=str(e))
            return {"status": "failed", "error": str(e), "stats": stats}

    # Private helper methods

    async def _get_namespaces_needing_merge(self) -> List[LearnerNamespace]:
        """Get namespaces that need nightly merge."""
        # Criteria for needing merge:
        # 1. Active status
        # 2. No merge in last 20 hours
        # 3. Not currently merging
        
        cutoff_time = datetime.now(timezone.utc) - timedelta(hours=20)
        
        result = await self.db.execute(
            select(LearnerNamespace)
            .where(and_(
                LearnerNamespace.status == NamespaceStatus.ACTIVE,
                or_(
                    LearnerNamespace.last_merge_at.is_(None),
                    LearnerNamespace.last_merge_at < cutoff_time
                )
            ))
        )
        
        return result.scalars().all()

    async def _process_namespace_merge(self, namespace: LearnerNamespace) -> Dict[str, Any]:
        """Process merge for a single namespace."""
        try:
            # Check if there's already a pending/running merge
            recent_merge = await self.db.execute(
                select(MergeOperation)
                .where(and_(
                    MergeOperation.namespace_id == namespace.id,
                    MergeOperation.status.in_([MergeStatus.PENDING, MergeStatus.RUNNING])
                ))
                .order_by(MergeOperation.created_at.desc())
                .limit(1)
            )
            
            if recent_merge.scalar_one_or_none():
                return {"merge_initiated": False, "reason": "already_pending"}
            
            # Trigger nightly merge
            merge_op = await self.isolator.trigger_merge(
                namespace.learner_id,
                operation_type="nightly",
                force=False
            )
            
            return {
                "merge_initiated": True,
                "operation_id": str(merge_op.id),
                "namespace_id": str(namespace.id)
            }
            
        except Exception as e:
            self.logger.error("Failed to process namespace merge",
                            namespace_id=str(namespace.id),
                            learner_id=str(namespace.learner_id),
                            error=str(e))
            raise

    async def _evaluate_fallback_necessity(self, health) -> bool:
        """Evaluate if a namespace needs fallback recovery."""
        # Criteria for fallback:
        # 1. Integrity score below threshold
        # 2. Severe version lag
        # 3. Critical issues detected
        
        if health.integrity_score < 0.8:
            return True
        
        if health.version_lag > 5:  # More strict than regular max_version_lag
            return True
        
        critical_issues = [
            "Checkpoint integrity verification failed",
            "corruption_detected"
        ]
        
        if any(issue in str(health.issues) for issue in critical_issues):
            return True
        
        return False

    def _determine_fallback_reason(self, health) -> FallbackReason:
        """Determine the reason for fallback based on health status."""
        if health.integrity_score < 0.5:
            return FallbackReason.CORRUPTION_DETECTED
        
        if health.version_lag > 5:
            return FallbackReason.VERSION_LAG
        
        if "integrity" in str(health.issues).lower():
            return FallbackReason.INTEGRITY_FAILURE
        
        return FallbackReason.CORRUPTION_DETECTED

    async def _execute_fallback_recovery(self, fallback_data: Dict[str, Any]) -> bool:
        """Execute fallback recovery operation."""
        operation_id = UUID(fallback_data["operation_id"])
        namespace_id = UUID(fallback_data["namespace_id"])
        target_fm_version = fallback_data["target_fm_version"]
        reason = FallbackReason(fallback_data["reason"])
        
        self.logger.info("Starting fallback recovery execution",
                        operation_id=str(operation_id),
                        namespace_id=str(namespace_id),
                        reason=reason.value)
        
        try:
            # Get namespace
            result = await self.db.execute(
                select(LearnerNamespace).where(LearnerNamespace.id == namespace_id)
            )
            namespace = result.scalar_one_or_none()
            
            if not namespace:
                self.logger.error("Namespace not found for fallback", namespace_id=str(namespace_id))
                return False
            
            # Simulate fallback recovery steps
            recovery_steps = [
                "Backing up current state",
                "Re-cloning from foundation model",
                "Identifying events to replay", 
                "Replaying event log",
                "Validating recovered state",
                "Updating namespace status"
            ]
            
            for step in recovery_steps:
                self.logger.debug("Fallback recovery step", step=step, operation_id=str(operation_id))
                await asyncio.sleep(3)  # Simulate work
            
            # Generate new checkpoint
            new_checkpoint_hash = self.isolator._generate_checkpoint_hash(
                namespace.id,
                target_fm_version,
                1  # Reset version count
            )
            
            # Update namespace
            namespace.current_checkpoint_hash = new_checkpoint_hash
            namespace.base_fm_version = target_fm_version
            namespace.version_count = 1  # Reset after fallback
            namespace.status = NamespaceStatus.ACTIVE
            namespace.updated_at = datetime.now(timezone.utc)
            
            # Log successful fallback
            await self.isolator._log_event(
                namespace.id,
                namespace.learner_id,
                "fallback_completed",
                {
                    "operation_id": str(operation_id),
                    "reason": reason.value,
                    "target_fm_version": target_fm_version,
                    "new_checkpoint_hash": new_checkpoint_hash,
                    "recovered_version": namespace.version_count
                },
                checkpoint_hash=new_checkpoint_hash
            )
            
            await self.db.commit()
            
            self.logger.info("Fallback recovery completed successfully",
                           operation_id=str(operation_id),
                           namespace_id=str(namespace_id))
            
            return True
            
        except Exception as e:
            self.logger.error("Fallback recovery failed",
                            operation_id=str(operation_id),
                            namespace_id=str(namespace_id),
                            error=str(e))
            
            # Try to restore namespace to previous state
            try:
                namespace.status = NamespaceStatus.CORRUPTED
                await self.db.commit()
            except Exception:
                pass  # Best effort
            
            return False

    async def _store_job_stats(self, job_name: str, stats: Dict[str, Any]) -> None:
        """Store job statistics in Redis."""
        stats_key = f"job_stats:{job_name}:{datetime.now(timezone.utc).strftime('%Y%m%d')}"
        await self.redis.hset(stats_key, mapping={
            k: json.dumps(v) if not isinstance(v, str) else v
            for k, v in stats.items()
        })
        await self.redis.expire(stats_key, 86400 * 7)  # Keep for 7 days
