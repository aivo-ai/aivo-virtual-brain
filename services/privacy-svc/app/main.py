"""
Privacy Service - GDPR Compliance & Data Rights
Handles data export, erasure, and retention for AIVO platform
"""

import logging
import os
from datetime import datetime
from typing import Optional

from fastapi import FastAPI, HTTPException, BackgroundTasks, Depends
from fastapi.middleware.cors import CORSMiddleware
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from fastapi.responses import FileResponse
from pydantic import BaseSettings
import asyncpg
import redis.asyncio as redis
import structlog

from .routes import router as privacy_router
from .models import PrivacyRequestStatus, AuditLog
from .database import init_db, get_db_pool

# Configure structured logging
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

class Settings(BaseSettings):
    """Application settings"""
    database_url: str = "postgresql://privacy:password@localhost:5432/aivo_privacy"
    redis_url: str = "redis://localhost:6379/0"
    encryption_key: str = ""
    export_storage_path: str = "/tmp/privacy-exports"
    max_export_size_mb: int = 500
    retention_days: int = 2555  # 7 years default
    checkpoint_retention_count: int = 3
    jwt_secret: str = ""
    environment: str = "development"
    service_name: str = "privacy-svc"
    version: str = "1.0.0"
    
    class Config:
        env_file = ".env"

settings = Settings()

# Security
security = HTTPBearer()

async def verify_token(credentials: HTTPAuthorizationCredentials = Depends(security)):
    """Verify JWT token for API access"""
    # TODO: Implement JWT verification with auth service
    token = credentials.credentials
    if not token:
        raise HTTPException(status_code=401, detail="Missing authentication token")
    
    # For now, basic validation - integrate with auth-svc in production
    if token == "dev-token" and settings.environment == "development":
        return {"user_id": "system", "scope": "privacy"}
    
    raise HTTPException(status_code=401, detail="Invalid authentication token")

# Initialize FastAPI app
app = FastAPI(
    title="AIVO Privacy Service",
    description="GDPR compliance service for data export, erasure, and retention",
    version=settings.version,
    docs_url="/docs" if settings.environment != "production" else None,
    redoc_url="/redoc" if settings.environment != "production" else None
)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["https://aivo.com", "https://*.aivo.com"] if settings.environment == "production" else ["*"],
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE"],
    allow_headers=["*"],
)

# Global variables for database and redis connections
db_pool: Optional[asyncpg.Pool] = None
redis_client: Optional[redis.Redis] = None

@app.on_event("startup")
async def startup_event():
    """Initialize database and redis connections"""
    global db_pool, redis_client
    
    logger.info("Starting Privacy Service", version=settings.version)
    
    # Initialize database
    try:
        db_pool = await init_db(settings.database_url)
        logger.info("Database connection established")
    except Exception as e:
        logger.error("Failed to connect to database", error=str(e))
        raise
    
    # Initialize Redis
    try:
        redis_client = redis.from_url(settings.redis_url)
        await redis_client.ping()
        logger.info("Redis connection established")
    except Exception as e:
        logger.error("Failed to connect to Redis", error=str(e))
        raise
    
    # Create export directory
    os.makedirs(settings.export_storage_path, exist_ok=True)
    logger.info("Export storage initialized", path=settings.export_storage_path)

@app.on_event("shutdown")
async def shutdown_event():
    """Clean up connections"""
    global db_pool, redis_client
    
    if db_pool:
        await db_pool.close()
        logger.info("Database connection closed")
    
    if redis_client:
        await redis_client.close()
        logger.info("Redis connection closed")

# Health check
@app.get("/health")
async def health_check():
    """Health check endpoint"""
    return {
        "status": "healthy",
        "service": settings.service_name,
        "version": settings.version,
        "timestamp": datetime.utcnow().isoformat()
    }

@app.get("/ready")
async def readiness_check():
    """Readiness check endpoint"""
    try:
        # Check database
        async with db_pool.acquire() as conn:
            await conn.fetchval("SELECT 1")
        
        # Check Redis
        await redis_client.ping()
        
        return {
            "status": "ready",
            "service": settings.service_name,
            "timestamp": datetime.utcnow().isoformat()
        }
    except Exception as e:
        logger.error("Readiness check failed", error=str(e))
        raise HTTPException(status_code=503, detail="Service not ready")

# Include privacy routes
app.include_router(privacy_router, prefix="/api/v1", dependencies=[Depends(verify_token)])

# Error handlers
@app.exception_handler(ValueError)
async def value_error_handler(request, exc):
    logger.error("Value error", error=str(exc))
    return HTTPException(status_code=400, detail=str(exc))

@app.exception_handler(Exception)
async def general_error_handler(request, exc):
    logger.error("Unexpected error", error=str(exc))
    return HTTPException(status_code=500, detail="Internal server error")

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=8080,
        log_level="info",
        reload=settings.environment == "development"
    )
