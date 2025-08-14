# AIVO SLP Service - Database Configuration
# S2-11 Implementation - SQLAlchemy database setup and session management

from sqlalchemy import create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, Session
from sqlalchemy.pool import StaticPool
import os
from typing import Generator

# Database configuration
DATABASE_URL = os.getenv(
    "DATABASE_URL",
    "postgresql://aivo:aivo123@localhost:5432/aivo_slp"
)

# For testing with SQLite
if os.getenv("TESTING"):
    DATABASE_URL = "sqlite:///./test_slp.db"

# Create engine with proper configuration for SQLite vs PostgreSQL
if "sqlite" in DATABASE_URL:
    # SQLite specific settings
    engine = create_engine(
        DATABASE_URL,
        poolclass=StaticPool,
        connect_args={"check_same_thread": False},
        echo=os.getenv("SQL_ECHO", "false").lower() == "true"
    )
else:
    # PostgreSQL settings
    engine = create_engine(
        DATABASE_URL,
        pool_size=10,
        max_overflow=20,
        pool_pre_ping=True,
        echo=os.getenv("SQL_ECHO", "false").lower() == "true"
    )

# Create session factory
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# Create base class for models
Base = declarative_base()


def get_db() -> Generator[Session, None, None]:
    """
    Database dependency for FastAPI.
    Creates a new database session for each request.
    """
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def create_tables():
    """Create all database tables."""
    Base.metadata.create_all(bind=engine)


def drop_tables():
    """Drop all database tables (for testing)."""
    Base.metadata.drop_all(bind=engine)
