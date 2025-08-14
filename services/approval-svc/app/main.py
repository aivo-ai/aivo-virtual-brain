# AIVO Approval Service - Main Application
# S2-10 Implementation - FastAPI app with approval workflow

from fastapi import FastAPI, HTTPException, Depends, status, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from sqlalchemy.orm import Session
from datetime import datetime, timezone
import logging
import os
import asyncio
import json
from contextlib import asynccontextmanager

from .database import engine, create_tables, check_database_health, get_db
from .models import Base, ApprovalRequest, ApprovalStatus
from .routes import router as approval_router
from .schemas import ErrorResponse


class CustomJSONEncoder(json.JSONEncoder):
    """Custom JSON encoder to handle datetime objects."""
    def default(self, obj):
        if isinstance(obj, datetime):
            return obj.isoformat()
        return super().default(obj)


# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan events."""
    # Startup
    logger.info("Starting AIVO Approval Service")
    
    # Create tables on startup (not during import)
    # Skip in test environment
    import os
    if not os.getenv("TESTING", False):
        try:
            create_tables()
            logger.info("Database tables created successfully")
        except Exception as e:
            logger.error(f"Failed to create database tables: {e}")
    else:
        logger.info("Skipping database table creation in test mode")
    
    # Start background tasks
    asyncio.create_task(expiry_cleanup_task())
    
    yield
    
    # Shutdown
    logger.info("Shutting down AIVO Approval Service")


# Create FastAPI application
app = FastAPI(
    title="AIVO Approval Service",
    description="Approval workflow service for level changes, IEP changes, and consent-sensitive actions",
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc",
    lifespan=lifespan
)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=os.getenv("CORS_ORIGINS", "*").split(","),
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routers
app.include_router(approval_router)


# ============================================================================
# HEALTH CHECK ENDPOINTS
# ============================================================================

@app.get("/health")
async def health_check():
    """Basic health check endpoint."""
    return {
        "status": "healthy",
        "service": "approval-svc",
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "version": "1.0.0"
    }


@app.get("/health/detailed")
async def detailed_health_check():
    """Detailed health check including database connectivity."""
    db_healthy = check_database_health()
    
    overall_status = "healthy" if db_healthy else "unhealthy"
    status_code = status.HTTP_200_OK if db_healthy else status.HTTP_503_SERVICE_UNAVAILABLE
    
    response = {
        "status": overall_status,
        "service": "approval-svc",
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "version": "1.0.0",
        "checks": {
            "database": "healthy" if db_healthy else "unhealthy"
        }
    }
    
    return JSONResponse(
        content=response,
        status_code=status_code
    )


# ============================================================================
# ERROR HANDLERS
# ============================================================================

@app.exception_handler(HTTPException)
async def http_exception_handler(request, exc):
    """Handle HTTP exceptions with consistent error format."""
    error_data = ErrorResponse(
        error=exc.__class__.__name__,
        message=str(exc.detail),
        timestamp=datetime.now(timezone.utc)
    ).model_dump()
    
    return JSONResponse(
        status_code=exc.status_code,
        content=json.loads(json.dumps(error_data, cls=CustomJSONEncoder))
    )


@app.exception_handler(Exception)
async def general_exception_handler(request, exc):
    """Handle general exceptions."""
    logger.error(f"Unhandled exception: {str(exc)}", exc_info=True)
    
    error_data = ErrorResponse(
        error="InternalServerError",
        message="An unexpected error occurred",
        timestamp=datetime.now(timezone.utc)
    ).model_dump()
    
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content=json.loads(json.dumps(error_data, cls=CustomJSONEncoder))
    )


# ============================================================================
# BACKGROUND TASKS
# ============================================================================

async def expiry_cleanup_task():
    """
    Background task to cleanup expired approval requests.
    Runs every 5 minutes to check for and handle expired requests.
    """
    while True:
        try:
            await asyncio.sleep(300)  # Run every 5 minutes
            
            logger.info("Running approval expiry cleanup task")
            
            # Get database session
            db = next(get_db())
            
            try:
                # Find expired pending requests
                now = datetime.now(timezone.utc)
                expired_requests = db.query(ApprovalRequest).filter(
                    ApprovalRequest.status == ApprovalStatus.PENDING,
                    ApprovalRequest.expires_at < now
                ).all()
                
                for request in expired_requests:
                    logger.info(f"Expiring request {request.id}")
                    
                    # Update status
                    request.status = ApprovalStatus.EXPIRED
                    request.decided_at = now
                    request.decision_reason = "Request expired due to timeout"
                    request.updated_at = now
                    
                    # TODO: Send webhook notification
                    # TODO: Create audit log entry
                
                if expired_requests:
                    db.commit()
                    logger.info(f"Expired {len(expired_requests)} approval requests")
                
            finally:
                db.close()
                
        except Exception as e:
            logger.error(f"Error in expiry cleanup task: {str(e)}")
            await asyncio.sleep(60)  # Wait 1 minute before retry


# ============================================================================
# ROOT ENDPOINT
# ============================================================================

@app.get("/")
async def root():
    """Root endpoint with service information."""
    return {
        "service": "AIVO Approval Service",
        "version": "1.0.0",
        "description": "Approval workflow service for level changes, IEP changes, and consent-sensitive actions",
        "docs_url": "/docs",
        "health_url": "/health",
        "api_base": "/api/v1/approvals"
    }


if __name__ == "__main__":
    import uvicorn
    
    port = int(os.getenv("PORT", 8000))
    host = os.getenv("HOST", "0.0.0.0")
    
    uvicorn.run(
        "app.main:app",
        host=host,
        port=port,
        reload=os.getenv("ENVIRONMENT") == "development",
        log_level="info"
    )
