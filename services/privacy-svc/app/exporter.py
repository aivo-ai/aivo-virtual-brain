"""
Data export functionality
Handles creation of export bundles with PII redaction
"""

import asyncio
import json
import csv
import zipfile
import hashlib
import os
from datetime import datetime, timedelta
from pathlib import Path
from typing import List, Dict, Any, Optional
from uuid import UUID

import asyncpg
import structlog

from .models import DataCategory, ExportBundle, PrivacyRequestStatus
from .database import get_db_pool, log_audit_event

logger = structlog.get_logger()

class DataExporter:
    """Handles data export operations"""
    
    def __init__(self, storage_path: str, max_size_mb: int = 500):
        self.storage_path = Path(storage_path)
        self.max_size_bytes = max_size_mb * 1024 * 1024
        self.storage_path.mkdir(parents=True, exist_ok=True)
    
    async def create_export_bundle(
        self,
        request_id: UUID,
        learner_id: UUID,
        data_categories: List[DataCategory],
        export_format: str = "json",
        include_metadata: bool = True
    ) -> ExportBundle:
        """Create export bundle for learner data"""
        
        logger.info("Starting export bundle creation", 
                   request_id=str(request_id), 
                   learner_id=str(learner_id))
        
        try:
            # Update request status
            await self._update_request_status(request_id, PrivacyRequestStatus.PROCESSING)
            
            # Create export directory
            export_dir = self.storage_path / str(request_id)
            export_dir.mkdir(exist_ok=True)
            
            # Collect data by category
            exported_data = {}
            total_records = 0
            
            for category in data_categories:
                logger.info("Exporting category", category=category.value)
                
                category_data = await self._export_category_data(learner_id, category)
                if category_data:
                    # Apply PII redaction if needed
                    redacted_data = await self._apply_pii_redaction(category_data, category)
                    exported_data[category.value] = redacted_data
                    total_records += len(redacted_data) if isinstance(redacted_data, list) else 1
            
            # Create export files
            file_paths = []
            if export_format == "json":
                file_paths = await self._create_json_export(export_dir, exported_data, include_metadata)
            elif export_format == "csv":
                file_paths = await self._create_csv_export(export_dir, exported_data, include_metadata)
            
            # Create ZIP archive
            zip_path = export_dir / f"learner_data_{learner_id}_{datetime.utcnow().strftime('%Y%m%d_%H%M%S')}.zip"
            await self._create_zip_archive(file_paths, zip_path)
            
            # Calculate checksum
            checksum = await self._calculate_file_checksum(zip_path)
            
            # Get file size
            file_size = zip_path.stat().st_size
            
            # Check size limits
            if file_size > self.max_size_bytes:
                raise ValueError(f"Export file too large: {file_size} bytes (max: {self.max_size_bytes})")
            
            # Create bundle metadata
            bundle = ExportBundle(
                learner_id=learner_id,
                created_at=datetime.utcnow(),
                data_categories=data_categories,
                export_format=export_format,
                file_count=len(file_paths),
                total_size_bytes=file_size,
                checksum=checksum
            )
            
            # Update request with completion details
            await self._update_request_completion(
                request_id, 
                str(zip_path), 
                file_size, 
                total_records
            )
            
            # Log audit event
            await log_audit_event(
                "export_completed",
                learner_id=str(learner_id),
                request_id=str(request_id),
                event_data={
                    "categories": [cat.value for cat in data_categories],
                    "format": export_format,
                    "file_size": file_size,
                    "records": total_records,
                    "checksum": checksum
                }
            )
            
            logger.info("Export bundle created successfully", 
                       request_id=str(request_id),
                       file_size=file_size,
                       records=total_records)
            
            return bundle
            
        except Exception as e:
            logger.error("Export bundle creation failed", 
                        request_id=str(request_id), 
                        error=str(e))
            
            await self._update_request_status(
                request_id, 
                PrivacyRequestStatus.FAILED, 
                error_message=str(e)
            )
            
            await log_audit_event(
                "export_failed",
                learner_id=str(learner_id),
                request_id=str(request_id),
                event_data={"error": str(e)}
            )
            
            raise
    
    async def _export_category_data(self, learner_id: UUID, category: DataCategory) -> List[Dict[str, Any]]:
        """Export data for a specific category"""
        pool = await get_db_pool()
        
        # Define data collection queries for each category
        queries = {
            DataCategory.PROFILE: """
                SELECT 'user_profile' as data_type, u.id, u.email, u.first_name, u.last_name, 
                       u.created_at, u.updated_at, u.preferences, u.locale, u.timezone
                FROM users u WHERE u.id = $1
            """,
            DataCategory.LEARNING: """
                SELECT 'learning_session' as data_type, ls.id, ls.course_id, ls.lesson_id,
                       ls.started_at, ls.completed_at, ls.duration_seconds, ls.score,
                       ls.metadata, c.title as course_title
                FROM learning_sessions ls
                JOIN courses c ON ls.course_id = c.id
                WHERE ls.user_id = $1
                ORDER BY ls.started_at DESC
            """,
            DataCategory.PROGRESS: """
                SELECT 'progress_tracking' as data_type, pt.id, pt.course_id, pt.completion_percentage,
                       pt.last_accessed, pt.milestones_completed, pt.time_spent_minutes,
                       c.title as course_title
                FROM progress_tracking pt
                JOIN courses c ON pt.course_id = c.id
                WHERE pt.user_id = $1
                ORDER BY pt.last_accessed DESC
            """,
            DataCategory.ASSESSMENTS: """
                SELECT 'assessment_result' as data_type, ar.id, ar.assessment_id, ar.score,
                       ar.max_score, ar.completed_at, ar.time_taken_seconds, ar.answers,
                       a.title as assessment_title
                FROM assessment_results ar
                JOIN assessments a ON ar.assessment_id = a.id
                WHERE ar.user_id = $1
                ORDER BY ar.completed_at DESC
            """,
            DataCategory.INTERACTIONS: """
                SELECT 'user_interaction' as data_type, ui.id, ui.interaction_type, ui.element_id,
                       ui.timestamp, ui.session_id, ui.metadata
                FROM user_interactions ui
                WHERE ui.user_id = $1 AND ui.timestamp > NOW() - INTERVAL '1 year'
                ORDER BY ui.timestamp DESC
                LIMIT 10000
            """,
            DataCategory.ANALYTICS: """
                SELECT 'analytics_event' as data_type, ae.id, ae.event_type, ae.event_data,
                       ae.timestamp, ae.session_id
                FROM analytics_events ae
                WHERE ae.user_id = $1 AND ae.timestamp > NOW() - INTERVAL '2 years'
                ORDER BY ae.timestamp DESC
                LIMIT 5000
            """,
            DataCategory.SYSTEM: """
                SELECT 'system_log' as data_type, sl.id, sl.log_level, sl.message,
                       sl.timestamp, sl.service_name, sl.request_id
                FROM system_logs sl
                WHERE sl.user_id = $1 AND sl.timestamp > NOW() - INTERVAL '90 days'
                ORDER BY sl.timestamp DESC
                LIMIT 1000
            """
        }
        
        query = queries.get(category)
        if not query:
            logger.warning("No query defined for category", category=category.value)
            return []
        
        try:
            async with pool.acquire() as conn:
                rows = await conn.fetch(query, learner_id)
                return [dict(row) for row in rows]
        except Exception as e:
            logger.error("Failed to export category data", 
                        category=category.value, 
                        error=str(e))
            # Return empty list on error to continue with other categories
            return []
    
    async def _apply_pii_redaction(self, data: List[Dict[str, Any]], category: DataCategory) -> List[Dict[str, Any]]:
        """Apply PII redaction based on category and data sensitivity"""
        
        # Define redaction rules for sensitive fields
        redaction_rules = {
            DataCategory.PROFILE: {
                "email": lambda x: self._mask_email(x),
                "ip_address": lambda x: self._mask_ip(x)
            },
            DataCategory.INTERACTIONS: {
                "ip_address": lambda x: self._mask_ip(x),
                "user_agent": lambda x: "REDACTED"
            },
            DataCategory.SYSTEM: {
                "ip_address": lambda x: self._mask_ip(x),
                "user_agent": lambda x: "REDACTED"
            }
        }
        
        rules = redaction_rules.get(category, {})
        if not rules:
            return data
        
        redacted_data = []
        for record in data:
            redacted_record = record.copy()
            for field, redaction_func in rules.items():
                if field in redacted_record:
                    redacted_record[field] = redaction_func(redacted_record[field])
            redacted_data.append(redacted_record)
        
        return redacted_data
    
    def _mask_email(self, email: str) -> str:
        """Mask email address"""
        if not email or "@" not in email:
            return email
        local, domain = email.split("@", 1)
        if len(local) <= 2:
            masked_local = "*" * len(local)
        else:
            masked_local = local[0] + "*" * (len(local) - 2) + local[-1]
        return f"{masked_local}@{domain}"
    
    def _mask_ip(self, ip: str) -> str:
        """Mask IP address"""
        if not ip:
            return ip
        if ":" in ip:  # IPv6
            return "::ffff:192.0.2.1"  # RFC 5737 documentation IP
        else:  # IPv4
            return "192.0.2.1"  # RFC 5737 documentation IP
    
    async def _create_json_export(
        self, 
        export_dir: Path, 
        data: Dict[str, Any], 
        include_metadata: bool
    ) -> List[Path]:
        """Create JSON export files"""
        files = []
        
        # Create metadata file if requested
        if include_metadata:
            metadata = {
                "export_timestamp": datetime.utcnow().isoformat(),
                "format": "json",
                "version": "1.0",
                "categories": list(data.keys()),
                "total_records": sum(len(v) if isinstance(v, list) else 1 for v in data.values())
            }
            
            metadata_file = export_dir / "metadata.json"
            with open(metadata_file, 'w', encoding='utf-8') as f:
                json.dump(metadata, f, indent=2, default=str)
            files.append(metadata_file)
        
        # Create data files by category
        for category, category_data in data.items():
            data_file = export_dir / f"{category}.json"
            with open(data_file, 'w', encoding='utf-8') as f:
                json.dump(category_data, f, indent=2, default=str)
            files.append(data_file)
        
        return files
    
    async def _create_csv_export(
        self, 
        export_dir: Path, 
        data: Dict[str, Any], 
        include_metadata: bool
    ) -> List[Path]:
        """Create CSV export files"""
        files = []
        
        # Create metadata file if requested
        if include_metadata:
            metadata_file = export_dir / "metadata.csv"
            with open(metadata_file, 'w', newline='', encoding='utf-8') as f:
                writer = csv.writer(f)
                writer.writerow(["Property", "Value"])
                writer.writerow(["Export Timestamp", datetime.utcnow().isoformat()])
                writer.writerow(["Format", "csv"])
                writer.writerow(["Version", "1.0"])
                writer.writerow(["Categories", ",".join(data.keys())])
                writer.writerow(["Total Records", sum(len(v) if isinstance(v, list) else 1 for v in data.values())])
            files.append(metadata_file)
        
        # Create CSV files by category
        for category, category_data in data.items():
            if not category_data:
                continue
                
            data_file = export_dir / f"{category}.csv"
            
            if isinstance(category_data, list) and len(category_data) > 0:
                # Extract all unique keys for CSV headers
                all_keys = set()
                for record in category_data:
                    if isinstance(record, dict):
                        all_keys.update(record.keys())
                
                headers = sorted(list(all_keys))
                
                with open(data_file, 'w', newline='', encoding='utf-8') as f:
                    writer = csv.DictWriter(f, fieldnames=headers)
                    writer.writeheader()
                    for record in category_data:
                        if isinstance(record, dict):
                            # Convert complex types to strings
                            csv_record = {}
                            for key in headers:
                                value = record.get(key)
                                if isinstance(value, (dict, list)):
                                    csv_record[key] = json.dumps(value, default=str)
                                else:
                                    csv_record[key] = str(value) if value is not None else ""
                            writer.writerow(csv_record)
            
            files.append(data_file)
        
        return files
    
    async def _create_zip_archive(self, file_paths: List[Path], zip_path: Path) -> None:
        """Create ZIP archive of export files"""
        with zipfile.ZipFile(zip_path, 'w', zipfile.ZIP_DEFLATED) as zipf:
            for file_path in file_paths:
                zipf.write(file_path, file_path.name)
                # Remove original file after adding to ZIP
                file_path.unlink()
    
    async def _calculate_file_checksum(self, file_path: Path) -> str:
        """Calculate SHA-256 checksum of file"""
        sha256_hash = hashlib.sha256()
        with open(file_path, "rb") as f:
            for chunk in iter(lambda: f.read(4096), b""):
                sha256_hash.update(chunk)
        return sha256_hash.hexdigest()
    
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
    
    async def _update_request_completion(
        self, 
        request_id: UUID, 
        file_path: str, 
        file_size: int, 
        records_processed: int
    ) -> None:
        """Update request with completion details"""
        pool = await get_db_pool()
        async with pool.acquire() as conn:
            await conn.execute(
                """
                UPDATE privacy_requests 
                SET status = $1, completed_at = NOW(), file_path = $2, 
                    file_size_bytes = $3, records_processed = $4,
                    expires_at = NOW() + INTERVAL '30 days'
                WHERE id = $5
                """,
                PrivacyRequestStatus.COMPLETED.value, file_path, file_size, 
                records_processed, request_id
            )
