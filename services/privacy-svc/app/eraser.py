"""
Data erasure functionality
Handles irreversible deletion of personal data with audit trails
"""

import asyncio
from datetime import datetime
from typing import List, Dict, Any, Optional, Set
from uuid import UUID

import asyncpg
import structlog

from .models import DataCategory, PrivacyRequestStatus, AdapterDeletionRule
from .database import get_db_pool, log_audit_event

logger = structlog.get_logger()

class DataEraser:
    """Handles data erasure operations"""
    
    def __init__(self):
        # Adapter deletion rules - never merge upwards
        self.adapter_rules = {
            "learning_adapters": AdapterDeletionRule(
                adapter_type="learning_adapters",
                delete_on_request=True,
                merge_upwards=False,  # Critical: never merge deletions upwards
                preserve_audit=True
            ),
            "assessment_adapters": AdapterDeletionRule(
                adapter_type="assessment_adapters", 
                delete_on_request=True,
                merge_upwards=False,
                preserve_audit=True
            ),
            "interaction_adapters": AdapterDeletionRule(
                adapter_type="interaction_adapters",
                delete_on_request=True, 
                merge_upwards=False,
                preserve_audit=True
            )
        }
    
    async def process_erasure_request(
        self,
        request_id: UUID,
        learner_id: UUID,
        data_categories: List[DataCategory],
        reason: Optional[str] = None
    ) -> Dict[str, Any]:
        """Process irreversible data erasure request"""
        
        logger.info("Starting data erasure", 
                   request_id=str(request_id),
                   learner_id=str(learner_id),
                   categories=[cat.value for cat in data_categories])
        
        try:
            # Update request status
            await self._update_request_status(request_id, PrivacyRequestStatus.PROCESSING)
            
            # Log erasure start
            await log_audit_event(
                "erasure_started",
                learner_id=str(learner_id),
                request_id=str(request_id),
                event_data={
                    "categories": [cat.value for cat in data_categories],
                    "reason": reason
                }
            )
            
            # Check for dependencies and constraints
            constraints = await self._check_erasure_constraints(learner_id, data_categories)
            if constraints["blocking_constraints"]:
                raise ValueError(f"Erasure blocked by constraints: {constraints['blocking_constraints']}")
            
            # Perform erasure by category
            erasure_results = {}
            total_records_deleted = 0
            
            for category in data_categories:
                logger.info("Erasing category data", category=category.value)
                
                result = await self._erase_category_data(learner_id, category)
                erasure_results[category.value] = result
                total_records_deleted += result["records_deleted"]
                
                # Log category erasure
                await log_audit_event(
                    f"erasure_category_{category.value}",
                    learner_id=str(learner_id),
                    request_id=str(request_id),
                    event_data=result
                )
            
            # Handle adapter deletions (never merge upwards)
            adapter_results = await self._handle_adapter_deletions(learner_id, data_categories)
            erasure_results["adapters"] = adapter_results
            
            # Update request completion
            await self._update_request_completion(request_id, total_records_deleted)
            
            # Final audit log
            await log_audit_event(
                "erasure_completed",
                learner_id=str(learner_id),
                request_id=str(request_id),
                event_data={
                    "total_records_deleted": total_records_deleted,
                    "categories_processed": len(data_categories),
                    "completion_timestamp": datetime.utcnow().isoformat(),
                    "irreversible": True
                }
            )
            
            logger.info("Data erasure completed", 
                       request_id=str(request_id),
                       records_deleted=total_records_deleted)
            
            return {
                "request_id": request_id,
                "learner_id": learner_id,
                "records_deleted": total_records_deleted,
                "categories_processed": [cat.value for cat in data_categories],
                "adapter_results": adapter_results,
                "completed_at": datetime.utcnow(),
                "irreversible": True
            }
            
        except Exception as e:
            logger.error("Data erasure failed", 
                        request_id=str(request_id),
                        error=str(e))
            
            await self._update_request_status(
                request_id,
                PrivacyRequestStatus.FAILED,
                error_message=str(e)
            )
            
            await log_audit_event(
                "erasure_failed",
                learner_id=str(learner_id),
                request_id=str(request_id),
                event_data={"error": str(e)}
            )
            
            raise
    
    async def _check_erasure_constraints(
        self, 
        learner_id: UUID, 
        data_categories: List[DataCategory]
    ) -> Dict[str, Any]:
        """Check for constraints that might block erasure"""
        pool = await get_db_pool()
        constraints = {
            "blocking_constraints": [],
            "warnings": [],
            "retention_policies": {}
        }
        
        async with pool.acquire() as conn:
            # Check for active legal holds
            legal_holds = await conn.fetch(
                "SELECT * FROM legal_holds WHERE learner_id = $1 AND active = true",
                learner_id
            )
            if legal_holds:
                constraints["blocking_constraints"].append("active_legal_holds")
            
            # Check for ongoing assessments
            ongoing_assessments = await conn.fetch(
                """
                SELECT COUNT(*) as count FROM assessment_sessions 
                WHERE user_id = $1 AND status = 'in_progress'
                """,
                learner_id
            )
            if ongoing_assessments[0]["count"] > 0:
                constraints["warnings"].append("ongoing_assessments")
            
            # Check retention policies
            for category in data_categories:
                policy = await conn.fetchrow(
                    "SELECT * FROM data_retention_policies WHERE data_category = $1 AND active = true",
                    category.value
                )
                if policy:
                    constraints["retention_policies"][category.value] = {
                        "retention_days": policy["retention_days"],
                        "checkpoint_count": policy["checkpoint_count"]
                    }
        
        return constraints
    
    async def _erase_category_data(self, learner_id: UUID, category: DataCategory) -> Dict[str, Any]:
        """Erase data for a specific category"""
        pool = await get_db_pool()
        
        # Define erasure queries for each category
        erasure_queries = {
            DataCategory.PROFILE: [
                # Anonymize rather than delete core profile (may have FK constraints)
                """
                UPDATE users SET 
                    email = 'erased_' || id || '@privacy.local',
                    first_name = 'ERASED',
                    last_name = 'ERASED', 
                    phone = NULL,
                    address = NULL,
                    preferences = '{}',
                    profile_image_url = NULL,
                    bio = NULL,
                    erased_at = NOW()
                WHERE id = $1 AND erased_at IS NULL
                """,
                # Delete profile metadata
                "DELETE FROM user_preferences WHERE user_id = $1",
                "DELETE FROM user_settings WHERE user_id = $1"
            ],
            DataCategory.LEARNING: [
                "DELETE FROM learning_sessions WHERE user_id = $1",
                "DELETE FROM lesson_completions WHERE user_id = $1",
                "DELETE FROM course_enrollments WHERE user_id = $1"
            ],
            DataCategory.PROGRESS: [
                "DELETE FROM progress_tracking WHERE user_id = $1",
                "DELETE FROM achievement_progress WHERE user_id = $1",
                "DELETE FROM learning_paths WHERE user_id = $1"
            ],
            DataCategory.ASSESSMENTS: [
                # Keep assessment structure but remove personal responses
                """
                UPDATE assessment_results SET
                    answers = '[]',
                    personal_notes = NULL,
                    anonymized = true,
                    erased_at = NOW()
                WHERE user_id = $1 AND erased_at IS NULL
                """,
                "DELETE FROM assessment_attempts WHERE user_id = $1"
            ],
            DataCategory.INTERACTIONS: [
                "DELETE FROM user_interactions WHERE user_id = $1",
                "DELETE FROM click_events WHERE user_id = $1",
                "DELETE FROM session_recordings WHERE user_id = $1"
            ],
            DataCategory.ANALYTICS: [
                "DELETE FROM analytics_events WHERE user_id = $1",
                "DELETE FROM user_analytics WHERE user_id = $1",
                "DELETE FROM behavior_tracking WHERE user_id = $1"
            ],
            DataCategory.SYSTEM: [
                "DELETE FROM audit_logs WHERE user_id = $1",
                "DELETE FROM error_logs WHERE user_id = $1",
                "DELETE FROM session_logs WHERE user_id = $1"
            ]
        }
        
        queries = erasure_queries.get(category, [])
        if not queries:
            logger.warning("No erasure queries defined for category", category=category.value)
            return {"records_deleted": 0, "queries_executed": 0}
        
        total_deleted = 0
        queries_executed = 0
        
        try:
            async with pool.acquire() as conn:
                async with conn.transaction():
                    for query in queries:
                        if "DELETE" in query.upper():
                            # Count records before deletion for audit
                            count_query = query.replace("DELETE", "SELECT COUNT(*)", 1)
                            count_result = await conn.fetchval(count_query, learner_id)
                            
                            # Execute deletion
                            await conn.execute(query, learner_id)
                            total_deleted += count_result if count_result else 0
                        else:
                            # For UPDATE queries
                            result = await conn.execute(query, learner_id)
                            # Extract affected rows from result (format: "UPDATE n")
                            if result.startswith("UPDATE "):
                                affected_rows = int(result.split()[1])
                                total_deleted += affected_rows
                        
                        queries_executed += 1
            
            return {
                "records_deleted": total_deleted,
                "queries_executed": queries_executed,
                "category": category.value,
                "timestamp": datetime.utcnow().isoformat()
            }
            
        except Exception as e:
            logger.error("Failed to erase category data", 
                        category=category.value, 
                        error=str(e))
            raise
    
    async def _handle_adapter_deletions(
        self, 
        learner_id: UUID, 
        data_categories: List[DataCategory]
    ) -> Dict[str, Any]:
        """Handle adapter deletions with one-way rule enforcement"""
        
        adapter_results = {}
        pool = await get_db_pool()
        
        for adapter_type, rule in self.adapter_rules.items():
            if not rule.delete_on_request:
                continue
            
            # Enforce one-way rule: delete adapters but never merge upwards
            if rule.merge_upwards:
                logger.error("CRITICAL: Adapter rule violation - merge_upwards must be False",
                           adapter_type=adapter_type)
                raise ValueError(f"Adapter rule violation: {adapter_type} attempted upward merge")
            
            try:
                async with pool.acquire() as conn:
                    # Delete adapter data
                    deleted_count = await conn.fetchval(
                        f"SELECT COUNT(*) FROM {adapter_type} WHERE learner_id = $1",
                        learner_id
                    )
                    
                    await conn.execute(
                        f"DELETE FROM {adapter_type} WHERE learner_id = $1",
                        learner_id
                    )
                    
                    # Preserve audit trail if required
                    if rule.preserve_audit:
                        await conn.execute(
                            """
                            INSERT INTO adapter_deletion_audit 
                            (adapter_type, learner_id, records_deleted, deletion_timestamp, rule_enforced)
                            VALUES ($1, $2, $3, NOW(), $4)
                            """,
                            adapter_type, learner_id, deleted_count, "one_way_only"
                        )
                    
                    adapter_results[adapter_type] = {
                        "records_deleted": deleted_count or 0,
                        "merge_upwards": False,  # Always False - enforced
                        "audit_preserved": rule.preserve_audit
                    }
                    
                    logger.info("Adapter data deleted", 
                               adapter_type=adapter_type,
                               records_deleted=deleted_count)
                    
            except Exception as e:
                logger.error("Failed to delete adapter data",
                           adapter_type=adapter_type,
                           error=str(e))
                adapter_results[adapter_type] = {
                    "error": str(e),
                    "records_deleted": 0
                }
        
        return adapter_results
    
    async def verify_erasure_idempotency(self, learner_id: UUID, request_id: UUID) -> bool:
        """Verify that erasure is idempotent (safe to run multiple times)"""
        pool = await get_db_pool()
        
        try:
            async with pool.acquire() as conn:
                # Check if there's already a completed erasure request for this learner
                existing_request = await conn.fetchrow(
                    """
                    SELECT id, status, completed_at FROM privacy_requests 
                    WHERE learner_id = $1 AND request_type = 'erase' 
                    AND status = 'completed' AND id != $2
                    ORDER BY completed_at DESC LIMIT 1
                    """,
                    learner_id, request_id
                )
                
                if existing_request:
                    logger.info("Previous erasure request found", 
                               previous_request=str(existing_request["id"]),
                               completed_at=existing_request["completed_at"])
                    return True  # Idempotent - already erased
                
                return False  # First erasure request
                
        except Exception as e:
            logger.error("Failed to verify erasure idempotency", error=str(e))
            return False
    
    async def _update_request_status(
        self, 
        request_id: UUID, 
        status: PrivacyRequestStatus, 
        error_message: Optional[str] = None
    ) -> None:
        """Update privacy request status"""
        pool = await get_db_pool()
        async with pool.acquire() as conn:
            if status == PrivacyRequestStatus.COMPLETED:
                await conn.execute(
                    "UPDATE privacy_requests SET status = $1, completed_at = NOW() WHERE id = $2",
                    status.value, request_id
                )
            else:
                await conn.execute(
                    "UPDATE privacy_requests SET status = $1, error_message = $2 WHERE id = $3",
                    status.value, error_message, request_id
                )
    
    async def _update_request_completion(self, request_id: UUID, records_processed: int) -> None:
        """Update request with completion details"""
        pool = await get_db_pool()
        async with pool.acquire() as conn:
            await conn.execute(
                """
                UPDATE privacy_requests 
                SET status = $1, completed_at = NOW(), records_processed = $2
                WHERE id = $3
                """,
                PrivacyRequestStatus.COMPLETED.value, records_processed, request_id
            )
