"""
SIS Bridge Service - Main Application

FastAPI application for synchronizing SIS data with SCIM 2.0 provider.
Supports Clever and ClassLink integrations with automated sync jobs.
"""

import uvicorn
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from contextlib import asynccontextmanager

from app.database import init_db
from app.routes import sync_router, webhook_router, provider_router
from app.scheduler import SyncScheduler
from app.config import get_settings

settings = get_settings()


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan manager."""
    # Startup
    init_db()
    
    # Start sync scheduler
    scheduler = SyncScheduler()
    await scheduler.start()
    app.state.scheduler = scheduler
    
    yield
    
    # Shutdown
    if hasattr(app.state, 'scheduler'):
        await app.state.scheduler.stop()


# Create FastAPI application
app = FastAPI(
    title="SIS Bridge Service",
    description="Student Information System integration service with SCIM 2.0 sync",
    version="1.0.0",
    docs_url="/docs" if settings.environment != "production" else None,
    redoc_url="/redoc" if settings.environment != "production" else None,
    lifespan=lifespan
)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.allowed_origins,
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "PATCH", "DELETE", "OPTIONS"],
    allow_headers=["*"],
)


# Health check endpoint
@app.get("/health")
async def health_check():
    """Health check endpoint."""
    return {
        "status": "healthy", 
        "service": "sis-bridge-svc",
        "scheduler_running": hasattr(app.state, 'scheduler') and app.state.scheduler.is_running()
    }


# Error handlers
@app.exception_handler(404)
async def not_found_handler(request: Request, exc):
    """Handle 404 errors."""
    return JSONResponse(
        status_code=404,
        content={
            "error": "not_found",
            "message": "Resource not found"
        }
    )


@app.exception_handler(500)
async def internal_error_handler(request: Request, exc):
    """Handle 500 errors."""
    return JSONResponse(
        status_code=500,
        content={
            "error": "internal_error",
            "message": "Internal server error"
        }
    )


# Include routers
app.include_router(sync_router, prefix="/sync", tags=["Sync"])
app.include_router(webhook_router, prefix="/webhooks", tags=["Webhooks"])
app.include_router(provider_router, prefix="/tenants", tags=["Providers"])


if __name__ == "__main__":
    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=8001,
        reload=settings.environment == "development"
    )
