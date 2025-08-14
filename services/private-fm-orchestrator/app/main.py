"""
FastAPI main application for Private Foundation Model Orchestrator.
"""

import os
import asyncio
from contextlib import asynccontextmanager
from datetime import datetime, timezone
from typing import Dict, Any, Optional
from uuid import UUID

from fastapi import FastAPI, Depends, HTTPException, BackgroundTasks, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
from sqlalchemy.exc import SQLAlchemyError
import structlog
import redis.asyncio as redis
from prometheus_client import Counter, Histogram, Gauge, generate_latest
from starlette.responses import Response

from .models import Base, LearnerNamespace, NamespaceStatus
from .isolator import NamespaceIsolator
from .cron import CronScheduler
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
namespace_count = Gauge('private_fm_namespaces_total', 'Total number of learner namespaces')
merge_operations = Counter('private_fm_merge_operations_total', 'Total merge operations', ['status'])
namespace_health_checks = Counter('private_fm_health_checks_total', 'Total health checks', ['result'])
operation_duration = Histogram('private_fm_operation_duration_seconds', 'Operation duration', ['operation_type'])
namespace_status_gauge = Gauge('private_fm_namespace_status', 'Namespace status by status', ['status'])

# Global application state
app_state = {}


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan context manager."""
    
    # Startup
    logger.info("Starting Private Foundation Model Orchestrator")
    
    try:
        # Database setup
        database_url = os.getenv("DATABASE_URL", "postgresql+asyncpg://user:password@localhost/private_fm")
        engine = create_async_engine(database_url, echo=os.getenv("SQL_ECHO", "false").lower() == "true")
        async_session = async_sessionmaker(engine, expire_on_commit=False)
        
        # Create tables
        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)
        
        # Redis setup
        redis_url = os.getenv("REDIS_URL", "redis://localhost:6379")
        redis_client = redis.from_url(redis_url)
        
        # Test connections
        async with async_session() as session:
            await session.execute("SELECT 1")
        
        await redis_client.ping()
        
        # Initialize components
        app_state["engine"] = engine
        app_state["async_session"] = async_session
        app_state["redis"] = redis_client
        
        # Initialize isolator and scheduler
        async with async_session() as session:
            isolator = NamespaceIsolator(session, redis_client)
            scheduler = CronScheduler(session, isolator, redis_client)
            
            app_state["isolator"] = isolator
            app_state["scheduler"] = scheduler
        
        # Start background tasks
        app_state["background_tasks"] = []
        
        # Merge queue processor
        if os.getenv("ENABLE_MERGE_PROCESSOR", "true").lower() == "true":
            merge_task = asyncio.create_task(merge_queue_processor())
            app_state["background_tasks"].append(merge_task)
        
        # Fallback queue processor
        if os.getenv("ENABLE_FALLBACK_PROCESSOR", "true").lower() == "true":
            fallback_task = asyncio.create_task(fallback_queue_processor())
            app_state["background_tasks"].append(fallback_task)
        
        # Metrics updater
        if os.getenv("ENABLE_METRICS", "true").lower() == "true":
            metrics_task = asyncio.create_task(update_metrics())
            app_state["background_tasks"].append(metrics_task)
        
        logger.info("Private Foundation Model Orchestrator started successfully")
        
        yield
        
    except Exception as e:
        logger.error("Failed to start application", error=str(e))
        raise
    
    # Shutdown
    logger.info("Shutting down Private Foundation Model Orchestrator")
    
    # Cancel background tasks
    for task in app_state.get("background_tasks", []):
        task.cancel()
        try:
            await task
        except asyncio.CancelledError:
            pass
    
    # Close connections
    if "redis" in app_state:
        await app_state["redis"].close()
    
    if "engine" in app_state:
        await app_state["engine"].dispose()
    
    logger.info("Private Foundation Model Orchestrator shutdown complete")


# FastAPI app
app = FastAPI(
    title="Private Foundation Model Orchestrator",
    description="Federated AI orchestration service with per-learner namespace isolation",
    version="1.0.0",
    lifespan=lifespan,
    docs_url="/docs" if os.getenv("ENVIRONMENT") != "production" else None,
    redoc_url="/redoc" if os.getenv("ENVIRONMENT") != "production" else None,
)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=os.getenv("CORS_ORIGINS", "*").split(","),
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# Dependencies
async def get_db() -> AsyncSession:
    """Get database session."""
    async_session = app_state["async_session"]
    async with async_session() as session:
        try:
            yield session
        except SQLAlchemyError as e:
            await session.rollback()
            logger.error("Database error", error=str(e))
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Database error occurred"
            )
        finally:
            await session.close()


async def get_redis() -> redis.Redis:
    """Get Redis client."""
    return app_state["redis"]


async def get_isolator() -> NamespaceIsolator:
    """Get namespace isolator."""
    async_session = app_state["async_session"]
    redis_client = app_state["redis"]
    
    async with async_session() as session:
        yield NamespaceIsolator(session, redis_client)


async def get_scheduler() -> CronScheduler:
    """Get cron scheduler."""
    async_session = app_state["async_session"]
    redis_client = app_state["redis"]
    
    async with async_session() as session:
        isolator = NamespaceIsolator(session, redis_client)
        yield CronScheduler(session, isolator, redis_client)


# Health check endpoints
@app.get("/health")
async def health_check() -> Dict[str, Any]:
    """Basic health check."""
    return {
        "status": "healthy",
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "version": "1.0.0"
    }


@app.get("/health/detailed")
async def detailed_health_check(
    db: AsyncSession = Depends(get_db),
    redis_client: redis.Redis = Depends(get_redis)
) -> Dict[str, Any]:
    """Detailed health check including dependencies."""
    
    health_status = {
        "status": "healthy",
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "version": "1.0.0",
        "checks": {}
    }
    
    # Database check
    try:
        await db.execute("SELECT 1")
        health_status["checks"]["database"] = {"status": "healthy"}
    except Exception as e:
        health_status["status"] = "unhealthy"
        health_status["checks"]["database"] = {
            "status": "unhealthy",
            "error": str(e)
        }
    
    # Redis check
    try:
        await redis_client.ping()
        health_status["checks"]["redis"] = {"status": "healthy"}
    except Exception as e:
        health_status["status"] = "unhealthy"
        health_status["checks"]["redis"] = {
            "status": "unhealthy",
            "error": str(e)
        }
    
    # Background task status
    active_tasks = sum(1 for task in app_state.get("background_tasks", []) if not task.done())
    health_status["checks"]["background_tasks"] = {
        "status": "healthy" if active_tasks > 0 else "warning",
        "active_tasks": active_tasks
    }
    
    return health_status


@app.get("/metrics")
async def get_metrics() -> Response:
    """Prometheus metrics endpoint."""
    metrics = generate_latest()
    return Response(content=metrics, media_type="text/plain")


# Admin endpoints
@app.post("/admin/jobs/nightly-merge")
async def trigger_nightly_merge_job(
    background_tasks: BackgroundTasks,
    scheduler: CronScheduler = Depends(get_scheduler)
) -> Dict[str, Any]:
    """Manually trigger nightly merge job."""
    
    background_tasks.add_task(_run_job_safely, "nightly_merge", scheduler.run_nightly_merge_job)
    
    return {
        "message": "Nightly merge job triggered",
        "timestamp": datetime.now(timezone.utc).isoformat()
    }


@app.post("/admin/jobs/health-check")
async def trigger_health_check_job(
    background_tasks: BackgroundTasks,
    scheduler: CronScheduler = Depends(get_scheduler)
) -> Dict[str, Any]:
    """Manually trigger health check job."""
    
    background_tasks.add_task(_run_job_safely, "health_check", scheduler.run_health_check_job)
    
    return {
        "message": "Health check job triggered",
        "timestamp": datetime.now(timezone.utc).isoformat()
    }


@app.post("/admin/jobs/cleanup")
async def trigger_cleanup_job(
    background_tasks: BackgroundTasks,
    scheduler: CronScheduler = Depends(get_scheduler)
) -> Dict[str, Any]:
    """Manually trigger cleanup job."""
    
    background_tasks.add_task(_run_job_safely, "cleanup", scheduler.run_cleanup_job)
    
    return {
        "message": "Cleanup job triggered",
        "timestamp": datetime.now(timezone.utc).isoformat()
    }


@app.get("/admin/stats")
async def get_admin_stats(
    db: AsyncSession = Depends(get_db),
    redis_client: redis.Redis = Depends(get_redis)
) -> Dict[str, Any]:
    """Get administrative statistics."""
    
    from sqlalchemy import select, func
    from .models import MergeOperation, EventLog
    
    # Database stats
    namespace_count_result = await db.execute(
        select(func.count(LearnerNamespace.id))
    )
    total_namespaces = namespace_count_result.scalar()
    
    # Status distribution
    status_result = await db.execute(
        select(LearnerNamespace.status, func.count(LearnerNamespace.id))
        .group_by(LearnerNamespace.status)
    )
    status_distribution = {status.value: count for status, count in status_result.all()}
    
    # Merge operation stats
    merge_count_result = await db.execute(
        select(func.count(MergeOperation.id))
    )
    total_merges = merge_count_result.scalar()
    
    # Event log stats
    event_count_result = await db.execute(
        select(func.count(EventLog.id))
    )
    total_events = event_count_result.scalar()
    
    # Redis queue sizes
    merge_queue_size = await redis_client.llen("merge_queue")
    fallback_queue_size = await redis_client.llen("fallback_queue")
    
    # Memory usage
    redis_info = await redis_client.info("memory")
    
    return {
        "database": {
            "total_namespaces": total_namespaces,
            "status_distribution": status_distribution,
            "total_merge_operations": total_merges,
            "total_event_logs": total_events
        },
        "queues": {
            "merge_queue_size": merge_queue_size,
            "fallback_queue_size": fallback_queue_size
        },
        "memory": {
            "redis_used_memory": redis_info.get("used_memory_human", "unknown"),
            "redis_peak_memory": redis_info.get("used_memory_peak_human", "unknown")
        },
        "background_tasks": {
            "active_count": sum(1 for task in app_state.get("background_tasks", []) if not task.done()),
            "total_count": len(app_state.get("background_tasks", []))
        }
    }


# Include API routes
app.include_router(create_router(), prefix="/api/v1")


# Background task processors
async def merge_queue_processor():
    """Process merge operations from queue."""
    logger.info("Starting merge queue processor")
    
    while True:
        try:
            async_session = app_state["async_session"]
            redis_client = app_state["redis"]
            
            async with async_session() as session:
                isolator = NamespaceIsolator(session, redis_client)
                scheduler = CronScheduler(session, isolator, redis_client)
                
                result = await scheduler.process_merge_queue()
                
                if result["stats"]["operations_processed"] == 0:
                    await asyncio.sleep(30)  # No operations, wait longer
                else:
                    await asyncio.sleep(5)   # Process more quickly when busy
                    
        except asyncio.CancelledError:
            break
        except Exception as e:
            logger.error("Merge queue processor error", error=str(e))
            await asyncio.sleep(60)  # Back off on error
    
    logger.info("Merge queue processor stopped")


async def fallback_queue_processor():
    """Process fallback operations from queue."""
    logger.info("Starting fallback queue processor")
    
    while True:
        try:
            async_session = app_state["async_session"]
            redis_client = app_state["redis"]
            
            async with async_session() as session:
                isolator = NamespaceIsolator(session, redis_client)
                scheduler = CronScheduler(session, isolator, redis_client)
                
                result = await scheduler.process_fallback_queue()
                
                if result["stats"]["operations_processed"] == 0:
                    await asyncio.sleep(30)  # No operations, wait longer
                else:
                    await asyncio.sleep(10)  # Process fallbacks more carefully
                    
        except asyncio.CancelledError:
            break
        except Exception as e:
            logger.error("Fallback queue processor error", error=str(e))
            await asyncio.sleep(120)  # Longer back off for fallback errors
    
    logger.info("Fallback queue processor stopped")


async def update_metrics():
    """Update Prometheus metrics periodically."""
    logger.info("Starting metrics updater")
    
    while True:
        try:
            async_session = app_state["async_session"]
            
            async with async_session() as session:
                from sqlalchemy import select, func
                
                # Update namespace count
                namespace_count_result = await session.execute(
                    select(func.count(LearnerNamespace.id))
                )
                namespace_count.set(namespace_count_result.scalar())
                
                # Update status distribution
                status_result = await session.execute(
                    select(LearnerNamespace.status, func.count(LearnerNamespace.id))
                    .group_by(LearnerNamespace.status)
                )
                
                # Reset status gauges
                for status in NamespaceStatus:
                    namespace_status_gauge.labels(status=status.value).set(0)
                
                # Update with current values
                for status, count in status_result.all():
                    namespace_status_gauge.labels(status=status.value).set(count)
            
            await asyncio.sleep(60)  # Update every minute
            
        except asyncio.CancelledError:
            break
        except Exception as e:
            logger.error("Metrics updater error", error=str(e))
            await asyncio.sleep(60)
    
    logger.info("Metrics updater stopped")


async def _run_job_safely(job_name: str, job_func):
    """Run a job function safely with error handling."""
    try:
        logger.info("Starting manual job", job=job_name)
        result = await job_func()
        logger.info("Manual job completed", job=job_name, result=result)
    except Exception as e:
        logger.error("Manual job failed", job=job_name, error=str(e))


if __name__ == "__main__":
    import uvicorn
    
    # Development server
    uvicorn.run(
        "app.main:app",
        host="0.0.0.0",
        port=int(os.getenv("PORT", "8000")),
        reload=os.getenv("ENVIRONMENT") == "development",
        log_config=None,  # Use structlog configuration
    )
