"""
FinOps Service Main Application
FastAPI service for cost metering, budget management, and financial operations
"""

import asyncio
import logging
import sys
from contextlib import asynccontextmanager
from datetime import datetime
from typing import Dict, Any

import structlog
from fastapi import FastAPI, HTTPException, Request, Response
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.trustedhost import TrustedHostMiddleware
from fastapi.responses import JSONResponse
import uvicorn

from .database import (
    create_connection_pool, close_connection_pool,
    create_finops_tables, health_check_db
)
from .routes import router as finops_router
from .models import FinOpsHealth
from .cost_calculator import CostCalculator
from .budget_monitor import BudgetMonitor
from .pricing_updater import PricingUpdater

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

logger = structlog.get_logger(__name__)

# Global state
app_state = {
    "startup_time": datetime.utcnow(),
    "cost_calculator": None,
    "budget_monitor": None,
    "pricing_updater": None,
    "background_tasks": set(),
}


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan management"""
    logger.info("Starting FinOps service...")
    
    try:
        # Initialize database connection pool
        await create_connection_pool()
        logger.info("Database connection pool created")
        
        # Create database tables
        await create_finops_tables()
        logger.info("Database tables initialized")
        
        # Initialize cost calculator
        app_state["cost_calculator"] = CostCalculator()
        logger.info("Cost calculator initialized")
        
        # Initialize budget monitor
        app_state["budget_monitor"] = BudgetMonitor()
        logger.info("Budget monitor initialized")
        
        # Initialize pricing updater
        app_state["pricing_updater"] = PricingUpdater()
        logger.info("Pricing updater initialized")
        
        # Start background tasks
        await start_background_tasks()
        logger.info("Background tasks started")
        
        logger.info("FinOps service startup complete")
        
    except Exception as e:
        logger.error("Failed to start FinOps service", error=str(e), exc_info=True)
        raise
    
    yield
    
    # Cleanup
    logger.info("Shutting down FinOps service...")
    
    try:
        # Stop background tasks
        await stop_background_tasks()
        logger.info("Background tasks stopped")
        
        # Close database connections
        await close_connection_pool()
        logger.info("Database connections closed")
        
    except Exception as e:
        logger.error("Error during shutdown", error=str(e), exc_info=True)
    
    logger.info("FinOps service shutdown complete")


async def start_background_tasks():
    """Start background monitoring and update tasks"""
    
    # Start budget monitoring
    budget_task = asyncio.create_task(
        app_state["budget_monitor"].start_monitoring(),
        name="budget_monitor"
    )
    app_state["background_tasks"].add(budget_task)
    budget_task.add_done_callback(app_state["background_tasks"].discard)
    
    # Start pricing updates
    pricing_task = asyncio.create_task(
        app_state["pricing_updater"].start_updates(),
        name="pricing_updater"
    )
    app_state["background_tasks"].add(pricing_task)
    pricing_task.add_done_callback(app_state["background_tasks"].discard)
    
    # Start cost aggregation
    aggregation_task = asyncio.create_task(
        periodic_cost_aggregation(),
        name="cost_aggregation"
    )
    app_state["background_tasks"].add(aggregation_task)
    aggregation_task.add_done_callback(app_state["background_tasks"].discard)


async def stop_background_tasks():
    """Stop all background tasks"""
    for task in app_state["background_tasks"]:
        if not task.done():
            task.cancel()
    
    # Wait for tasks to complete
    if app_state["background_tasks"]:
        await asyncio.gather(*app_state["background_tasks"], return_exceptions=True)
    
    app_state["background_tasks"].clear()


async def periodic_cost_aggregation():
    """Periodically aggregate cost data for reporting"""
    while True:
        try:
            await asyncio.sleep(300)  # Run every 5 minutes
            
            calculator = app_state["cost_calculator"]
            if calculator:
                await calculator.aggregate_recent_costs()
                logger.debug("Cost aggregation completed")
                
        except asyncio.CancelledError:
            break
        except Exception as e:
            logger.error("Error in cost aggregation", error=str(e), exc_info=True)
            await asyncio.sleep(60)  # Wait before retrying


# Create FastAPI application
app = FastAPI(
    title="FinOps Service",
    description="Cost metering, budget management, and financial operations for AI inference services",
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc",
    openapi_url="/openapi.json",
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

# Add trusted host middleware
app.add_middleware(
    TrustedHostMiddleware,
    allowed_hosts=["*"]  # Configure appropriately for production
)


@app.middleware("http")
async def request_logging_middleware(request: Request, call_next):
    """Log all requests with timing and cost tracking context"""
    start_time = datetime.utcnow()
    
    # Extract request context
    tenant_id = request.headers.get("X-Tenant-ID")
    user_id = request.headers.get("X-User-ID")
    trace_id = request.headers.get("X-Trace-ID", f"trace-{start_time.timestamp()}")
    
    # Create structured logger with context
    request_logger = logger.bind(
        method=request.method,
        url=str(request.url),
        tenant_id=tenant_id,
        user_id=user_id,
        trace_id=trace_id,
    )
    
    request_logger.info("Request started")
    
    try:
        response = await call_next(request)
        
        # Calculate processing time
        end_time = datetime.utcnow()
        processing_time = (end_time - start_time).total_seconds() * 1000
        
        request_logger.info(
            "Request completed",
            status_code=response.status_code,
            processing_time_ms=processing_time
        )
        
        # Add timing headers
        response.headers["X-Processing-Time"] = str(processing_time)
        response.headers["X-Trace-ID"] = trace_id
        
        return response
        
    except Exception as e:
        end_time = datetime.utcnow()
        processing_time = (end_time - start_time).total_seconds() * 1000
        
        request_logger.error(
            "Request failed",
            error=str(e),
            processing_time_ms=processing_time,
            exc_info=True
        )
        
        # Return structured error response
        return JSONResponse(
            status_code=500,
            content={
                "error": "Internal server error",
                "trace_id": trace_id,
                "timestamp": end_time.isoformat()
            },
            headers={"X-Trace-ID": trace_id}
        )


@app.middleware("http")
async def cost_tracking_middleware(request: Request, call_next):
    """Track API usage for internal cost attribution"""
    start_time = datetime.utcnow()
    
    try:
        response = await call_next(request)
        
        # Track internal API usage if cost calculator is available
        if app_state["cost_calculator"] and request.method in ["GET", "POST", "PUT", "DELETE"]:
            end_time = datetime.utcnow()
            processing_time = (end_time - start_time).total_seconds() * 1000
            
            # Estimate computational cost based on processing time and endpoint
            await app_state["cost_calculator"].track_api_usage(
                endpoint=str(request.url.path),
                method=request.method,
                processing_time_ms=processing_time,
                tenant_id=request.headers.get("X-Tenant-ID"),
                timestamp=start_time
            )
        
        return response
        
    except Exception as e:
        # Still track failed requests for cost attribution
        if app_state["cost_calculator"]:
            end_time = datetime.utcnow()
            processing_time = (end_time - start_time).total_seconds() * 1000
            
            await app_state["cost_calculator"].track_api_usage(
                endpoint=str(request.url.path),
                method=request.method,
                processing_time_ms=processing_time,
                tenant_id=request.headers.get("X-Tenant-ID"),
                timestamp=start_time,
                error=str(e)
            )
        
        raise


# Include API routes
app.include_router(finops_router, prefix="/api/v1", tags=["finops"])


# Health check endpoints
@app.get("/health", response_model=FinOpsHealth, tags=["health"])
async def health_check():
    """Health check endpoint with detailed service status"""
    try:
        # Check database connectivity
        db_healthy = await health_check_db()
        
        # Check component status
        calculator_healthy = app_state["cost_calculator"] is not None
        monitor_healthy = app_state["budget_monitor"] is not None
        updater_healthy = app_state["pricing_updater"] is not None
        
        # Calculate uptime
        uptime = (datetime.utcnow() - app_state["startup_time"]).total_seconds()
        
        # Get system metrics
        health_status = FinOpsHealth(
            status="healthy" if all([
                db_healthy, calculator_healthy, monitor_healthy, updater_healthy
            ]) else "degraded",
            database_connected=db_healthy,
            uptime_seconds=int(uptime)
        )
        
        # Add component-specific health data
        if app_state["budget_monitor"]:
            health_status.budgets_monitored = await app_state["budget_monitor"].get_active_budget_count()
            health_status.alerts_pending = await app_state["budget_monitor"].get_pending_alert_count()
        
        if app_state["cost_calculator"]:
            health_status.latest_usage_event = await app_state["cost_calculator"].get_latest_event_time()
            health_status.daily_events_processed = await app_state["cost_calculator"].get_daily_event_count()
        
        if app_state["pricing_updater"]:
            health_status.pricing_data_current = await app_state["pricing_updater"].is_pricing_current()
            health_status.last_usage_sync = await app_state["pricing_updater"].get_last_sync_time()
        
        return health_status
        
    except Exception as e:
        logger.error("Health check failed", error=str(e), exc_info=True)
        raise HTTPException(
            status_code=503,
            detail=f"Service unhealthy: {str(e)}"
        )


@app.get("/health/ready", tags=["health"])
async def readiness_check():
    """Kubernetes readiness probe"""
    try:
        # Check if all critical components are initialized
        if not all([
            app_state["cost_calculator"],
            app_state["budget_monitor"],
            app_state["pricing_updater"]
        ]):
            raise HTTPException(status_code=503, detail="Service not ready")
        
        # Check database connectivity
        if not await health_check_db():
            raise HTTPException(status_code=503, detail="Database not ready")
        
        return {"status": "ready"}
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error("Readiness check failed", error=str(e), exc_info=True)
        raise HTTPException(status_code=503, detail="Service not ready")


@app.get("/health/live", tags=["health"])
async def liveness_check():
    """Kubernetes liveness probe"""
    return {"status": "alive", "timestamp": datetime.utcnow().isoformat()}


@app.get("/metrics", tags=["metrics"])
async def metrics():
    """Prometheus metrics endpoint"""
    try:
        metrics_data = []
        
        # Service uptime
        uptime = (datetime.utcnow() - app_state["startup_time"]).total_seconds()
        metrics_data.append(f"finops_uptime_seconds {uptime}")
        
        # Component status
        metrics_data.append(f"finops_cost_calculator_status {1 if app_state['cost_calculator'] else 0}")
        metrics_data.append(f"finops_budget_monitor_status {1 if app_state['budget_monitor'] else 0}")
        metrics_data.append(f"finops_pricing_updater_status {1 if app_state['pricing_updater'] else 0}")
        
        # Background task count
        metrics_data.append(f"finops_background_tasks {len(app_state['background_tasks'])}")
        
        # Database connectivity
        db_status = 1 if await health_check_db() else 0
        metrics_data.append(f"finops_database_connected {db_status}")
        
        # Get additional metrics from components
        if app_state["budget_monitor"]:
            budget_count = await app_state["budget_monitor"].get_active_budget_count()
            alert_count = await app_state["budget_monitor"].get_pending_alert_count()
            metrics_data.append(f"finops_budgets_monitored {budget_count}")
            metrics_data.append(f"finops_alerts_pending {alert_count}")
        
        if app_state["cost_calculator"]:
            daily_events = await app_state["cost_calculator"].get_daily_event_count()
            metrics_data.append(f"finops_daily_events_processed {daily_events}")
        
        return Response(
            content="\n".join(metrics_data) + "\n",
            media_type="text/plain"
        )
        
    except Exception as e:
        logger.error("Metrics generation failed", error=str(e), exc_info=True)
        return Response(
            content="# Error generating metrics\n",
            media_type="text/plain",
            status_code=500
        )


@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    """Global exception handler with structured logging"""
    trace_id = request.headers.get("X-Trace-ID", f"error-{datetime.utcnow().timestamp()}")
    
    logger.error(
        "Unhandled exception",
        error=str(exc),
        trace_id=trace_id,
        method=request.method,
        url=str(request.url),
        exc_info=True
    )
    
    return JSONResponse(
        status_code=500,
        content={
            "error": "Internal server error",
            "trace_id": trace_id,
            "timestamp": datetime.utcnow().isoformat()
        },
        headers={"X-Trace-ID": trace_id}
    )


def create_app() -> FastAPI:
    """Factory function to create the FastAPI application"""
    return app


if __name__ == "__main__":
    # Development server
    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=8000,
        reload=True,
        log_config={
            "version": 1,
            "disable_existing_loggers": False,
            "formatters": {
                "default": {
                    "format": "%(asctime)s - %(name)s - %(levelname)s - %(message)s",
                },
            },
            "handlers": {
                "default": {
                    "formatter": "default",
                    "class": "logging.StreamHandler",
                    "stream": "ext://sys.stdout",
                },
            },
            "root": {
                "level": "INFO",
                "handlers": ["default"],
            },
        }
    )
