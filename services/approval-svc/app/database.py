# AIVO Approval Service - Database Configuration
# S2-10 Implementation - PostgreSQL connection and session management

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, Session
from sqlalchemy.pool import StaticPool
import os
from typing import Generator

# Database configuration
DATABASE_URL = os.getenv(
    "DATABASE_URL", 
    "postgresql://aivo_user:aivo_pass@localhost:5432/aivo_approval_db"
)

# Create engine with connection pooling
engine = create_engine(
    DATABASE_URL,
    echo=bool(os.getenv("SQL_DEBUG", "false").lower() == "true"),
    pool_pre_ping=True,
    pool_recycle=3600,
    pool_size=20,
    max_overflow=30
)

# Create SessionLocal class
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# Import shared Base
from .base import Base


def get_db() -> Generator[Session, None, None]:
    """
    Dependency to get database session.
    
    Yields:
        Session: SQLAlchemy database session
    """
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def create_tables():
    """Create all database tables."""
    from .models import ApprovalRequest, ApprovalDecision, ApprovalReminder, ApprovalAuditLog
    Base.metadata.create_all(bind=engine)


def drop_tables():
    """Drop all database tables (for testing)."""
    Base.metadata.drop_all(bind=engine)


# Health check function
def check_database_health() -> bool:
    """
    Check if database is accessible.
    
    Returns:
        bool: True if database is healthy, False otherwise
    """
    try:
        db = SessionLocal()
        db.execute("SELECT 1")
        db.close()
        return True
    except Exception:
        return False
