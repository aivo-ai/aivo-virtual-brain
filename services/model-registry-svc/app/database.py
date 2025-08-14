"""
AIVO Model Registry - Database Configuration
S2-02 Implementation: PostgreSQL connection and session management
"""

import os
from typing import Generator
from contextlib import contextmanager

from sqlalchemy import create_engine, MetaData
from sqlalchemy.orm import sessionmaker, Session
from sqlalchemy.pool import QueuePool

from .models import Base


class DatabaseConfig:
    """Database configuration settings"""
    
    def __init__(self):
        # PostgreSQL connection settings
        self.host = os.getenv("POSTGRES_HOST", "localhost")
        self.port = int(os.getenv("POSTGRES_PORT", "5432"))
        self.database = os.getenv("POSTGRES_DB", "model_registry")
        self.username = os.getenv("POSTGRES_USER", "postgres")
        self.password = os.getenv("POSTGRES_PASSWORD", "postgres")
        
        # Connection pool settings
        self.pool_size = int(os.getenv("DB_POOL_SIZE", "10"))
        self.max_overflow = int(os.getenv("DB_MAX_OVERFLOW", "20"))
        self.pool_timeout = int(os.getenv("DB_POOL_TIMEOUT", "30"))
        self.pool_recycle = int(os.getenv("DB_POOL_RECYCLE", "3600"))
        
        # Connection URL
        self.database_url = (
            f"postgresql://{self.username}:{self.password}@"
            f"{self.host}:{self.port}/{self.database}"
        )
    
    @property
    def is_test_env(self) -> bool:
        """Check if running in test environment"""
        return os.getenv("ENVIRONMENT") == "test"


# Global database configuration
db_config = DatabaseConfig()

# Create SQLAlchemy engine
engine = create_engine(
    db_config.database_url,
    poolclass=QueuePool,
    pool_size=db_config.pool_size,
    max_overflow=db_config.max_overflow,
    pool_timeout=db_config.pool_timeout,
    pool_recycle=db_config.pool_recycle,
    pool_pre_ping=True,  # Validate connections before use
    echo=os.getenv("SQL_DEBUG", "false").lower() == "true"
)

# Create session factory
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


def create_all_tables():
    """Create all database tables"""
    Base.metadata.create_all(bind=engine)


def drop_all_tables():
    """Drop all database tables (use with caution!)"""
    Base.metadata.drop_all(bind=engine)


def get_db_session() -> Generator[Session, None, None]:
    """
    FastAPI dependency to get database session
    Automatically handles session cleanup
    """
    session = SessionLocal()
    try:
        yield session
        session.commit()
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()


@contextmanager
def get_db_session_context() -> Generator[Session, None, None]:
    """
    Context manager for database sessions
    Use for standalone operations outside FastAPI
    """
    session = SessionLocal()
    try:
        yield session
        session.commit()
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()


def check_db_connection() -> bool:
    """Check if database connection is working"""
    try:
        with get_db_session_context() as session:
            session.execute("SELECT 1")
        return True
    except Exception as e:
        print(f"Database connection failed: {e}")
        return False


# Metadata for migrations
metadata = Base.metadata
