# AIVO Notification Service - FastAPI Main Application
# S1-12 Implementation - WebSocket Hub + Push Subscribe + Daily Digest

import asyncio
import logging
import os
from contextlib import asynccontextmanager
from typing import Dict, Any

from fastapi import FastAPI, HTTPException, Depends, WebSocket, WebSocketDisconnect, Query
from fastapi.middleware.cors import CORSMiddleware
from fastapi.security import HTTPBearer
from sqlalchemy.orm import Session
import redis.asyncio as redis
import uvicorn

from .database import engine, get_db, init_db
from .models import Base
from .ws import WebSocketManager, authenticate_websocket, ws_manager
from .routes import router as notification_routes
from .cron import start_cron_jobs, stop_cron_jobs

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Global Redis client
redis_client = None

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan management."""
    global redis_client, ws_manager
    
    try:
        # Initialize Redis connection
        redis_url = os.getenv("REDIS_URL", "redis://localhost:6379")
        redis_client = redis.from_url(redis_url, decode_responses=False)
        await redis_client.ping()
        logger.info("Redis connection established")
        
        # Initialize WebSocket manager
        ws_manager = WebSocketManager(redis_client)
        logger.info("WebSocket manager initialized")
        
        # Initialize database
        init_db()
        logger.info("Database initialized")
        
        # Start background cron jobs
        await start_cron_jobs(redis_client)
        logger.info("Cron jobs started")
        
        yield
        
    except Exception as e:
        logger.error(f"Startup error: {e}")
        raise
    finally:
        # Cleanup
        try:
            await stop_cron_jobs()
            if redis_client:
                await redis_client.close()
            logger.info("Cleanup completed")
        except Exception as e:
            logger.error(f"Cleanup error: {e}")

# Create FastAPI application
app = FastAPI(
    title="AIVO Notification Service",
    description="Real-time notification service with WebSocket hub, push subscriptions, and daily digest",
    version="1.0.0",
    lifespan=lifespan
)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Configure properly for production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Security
security = HTTPBearer()

# Include notification routes
app.include_router(notification_routes, prefix="/api/v1")

# Health check endpoint
@app.get("/health")
async def health_check():
    """Health check endpoint."""
    try:
        # Check Redis connection
        await redis_client.ping()
        
        # Check WebSocket manager
        stats = ws_manager.get_connection_stats() if ws_manager else {}
        
        return {
            "status": "healthy",
            "timestamp": "2025-01-15T16:00:00Z",
            "redis": "connected",
            "websocket_connections": stats.get("total_connections", 0),
            "version": "1.0.0"
        }
    except Exception as e:
        raise HTTPException(status_code=503, detail=f"Service unhealthy: {e}")

# WebSocket endpoint
@app.websocket("/ws/notify")
async def websocket_endpoint(
    websocket: WebSocket,
    token: str = Query(...),
    db: Session = Depends(get_db)
):
    """
    WebSocket endpoint for real-time notifications.
    
    Requires JWT token for authentication.
    Query parameter: ?token=<jwt_token>
    """
    try:
        # Authenticate WebSocket connection
        auth_data = await authenticate_websocket(token)
        user_id = auth_data["user_id"]
        tenant_id = auth_data["tenant_id"]
        
        if not user_id or not tenant_id:
            await websocket.close(code=4001, reason="Missing user_id or tenant_id")
            return
        
        # Connect to WebSocket manager
        connection_id = await ws_manager.connect(websocket, user_id, tenant_id, db)
        
        try:
            # Handle connection messages
            await ws_manager.handle_connection_messages(
                websocket, connection_id, user_id, db
            )
        except WebSocketDisconnect:
            logger.info(f"WebSocket disconnected: {connection_id}")
        finally:
            await ws_manager.disconnect(connection_id, db)
            
    except Exception as e:
        logger.error(f"WebSocket error: {e}")
        await websocket.close(code=4000, reason="Authentication failed")

# WebSocket status endpoint
@app.get("/ws/status")
async def websocket_status():
    """Get WebSocket connection status."""
    if not ws_manager:
        raise HTTPException(status_code=503, detail="WebSocket manager not available")
    
    return ws_manager.get_connection_stats()

# Notification broadcasting endpoint (internal use)
@app.post("/internal/broadcast")
async def broadcast_notification(
    notification_data: Dict[str, Any],
    db: Session = Depends(get_db)
):
    """
    Internal endpoint for broadcasting notifications via WebSocket.
    Used by other services to trigger real-time notifications.
    """
    try:
        user_id = notification_data.get("user_id")
        tenant_id = notification_data.get("tenant_id")
        broadcast_to_tenant = notification_data.get("broadcast_to_tenant", False)
        
        if not ws_manager:
            raise HTTPException(status_code=503, detail="WebSocket manager not available")
        
        if broadcast_to_tenant and tenant_id:
            # Broadcast to all users in tenant
            message = {
                "type": "notification",
                "data": notification_data,
                "timestamp": "2025-01-15T16:00:00Z"
            }
            await ws_manager.broadcast_to_tenant(tenant_id, message)
        elif user_id:
            # Send to specific user
            await ws_manager.notify_user(user_id, notification_data, db)
        else:
            raise HTTPException(status_code=400, detail="user_id or tenant_id required")
        
        return {"status": "success", "message": "Notification broadcasted"}
        
    except Exception as e:
        logger.error(f"Broadcast error: {e}")
        raise HTTPException(status_code=500, detail=f"Broadcast failed: {e}")

# Development server
if __name__ == "__main__":
    uvicorn.run(
        "app.main:app",
        host="0.0.0.0",
        port=8003,
        reload=True,
        log_level="info"
    )
