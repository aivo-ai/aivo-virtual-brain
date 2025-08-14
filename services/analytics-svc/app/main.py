"""
Analytics Service - Main Application (S2-15)
Privacy-aware analytics and ETL service for educational data
"""
import logging
import os
from contextlib import asynccontextmanager
from datetime import datetime

import uvicorn
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.gzip import GZipMiddleware
from fastapi.responses import JSONResponse
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from .routes import router as analytics_router
from .models import Base

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Database configuration
DATABASE_URL = os.getenv(
    "DATABASE_URL", 
    "postgresql://analytics_user:analytics_pass@localhost:5432/analytics_db"
)

# Create database engine and session factory
engine = create_engine(DATABASE_URL, echo=False)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# Global database session
db_session = None


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan manager - handles startup and shutdown."""
    global db_session
    
    # Startup
    logger.info("Starting Analytics Service S2-15")
    
    try:
        # Create database tables
        Base.metadata.create_all(bind=engine)
        logger.info("Database tables created/verified")
        
        # Initialize database session
        db_session = SessionLocal()
        
        # Update dependency injection in routes
        import app.routes as routes_module
        routes_module.get_db = lambda: db_session
        
        logger.info("Analytics Service started successfully")
        
    except Exception as e:
        logger.error(f"Failed to initialize Analytics Service: {e}")
        raise
    
    yield
    
    # Shutdown
    logger.info("Shutting down Analytics Service")
    
    if db_session:
        try:
            db_session.close()
            logger.info("Database session closed")
        except Exception as e:
            logger.error(f"Error closing database session: {e}")


# Create FastAPI app
app = FastAPI(
    title="Analytics Service (S2-15)",
    description="""
    Privacy-aware analytics and ETL service for educational data.
    
    ## Features
    - **ETL Processing**: Transform raw events into anonymized aggregates
    - **Privacy Protection**: Differential privacy and k-anonymity support
    - **Tenant Analytics**: Organization-wide metrics and dashboards
    - **Learner Analytics**: Individual progress with privacy guarantees
    - **IEP Tracking**: Special needs progress monitoring
    
    ## Privacy Levels
    - **Anonymized**: PII removed, aggregated data
    - **DP Low/Medium/High**: Differential privacy with varying noise levels
    
    ## Key Metrics
    - Session duration and engagement
    - Subject mastery progression
    - Weekly active learner trends
    - IEP goal progress deltas
    
    ## Compliance
    - FERPA compliant data handling
    - COPPA privacy protections
    - GDPR data minimization
    - SOC 2 security controls
    """,
    version="1.0.0",
    lifespan=lifespan,
    docs_url="/docs",
    redoc_url="/redoc"
)

# Add middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Configure appropriately for production
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE"],
    allow_headers=["*"],
)

app.add_middleware(GZipMiddleware, minimum_size=1000)


@app.middleware("http")
async def add_process_time_header(request: Request, call_next):
    """Add processing time header to responses."""
    start_time = datetime.utcnow()
    response = await call_next(request)
    process_time = (datetime.utcnow() - start_time).total_seconds()
    response.headers["X-Process-Time"] = str(process_time)
    return response


@app.middleware("http") 
async def log_requests(request: Request, call_next):
    """Log incoming requests with privacy considerations."""
    start_time = datetime.utcnow()
    
    # Sanitize URL for logging (remove sensitive parameters)
    sanitized_path = request.url.path
    if "learner" in sanitized_path:
        sanitized_path = sanitized_path.split("/")
        for i, part in enumerate(sanitized_path):
            if len(part) == 16 and all(c in '0123456789abcdef' for c in part.lower()):
                sanitized_path[i] = "[LEARNER_HASH]"
        sanitized_path = "/".join(sanitized_path)
    
    response = await call_next(request)
    process_time = (datetime.utcnow() - start_time).total_seconds()
    
    logger.info(
        f"{request.method} {sanitized_path} - "
        f"Status: {response.status_code} - "
        f"Time: {process_time:.3f}s"
    )
    return response


# Exception handlers
@app.exception_handler(404)
async def not_found_handler(request: Request, exc):
    """Handle 404 errors."""
    return JSONResponse(
        status_code=404,
        content={
            "error_code": "NOT_FOUND",
            "error_message": "Endpoint not found",
            "timestamp": datetime.utcnow().isoformat(),
            "request_path": request.url.path
        }
    )


@app.exception_handler(500)
async def internal_server_error_handler(request: Request, exc: Exception):
    """Handle internal server errors."""
    logger.error(f"Internal server error: {exc}")
    
    return JSONResponse(
        status_code=500,
        content={
            "error_code": "INTERNAL_ERROR",
            "error_message": "Internal server error occurred",
            "timestamp": datetime.utcnow().isoformat(),
            "request_id": request.headers.get("x-request-id", "unknown")
        }
    )


# Include routers
app.include_router(
    analytics_router,
    prefix="/api/v1",
    tags=["analytics"]
)


# Root endpoint
@app.get("/")
async def root():
    """Root endpoint with service information."""
    return {
        "service": "Analytics Service",
        "version": "1.0.0",
        "stage": "S2-15",
        "description": "Privacy-aware analytics and ETL for educational data",
        "features": [
            "ETL event processing",
            "Differential privacy protection",
            "Tenant and learner analytics",
            "IEP progress tracking",
            "FERPA/COPPA compliance"
        ],
        "endpoints": {
            "tenant_analytics": "/api/v1/metrics/tenant/{tenant_id}",
            "learner_analytics": "/api/v1/metrics/learner/{learner_id_hash}",
            "etl_jobs": "/api/v1/etl/jobs",
            "trigger_etl": "/api/v1/etl/trigger/{tenant_id}",
            "privacy_levels": "/api/v1/privacy/levels",
            "health": "/api/v1/health",
            "docs": "/docs"
        },
        "privacy_notice": "All data is processed with appropriate privacy protections including anonymization, k-anonymity, and differential privacy as required by FERPA, COPPA, and GDPR regulations."
    }


# Health check endpoints
@app.get("/health")
async def simple_health():
    """Simple health check endpoint."""
    return {
        "status": "healthy",
        "service": "analytics-svc",
        "timestamp": datetime.utcnow().isoformat()
    }


@app.get("/privacy/policy")
async def privacy_policy():
    """Privacy policy and data handling information."""
    return {
        "privacy_policy": {
            "data_minimization": "Only necessary data is collected and processed",
            "purpose_limitation": "Data is used only for educational analytics",
            "retention_limits": "Aggregated data retained for 7 years, raw data for 1 year",
            "anonymization": "PII is removed or hashed before storage",
            "differential_privacy": "Statistical noise added to prevent individual identification",
            "k_anonymity": "Small groups are suppressed to prevent re-identification",
            "access_controls": "Role-based access with tenant and learner scoping",
            "compliance": ["FERPA", "COPPA", "GDPR", "SOC 2"]
        },
        "data_types": {
            "collected": [
                "Learning session duration",
                "Assessment scores and mastery",
                "IEP goal progress (anonymized)",
                "Engagement metrics"
            ],
            "not_collected": [
                "Names or direct identifiers",
                "Contact information", 
                "Detailed personal information",
                "Biometric data"
            ]
        },
        "privacy_controls": {
            "learner_data": "Hashed identifiers, k-anonymity enforcement",
            "tenant_data": "Aggregated metrics, differential privacy option",
            "iep_data": "Category-based anonymization, support level only",
            "demographics": "Broad categories, small counts suppressed"
        }
    }


if __name__ == "__main__":
    # Development server
    uvicorn.run(
        "app.main:app",
        host="0.0.0.0",
        port=8001,  # Different port from event-collector
        reload=True,
        log_level="info"
    )
