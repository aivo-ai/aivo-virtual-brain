"""
Database configuration and session management
"""

from contextlib import asynccontextmanager
from typing import AsyncGenerator

from sqlalchemy import create_engine
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker

from .config import settings

# Create sync engine for Alembic migrations
engine = create_engine(
    settings.database_url.replace("postgresql://", "postgresql+psycopg2://"),
    pool_pre_ping=True,
    pool_recycle=300,
    echo=settings.environment == "development",
)

# Create async engine for FastAPI
async_engine = create_async_engine(
    settings.database_url.replace("postgresql://", "postgresql+asyncpg://"),
    pool_pre_ping=True,
    pool_recycle=300,
    echo=settings.environment == "development",
)

# Session makers
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
AsyncSessionLocal = async_sessionmaker(
    bind=async_engine,
    class_=AsyncSession,
    expire_on_commit=False,
)

# Base class for models
Base = declarative_base()


@asynccontextmanager
async def get_db() -> AsyncGenerator[AsyncSession, None]:
    """Get async database session"""
    async with AsyncSessionLocal() as session:
        try:
            yield session
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()


def get_sync_db():
    """Get sync database session (for Celery tasks)"""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
