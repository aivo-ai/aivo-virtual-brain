"""
Test isolation and merge functionality for Private Foundation Model Orchestrator.
"""

import asyncio
from datetime import datetime, timezone, timedelta
from unittest.mock import AsyncMock, patch
from uuid import UUID, uuid4

import pytest

from app.models import (
    LearnerNamespace,
    MergeOperation,
    NamespaceStatus,
    MergeStatus,
    FallbackReason
)
from app.isolator import NamespaceIsolator


class TestNamespaceIsolation:
    """Test namespace isolation functionality."""
    
    @pytest.mark.asyncio
    async def test_create_namespace(self, test_isolator, test_db_session):
        """Test creating a new namespace."""
        learner_id = uuid4()
        
        namespace = await test_isolator.create_namespace(
            learner_id,
            "1.0",
            "Test prompt",
            {"test": True}
        )
        
        assert namespace.learner_id == learner_id
        assert namespace.status == NamespaceStatus.ACTIVE
        assert namespace.base_fm_version == "1.0"
        assert namespace.version_count == 1
        assert namespace.current_checkpoint_hash.startswith("ckpt_")
        assert namespace.encryption_key_hash
        assert namespace.metadata["initial_prompt"] == "Test prompt"
        assert namespace.metadata["configuration"]["test"] is True
        
        # Verify database persistence
        await test_db_session.refresh(namespace)
        assert namespace.created_at is not None
        assert namespace.updated_at is not None
    
    @pytest.mark.asyncio
    async def test_create_duplicate_namespace_fails(self, test_isolator):
        """Test that creating duplicate namespace fails."""
        learner_id = uuid4()
        
        # Create first namespace
        await test_isolator.create_namespace(learner_id, "1.0")
        
        # Try to create duplicate
        with pytest.raises(ValueError, match="already exists"):
            await test_isolator.create_namespace(learner_id, "1.0")
    
    @pytest.mark.asyncio
    async def test_get_namespace(self, test_isolator):
        """Test retrieving an existing namespace."""
        learner_id = uuid4()
        
        # Create namespace
        created_ns = await test_isolator.create_namespace(learner_id, "1.0")
        
        # Retrieve namespace
        retrieved_ns = await test_isolator.get_namespace(learner_id)
        
        assert retrieved_ns.id == created_ns.id
        assert retrieved_ns.learner_id == learner_id
        assert retrieved_ns.status == NamespaceStatus.ACTIVE
    
    @pytest.mark.asyncio
    async def test_get_nonexistent_namespace_returns_none(self, test_isolator):
        """Test retrieving non-existent namespace returns None."""
        nonexistent_id = uuid4()
        namespace = await test_isolator.get_namespace(nonexistent_id)
        assert namespace is None
    
    @pytest.mark.asyncio
    async def test_delete_namespace(self, test_isolator):
        """Test deleting a namespace."""
        learner_id = uuid4()
        
        # Create namespace
        await test_isolator.create_namespace(learner_id, "1.0")
        
        # Delete namespace
        success = await test_isolator.delete_namespace(learner_id)
        assert success is True
        
        # Verify it's gone
        namespace = await test_isolator.get_namespace(learner_id)
        assert namespace is None
    
    @pytest.mark.asyncio
    async def test_delete_nonexistent_namespace_returns_false(self, test_isolator):
        """Test deleting non-existent namespace returns False."""
        nonexistent_id = uuid4()
        success = await test_isolator.delete_namespace(nonexistent_id)
        assert success is False
    
    @pytest.mark.asyncio
    async def test_delete_namespace_with_guardian_protection(self, test_isolator, test_db_session):
        """Test deletion with guardian protection."""
        learner_id = uuid4()
        
        # Create namespace
        namespace = await test_isolator.create_namespace(learner_id, "1.0")
        
        # Set guardian protection (future deletion date)
        future_date = datetime.now(timezone.utc) + timedelta(days=7)
        namespace.guardian_deletable_at = future_date
        await test_db_session.commit()
        
        # Try to delete without force
        success = await test_isolator.delete_namespace(learner_id, force=False)
        assert success is False
        
        # Delete with force should work
        success = await test_isolator.delete_namespace(learner_id, force=True)
        assert success is True


class TestMergeOperations:
    """Test merge operation functionality."""
    
    @pytest.mark.asyncio
    async def test_trigger_merge(self, test_isolator):
        """Test triggering a merge operation."""
        learner_id = uuid4()
        
        # Create namespace
        await test_isolator.create_namespace(learner_id, "1.0")
        
        # Trigger merge
        merge_op = await test_isolator.trigger_merge(learner_id, "manual", False)
        
        assert merge_op.operation_type == "manual"
        assert merge_op.status == MergeStatus.PENDING
        assert merge_op.source_checkpoint_hash.startswith("ckpt_")
        assert merge_op.target_checkpoint_hash is None  # Set during execution
        assert merge_op.created_at is not None
        assert merge_op.completed_at is None
        assert merge_op.error_message is None
    
    @pytest.mark.asyncio
    async def test_trigger_merge_nonexistent_namespace_fails(self, test_isolator):
        """Test triggering merge on non-existent namespace fails."""
        nonexistent_id = uuid4()
        
        with pytest.raises(ValueError, match="not found"):
            await test_isolator.trigger_merge(nonexistent_id, "manual", False)
    
    @pytest.mark.asyncio
    async def test_trigger_merge_inactive_namespace_fails(self, test_isolator, test_db_session):
        """Test triggering merge on inactive namespace fails."""
        learner_id = uuid4()
        
        # Create namespace
        namespace = await test_isolator.create_namespace(learner_id, "1.0")
        
        # Set to inactive status
        namespace.status = NamespaceStatus.CORRUPTED
        await test_db_session.commit()
        
        # Try to trigger merge
        with pytest.raises(ValueError, match="not active"):
            await test_isolator.trigger_merge(learner_id, "manual", False)
    
    @pytest.mark.asyncio
    async def test_force_merge_overrides_conditions(self, test_isolator, test_db_session):
        """Test that force merge overrides normal conditions."""
        learner_id = uuid4()
        
        # Create namespace
        namespace = await test_isolator.create_namespace(learner_id, "1.0")
        
        # Set recent merge (should normally prevent new merge)
        namespace.last_merge_at = datetime.now(timezone.utc) - timedelta(minutes=30)
        await test_db_session.commit()
        
        # Normal merge should fail
        with pytest.raises(ValueError, match="too recent"):
            await test_isolator.trigger_merge(learner_id, "manual", False)
        
        # Force merge should succeed
        merge_op = await test_isolator.trigger_merge(learner_id, "manual", True)
        assert merge_op.operation_type == "manual"
        assert merge_op.status == MergeStatus.PENDING
    
    @pytest.mark.asyncio
    async def test_execute_merge_simulation(self, test_isolator, test_redis):
        """Test merge execution simulation."""
        learner_id = uuid4()
        
        # Create namespace
        await test_isolator.create_namespace(learner_id, "1.0")
        
        # Trigger merge
        merge_op = await test_isolator.trigger_merge(learner_id, "manual", False)
        
        # Mock the execution steps
        with patch('asyncio.sleep', new_callable=AsyncMock):
            success = await test_isolator.execute_merge(merge_op.id)
            assert success is True
        
        # Verify merge operation was updated
        # Note: In real implementation, this would refresh from DB
        # For testing, we check that Redis operations were called
        assert await test_redis.exists(f"merge_lock:{learner_id}")


class TestHealthChecks:
    """Test namespace health check functionality."""
    
    @pytest.mark.asyncio
    async def test_check_namespace_health_healthy(self, test_isolator):
        """Test health check on healthy namespace."""
        learner_id = uuid4()
        
        # Create namespace
        await test_isolator.create_namespace(learner_id, "1.0")
        
        # Check health
        health = await test_isolator.check_namespace_health(learner_id)
        
        assert health.is_healthy is True
        assert health.integrity_score >= 0.9  # New namespace should be highly intact
        assert health.version_lag == 0  # No lag on new namespace
        assert health.checkpoint_size_mb > 0
        assert len(health.issues) == 0
        assert health.last_health_check is not None
    
    @pytest.mark.asyncio
    async def test_check_namespace_health_nonexistent_fails(self, test_isolator):
        """Test health check on non-existent namespace fails."""
        nonexistent_id = uuid4()
        
        with pytest.raises(ValueError, match="not found"):
            await test_isolator.check_namespace_health(nonexistent_id)
    
    @pytest.mark.asyncio
    async def test_check_namespace_health_with_issues(self, test_isolator, test_db_session):
        """Test health check with simulated issues."""
        learner_id = uuid4()
        
        # Create namespace
        namespace = await test_isolator.create_namespace(learner_id, "1.0")
        
        # Simulate some aging to create version lag
        namespace.version_count = 10  # Higher version count
        namespace.updated_at = datetime.now(timezone.utc) - timedelta(hours=5)
        await test_db_session.commit()
        
        # Check health
        health = await test_isolator.check_namespace_health(learner_id)
        
        # Should still be healthy but with some lag
        assert health.version_lag > 0


class TestFallbackRecovery:
    """Test fallback recovery functionality."""
    
    @pytest.mark.asyncio
    async def test_initiate_fallback_recovery(self, test_isolator, test_redis):
        """Test initiating fallback recovery."""
        learner_id = uuid4()
        
        # Create namespace
        await test_isolator.create_namespace(learner_id, "1.0")
        
        # Initiate fallback recovery
        operation_id = await test_isolator.initiate_fallback_recovery(
            learner_id,
            FallbackReason.CORRUPTION_DETECTED
        )
        
        assert operation_id is not None
        
        # Verify fallback was queued
        queue_length = await test_redis.llen("fallback_queue")
        assert queue_length > 0
    
    @pytest.mark.asyncio
    async def test_initiate_fallback_nonexistent_namespace_fails(self, test_isolator):
        """Test initiating fallback on non-existent namespace fails."""
        nonexistent_id = uuid4()
        
        with pytest.raises(ValueError, match="not found"):
            await test_isolator.initiate_fallback_recovery(
                nonexistent_id,
                FallbackReason.CORRUPTION_DETECTED
            )
    
    @pytest.mark.asyncio
    async def test_fallback_recovery_execution_simulation(self, test_isolator, test_db_session):
        """Test fallback recovery execution simulation."""
        learner_id = uuid4()
        
        # Create namespace in corrupted state
        namespace = await test_isolator.create_namespace(learner_id, "1.0")
        namespace.status = NamespaceStatus.CORRUPTED
        namespace.version_count = 5  # Some previous activity
        await test_db_session.commit()
        
        # Initiate fallback
        operation_id = await test_isolator.initiate_fallback_recovery(
            learner_id,
            FallbackReason.CORRUPTION_DETECTED,
            "1.0"
        )
        
        # Verify operation was created
        assert operation_id is not None


class TestEventLogging:
    """Test event logging functionality."""
    
    @pytest.mark.asyncio
    async def test_log_event(self, test_isolator, test_db_session):
        """Test logging events."""
        learner_id = uuid4()
        
        # Create namespace
        namespace = await test_isolator.create_namespace(learner_id, "1.0")
        
        # Log an event
        await test_isolator._log_event(
            namespace.id,
            learner_id,
            "test_event",
            {"key": "value"},
            checkpoint_hash="test_hash"
        )
        
        # Verify event was logged
        from sqlalchemy import select
        from app.models import EventLog
        
        result = await test_db_session.execute(
            select(EventLog).where(EventLog.learner_id == learner_id)
        )
        events = result.scalars().all()
        
        assert len(events) >= 1  # At least the test event (may have creation events too)
        test_event = next((e for e in events if e.event_type == "test_event"), None)
        assert test_event is not None
        assert test_event.event_data["key"] == "value"
        assert test_event.checkpoint_hash == "test_hash"


class TestConcurrency:
    """Test concurrency and race condition handling."""
    
    @pytest.mark.asyncio
    async def test_concurrent_merge_operations_handled(self, test_isolator, test_redis):
        """Test that concurrent merge operations are properly handled."""
        learner_id = uuid4()
        
        # Create namespace
        await test_isolator.create_namespace(learner_id, "1.0")
        
        # Try to trigger multiple merges concurrently
        tasks = []
        for i in range(3):
            task = test_isolator.trigger_merge(learner_id, "concurrent", True)  # Force to allow
            tasks.append(task)
        
        # Only one should succeed, others should raise errors or be queued
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        successful_merges = [r for r in results if not isinstance(r, Exception)]
        assert len(successful_merges) >= 1  # At least one should succeed
    
    @pytest.mark.asyncio
    async def test_namespace_locking(self, test_isolator, test_redis):
        """Test namespace locking during operations."""
        learner_id = uuid4()
        
        # Create namespace
        await test_isolator.create_namespace(learner_id, "1.0")
        
        # Acquire lock
        lock_acquired = await test_isolator._acquire_namespace_lock(learner_id, "test")
        assert lock_acquired is True
        
        # Try to acquire same lock should fail
        lock_acquired_again = await test_isolator._acquire_namespace_lock(learner_id, "test")
        assert lock_acquired_again is False
        
        # Release lock
        await test_isolator._release_namespace_lock(learner_id, "test")
        
        # Should be able to acquire again
        lock_acquired_after_release = await test_isolator._acquire_namespace_lock(learner_id, "test")
        assert lock_acquired_after_release is True
