# AIVO SLP Service - Main Application
# S2-11 Implementation - FastAPI application with lifecycle management

from fastapi import FastAPI, Request, Response
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from fastapi.exceptions import RequestValidationError
from starlette.exceptions import HTTPException as StarletteHTTPException
from contextlib import asynccontextmanager
import logging
import uvicorn
from datetime import datetime, timezone
import uuid

from .routes import router
from .database import engine, Base
from .engine import SLPEngine


# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    handlers=[logging.StreamHandler()]
)
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan events."""
    logger.info("Starting SLP Service...")
    
    try:
        # Create database tables
        Base.metadata.create_all(bind=engine)
        logger.info("Database tables created successfully")
        
        # Initialize SLP engine
        slp_engine = SLPEngine()
        await slp_engine.initialize()
        logger.info("SLP engine initialized successfully")
        
        # Store engine in app state
        app.state.slp_engine = slp_engine
        
    except Exception as e:
        logger.error(f"Startup error: {str(e)}")
        raise
    
    yield
    
    # Shutdown
    logger.info("Shutting down SLP Service...")
    
    try:
        # Clean up resources
        if hasattr(app.state, 'slp_engine'):
            await app.state.slp_engine.cleanup()
        
    except Exception as e:
        logger.error(f"Shutdown error: {str(e)}")


# Create FastAPI application
app = FastAPI(
    title="AIVO SLP Service",
    description="Speech & Language Pathology service for screening, therapy planning, and exercise generation",
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc",
    openapi_url="/openapi.json",
    lifespan=lifespan
)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Configure based on your needs
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# Request ID middleware
@app.middleware("http")
async def add_request_id(request: Request, call_next):
    """Add request ID to all requests."""
    request_id = str(uuid.uuid4())
    request.state.request_id = request_id
    
    response = await call_next(request)
    response.headers["X-Request-ID"] = request_id
    
    return response


# Request logging middleware
@app.middleware("http")
async def log_requests(request: Request, call_next):
    """Log all requests."""
    start_time = datetime.now(timezone.utc)
    
    # Log request
    logger.info(f"Request {request.state.request_id}: {request.method} {request.url}")
    
    response = await call_next(request)
    
    # Calculate duration
    duration = (datetime.now(timezone.utc) - start_time).total_seconds()
    
    # Log response
    logger.info(
        f"Response {request.state.request_id}: {response.status_code} "
        f"({duration:.3f}s)"
    )
    
    return response


# Error handlers
@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request: Request, exc: RequestValidationError):
    """Handle validation errors."""
    logger.warning(f"Validation error for {request.state.request_id}: {exc.errors()}")
    
    return JSONResponse(
        status_code=422,
        content={
            "error": "Validation Error",
            "message": "Request validation failed",
            "details": exc.errors(),
            "request_id": request.state.request_id,
            "timestamp": datetime.now(timezone.utc).isoformat()
        }
    )


@app.exception_handler(StarletteHTTPException)
async def http_exception_handler(request: Request, exc: StarletteHTTPException):
    """Handle HTTP exceptions."""
    logger.warning(f"HTTP error for {request.state.request_id}: {exc.status_code} - {exc.detail}")
    
    return JSONResponse(
        status_code=exc.status_code,
        content={
            "error": f"HTTP {exc.status_code}",
            "message": exc.detail,
            "request_id": request.state.request_id,
            "timestamp": datetime.now(timezone.utc).isoformat()
        }
    )


@app.exception_handler(Exception)
async def general_exception_handler(request: Request, exc: Exception):
    """Handle all other exceptions."""
    logger.error(f"Unexpected error for {request.state.request_id}: {str(exc)}", exc_info=True)
    
    return JSONResponse(
        status_code=500,
        content={
            "error": "Internal Server Error",
            "message": "An unexpected error occurred",
            "request_id": request.state.request_id,
            "timestamp": datetime.now(timezone.utc).isoformat()
        }
    )


# Include routers
app.include_router(router)

# Root endpoint
@app.get("/")
async def root():
    """Root endpoint with service information."""
    return {
        "service": "slp-svc",
        "name": "AIVO Speech & Language Pathology Service",
        "description": "Provides screening, therapy planning, and exercise generation for SLP workflows",
        "version": "1.0.0",
        "status": "healthy",
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "docs": "/docs",
        "redoc": "/redoc",
        "openapi": "/openapi.json"
    }


# Health check with detailed status
@app.get("/health")
async def health_check():
    """Detailed health check endpoint."""
    try:
        # Check database connection
        from .database import get_db
        db = next(get_db())
        db.execute("SELECT 1")
        db_status = "healthy"
    except Exception as e:
        logger.error(f"Database health check failed: {str(e)}")
        db_status = "unhealthy"
    
    # Check SLP engine
    try:
        slp_engine_status = "healthy" if hasattr(app.state, 'slp_engine') else "not_initialized"
    except Exception as e:
        logger.error(f"SLP engine health check failed: {str(e)}")
        slp_engine_status = "unhealthy"
    
    overall_status = "healthy" if all([
        db_status == "healthy",
        slp_engine_status == "healthy"
    ]) else "degraded"
    
    return {
        "status": overall_status,
        "service": "slp-svc",
        "version": "1.0.0",
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "components": {
            "database": db_status,
            "slp_engine": slp_engine_status
        },
        "uptime_seconds": (datetime.now(timezone.utc) - start_time).total_seconds()
    }


# Metrics endpoint
@app.get("/metrics")
async def metrics():
    """Basic metrics endpoint."""
    try:
        from .database import get_db
        from .models import ScreeningAssessment, TherapyPlan, ExerciseSession
        
        db = next(get_db())
        
        # Count statistics
        total_screenings = db.query(ScreeningAssessment).count()
        total_plans = db.query(TherapyPlan).count()
        total_sessions = db.query(ExerciseSession).count()
        
        # Active counts
        active_plans = db.query(TherapyPlan).filter(
            TherapyPlan.status == "active"
        ).count()
        
        return {
            "service": "slp-svc",
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "statistics": {
                "screenings": {
                    "total": total_screenings
                },
                "therapy_plans": {
                    "total": total_plans,
                    "active": active_plans
                },
                "sessions": {
                    "total": total_sessions
                }
            }
        }
    
    except Exception as e:
        logger.error(f"Error retrieving metrics: {str(e)}")
        return JSONResponse(
            status_code=500,
            content={
                "error": "Metrics Error",
                "message": "Failed to retrieve service metrics"
            }
        )


# Environment info endpoint (for debugging)
@app.get("/info")
async def service_info():
    """Service information endpoint."""
    import sys
    import os
    
    return {
        "service": "slp-svc",
        "version": "1.0.0",
        "python_version": sys.version,
        "environment": os.getenv("ENVIRONMENT", "development"),
        "features": {
            "screening": True,
            "therapy_planning": True,
            "exercise_generation": True,
            "voice_integration": True,
            "progress_tracking": True,
            "event_emission": True
        },
        "endpoints": {
            "screening": {
                "create": "POST /api/v1/slp/screen",
                "get": "GET /api/v1/slp/screen/{id}",
                "list": "GET /api/v1/slp/screen"
            },
            "therapy_planning": {
                "create": "POST /api/v1/slp/plan",
                "get": "GET /api/v1/slp/plan/{id}",
                "list": "GET /api/v1/slp/plan"
            },
            "exercises": {
                "generate": "POST /api/v1/slp/exercise/next",
                "get": "GET /api/v1/slp/exercise/{id}"
            },
            "sessions": {
                "create": "POST /api/v1/slp/session",
                "submit": "POST /api/v1/slp/session/submit",
                "get": "GET /api/v1/slp/session/{id}"
            },
            "progress": {
                "events": "GET /api/v1/slp/progress/{patient_id}"
            }
        }
    }


# Store startup time for uptime calculation
start_time = datetime.now(timezone.utc)


if __name__ == "__main__":
    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=8000,
        reload=True,
        log_level="info"
    )
