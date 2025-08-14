# AIVO SEL Service - Main Application
# S2-12 Implementation - FastAPI application setup

import logging
import asyncio
from contextlib import asynccontextmanager
from typing import Dict, Any

from fastapi import FastAPI, Request, HTTPException, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.trustedhost import TrustedHostMiddleware
from fastapi.responses import JSONResponse
from fastapi.exceptions import RequestValidationError
import uvicorn

from .database import init_database, health_check_db, DatabaseManager
from .routes import router
from .engine import SELEngine

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Application lifespan manager for startup and shutdown tasks.
    """
    # Startup
    logger.info("Starting AIVO SEL Service...")
    
    try:
        # Initialize database
        await init_database()
        logger.info("Database initialization completed")
        
        # Initialize SEL engine
        from .routes import sel_engine
        await sel_engine.initialize()
        logger.info("SEL engine initialization completed")
        
        # Create test data in development
        import os
        if os.getenv("ENVIRONMENT", "development") == "development":
            await DatabaseManager.create_test_data()
            logger.info("Test data created")
        
        logger.info("AIVO SEL Service startup completed successfully")
        
    except Exception as e:
        logger.error(f"Startup failed: {str(e)}")
        raise
    
    yield
    
    # Shutdown
    logger.info("Shutting down AIVO SEL Service...")
    
    try:
        # Cleanup SEL engine
        from .routes import sel_engine
        await sel_engine.cleanup()
        logger.info("SEL engine cleanup completed")
        
        # Perform data cleanup if needed
        # await DatabaseManager.cleanup_expired_data()
        
        logger.info("AIVO SEL Service shutdown completed successfully")
        
    except Exception as e:
        logger.error(f"Shutdown error: {str(e)}")


# Create FastAPI application
app = FastAPI(
    title="AIVO SEL Service",
    description="Social-Emotional Learning service with check-ins, strategies, and consent-aware alerts",
    version="2.12.0",
    docs_url="/docs",
    redoc_url="/redoc",
    lifespan=lifespan
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Configure appropriately for production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Add trusted host middleware for production security
app.add_middleware(
    TrustedHostMiddleware,
    allowed_hosts=["*"]  # Configure appropriately for production
)

# Include API routes
app.include_router(router)


# Global exception handlers
@app.exception_handler(HTTPException)
async def http_exception_handler(request: Request, exc: HTTPException):
    """Handle HTTP exceptions with consistent format."""
    return JSONResponse(
        status_code=exc.status_code,
        content={
            "error": {
                "code": exc.status_code,
                "message": exc.detail,
                "type": "HTTPException"
            },
            "path": str(request.url.path),
            "method": request.method,
            "timestamp": "2025-01-12T00:00:00Z"  # Would use actual timestamp
        }
    )


@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request: Request, exc: RequestValidationError):
    """Handle request validation errors."""
    return JSONResponse(
        status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
        content={
            "error": {
                "code": 422,
                "message": "Request validation failed",
                "type": "ValidationError",
                "details": exc.errors()
            },
            "path": str(request.url.path),
            "method": request.method,
            "timestamp": "2025-01-12T00:00:00Z"  # Would use actual timestamp
        }
    )


@app.exception_handler(Exception)
async def general_exception_handler(request: Request, exc: Exception):
    """Handle general exceptions."""
    logger.error(f"Unhandled exception: {str(exc)}")
    
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content={
            "error": {
                "code": 500,
                "message": "Internal server error",
                "type": "InternalServerError"
            },
            "path": str(request.url.path),
            "method": request.method,
            "timestamp": "2025-01-12T00:00:00Z"  # Would use actual timestamp
        }
    )


# Middleware for request logging and monitoring
@app.middleware("http")
async def logging_middleware(request: Request, call_next):
    """Log requests for monitoring and debugging."""
    start_time = asyncio.get_event_loop().time()
    
    # Log request
    logger.info(f"Request: {request.method} {request.url.path}")
    
    response = await call_next(request)
    
    # Log response
    process_time = asyncio.get_event_loop().time() - start_time
    logger.info(f"Response: {response.status_code} - {process_time:.4f}s")
    
    return response


# Root endpoint
@app.get("/", status_code=200)
async def root():
    """Root endpoint with service information."""
    return {
        "service": "AIVO SEL Service",
        "version": "2.12.0",
        "description": "Social-Emotional Learning service with check-ins, strategies, and consent-aware alerts",
        "status": "active",
        "endpoints": {
            "health": "/api/v1/health",
            "docs": "/docs",
            "redoc": "/redoc"
        }
    }


# Health check endpoints
@app.get("/health", status_code=200)
async def health_check():
    """Basic health check."""
    return {
        "status": "healthy",
        "service": "sel-svc",
        "timestamp": "2025-01-12T00:00:00Z"  # Would use actual timestamp
    }


@app.get("/health/detailed", status_code=200)
async def detailed_health_check():
    """Detailed health check including dependencies."""
    try:
        # Check database connectivity
        db_healthy = await health_check_db()
        
        # Check SEL engine status
        from .routes import sel_engine
        engine_healthy = sel_engine.http_client is not None
        
        overall_status = "healthy" if db_healthy and engine_healthy else "unhealthy"
        status_code = 200 if overall_status == "healthy" else 503
        
        return JSONResponse(
            status_code=status_code,
            content={
                "status": overall_status,
                "service": "sel-svc",
                "timestamp": "2025-01-12T00:00:00Z",  # Would use actual timestamp
                "components": {
                    "database": "healthy" if db_healthy else "unhealthy",
                    "engine": "healthy" if engine_healthy else "unhealthy",
                    "api": "healthy"
                }
            }
        )
        
    except Exception as e:
        logger.error(f"Health check failed: {str(e)}")
        return JSONResponse(
            status_code=503,
            content={
                "status": "unhealthy",
                "service": "sel-svc",
                "timestamp": "2025-01-12T00:00:00Z",
                "error": str(e)
            }
        )


# Development utilities
@app.get("/debug/info")
async def debug_info():
    """Debug information (development only)."""
    import os
    
    if os.getenv("ENVIRONMENT", "development") not in ["development", "testing"]:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Debug endpoint not available in production"
        )
    
    return {
        "environment": os.getenv("ENVIRONMENT", "development"),
        "database_url": os.getenv("DATABASE_URL", "not_set")[:50] + "...",
        "python_version": "3.11+",
        "fastapi_version": "0.104+",
        "models_loaded": True,
        "routes_loaded": True
    }


# Event publishing utilities (placeholder for orchestrator integration)
async def publish_event(event_type: str, event_data: Dict[str, Any]):
    """
    Publish event to orchestrator or message queue.
    This is a placeholder implementation.
    """
    try:
        # In production, this would publish to:
        # - Apache Kafka
        # - RabbitMQ
        # - Azure Service Bus
        # - AWS SQS/SNS
        # - Or directly to orchestrator
        
        logger.info(f"Publishing event: {event_type}")
        logger.debug(f"Event data: {event_data}")
        
        # Mock event publishing
        if event_type == "SEL_ALERT":
            logger.info(f"SEL_ALERT event published for student {event_data.get('student_id')}")
        
        return True
        
    except Exception as e:
        logger.error(f"Event publishing failed: {str(e)}")
        return False


if __name__ == "__main__":
    # Development server
    uvicorn.run(
        "app.main:app",
        host="0.0.0.0",
        port=8000,
        reload=True,
        log_level="info"
    )
