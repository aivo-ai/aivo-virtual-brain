"""
Consent Service Database Operations
Database service layer for consent state and immutable logging
"""

import json
import structlog
from datetime import datetime, timedelta
from typing import List, Optional, Dict, Any, Tuple
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine, async_sessionmaker
from sqlalchemy.orm import selectinload
from sqlalchemy import select, insert, update, delete, and_, or_, desc, func
from sqlalchemy.exc import SQLAlchemyError

from app.config import settings
from app.models import ConsentLog, ConsentState, Base
from app.schemas import ConsentKey, ConsentValue, ConsentUpdateRequest, ConsentLogEntry

logger = structlog.get_logger(__name__)

# Database engine and session
engine = create_async_engine(
    settings.database_url,
    echo=settings.database_echo,
    pool_size=10,
    max_overflow=20,
    pool_timeout=30
)

AsyncSessionLocal = async_sessionmaker(
    engine, 
    class_=AsyncSession, 
    expire_on_commit=False
)


class ConsentDatabaseService:
    """Database service for consent operations"""
    
    def __init__(self):
        self.engine = engine
        self.session_factory = AsyncSessionLocal
        logger.info("Consent database service initialized")
    
    async def create_tables(self):
        """Create database tables"""
        try:
            async with self.engine.begin() as conn:
                await conn.run_sync(Base.metadata.create_all)
            logger.info("Database tables created successfully")
        except Exception as e:
            logger.error("Failed to create database tables", error=str(e))
            raise
    
    async def get_session(self) -> AsyncSession:
        """Get database session"""
        return self.session_factory()
    
    async def get_consent_state(self, learner_id: str) -> Optional[ConsentState]:
        """Get current consent state for a learner"""
        try:
            async with self.get_session() as session:
                result = await session.execute(
                    select(ConsentState).where(ConsentState.learner_id == learner_id)
                )
                consent_state = result.scalar_one_or_none()
                
                logger.info(
                    "Retrieved consent state",
                    learner_id=learner_id,
                    found=consent_state is not None
                )
                
                return consent_state
                
        except Exception as e:
            logger.error(
                "Failed to retrieve consent state",
                learner_id=learner_id,
                error=str(e)
            )
            raise
    
    async def create_consent_state(
        self, 
        learner_id: str, 
        guardian_id: Optional[str] = None,
        tenant_id: Optional[str] = None
    ) -> ConsentState:
        """Create initial consent state with default values"""
        try:
            async with self.get_session() as session:
                consent_state = ConsentState(
                    learner_id=learner_id,
                    media=settings.default_media_consent,
                    chat=settings.default_chat_consent,
                    third_party=settings.default_third_party_consent,
                    guardian_id=guardian_id,
                    tenant_id=tenant_id,
                    created_at=datetime.utcnow(),
                    updated_at=datetime.utcnow()
                )
                
                session.add(consent_state)
                await session.commit()
                await session.refresh(consent_state)
                
                logger.info(
                    "Created consent state",
                    learner_id=learner_id,
                    guardian_id=guardian_id,
                    tenant_id=tenant_id,
                    defaults={
                        "media": settings.default_media_consent,
                        "chat": settings.default_chat_consent,
                        "third_party": settings.default_third_party_consent
                    }
                )
                
                return consent_state
                
        except Exception as e:
            logger.error(
                "Failed to create consent state",
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
    ) -> ConsentState:
        """Update consent state and log changes"""
        try:
            async with self.get_session() as session:
                async with session.begin():
                    # Get or create consent state
                    result = await session.execute(
                        select(ConsentState).where(ConsentState.learner_id == learner_id)
                    )
                    consent_state = result.scalar_one_or_none()
                    
                    if not consent_state:
                        consent_state = ConsentState(
                            learner_id=learner_id,
                            media=settings.default_media_consent,
                            chat=settings.default_chat_consent,
                            third_party=settings.default_third_party_consent,
                            created_at=datetime.utcnow(),
                            updated_at=datetime.utcnow()
                        )
                        session.add(consent_state)
                        await session.flush()
                    
                    # Apply consent changes and create log entries
                    log_entries = []
                    changes_made = False
                    
                    for consent in consents:
                        old_value = getattr(consent_state, consent.key.value)
                        
                        if old_value != consent.value:
                            # Update state
                            setattr(consent_state, consent.key.value, consent.value)
                            changes_made = True
                            
                            # Create log entry
                            log_entry = ConsentLog(
                                learner_id=learner_id,
                                actor_user_id=actor_user_id,
                                key=consent.key.value,
                                value=consent.value,
                                ts=datetime.utcnow(),
                                metadata_json=json.dumps(metadata) if metadata else None,
                                ip_address=ip_address,
                                user_agent=user_agent
                            )
                            session.add(log_entry)
                            log_entries.append(log_entry)
                    
                    if changes_made:
                        consent_state.updated_at = datetime.utcnow()
                    
                    await session.commit()
                    
                    logger.info(
                        "Updated consent state",
                        learner_id=learner_id,
                        actor_user_id=actor_user_id,
                        changes=len(log_entries),
                        consents={c.key.value: c.value for c in consents}
                    )
                    
                    return consent_state
                    
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
    ) -> Tuple[List[ConsentLog], int]:
        """Get consent log history for a learner"""
        try:
            async with self.get_session() as session:
                # Get total count
                count_result = await session.execute(
                    select(func.count(ConsentLog.id)).where(
                        ConsentLog.learner_id == learner_id
                    )
                )
                total_count = count_result.scalar()
                
                # Get log entries
                result = await session.execute(
                    select(ConsentLog)
                    .where(ConsentLog.learner_id == learner_id)
                    .order_by(desc(ConsentLog.ts))
                    .limit(limit)
                    .offset(offset)
                )
                log_entries = result.scalars().all()
                
                logger.info(
                    "Retrieved consent log",
                    learner_id=learner_id,
                    total_entries=total_count,
                    returned_entries=len(log_entries)
                )
                
                return list(log_entries), total_count
                
        except Exception as e:
            logger.error(
                "Failed to retrieve consent log",
                learner_id=learner_id,
                error=str(e)
            )
            raise
    
    async def get_bulk_consent_states(
        self, 
        learner_ids: List[str]
    ) -> List[ConsentState]:
        """Get consent states for multiple learners"""
        try:
            async with self.get_session() as session:
                result = await session.execute(
                    select(ConsentState).where(
                        ConsentState.learner_id.in_(learner_ids)
                    )
                )
                consent_states = result.scalars().all()
                
                logger.info(
                    "Retrieved bulk consent states",
                    requested=len(learner_ids),
                    found=len(consent_states)
                )
                
                return list(consent_states)
                
        except Exception as e:
            logger.error(
                "Failed to retrieve bulk consent states",
                learner_count=len(learner_ids),
                error=str(e)
            )
            raise
    
    async def get_consent_statistics(self) -> Dict[str, Any]:
        """Get consent statistics for monitoring"""
        try:
            async with self.get_session() as session:
                # Total learners
                total_result = await session.execute(
                    select(func.count(ConsentState.learner_id))
                )
                total_learners = total_result.scalar()
                
                # Consent statistics by type
                stats = {}
                for consent_type in ['media', 'chat', 'third_party']:
                    # Count granted
                    granted_result = await session.execute(
                        select(func.count(ConsentState.learner_id)).where(
                            getattr(ConsentState, consent_type) == True
                        )
                    )
                    granted = granted_result.scalar()
                    
                    # Count revoked
                    revoked_result = await session.execute(
                        select(func.count(ConsentState.learner_id)).where(
                            getattr(ConsentState, consent_type) == False
                        )
                    )
                    revoked = revoked_result.scalar()
                    
                    stats[consent_type] = {
                        "granted": granted,
                        "revoked": revoked
                    }
                
                # Recent activity
                recent_changes_result = await session.execute(
                    select(func.count(ConsentLog.id)).where(
                        ConsentLog.ts >= datetime.utcnow() - timedelta(days=7)
                    )
                )
                recent_changes = recent_changes_result.scalar()
                
                logger.info(
                    "Retrieved consent statistics",
                    total_learners=total_learners,
                    recent_changes=recent_changes
                )
                
                return {
                    "total_learners": total_learners,
                    "consent_stats": stats,
                    "recent_changes_7d": recent_changes
                }
                
        except Exception as e:
            logger.error("Failed to retrieve consent statistics", error=str(e))
            raise
    
    async def cleanup_old_logs(self, retention_days: int = None) -> int:
        """Clean up old consent log entries beyond retention period"""
        try:
            retention_days = retention_days or settings.audit_retention_days
            cutoff_date = datetime.utcnow() - timedelta(days=retention_days)
            
            async with self.get_session() as session:
                result = await session.execute(
                    delete(ConsentLog).where(ConsentLog.ts < cutoff_date)
                )
                deleted_count = result.rowcount
                await session.commit()
                
                logger.info(
                    "Cleaned up old consent logs",
                    retention_days=retention_days,
                    deleted_count=deleted_count,
                    cutoff_date=cutoff_date
                )
                
                return deleted_count
                
        except Exception as e:
            logger.error(
                "Failed to cleanup old consent logs",
                retention_days=retention_days,
                error=str(e)
            )
            raise
    
    async def health_check(self) -> bool:
        """Check database connectivity"""
        try:
            async with self.get_session() as session:
                await session.execute(select(1))
            return True
        except Exception as e:
            logger.error("Database health check failed", error=str(e))
            return False


# Global database service instance
db_service = ConsentDatabaseService()
