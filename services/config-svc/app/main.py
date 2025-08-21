"""
Config Service - Feature Flags & Remote Configuration
Provides dynamic feature flagging with targeting rules for cohorts, tenants, and grade bands.
"""

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager
import asyncio
import logging
import os

import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.routes import router
from app.models import ConfigCache, FlagEvaluator


# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan management"""
    # Startup
    logger.info("🚀 Starting Config Service...")
    
    # Initialize config cache
    config_cache = ConfigCache()
    await config_cache.initialize()
    app.state.config_cache = config_cache
    logger.info("✅ Config cache initialized")
    
    # Initialize flag evaluator
    flag_evaluator = FlagEvaluator(config_cache)
    app.state.flag_evaluator = flag_evaluator
    logger.info("✅ Flag evaluator initialized")
    
    # Start background tasks
    refresh_task = asyncio.create_task(config_cache.start_refresh_loop())
    app.state.refresh_task = refresh_task
    logger.info("✅ Background refresh task started")
    
    yield
    
    # Shutdown
    logger.info("🛑 Shutting down Config Service...")
    if hasattr(app.state, 'refresh_task'):
        app.state.refresh_task.cancel()
        try:
            await app.state.refresh_task
        except asyncio.CancelledError:
            pass
    
    if hasattr(app.state, 'config_cache'):
        await app.state.config_cache.close()
    logger.info("✅ Cleanup completed")


# Create FastAPI app
app = FastAPI(
    title="Aivo Config Service",
    description="Feature flags and remote configuration with targeting rules",
    version="1.0.0",
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

# Include routes
app.include_router(router, prefix="/api/v1")


@app.get("/health")
async def health_check():
    """Health check endpoint"""
    return {
        "status": "healthy",
        "service": "config-svc",
        "version": "1.0.0"
    }


@app.get("/ready")
async def readiness_check():
    """Readiness check endpoint"""
    try:
        # Check if config cache is ready
        if not hasattr(app.state, 'config_cache'):
            raise HTTPException(status_code=503, detail="Config cache not initialized")
        
        # Check cache health
        cache_health = await app.state.config_cache.health_check()
        if not cache_health:
            raise HTTPException(status_code=503, detail="Config cache unhealthy")
        
        return {
            "status": "ready",
            "service": "config-svc",
            "cache_healthy": True
        }
    except Exception as e:
        logger.error(f"Readiness check failed: {e}")
        raise HTTPException(status_code=503, detail="Service not ready")


if __name__ == "__main__":
    import uvicorn
    
    # Get configuration from environment
    host = os.getenv("HOST", "0.0.0.0")
    port = int(os.getenv("PORT", "8080"))
    debug = os.getenv("DEBUG", "false").lower() == "true"
    
    uvicorn.run(
        "main:app",
        host=host,
        port=port,
        reload=debug,
        log_level="info" if not debug else "debug"
    )
