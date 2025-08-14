# AIVO SEL Service - Database Configuration
# S2-12 Implementation - SQLAlchemy database setup

import os
import logging
from datetime import datetime, timezone, timedelta
from typing import Generator
from sqlalchemy import create_engine, event, and_
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, Session
from sqlalchemy.pool import StaticPool

logger = logging.getLogger(__name__)

# Database configuration
DATABASE_URL = os.getenv(
    "DATABASE_URL",
    "postgresql://aivo_sel:sel_secure_pass@postgres:5432/aivo_sel_db"
)

# Create SQLAlchemy engine
engine = create_engine(
    DATABASE_URL,
    pool_size=20,
    max_overflow=30,
    pool_timeout=30,
    pool_recycle=3600,
    echo=os.getenv("SQL_ECHO", "false").lower() == "true"
)

# Create sessionmaker
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# Create declarative base
Base = declarative_base()


def get_db() -> Generator[Session, None, None]:
    """
    Database dependency for FastAPI.
    Creates a new database session for each request.
    """
    db = SessionLocal()
    try:
        yield db
    except Exception as e:
        logger.error(f"Database error: {str(e)}")
        db.rollback()
        raise
    finally:
        db.close()


async def init_database():
    """
    Initialize database schema and perform setup tasks.
    """
    try:
        logger.info("Initializing database schema...")
        
        # Import models to register them with Base
        from . import models
        
        # Create all tables
        Base.metadata.create_all(bind=engine)
        
        logger.info("Database schema initialization completed")
        
    except Exception as e:
        logger.error(f"Database initialization failed: {str(e)}")
        raise


async def health_check_db() -> bool:
    """
    Check database connectivity for health checks.
    
    Returns:
        Boolean indicating if database is accessible
    """
    try:
        db = SessionLocal()
        
        # Simple connectivity test
        result = db.execute("SELECT 1").scalar()
        db.close()
        
        return result == 1
        
    except Exception as e:
        logger.error(f"Database health check failed: {str(e)}")
        return False


# Database event listeners for additional functionality
@event.listens_for(engine, "connect")
def set_sqlite_pragma(dbapi_connection, connection_record):
    """
    Set SQLite pragmas for development/testing.
    Only applies if using SQLite.
    """
    if "sqlite" in DATABASE_URL:
        cursor = dbapi_connection.cursor()
        cursor.execute("PRAGMA foreign_keys=ON")
        cursor.close()


@event.listens_for(SessionLocal, "before_commit")
def before_commit(session):
    """
    Hook executed before database commit.
    Can be used for additional validation or logging.
    """
    pass


@event.listens_for(SessionLocal, "after_commit")
def after_commit(session):
    """
    Hook executed after successful database commit.
    Can be used for cleanup or event publishing.
    """
    pass


class DatabaseManager:
    """
    Centralized database management utilities.
    """
    
    @staticmethod
    async def create_test_data():
        """
        Create test data for development and testing.
        Only use in non-production environments.
        """
        if os.getenv("ENVIRONMENT", "development") not in ["development", "testing"]:
            logger.warning("Test data creation attempted in non-development environment")
            return
        
        try:
            from .models import ConsentRecord, ConsentStatus
            from datetime import datetime, timezone, timedelta
            import uuid
            
            db = SessionLocal()
            
            # Create sample consent records for testing
            test_consents = [
                ConsentRecord(
                    id=uuid.uuid4(),
                    tenant_id=uuid.UUID("12345678-1234-5678-9abc-123456789012"),
                    student_id=uuid.UUID("87654321-4321-8765-cbaa-210987654321"),
                    status=ConsentStatus.GRANTED,
                    consent_type="comprehensive",
                    data_collection_allowed=True,
                    data_sharing_allowed=True,
                    alert_notifications_allowed=True,
                    ai_processing_allowed=True,
                    research_participation_allowed=False,
                    parent_guardian_consent=True,
                    student_assent=True,
                    consent_date=datetime.now(timezone.utc),
                    expiration_date=datetime.now(timezone.utc) + timedelta(days=365),
                    consent_method="digital_signature",
                    consenting_party_name="Test Parent",
                    consenting_party_relationship="parent"
                )
            ]
            
            for consent in test_consents:
                existing = db.query(ConsentRecord).filter(
                    ConsentRecord.student_id == consent.student_id
                ).first()
                
                if not existing:
                    db.add(consent)
                    
            db.commit()
            db.close()
            
            logger.info("Test data created successfully")
            
        except Exception as e:
            logger.error(f"Error creating test data: {str(e)}")
            raise
    
    @staticmethod
    async def backup_database(backup_path: str = None):
        """
        Create database backup.
        Implementation depends on database type.
        """
        try:
            if not backup_path:
                backup_path = f"/tmp/sel_db_backup_{datetime.now().strftime('%Y%m%d_%H%M%S')}.sql"
            
            logger.info(f"Database backup functionality not implemented for {DATABASE_URL}")
            # Implementation would depend on database type (PostgreSQL, MySQL, etc.)
            
        except Exception as e:
            logger.error(f"Database backup failed: {str(e)}")
            raise
    
    @staticmethod
    async def cleanup_expired_data():
        """
        Clean up expired data according to retention policies.
        """
        try:
            from .models import ConsentRecord, SELCheckIn, SELAlert
            from datetime import datetime, timezone, timedelta
            
            db = SessionLocal()
            
            # Clean up expired consent records
            expired_date = datetime.now(timezone.utc)
            expired_consents = db.query(ConsentRecord).filter(
                ConsentRecord.expiration_date < expired_date
            ).all()
            
            from .models import ConsentStatus
            for consent in expired_consents:
                consent.status = ConsentStatus.EXPIRED
            
            # Clean up old check-ins based on retention policy (example: 2 years)
            retention_cutoff = datetime.now(timezone.utc) - timedelta(days=730)
            old_checkins_query = db.query(SELCheckIn).filter(
                SELCheckIn.created_at < retention_cutoff
            )
            
            old_checkins_count = old_checkins_query.count()
            if old_checkins_count > 0:
                logger.info(f"Would delete {old_checkins_count} old check-ins (retention policy)")
                # Uncomment to actually delete:
                # old_checkins_query.delete()
            
            # Clean up resolved alerts older than 90 days
            alert_cutoff = datetime.now(timezone.utc) - timedelta(days=90)
            old_alerts_query = db.query(SELAlert).filter(
                and_(
                    SELAlert.status == "resolved",
                    SELAlert.resolved_at < alert_cutoff
                )
            )
            
            old_alerts_count = old_alerts_query.count()
            if old_alerts_count > 0:
                logger.info(f"Would delete {old_alerts_count} old resolved alerts")
                # Uncomment to actually delete:
                # old_alerts_query.delete()
            
            db.commit()
            db.close()
            
            logger.info("Data cleanup completed")
            
        except Exception as e:
            logger.error(f"Data cleanup failed: {str(e)}")
            raise


# Database connection testing utilities
async def test_database_connection():
    """
    Test database connection and basic operations.
    """
    try:
        logger.info("Testing database connection...")
        
        # Test basic connectivity
        if not await health_check_db():
            raise Exception("Database connectivity test failed")
        
        # Test table creation/access
        db = SessionLocal()
        
        # Import models to ensure they're registered
        from . import models
        
        # Test query execution
        result = db.execute("SELECT current_timestamp").scalar()
        logger.info(f"Database timestamp: {result}")
        
        db.close()
        
        logger.info("Database connection test passed")
        return True
        
    except Exception as e:
        logger.error(f"Database connection test failed: {str(e)}")
        return False
