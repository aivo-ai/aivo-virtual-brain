"""
Data Retention Cleanup Module
Automated cleanup of expired data based on retention policies
"""

import asyncio
import logging
import os
from datetime import datetime, timedelta
from pathlib import Path
from typing import List, Dict, Any, Optional

import asyncpg
import structlog

from .models import DataCategory, RetentionPolicy
from .database import get_db_pool, log_audit_event

logger = structlog.get_logger()

class RetentionManager:
    """Manages data retention and automated cleanup"""
    
    def __init__(self):
        self.retention_policies = {
            DataCategory.LEARNING_PROGRESS: RetentionPolicy(
                category=DataCategory.LEARNING_PROGRESS,
                retention_days=2555,  # 7 years
                auto_delete=True,
                exceptions=["academic_transcripts", "graduation_records"]
            ),
            DataCategory.ASSESSMENTS: RetentionPolicy(
                category=DataCategory.ASSESSMENTS,
                retention_days=2555,  # 7 years
                auto_delete=False,  # Manual review required
                anonymize_after_days=1095  # 3 years
            ),
            DataCategory.INTERACTIONS: RetentionPolicy(
                category=DataCategory.INTERACTIONS,
                retention_days=1095,  # 3 years
                auto_delete=True,
                anonymize_after_days=365  # 1 year
            ),
            DataCategory.ANALYTICS: RetentionPolicy(
                category=DataCategory.ANALYTICS,
                retention_days=1825,  # 5 years
                auto_delete=True,
                anonymize_after_days=730  # 2 years
            ),
            DataCategory.PERSONALIZED_ADAPTERS: RetentionPolicy(
                category=DataCategory.PERSONALIZED_ADAPTERS,
                retention_days=1825,  # 5 years
                keep_latest_count=3,  # Keep 3 most recent checkpoints
                auto_delete=True
            )
        }
    
    async def run_retention_cleanup(self, dry_run: bool = False) -> Dict[str, Any]:
        """Run comprehensive retention cleanup"""
        
        logger.info("Starting retention cleanup", dry_run=dry_run)
        cleanup_summary = {
            "started_at": datetime.utcnow(),
            "dry_run": dry_run,
            "categories_processed": [],
            "total_records_deleted": 0,
            "total_records_anonymized": 0,
            "errors": []
        }
        
        try:
            pool = await get_db_pool()
            
            for category, policy in self.retention_policies.items():
                try:
                    category_result = await self._cleanup_category(
                        pool, category, policy, dry_run
                    )
                    cleanup_summary["categories_processed"].append({
                        "category": category.value,
                        "result": category_result
                    })
                    cleanup_summary["total_records_deleted"] += category_result.get("deleted", 0)
                    cleanup_summary["total_records_anonymized"] += category_result.get("anonymized", 0)
                    
                except Exception as e:
                    error_msg = f"Error processing {category.value}: {str(e)}"
                    logger.error(error_msg, category=category.value, error=str(e))
                    cleanup_summary["errors"].append(error_msg)
            
            cleanup_summary["completed_at"] = datetime.utcnow()
            cleanup_summary["duration_minutes"] = (
                cleanup_summary["completed_at"] - cleanup_summary["started_at"]
            ).total_seconds() / 60
            
            # Log cleanup summary
            await log_audit_event(
                event_type="retention_cleanup_completed",
                details=cleanup_summary,
                pool=pool
            )
            
            logger.info("Retention cleanup completed", summary=cleanup_summary)
            return cleanup_summary
            
        except Exception as e:
            logger.error("Retention cleanup failed", error=str(e))
            cleanup_summary["errors"].append(f"Global error: {str(e)}")
            cleanup_summary["status"] = "failed"
            return cleanup_summary
    
    async def _cleanup_category(
        self, 
        pool: asyncpg.Pool, 
        category: DataCategory, 
        policy: RetentionPolicy,
        dry_run: bool
    ) -> Dict[str, Any]:
        """Clean up a specific data category"""
        
        logger.info("Processing category", category=category.value, policy=policy.dict())
        
        result = {
            "category": category.value,
            "deleted": 0,
            "anonymized": 0,
            "skipped": 0,
            "errors": []
        }
        
        try:
            # Calculate cutoff dates
            deletion_cutoff = datetime.utcnow() - timedelta(days=policy.retention_days)
            anonymization_cutoff = None
            if policy.anonymize_after_days:
                anonymization_cutoff = datetime.utcnow() - timedelta(days=policy.anonymize_after_days)
            
            async with pool.acquire() as conn:
                
                # Handle personalized adapters with keep_latest_count
                if category == DataCategory.PERSONALIZED_ADAPTERS and policy.keep_latest_count:
                    adapter_result = await self._cleanup_personalized_adapters(
                        conn, policy.keep_latest_count, dry_run
                    )
                    result.update(adapter_result)
                
                # Handle regular retention cleanup
                else:
                    # Get records for deletion
                    if policy.auto_delete:
                        delete_query = self._build_deletion_query(category, deletion_cutoff, policy.exceptions)
                        
                        if dry_run:
                            count_result = await conn.fetchval(
                                delete_query.replace("DELETE FROM", "SELECT COUNT(*) FROM").split("WHERE")[0] + 
                                " WHERE " + delete_query.split("WHERE")[1]
                            )
                            result["deleted"] = count_result or 0
                        else:
                            deleted_count = await conn.execute(delete_query)
                            result["deleted"] = int(deleted_count.split()[-1]) if deleted_count else 0
                    
                    # Handle anonymization
                    if anonymization_cutoff and not dry_run:
                        anonymize_query = self._build_anonymization_query(category, anonymization_cutoff)
                        if anonymize_query:
                            anonymized_count = await conn.execute(anonymize_query)
                            result["anonymized"] = int(anonymized_count.split()[-1]) if anonymized_count else 0
                
                # Log category cleanup
                await log_audit_event(
                    event_type="category_retention_cleanup",
                    details={
                        "category": category.value,
                        "policy": policy.dict(),
                        "result": result,
                        "dry_run": dry_run
                    },
                    pool=pool
                )
                
        except Exception as e:
            error_msg = f"Error cleaning up {category.value}: {str(e)}"
            logger.error(error_msg, category=category.value, error=str(e))
            result["errors"].append(error_msg)
        
        return result
    
    async def _cleanup_personalized_adapters(
        self, 
        conn: asyncpg.Connection, 
        keep_count: int, 
        dry_run: bool
    ) -> Dict[str, Any]:
        """Clean up personalized adapters, keeping only the latest N per learner"""
        
        result = {"deleted": 0, "skipped": 0}
        
        try:
            # Get learners with more than keep_count adapters
            learners_query = """
                SELECT learner_id, COUNT(*) as adapter_count
                FROM personalized_adapters 
                WHERE created_at < NOW() - INTERVAL '30 days'  -- Only consider adapters older than 30 days
                GROUP BY learner_id 
                HAVING COUNT(*) > $1
            """
            
            learners_to_cleanup = await conn.fetch(learners_query, keep_count)
            
            for learner_row in learners_to_cleanup:
                learner_id = learner_row["learner_id"]
                
                # Get adapters to delete (keeping latest keep_count)
                adapters_to_delete_query = """
                    SELECT id FROM personalized_adapters 
                    WHERE learner_id = $1 
                    AND created_at < NOW() - INTERVAL '30 days'
                    ORDER BY created_at DESC 
                    OFFSET $2
                """
                
                adapters_to_delete = await conn.fetch(adapters_to_delete_query, learner_id, keep_count)
                
                if adapters_to_delete:
                    if dry_run:
                        result["deleted"] += len(adapters_to_delete)
                    else:
                        # Delete old adapters
                        adapter_ids = [row["id"] for row in adapters_to_delete]
                        delete_query = "DELETE FROM personalized_adapters WHERE id = ANY($1)"
                        await conn.execute(delete_query, adapter_ids)
                        result["deleted"] += len(adapter_ids)
                        
                        # Log adapter deletions
                        await log_audit_event(
                            event_type="personalized_adapters_cleanup",
                            details={
                                "learner_id": str(learner_id),
                                "deleted_adapter_ids": [str(aid) for aid in adapter_ids],
                                "kept_count": keep_count
                            },
                            pool=conn
                        )
        
        except Exception as e:
            logger.error("Error cleaning up personalized adapters", error=str(e))
            result["errors"] = [str(e)]
        
        return result
    
    def _build_deletion_query(
        self, 
        category: DataCategory, 
        cutoff_date: datetime, 
        exceptions: List[str] = None
    ) -> str:
        """Build SQL query for data deletion"""
        
        table_mapping = {
            DataCategory.LEARNING_PROGRESS: "learning_progress",
            DataCategory.ASSESSMENTS: "assessments", 
            DataCategory.INTERACTIONS: "interactions",
            DataCategory.ANALYTICS: "analytics_events",
            DataCategory.PERSONALIZED_ADAPTERS: "personalized_adapters"
        }
        
        table_name = table_mapping.get(category)
        if not table_name:
            raise ValueError(f"Unknown category: {category}")
        
        base_query = f"DELETE FROM {table_name} WHERE created_at < '{cutoff_date.isoformat()}'"
        
        # Add exceptions
        if exceptions:
            exception_conditions = " AND ".join([
                f"data_type != '{exception}'" for exception in exceptions
            ])
            base_query += f" AND ({exception_conditions})"
        
        return base_query
    
    def _build_anonymization_query(
        self, 
        category: DataCategory, 
        cutoff_date: datetime
    ) -> Optional[str]:
        """Build SQL query for data anonymization"""
        
        anonymization_mapping = {
            DataCategory.INTERACTIONS: """
                UPDATE interactions 
                SET 
                    user_input = '[ANONYMIZED]',
                    ip_address = NULL,
                    device_fingerprint = NULL,
                    anonymized_at = NOW()
                WHERE created_at < '{cutoff}' 
                AND anonymized_at IS NULL
            """,
            DataCategory.ANALYTICS: """
                UPDATE analytics_events 
                SET 
                    user_agent = '[ANONYMIZED]',
                    ip_address = NULL,
                    session_data = '{{}}',
                    anonymized_at = NOW()
                WHERE created_at < '{cutoff}'
                AND anonymized_at IS NULL
            """
        }
        
        query_template = anonymization_mapping.get(category)
        if query_template:
            return query_template.format(cutoff=cutoff_date.isoformat())
        
        return None


async def cleanup_personalized_checkpoints(keep_count: int = 3) -> Dict[str, Any]:
    """Standalone function for checkpoint cleanup (used by CronJob)"""
    
    logger.info("Starting personalized checkpoint cleanup", keep_count=keep_count)
    
    try:
        pool = await get_db_pool()
        retention_manager = RetentionManager()
        
        async with pool.acquire() as conn:
            result = await retention_manager._cleanup_personalized_adapters(
                conn, keep_count, dry_run=False
            )
        
        logger.info("Checkpoint cleanup completed", result=result)
        return result
        
    except Exception as e:
        logger.error("Checkpoint cleanup failed", error=str(e))
        return {"error": str(e), "deleted": 0}


async def cleanup_export_files(export_path: str, retention_days: int = 7) -> int:
    """Clean up old export files"""
    
    logger.info("Starting export file cleanup", path=export_path, retention_days=retention_days)
    
    try:
        export_dir = Path(export_path)
        if not export_dir.exists():
            logger.warning("Export directory does not exist", path=export_path)
            return 0
        
        cutoff_date = datetime.utcnow() - timedelta(days=retention_days)
        deleted_count = 0
        
        for file_path in export_dir.rglob("*.zip"):
            try:
                file_mtime = datetime.fromtimestamp(file_path.stat().st_mtime)
                if file_mtime < cutoff_date:
                    file_path.unlink()
                    deleted_count += 1
                    logger.debug("Deleted old export file", file=str(file_path), age_days=(datetime.utcnow() - file_mtime).days)
            
            except Exception as e:
                logger.error("Error deleting export file", file=str(file_path), error=str(e))
        
        logger.info("Export file cleanup completed", deleted_count=deleted_count)
        return deleted_count
        
    except Exception as e:
        logger.error("Export file cleanup failed", error=str(e))
        return 0


# CLI entry points for CronJob
async def main_retention_cleanup():
    """Main entry point for retention cleanup CronJob"""
    
    # Get configuration from environment
    dry_run = os.getenv("DRY_RUN", "false").lower() == "true"
    
    retention_manager = RetentionManager()
    result = await retention_manager.run_retention_cleanup(dry_run=dry_run)
    
    if result.get("errors"):
        logger.error("Retention cleanup completed with errors", result=result)
        exit(1)
    else:
        logger.info("Retention cleanup completed successfully", result=result)
        exit(0)


async def main_checkpoint_cleanup():
    """Main entry point for checkpoint cleanup CronJob"""
    
    keep_count = int(os.getenv("CHECKPOINT_KEEP_COUNT", "3"))
    result = await cleanup_personalized_checkpoints(keep_count=keep_count)
    
    if result.get("error"):
        logger.error("Checkpoint cleanup failed", result=result)
        exit(1)
    else:
        logger.info("Checkpoint cleanup completed", result=result)
        exit(0)


async def main_export_cleanup():
    """Main entry point for export file cleanup CronJob"""
    
    export_path = os.getenv("EXPORT_STORAGE_PATH", "/exports")
    retention_days = int(os.getenv("EXPORT_RETENTION_DAYS", "7"))
    
    deleted_count = await cleanup_export_files(export_path, retention_days)
    logger.info("Export cleanup completed", deleted_count=deleted_count)
    exit(0)


if __name__ == "__main__":
    import sys
    
    if len(sys.argv) > 1:
        if sys.argv[1] == "retention":
            asyncio.run(main_retention_cleanup())
        elif sys.argv[1] == "checkpoints":
            asyncio.run(main_checkpoint_cleanup())
        elif sys.argv[1] == "exports":
            asyncio.run(main_export_cleanup())
        else:
            print(f"Unknown cleanup type: {sys.argv[1]}")
            exit(1)
    else:
        print("Usage: python retention.py [retention|checkpoints|exports]")
        exit(1)
