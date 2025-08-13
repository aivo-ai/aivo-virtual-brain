"""
AIVO Search Service - Main Application
S1-13 Implementation

FastAPI application providing OpenSearch-powered search and suggestions
with role-based access control and multi-tenant support.
"""

import logging
from contextlib import asynccontextmanager
from typing import Dict, Any

from fastapi import FastAPI, HTTPException, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
import uvicorn

from .client import get_search_client, SearchConfig
from .routes import router as search_router

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan manager"""
    
    # Startup
    logger.info("Starting AIVO Search Service...")
    
    try:
        # Initialize OpenSearch client and ensure indices
        search_client = get_search_client()
        await search_client.ensure_indices()
        logger.info("OpenSearch indices initialized")
        
    except Exception as e:
        logger.error(f"Failed to initialize search service: {e}")
        raise
        
    yield
    
    # Shutdown
    logger.info("Shutting down AIVO Search Service...")


# Create FastAPI application
app = FastAPI(
    title="AIVO Search Service",
    description="""
    OpenSearch-powered search and suggestion service with role-based access control.
    
    ## Features
    
    * **Full-text Search**: Multi-field search across IEPs, assessments, students, and curriculum
    * **Auto-suggestions**: Real-time search suggestions with RBAC filtering
    * **Role-based Access**: Granular permission system for multi-tenant security
    * **Document Types**: Support for IEP, assessment, student, curriculum, and resource documents
    * **Multi-tenant**: Tenant and school-level data isolation
    * **High Performance**: OpenSearch backend with optimized queries
    
    ## Authentication
    
    All endpoints require JWT authentication via the `Authorization: Bearer <token>` header.
    
    ## Role-based Access Control
    
    * **System Admin**: Access to all data across all tenants
    * **Tenant Admin**: Access to all data within their tenant
    * **School Admin**: Access to data within their assigned schools
    * **Teacher**: Access to student data within their schools
    * **Parent**: Access to their children's IEPs and assessments
    * **Student**: Access to their own IEP data
    """,
    version="1.0.0",
    lifespan=lifespan,
    docs_url="/docs",
    redoc_url="/redoc"
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Configure appropriately for production
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE"],
    allow_headers=["*"],
)

# Include search routes
app.include_router(search_router, prefix="/api/v1", tags=["search"])


@app.get("/health", summary="Health Check")
async def health_check() -> Dict[str, Any]:
    """
    Health check endpoint for monitoring and load balancers.
    
    Returns service status and OpenSearch cluster information.
    """
    try:
        search_client = get_search_client()
        search_health = await search_client.health_check()
        
        return {
            "status": "healthy",
            "service": "aivo-search-svc",
            "version": "1.0.0",
            "timestamp": "2025-01-15T14:30:00Z",
            "opensearch": search_health
        }
    except Exception as e:
        logger.error(f"Health check failed: {e}")
        return JSONResponse(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            content={
                "status": "unhealthy",
                "service": "aivo-search-svc",
                "error": str(e)
            }
        )


@app.get("/", summary="Service Information")
async def root() -> Dict[str, str]:
    """
    Root endpoint providing basic service information.
    """
    return {
        "service": "AIVO Search Service",
        "description": "OpenSearch-powered search with RBAC",
        "version": "1.0.0",
        "docs": "/docs",
        "health": "/health"
    }


# Exception handlers
@app.exception_handler(HTTPException)
async def http_exception_handler(request, exc: HTTPException):
    """Handle HTTP exceptions with consistent error format"""
    return JSONResponse(
        status_code=exc.status_code,
        content={
            "error": exc.detail,
            "status_code": exc.status_code,
            "timestamp": "2025-01-15T14:30:00Z"
        }
    )


@app.exception_handler(Exception)
async def general_exception_handler(request, exc: Exception):
    """Handle unexpected exceptions"""
    logger.error(f"Unexpected error: {exc}")
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content={
            "error": "Internal server error",
            "status_code": 500,
            "timestamp": "2025-01-15T14:30:00Z"
        }
    )


if __name__ == "__main__":
    # Development server
    uvicorn.run(
        "app.main:app",
        host="0.0.0.0",
        port=8004,
        reload=True,
        log_level="info"
    )
