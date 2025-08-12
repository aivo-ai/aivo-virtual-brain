"""
Consent Service Core
Core business logic for consent state management and audit logging
"""

import structlog
from datetime import datetime
from typing import List, Optional, Dict, Any, Tuple, Union
from uuid import UUID

from app.config import settings
from app.database import db_service, ConsentState, ConsentLog
from app.cache import cache_service
from app.schemas import (
    ConsentKey, ConsentValue, ConsentUpdateRequest, ConsentStateResponse,
    ConsentLogEntry, ConsentGateCheckRequest, ConsentGateCheckResponse,
    ConsentBulkRequest, ConsentBulkResponse
)

logger = structlog.get_logger(__name__)


class ConsentService:
    """Core consent service for state management and audit logging"""
    
    def __init__(self):
        self.db = db_service
        self.cache = cache_service
        logger.info("Consent service initialized")
    
    async def get_consent_state(
        self, 
        learner_id: str,
        use_cache: bool = True
    ) -> Optional[ConsentStateResponse]:
        """Get current consent state for a learner"""
        try:
            # Try cache first if enabled
            if use_cache:
                cached_state = await self.cache.get_consent_state(learner_id)
                if cached_state:
                    logger.debug("Consent state from cache", learner_id=learner_id)
                    return cached_state
            
            # Get from database
            db_state = await self.db.get_consent_state(learner_id)
            
            if not db_state:
                logger.info("No consent state found, creating default", learner_id=learner_id)
                
                # Create default consent state
                db_state = await self.db.create_consent_state(learner_id)
            
            # Convert to response model
            response = ConsentStateResponse(
                learner_id=db_state.learner_id,
                media=db_state.media,
                chat=db_state.chat,
                third_party=db_state.third_party,
                guardian_id=db_state.guardian_id,
                tenant_id=db_state.tenant_id,
                created_at=db_state.created_at,
                updated_at=db_state.updated_at
            )
            
            # Cache the result
            if use_cache:
                await self.cache.set_consent_state(learner_id, response)
            
            logger.info("Retrieved consent state", learner_id=learner_id)
            return response
            
        except Exception as e:
            logger.error(
                "Failed to get consent state",
                learner_id=learner_id,
                error=str(e)
            )
            raise
    
    async def update_consent_state(
        self, 
        learner_id: str,
        consents: List[ConsentValue],
        actor_user_id: str,
        metadata: Optional[Dict[str, Any]] = None,
        ip_address: Optional[str] = None,
        user_agent: Optional[str] = None
    ) -> ConsentStateResponse:
        """Update consent state with audit logging"""
        try:
            # Validate consent keys
            valid_keys = {key.value for key in ConsentKey}
            for consent in consents:
                if consent.key.value not in valid_keys:
                    raise ValueError(f"Invalid consent key: {consent.key.value}")
            
            # Update in database with audit trail
            db_state = await self.db.update_consent_state(
                learner_id=learner_id,
                consents=consents,
                actor_user_id=actor_user_id,
                metadata=metadata,
                ip_address=ip_address,
                user_agent=user_agent
            )
            
            # Convert to response model
            response = ConsentStateResponse(
                learner_id=db_state.learner_id,
                media=db_state.media,
                chat=db_state.chat,
                third_party=db_state.third_party,
                guardian_id=db_state.guardian_id,
                tenant_id=db_state.tenant_id,
                created_at=db_state.created_at,
                updated_at=db_state.updated_at
            )
            
            # Invalidate and update cache
            await self.cache.invalidate_consent_state(learner_id)
            await self.cache.set_consent_state(learner_id, response)
            
            logger.info(
                "Updated consent state",
                learner_id=learner_id,
                actor_user_id=actor_user_id,
                consents={c.key.value: c.value for c in consents}
            )
            
            return response
            
        except Exception as e:
            logger.error(
                "Failed to update consent state",
                learner_id=learner_id,
                error=str(e)
            )
            raise
    
    async def get_consent_log(
        self, 
        learner_id: str,
        limit: int = 100,
        offset: int = 0
    ) -> Tuple[List[ConsentLogEntry], int]:
        """Get consent audit log for a learner"""
        try:
            log_entries, total_count = await self.db.get_consent_log(
                learner_id=learner_id,
                limit=limit,
                offset=offset
            )
            
            # Convert to response models
            response_entries = []
            for entry in log_entries:
                response_entry = ConsentLogEntry(
                    id=entry.id,
                    learner_id=entry.learner_id,
                    actor_user_id=entry.actor_user_id,
                    key=entry.key,
                    value=entry.value,
                    ts=entry.ts,
                    metadata=entry.metadata,
                    ip_address=entry.ip_address,
                    user_agent=entry.user_agent
                )
                response_entries.append(response_entry)
            
            logger.info(
                "Retrieved consent log",
                learner_id=learner_id,
                entries=len(response_entries),
                total=total_count
            )
            
            return response_entries, total_count
            
        except Exception as e:
            logger.error(
                "Failed to get consent log",
                learner_id=learner_id,
                error=str(e)
            )
            raise
    
    async def check_consent_gate(
        self, 
        request: ConsentGateCheckRequest
    ) -> ConsentGateCheckResponse:
        """Check consent for gateway filtering"""
        try:
            learner_id = request.learner_id
            consent_type = request.consent_type
            
            # Try cache first for gateway performance
            cached_value = await self.cache.get_consent_gate_value(
                learner_id, 
                consent_type
            )
            
            if cached_value is not None:
                response = ConsentGateCheckResponse(
                    learner_id=learner_id,
                    consent_type=consent_type,
                    allowed=cached_value,
                    source="cache"
                )
                
                logger.debug(
                    "Gateway consent check (cache)",
                    learner_id=learner_id,
                    consent_type=consent_type,
                    allowed=cached_value
                )
                
                return response
            
            # Fallback to database
            consent_state = await self.get_consent_state(learner_id, use_cache=False)
            
            if not consent_state:
                # Default to denied if no consent state exists
                response = ConsentGateCheckResponse(
                    learner_id=learner_id,
                    consent_type=consent_type,
                    allowed=False,
                    source="default"
                )
            else:
                allowed = getattr(consent_state, consent_type, False)
                response = ConsentGateCheckResponse(
                    learner_id=learner_id,
                    consent_type=consent_type,
                    allowed=allowed,
                    source="database"
                )
            
            logger.info(
                "Gateway consent check (database)",
                learner_id=learner_id,
                consent_type=consent_type,
                allowed=response.allowed
            )
            
            return response
            
        except Exception as e:
            logger.error(
                "Failed consent gate check",
                learner_id=request.learner_id,
                consent_type=request.consent_type,
                error=str(e)
            )
            
            # Return denied on error for security
            return ConsentGateCheckResponse(
                learner_id=request.learner_id,
                consent_type=request.consent_type,
                allowed=False,
                source="error"
            )
    
    async def bulk_get_consent_states(
        self, 
        learner_ids: List[str],
        use_cache: bool = True
    ) -> Dict[str, ConsentStateResponse]:
        """Get consent states for multiple learners"""
        try:
            if not learner_ids:
                return {}
            
            results = {}
            missing_ids = set(learner_ids)
            
            # Try cache first if enabled
            if use_cache:
                cached_states = await self.cache.get_bulk_consent_states(learner_ids)
                results.update(cached_states)
                missing_ids -= set(cached_states.keys())
            
            # Get missing states from database
            if missing_ids:
                db_states = await self.db.get_bulk_consent_states(list(missing_ids))
                
                for db_state in db_states:
                    response = ConsentStateResponse(
                        learner_id=db_state.learner_id,
                        media=db_state.media,
                        chat=db_state.chat,
                        third_party=db_state.third_party,
                        guardian_id=db_state.guardian_id,
                        tenant_id=db_state.tenant_id,
                        created_at=db_state.created_at,
                        updated_at=db_state.updated_at
                    )
                    results[db_state.learner_id] = response
                    
                    # Cache the result
                    if use_cache:
                        await self.cache.set_consent_state(
                            db_state.learner_id, 
                            response
                        )
                
                # Remove found IDs from missing set
                found_db_ids = {state.learner_id for state in db_states}
                missing_ids -= found_db_ids
            
            # Create default states for any still missing
            for missing_id in missing_ids:
                try:
                    db_state = await self.db.create_consent_state(missing_id)
                    response = ConsentStateResponse(
                        learner_id=db_state.learner_id,
                        media=db_state.media,
                        chat=db_state.chat,
                        third_party=db_state.third_party,
                        guardian_id=db_state.guardian_id,
                        tenant_id=db_state.tenant_id,
                        created_at=db_state.created_at,
                        updated_at=db_state.updated_at
                    )
                    results[missing_id] = response
                    
                    if use_cache:
                        await self.cache.set_consent_state(missing_id, response)
                        
                except Exception as e:
                    logger.warning(
                        "Failed to create default consent state",
                        learner_id=missing_id,
                        error=str(e)
                    )
            
            logger.info(
                "Bulk consent state retrieval",
                requested=len(learner_ids),
                found=len(results),
                cache_hits=len(learner_ids) - len(missing_ids) if use_cache else 0
            )
            
            return results
            
        except Exception as e:
            logger.error(
                "Failed to bulk get consent states",
                learner_count=len(learner_ids),
                error=str(e)
            )
            raise
    
    async def get_consent_statistics(self) -> Dict[str, Any]:
        """Get consent statistics for monitoring and reporting"""
        try:
            # Database statistics
            db_stats = await self.db.get_consent_statistics()
            
            # Cache statistics
            cache_stats = await self.cache.set_cache_stats()
            
            combined_stats = {
                "database": db_stats,
                "cache": cache_stats,
                "timestamp": datetime.utcnow().isoformat()
            }
            
            logger.info("Retrieved consent statistics")
            return combined_stats
            
        except Exception as e:
            logger.error("Failed to get consent statistics", error=str(e))
            raise
    
    async def health_check(self) -> Dict[str, bool]:
        """Check health of consent service components"""
        try:
            db_healthy = await self.db.health_check()
            cache_healthy = await self.cache.health_check()
            
            health_status = {
                "database": db_healthy,
                "cache": cache_healthy,
                "overall": db_healthy and cache_healthy
            }
            
            if health_status["overall"]:
                logger.debug("Consent service health check passed")
            else:
                logger.warning("Consent service health check failed", **health_status)
            
            return health_status
            
        except Exception as e:
            logger.error("Consent service health check error", error=str(e))
            return {
                "database": False,
                "cache": False,
                "overall": False
            }
    
    async def cleanup_old_logs(self, retention_days: Optional[int] = None) -> int:
        """Clean up old consent audit logs"""
        try:
            deleted_count = await self.db.cleanup_old_logs(retention_days)
            
            logger.info(
                "Cleaned up old consent logs",
                deleted_count=deleted_count,
                retention_days=retention_days or settings.audit_retention_days
            )
            
            return deleted_count
            
        except Exception as e:
            logger.error("Failed to cleanup old logs", error=str(e))
            raise
    
    async def invalidate_learner_cache(self, learner_id: str) -> bool:
        """Invalidate all cache entries for a learner"""
        try:
            success = await self.cache.invalidate_consent_state(learner_id)
            
            logger.info(
                "Invalidated learner consent cache",
                learner_id=learner_id,
                success=success
            )
            
            return success
            
        except Exception as e:
            logger.error(
                "Failed to invalidate learner cache",
                learner_id=learner_id,
                error=str(e)
            )
            return False


# Global consent service instance
consent_service = ConsentService()
