# AIVO Virtual Brains - Assessment Service
# S1-10 Implementation - Baseline Assessment with IRT Support

from fastapi import FastAPI, HTTPException, Depends, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.orm import Session
import logging
import os
from contextlib import asynccontextmanager

from app.database import engine, get_db
from app.models import Base
from app.routes.baseline import router as baseline_router
from app.routes.assessment_status import router as assessment_router  
from app.routes.health import router as health_router
from app.events import publish_event

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)

# Application lifespan management
@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application startup and shutdown events."""
    logger.info("Assessment Service starting up...")
    
    # Create database tables
    Base.metadata.create_all(bind=engine)
    logger.info("Database tables created/verified")
    
    yield
    
    logger.info("Assessment Service shutting down...")

# Create FastAPI application
app = FastAPI(
    title="AIVO Assessment Service",
    description="Baseline assessment service with IRT (Item Response Theory) support",
    version="1.0.0",
    lifespan=lifespan
)

# CORS middleware configuration
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:3000",
        "http://localhost:3001", 
        "https://*.aivo.ai"
    ],
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS"],
    allow_headers=["*"],
)

# Include routers
app.include_router(health_router, prefix="/api/v1", tags=["Health"])
app.include_router(baseline_router, prefix="/api/v1/baseline", tags=["Baseline Assessment"])
app.include_router(assessment_router, prefix="/api/v1/assessment", tags=["Assessment Status"])

@app.get("/")
async def root():
    """Health check endpoint."""
    return {
        "service": "aivo-assessment-svc",
        "version": "1.0.0",
        "status": "healthy",
        "description": "Baseline assessment service with IRT support"
    }

@app.get("/health")
async def health_check():
    """Detailed health check endpoint."""
    return {
        "status": "healthy",
        "service": "assessment-svc",
        "version": "1.0.0",
        "timestamp": "2025-08-13T00:00:00Z",
        "features": {
            "baseline_assessment": True,
            "irt_ready": True,
            "event_emission": True,
            "level_mapping": True
        }
    }

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "app.main:app",
        host="0.0.0.0",
        port=8080,
        reload=True,
        log_level="info"
    )
