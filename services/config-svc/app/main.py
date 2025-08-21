"""
Config Service - Feature Flags & Remote Configuration
Provides dynamic feature flagging with targeting rules for cohorts, tenants, and grade bands.
"""

from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager
import asyncio
import logging
import os
import uuid
import hashlib
from contextvars import ContextVar
from typing import Optional

import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.routes import router
from app.models import ConfigCache, FlagEvaluator

# OpenTelemetry imports
try:
    from opentelemetry import trace
    from opentelemetry.exporter.otlp.proto.grpc.trace_exporter import OTLPSpanExporter
    from opentelemetry.sdk.trace import TracerProvider
    from opentelemetry.sdk.trace.export import BatchSpanProcessor
    from opentelemetry.sdk.resources import Resource
    from opentelemetry.semconv.resource import ResourceAttributes
    from opentelemetry.instrumentation.fastapi import FastAPIInstrumentor
    from opentelemetry.trace import Status, StatusCode
    OTEL_AVAILABLE = True
except ImportError:
    OTEL_AVAILABLE = False
    print("OpenTelemetry not available - tracing disabled")

# Context variables for request correlation
session_id_context: ContextVar[Optional[str]] = ContextVar('session_id', default=None)
hashed_learner_id_context: ContextVar[Optional[str]] = ContextVar('hashed_learner_id', default=None)
user_role_context: ContextVar[Optional[str]] = ContextVar('user_role', default=None)
grade_band_context: ContextVar[Optional[str]] = ContextVar('grade_band', default=None)
tenant_id_context: ContextVar[Optional[str]] = ContextVar('tenant_id', default=None)


# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Service instance ID
SERVICE_INSTANCE_ID = f"config-svc-{os.getenv('HOSTNAME', 'unknown')}-{os.getpid()}-{str(uuid.uuid4())[:8]}"

def setup_tracing():
    """Initialize OpenTelemetry tracing"""
    if not OTEL_AVAILABLE:
        return None
        
    try:
        # Configure resource
        resource = Resource.create({
            ResourceAttributes.SERVICE_NAME: "config-svc",
            ResourceAttributes.SERVICE_VERSION: "1.0.0",
            ResourceAttributes.SERVICE_INSTANCE_ID: SERVICE_INSTANCE_ID,
            ResourceAttributes.DEPLOYMENT_ENVIRONMENT: os.getenv("ENVIRONMENT", "development"),
            "service.namespace": "aivo-virtual-brains",
        })
        
        # Set up tracer provider
        provider = TracerProvider(resource=resource)
        trace.set_tracer_provider(provider)
        
        # Configure OTLP exporter
        otlp_exporter = OTLPSpanExporter(
            endpoint=os.getenv("OTEL_EXPORTER_OTLP_ENDPOINT", "http://localhost:4317"),
        )
        
        # Add span processor
        span_processor = BatchSpanProcessor(otlp_exporter)
        provider.add_span_processor(span_processor)
        
        logger.info(f"OpenTelemetry initialized for config-svc, instance: {SERVICE_INSTANCE_ID}")
        return trace.get_tracer("config-svc", "1.0.0")
        
    except Exception as e:
        logger.error(f"Failed to initialize OpenTelemetry: {e}")
        return None

def hash_learner_id(learner_id: str) -> str:
    """Hash learner ID for privacy protection"""
    return hashlib.sha256(f"learner:{learner_id}".encode()).hexdigest()[:16]


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan management"""
    # Startup
    logger.info("🚀 Starting Config Service...")
    
    # Initialize tracing
    tracer = setup_tracing()
    app.state.tracer = tracer
    
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

# Add tracing middleware
@app.middleware("http")
async def tracing_middleware(request: Request, call_next):
    """Middleware to extract and set session/user context for tracing"""
    # Extract session and user context from headers
    session_id = request.headers.get("x-session-id")
    learner_id_hash = request.headers.get("x-learner-id-hash")
    user_role = request.headers.get("x-user-role")
    grade_band = request.headers.get("x-grade-band")
    tenant_id = request.headers.get("x-tenant-id")
    
    # Set context variables
    token_session = session_id_context.set(session_id)
    token_learner = hashed_learner_id_context.set(learner_id_hash)
    token_role = user_role_context.set(user_role)
    token_grade = grade_band_context.set(grade_band)
    token_tenant = tenant_id_context.set(tenant_id)
    
    try:
        # Add attributes to current span
        if OTEL_AVAILABLE:
            span = trace.get_current_span()
            if span and span.is_recording():
                span.set_attribute("service.instance.id", SERVICE_INSTANCE_ID)
                if session_id:
                    span.set_attribute("session.id", session_id)
                if learner_id_hash:
                    span.set_attribute("user.id.hashed", learner_id_hash)
                if user_role:
                    span.set_attribute("user.role", user_role)
                if grade_band:
                    span.set_attribute("user.grade_band", grade_band)
                if tenant_id:
                    span.set_attribute("tenant.id", tenant_id)
                    
        response = await call_next(request)
        return response
        
    finally:
        # Reset context variables
        session_id_context.reset(token_session)
        hashed_learner_id_context.reset(token_learner)
        user_role_context.reset(token_role)
        grade_band_context.reset(token_grade)
        tenant_id_context.reset(token_tenant)

# Instrument FastAPI if OpenTelemetry is available
if OTEL_AVAILABLE:
    FastAPIInstrumentor.instrument_app(
        app,
        excluded_urls="health,ready,metrics,favicon.ico",
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
