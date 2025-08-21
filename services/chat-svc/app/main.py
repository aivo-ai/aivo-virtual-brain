"""
Chat Service - Threaded Message History per Learner
Provides privacy-compliant chat storage with RBAC protection
"""

from fastapi import FastAPI
from contextlib import asynccontextmanager
import logging
import os
import uuid

from .config import settings
from .database import engine, create_tables
from .middleware import setup_cors, setup_logging, setup_auth_middleware, setup_rate_limiting
from .routes import router
from .events import EventPublisher

# Configure logging
logging.basicConfig(
    level=getattr(logging, settings.log_level.upper()),
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Service instance ID
SERVICE_INSTANCE_ID = f"chat-svc-{os.getenv('HOSTNAME', 'unknown')}-{os.getpid()}-{str(uuid.uuid4())[:8]}"


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan manager for startup and shutdown"""
    # Startup
    logger.info(f"Starting Chat Service instance: {SERVICE_INSTANCE_ID}")
    
    # Create database tables
    if settings.create_tables_on_startup:
        logger.info("Creating database tables...")
        await create_tables()
    
    logger.info("Database initialized")
    logger.info("Chat Service started successfully")
    
    yield
    
    # Shutdown
    logger.info("Shutting down Chat Service...")
    # Cleanup Kafka producer if needed
    try:
        event_publisher = EventPublisher()
        await event_publisher.close()
    except Exception as e:
        logger.warning(f"Error closing event publisher: {e}")
    
    # Dispose database engine
    await engine.dispose()
    logger.info("Chat Service shutdown complete")


# Create FastAPI app
app = FastAPI(
    title="AIVO Chat Service",
    description="Threaded message history per learner with privacy compliance",
    version="1.0.0",
    docs_url="/docs" if settings.environment != "production" else None,
    redoc_url="/redoc" if settings.environment != "production" else None,
    lifespan=lifespan,
)

# Setup middleware
setup_cors(app)
setup_logging(app)
setup_auth_middleware(app)
if settings.enable_rate_limiting:
    setup_rate_limiting(app)

# Include routers
app.include_router(router)


@app.get("/health")
async def health_check():
    """Health check endpoint with detailed status"""
    try:
        # Test database connection
        from .database import get_db_session
        async for db in get_db_session():
            await db.execute("SELECT 1")
            break
        
        db_status = "healthy"
    except Exception as e:
        logger.error(f"Database health check failed: {e}")
        db_status = "unhealthy"
    
    return {
        "status": "healthy" if db_status == "healthy" else "degraded",
        "service": "chat-svc",
        "instance": SERVICE_INSTANCE_ID,
        "version": "1.0.0",
        "database": db_status,
        "tenant_isolated": True,
        "privacy_compliant": True,
        "environment": settings.environment
    }


@app.get("/")
async def root():
    """Root endpoint"""
    return {
        "service": "AIVO Chat Service",
        "version": "1.0.0",
        "description": "Threaded message history per learner with privacy compliance",
        "docs": "/docs" if settings.environment != "production" else None,
        "health": "/health",
        "features": {
            "privacy_compliance": settings.privacy_enabled,
            "rate_limiting": settings.enable_rate_limiting,
            "message_retention": f"{settings.message_retention_days} days",
            "max_thread_messages": settings.max_messages_per_thread
        }
    }


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "app.main:app",
        host="0.0.0.0",
        port=settings.port,
        reload=settings.environment == "development",
        log_level=settings.log_level.lower()
    )
