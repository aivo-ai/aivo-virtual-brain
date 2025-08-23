"""
SIS Bridge Service Main Application

Provides SIS (Student Information System) integration with SCIM 2.0 API.
Supports Clever, ClassLink, and other SIS providers.
"""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager

from .config import get_settings
from .database import init_db
from .routes import sync, webhooks, providers
from .scheduler import SyncScheduler

settings = get_settings()


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan management."""
    
    # Initialize database
    await init_db()
    
    # Initialize sync scheduler
    scheduler = SyncScheduler()
    app.state.scheduler = scheduler
    await scheduler.start()
    
    yield
    
    # Cleanup
    await scheduler.stop()


# Create FastAPI application
app = FastAPI(
    title="SIS Bridge Service",
    description="SIS integration service with SCIM 2.0 synchronization",
    version="1.0.0",
    lifespan=lifespan
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.allowed_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routers
app.include_router(sync.router, prefix="/api/v1/sync", tags=["sync"])
app.include_router(webhooks.router, prefix="/api/v1/webhooks", tags=["webhooks"])
app.include_router(providers.router, prefix="/api/v1/providers", tags=["providers"])


@app.get("/health")
async def health_check():
    """Health check endpoint."""
    return {"status": "healthy", "service": "sis-bridge-svc"}


@app.get("/")
async def root():
    """Root endpoint with service information."""
    return {
        "service": "SIS Bridge Service",
        "version": "1.0.0",
        "description": "SIS integration service with SCIM 2.0 synchronization",
        "endpoints": {
            "health": "/health",
            "sync": "/api/v1/sync",
            "webhooks": "/api/v1/webhooks", 
            "providers": "/api/v1/providers"
        }
    }
