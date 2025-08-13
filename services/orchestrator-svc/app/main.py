"""
AIVO Orchestrator Service - Main Application
S1-14 Implementation

Event-driven orchestration service that consumes educational events and produces
intelligent level suggestions and game break triggers.
"""

import logging
import asyncio
from contextlib import asynccontextmanager
from typing import Dict, Any

from fastapi import FastAPI, HTTPException, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
import uvicorn

from .consumer import EventConsumer
from .logic import OrchestrationEngine

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)

# Global instances
event_consumer: EventConsumer = None
orchestration_engine: OrchestrationEngine = None


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan manager"""
    
    global event_consumer, orchestration_engine
    
    # Startup
    logger.info("Starting AIVO Orchestrator Service...")
    
    try:
        # Initialize orchestration engine
        orchestration_engine = OrchestrationEngine()
        await orchestration_engine.initialize()
        
        # Initialize event consumer  
        event_consumer = EventConsumer(orchestration_engine)
        
        # Start event consumption in background
        consumer_task = asyncio.create_task(event_consumer.start_consuming())
        logger.info("Event consumer started")
        
    except Exception as e:
        logger.error(f"Failed to initialize orchestrator service: {e}")
        raise
        
    yield
    
    # Shutdown
    logger.info("Shutting down AIVO Orchestrator Service...")
    
    if event_consumer:
        await event_consumer.stop_consuming()
        
    if consumer_task and not consumer_task.done():
        consumer_task.cancel()
        try:
            await consumer_task
        except asyncio.CancelledError:
            pass


# Create FastAPI application
app = FastAPI(
    title="AIVO Orchestrator Service",
    description="""
    Event-driven orchestration service for the AIVO Virtual Brains ecosystem.
    
    ## Overview
    
    The Orchestrator Service acts as the central intelligence hub that consumes
    educational events from various services and produces intelligent responses:
    
    * **Level Suggestions**: Analyzes learner progress and suggests appropriate difficulty adjustments
    * **Game Break Triggers**: Monitors engagement patterns and schedules therapeutic breaks
    * **SEL Interventions**: Responds to social-emotional learning alerts with targeted support
    * **Coursework Optimization**: Adjusts learning paths based on performance analytics
    
    ## Event Processing
    
    ### Input Events
    - `BASELINE_COMPLETE`: Initial assessment completed, establish learning baseline
    - `SLP_UPDATED`: Speech Language Pathology assessment updated 
    - `SEL_ALERT`: Social-emotional learning concern detected
    - `COURSEWORK_ANALYZED`: Learning analytics completed for coursework
    
    ### Output Actions
    - `LEVEL_SUGGESTED`: Update learner difficulty level via learner-svc REST API
    - `GAME_BREAK`: Schedule therapeutic break via notification-svc
    - `SEL_INTERVENTION`: Trigger social-emotional support workflow
    - `LEARNING_PATH_UPDATE`: Adjust curriculum progression
    
    ## Intelligence Engine
    
    Uses rule-based logic and machine learning insights to make real-time
    decisions about learner support and educational interventions.
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


@app.get("/health", summary="Health Check")
async def health_check() -> Dict[str, Any]:
    """
    Health check endpoint for monitoring and load balancers.
    
    Returns service status and event consumer health.
    """
    try:
        consumer_status = "unknown"
        engine_status = "unknown"
        
        if event_consumer:
            consumer_status = "running" if event_consumer.is_running else "stopped"
            
        if orchestration_engine:
            engine_status = "initialized" if orchestration_engine.is_initialized else "not_initialized"
        
        return {
            "status": "healthy",
            "service": "aivo-orchestrator-svc",
            "version": "1.0.0",
            "timestamp": "2025-01-15T14:30:00Z",
            "components": {
                "event_consumer": consumer_status,
                "orchestration_engine": engine_status
            }
        }
    except Exception as e:
        logger.error(f"Health check failed: {e}")
        return JSONResponse(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            content={
                "status": "unhealthy",
                "service": "aivo-orchestrator-svc",
                "error": str(e)
            }
        )


@app.get("/", summary="Service Information")
async def root() -> Dict[str, str]:
    """
    Root endpoint providing basic service information.
    """
    return {
        "service": "AIVO Orchestrator Service",
        "description": "Event-driven orchestration for educational intelligence",
        "version": "1.0.0",
        "docs": "/docs",
        "health": "/health"
    }


@app.get("/stats", summary="Orchestration Statistics")
async def get_stats() -> Dict[str, Any]:
    """
    Get orchestration statistics and event processing metrics.
    """
    try:
        stats = {
            "service_info": {
                "status": "running",
                "uptime": "0 minutes",  # Would be calculated from start time
                "version": "1.0.0"
            },
            "event_processing": {
                "total_events_processed": 0,
                "events_per_minute": 0,
                "last_event_time": None
            },
            "orchestration_actions": {
                "level_suggestions_sent": 0,
                "game_breaks_scheduled": 0,
                "sel_interventions_triggered": 0
            }
        }
        
        if event_consumer:
            stats["event_processing"].update(await event_consumer.get_stats())
            
        if orchestration_engine:
            stats["orchestration_actions"].update(await orchestration_engine.get_stats())
        
        return stats
        
    except Exception as e:
        logger.error(f"Stats retrieval failed: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve orchestration statistics"
        )


@app.post("/internal/trigger", summary="Manual Event Trigger (Testing)")
async def trigger_event(event_data: Dict[str, Any]) -> Dict[str, Any]:
    """
    Manually trigger an event for testing purposes.
    
    This endpoint allows manual triggering of orchestration logic
    for testing and debugging purposes.
    """
    try:
        if not orchestration_engine:
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="Orchestration engine not initialized"
            )
            
        # Process event through orchestration engine
        result = await orchestration_engine.process_event(event_data)
        
        return {
            "event_processed": True,
            "event_type": event_data.get("type", "unknown"),
            "actions_taken": result.get("actions", []),
            "processing_time_ms": result.get("processing_time_ms", 0)
        }
        
    except Exception as e:
        logger.error(f"Manual event trigger failed: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Event processing failed"
        )


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
        port=8005,
        reload=True,
        log_level="info"
    )
