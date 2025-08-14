"""
Event Collector Service - Main Application (S2-14)
FastAPI application for high-throughput event ingestion to Kafka
"""
import asyncio
import logging
import os
import time
from contextlib import asynccontextmanager
from typing import Dict, Any

import uvicorn
from fastapi import FastAPI, Request, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.gzip import GZipMiddleware
from fastapi.responses import JSONResponse

from .routers import http_router
from .writer import KafkaEventWriter
from .schemas import ErrorResponse

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Global writer instance
kafka_writer: KafkaEventWriter = None


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan manager - handles startup and shutdown."""
    global kafka_writer
    
    # Startup
    logger.info("Starting Event Collector Service S2-14")
    
    # Initialize Kafka writer
    kafka_config = {
        'bootstrap_servers': os.getenv('KAFKA_BOOTSTRAP_SERVERS', 'localhost:9092'),
        'topic': os.getenv('KAFKA_TOPIC', 'events'),
        'client_id': os.getenv('KAFKA_CLIENT_ID', 'event-collector-svc'),
        'max_retries': int(os.getenv('KAFKA_MAX_RETRIES', '3')),
        'retry_backoff_ms': int(os.getenv('KAFKA_RETRY_BACKOFF_MS', '100')),
        'request_timeout_ms': int(os.getenv('KAFKA_REQUEST_TIMEOUT_MS', '30000')),
        'compression_type': os.getenv('KAFKA_COMPRESSION_TYPE', 'gzip'),
        'acks': os.getenv('KAFKA_ACKS', 'all'),
        'max_in_flight_requests_per_connection': int(os.getenv('KAFKA_MAX_IN_FLIGHT', '1'))
    }
    
    buffer_config = {
        'buffer_dir': os.getenv('BUFFER_DIR', './data/buffer'),
        'max_buffer_size_mb': int(os.getenv('MAX_BUFFER_SIZE_MB', '100')),
        'batch_size': int(os.getenv('BUFFER_BATCH_SIZE', '100'))
    }
    
    dlq_config = {
        'dlq_topic': os.getenv('DLQ_TOPIC', 'events-dlq'),
        'poison_pill_threshold': int(os.getenv('POISON_PILL_THRESHOLD', '3'))
    }
    
    try:
        kafka_writer = KafkaEventWriter(
            kafka_config=kafka_config,
            buffer_config=buffer_config,
            dlq_config=dlq_config
        )
        kafka_writer._start_time = time.time()  # Track uptime
        
        # Set global writer in router
        import app.routers.http as http_module
        http_module.kafka_writer = kafka_writer
        
        logger.info("Event Collector Service started successfully")
        
    except Exception as e:
        logger.error(f"Failed to initialize Event Collector Service: {e}")
        raise
    
    yield
    
    # Shutdown
    logger.info("Shutting down Event Collector Service")
    
    if kafka_writer:
        try:
            await kafka_writer.close()
            logger.info("Kafka writer closed successfully")
        except Exception as e:
            logger.error(f"Error closing Kafka writer: {e}")


# Create FastAPI app
app = FastAPI(
    title="Event Collector Service (S2-14)",
    description="High-throughput event ingestion service with Kafka integration, backpressure handling, and DLQ support",
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
    allow_methods=["GET", "POST"],
    allow_headers=["*"],
)

app.add_middleware(GZipMiddleware, minimum_size=1000)


@app.middleware("http")
async def add_process_time_header(request: Request, call_next):
    """Add processing time header to responses."""
    start_time = time.time()
    response = await call_next(request)
    process_time = time.time() - start_time
    response.headers["X-Process-Time"] = str(process_time)
    return response


@app.middleware("http")
async def log_requests(request: Request, call_next):
    """Log incoming requests."""
    start_time = time.time()
    response = await call_next(request)
    process_time = time.time() - start_time
    
    logger.info(
        f"{request.method} {request.url.path} - "
        f"Status: {response.status_code} - "
        f"Time: {process_time:.3f}s"
    )
    return response


# Exception handlers
@app.exception_handler(HTTPException)
async def http_exception_handler(request: Request, exc: HTTPException):
    """Handle HTTP exceptions with structured error response."""
    error_response = ErrorResponse(
        error_code=f"HTTP_{exc.status_code}",
        error_message=exc.detail,
        timestamp=time.time(),
        request_id=request.headers.get("x-request-id", "unknown")
    )
    
    return JSONResponse(
        status_code=exc.status_code,
        content=error_response.model_dump()
    )


@app.exception_handler(500)
async def internal_server_error_handler(request: Request, exc: Exception):
    """Handle internal server errors."""
    logger.error(f"Internal server error: {exc}")
    
    error_response = ErrorResponse(
        error_code="INTERNAL_ERROR",
        error_message="Internal server error occurred",
        timestamp=time.time(),
        request_id=request.headers.get("x-request-id", "unknown")
    )
    
    return JSONResponse(
        status_code=500,
        content=error_response.model_dump()
    )


# Include routers
app.include_router(
    http_router,
    prefix="/api/v1",
    tags=["event-collection"]
)


# Root endpoint
@app.get("/")
async def root():
    """Root endpoint with service information."""
    return {
        "service": "Event Collector Service",
        "version": "1.0.0",
        "stage": "S2-14",
        "description": "High-throughput event ingestion with Kafka integration",
        "endpoints": {
            "collect": "/api/v1/collect",
            "health": "/api/v1/health",
            "metrics": "/api/v1/metrics",
            "docs": "/docs"
        }
    }


# Health check (also available at root level)
@app.get("/health")
async def simple_health():
    """Simple health check endpoint."""
    return {"status": "healthy", "service": "event-collector-svc"}


if __name__ == "__main__":
    # Development server
    uvicorn.run(
        "app.main:app",
        host="0.0.0.0",
        port=8000,
        reload=True,
        log_level="info"
    )
