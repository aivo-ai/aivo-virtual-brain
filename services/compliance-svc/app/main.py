"""
FastAPI main application for Compliance Service (S5-09)

Provides evidence aggregation endpoints for isolation tests, consent history,
data protection analytics, and audit logs.
"""

import os
import asyncio
from contextlib import asynccontextmanager
from datetime import datetime, timezone
from typing import Dict, Any, Optional

from fastapi import FastAPI, Depends, HTTPException, BackgroundTasks, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
from sqlalchemy.exc import SQLAlchemyError
import structlog
import redis.asyncio as redis
from prometheus_client import Counter, Histogram, Gauge, generate_latest
from starlette.responses import Response

from .models import Base
from .routes import create_router

# Logging setup
structlog.configure(
    processors=[
        structlog.stdlib.filter_by_level,
        structlog.stdlib.add_logger_name,
        structlog.stdlib.add_log_level,
        structlog.stdlib.PositionalArgumentsFormatter(),
        structlog.processors.TimeStamper(fmt="iso"),
        structlog.processors.StackInfoRenderer(),
        structlog.processors.format_exc_info,
        structlog.processors.UnicodeDecoder(),
        structlog.processors.JSONRenderer()
    ],
    context_class=dict,
    logger_factory=structlog.stdlib.LoggerFactory(),
    wrapper_class=structlog.stdlib.BoundLogger,
    cache_logger_on_first_use=True,
)

logger = structlog.get_logger()

# Metrics
evidence_requests = Counter('compliance_evidence_requests_total', 'Total evidence requests', ['endpoint', 'status'])
evidence_duration = Histogram('compliance_evidence_duration_seconds', 'Evidence request duration')
isolation_tests = Gauge('compliance_isolation_tests_total', 'Total isolation tests')
consent_records = Gauge('compliance_consent_records_total', 'Total consent records')
dp_requests = Gauge('compliance_dp_requests_total', 'Total data protection requests')
audit_events = Gauge('compliance_audit_events_total', 'Total audit events')

# Configuration
DATABASE_URL = os.getenv("DATABASE_URL", "postgresql+asyncpg://compliance:compliance@localhost/compliance")
REDIS_URL = os.getenv("REDIS_URL", "redis://localhost:6379")
LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO")
CORS_ORIGINS = os.getenv("CORS_ORIGINS", "*").split(",")

# Global variables
engine = None
async_session = None
redis_client = None


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan manager."""
    global engine, async_session, redis_client
    
    logger.info("Starting Compliance Service")
    
    # Initialize database
    engine = create_async_engine(
        DATABASE_URL,
        echo=LOG_LEVEL == "DEBUG",
        pool_size=10,
        max_overflow=20,
        pool_pre_ping=True,
        pool_recycle=3600
    )
    
    async_session = async_sessionmaker(
        engine,
        class_=AsyncSession,
        expire_on_commit=False
    )
    
    # Initialize Redis
    try:
        redis_client = redis.from_url(REDIS_URL, decode_responses=True)
        await redis_client.ping()
        logger.info("Redis connection established")
    except Exception as e:
        logger.warning("Redis connection failed", error=str(e))
        redis_client = None
    
    # Create tables
    try:
        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)
        logger.info("Database tables created/verified")
    except Exception as e:
        logger.error("Database initialization failed", error=str(e))
        raise
    
    # Start background tasks
    asyncio.create_task(update_metrics_periodically())
    
    yield
    
    # Cleanup
    logger.info("Shutting down Compliance Service")
    
    if redis_client:
        await redis_client.close()
    
    if engine:
        await engine.dispose()


# Dependency providers
async def get_db_session() -> AsyncSession:
    """Get database session."""
    if not async_session:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Database not available"
        )
    
    async with async_session() as session:
        try:
            yield session
        except SQLAlchemyError as e:
            await session.rollback()
            logger.error("Database error", error=str(e))
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Database operation failed"
            )
        finally:
            await session.close()


async def get_redis_client():
    """Get Redis client."""
    if not redis_client:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Redis not available"
        )
    return redis_client


# Background tasks
async def update_metrics_periodically():
    """Update Prometheus metrics periodically."""
    while True:
        try:
            if async_session:
                async with async_session() as session:
                    # Update metrics from database
                    from sqlalchemy import select, func
                    from .models import IsolationTestResult, ConsentRecord, DataProtectionRequest, AuditEvent
                    
                    # Count isolation tests
                    result = await session.execute(select(func.count(IsolationTestResult.id)))
                    isolation_tests.set(result.scalar())
                    
                    # Count consent records
                    result = await session.execute(select(func.count(ConsentRecord.id)))
                    consent_records.set(result.scalar())
                    
                    # Count DP requests
                    result = await session.execute(select(func.count(DataProtectionRequest.id)))
                    dp_requests.set(result.scalar())
                    
                    # Count audit events
                    result = await session.execute(select(func.count(AuditEvent.id)))
                    audit_events.set(result.scalar())
            
            await asyncio.sleep(60)  # Update every minute
            
        except Exception as e:
            logger.error("Failed to update metrics", error=str(e))
            await asyncio.sleep(300)  # Wait 5 minutes on error


# Create FastAPI app
app = FastAPI(
    title="Compliance Service",
    description="Evidence aggregation for isolation, consent, DP analytics, and audit logs",
    version="1.0.0",
    lifespan=lifespan,
    docs_url="/docs",
    redoc_url="/redoc"
)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# Health check
@app.get("/health")
async def health_check():
    """Health check endpoint."""
    try:
        # Check database
        if async_session:
            async with async_session() as session:
                await session.execute("SELECT 1")
        
        # Check Redis (optional)
        redis_status = "connected"
        if redis_client:
            try:
                await redis_client.ping()
            except Exception:
                redis_status = "disconnected"
        else:
            redis_status = "not_configured"
        
        return {
            "status": "healthy",
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "database": "connected",
            "redis": redis_status,
            "version": "1.0.0"
        }
    except Exception as e:
        logger.error("Health check failed", error=str(e))
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Service unhealthy"
        )


# Metrics endpoint
@app.get("/metrics")
async def get_metrics():
    """Prometheus metrics endpoint."""
    return Response(generate_latest(), media_type="text/plain")


# Error handlers
@app.exception_handler(HTTPException)
async def http_exception_handler(request, exc):
    """Handle HTTP exceptions."""
    evidence_requests.labels(
        endpoint=request.url.path,
        status=exc.status_code
    ).inc()
    
    return JSONResponse(
        status_code=exc.status_code,
        content={
            "detail": exc.detail,
            "timestamp": datetime.now(timezone.utc).isoformat()
        }
    )


@app.exception_handler(Exception)
async def general_exception_handler(request, exc):
    """Handle general exceptions."""
    logger.error("Unhandled exception", error=str(exc), path=request.url.path)
    
    evidence_requests.labels(
        endpoint=request.url.path,
        status=500
    ).inc()
    
    return JSONResponse(
        status_code=500,
        content={
            "detail": "Internal server error",
            "timestamp": datetime.now(timezone.utc).isoformat()
        }
    )


# Include routers
app.include_router(create_router(), prefix="/api/v1")

# Root redirect
@app.get("/")
async def root():
    """Root endpoint."""
    return {
        "service": "Compliance Service",
        "version": "1.0.0",
        "docs": "/docs",
        "health": "/health",
        "metrics": "/metrics"
    }


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=8083,
        log_level=LOG_LEVEL.lower(),
        reload=True
    )
