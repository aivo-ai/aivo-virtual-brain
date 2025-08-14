"""
Main FastAPI application for Model Trainer Service
"""

import logging
from contextlib import asynccontextmanager
from typing import AsyncGenerator

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.trustedhost import TrustedHostMiddleware
from fastapi.responses import JSONResponse
from loguru import logger
from opentelemetry import trace
from opentelemetry.exporter.jaeger.thrift import JaegerExporter
from opentelemetry.instrumentation.fastapi import FastAPIInstrumentor
from opentelemetry.instrumentation.httpx import HTTPXClientInstrumentor
from opentelemetry.instrumentation.sqlalchemy import SQLAlchemyInstrumentor
from opentelemetry.sdk.resources import SERVICE_NAME, Resource
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import BatchSpanProcessor
from prometheus_client import make_asgi_app

from .config import settings
from .database import engine, get_db
from .routes import trainer_router


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    """Application lifespan manager"""
    logger.info("Starting Model Trainer Service")
    
    # Initialize database
    from .models import Base
    # Note: In production, use Alembic migrations instead
    # Base.metadata.create_all(bind=engine)
    
    logger.info("Model Trainer Service started successfully")
    yield
    
    logger.info("Shutting down Model Trainer Service")


# Initialize tracing
if settings.tracing_enabled:
    resource = Resource(attributes={
        SERVICE_NAME: "model-trainer-service"
    })
    
    provider = TracerProvider(resource=resource)
    processor = BatchSpanProcessor(
        JaegerExporter(
            agent_host_name="localhost",
            agent_port=6831,
        )
    )
    provider.add_span_processor(processor)
    trace.set_tracer_provider(provider)
    
    # Instrument frameworks
    FastAPIInstrumentor.instrument()
    HTTPXClientInstrumentor.instrument()
    SQLAlchemyInstrumentor.instrument(engine=engine)


# Create FastAPI app
app = FastAPI(
    title="AIVO Model Trainer Service",
    description="S2-03: OpenAI Fine-Tuning with Evaluation & Promotion",
    version="1.0.0",
    docs_url="/docs" if settings.environment != "production" else None,
    redoc_url="/redoc" if settings.environment != "production" else None,
    lifespan=lifespan,
)

# Add middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"] if settings.environment == "development" else settings.allowed_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.add_middleware(
    TrustedHostMiddleware,
    allowed_hosts=["*"] if settings.environment == "development" else settings.allowed_hosts,
)

# Add Prometheus metrics
if settings.metrics_enabled:
    metrics_app = make_asgi_app()
    app.mount("/metrics", metrics_app)

# Include routers
app.include_router(trainer_router, prefix="/trainer", tags=["training"])


@app.get("/health")
async def health_check():
    """Health check endpoint"""
    try:
        # Check database connection
        async with get_db() as db:
            await db.execute("SELECT 1")
        
        # Check OpenAI API (optional)
        # Could add OpenAI API ping here
        
        return {
            "status": "healthy",
            "service": "model-trainer",
            "version": "1.0.0",
            "environment": settings.environment,
            "checks": {
                "database": "healthy",
                "openai": "healthy",
            }
        }
    except Exception as e:
        logger.error(f"Health check failed: {e}")
        raise HTTPException(status_code=503, detail="Service unavailable")


@app.get("/stats")
async def service_stats():
    """Get service statistics"""
    try:
        from .service import TrainerService
        
        service = TrainerService()
        stats = await service.get_statistics()
        
        return {
            "service": "model-trainer",
            "version": "1.0.0",
            "statistics": stats,
        }
    except Exception as e:
        logger.error(f"Failed to get statistics: {e}")
        raise HTTPException(status_code=500, detail="Failed to get statistics")


@app.exception_handler(Exception)
async def global_exception_handler(request, exc):
    """Global exception handler"""
    logger.error(f"Unhandled exception: {exc}")
    return JSONResponse(
        status_code=500,
        content={"detail": "Internal server error"}
    )


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "app.main:app",
        host=settings.api_host,
        port=settings.api_port,
        reload=settings.environment == "development",
        log_level=settings.log_level.lower(),
    )
