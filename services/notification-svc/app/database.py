# AIVO Notification Service - Database Configuration
# S1-12 Implementation - SQLAlchemy Database Setup

import os
from typing import Generator
from sqlalchemy import create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, Session

# Database configuration
DATABASE_URL = os.getenv("DATABASE_URL", "postgresql://notification_user:notification_pass@localhost:5432/notification_db")

# Create SQLAlchemy engine
engine = create_engine(
    DATABASE_URL,
    pool_size=20,
    max_overflow=30,
    pool_pre_ping=True,
    pool_recycle=3600,
    echo=False  # Set to True for SQL query logging
)

# Create session factory
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# Base class for models
Base = declarative_base()

def get_db() -> Generator[Session, None, None]:
    """Database dependency for FastAPI."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

def get_db_session() -> Session:
    """Get a database session for background tasks."""
    return SessionLocal()

def init_db():
    """Initialize database tables."""
    from .models import Base
    Base.metadata.create_all(bind=engine)
