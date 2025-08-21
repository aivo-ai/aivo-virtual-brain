"""
User Service with OpenTelemetry tracing integration
Provides user management with session correlation and privacy-first observability
"""

from fastapi import FastAPI, HTTPException, Request, Depends
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager
import asyncio
import logging
import os
import uuid
import hashlib
from contextvars import ContextVar
from typing import Optional, Dict, Any
from pydantic import BaseModel

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
SERVICE_INSTANCE_ID = f"user-svc-{os.getenv('HOSTNAME', 'unknown')}-{os.getpid()}-{str(uuid.uuid4())[:8]}"

def setup_tracing():
    """Initialize OpenTelemetry tracing"""
    if not OTEL_AVAILABLE:
        return None
        
    try:
        # Configure resource
        resource = Resource.create({
            ResourceAttributes.SERVICE_NAME: "user-svc",
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
        
        logger.info(f"OpenTelemetry initialized for user-svc, instance: {SERVICE_INSTANCE_ID}")
        return trace.get_tracer("user-svc", "1.0.0")
        
    except Exception as e:
        logger.error(f"Failed to initialize OpenTelemetry: {e}")
        return None

def hash_learner_id(learner_id: str) -> str:
    """Hash learner ID for privacy protection"""
    return hashlib.sha256(f"learner:{learner_id}".encode()).hexdigest()[:16]

def trace_operation(operation_name: str, user_id: Optional[str] = None):
    """Decorator for tracing operations with user correlation"""
    def decorator(func):
        async def wrapper(*args, **kwargs):
            if not OTEL_AVAILABLE:
                return await func(*args, **kwargs)
                
            tracer = trace.get_tracer("user-svc")
            
            with tracer.start_as_current_span(operation_name) as span:
                try:
                    # Add operation attributes
                    span.set_attribute("operation.name", operation_name)
                    span.set_attribute("operation.function", func.__name__)
                    span.set_attribute("service.instance.id", SERVICE_INSTANCE_ID)
                    
                    # Add context attributes
                    session_id = session_id_context.get()
                    if session_id:
                        span.set_attribute("session.id", session_id)
                        
                    hashed_learner_id = hashed_learner_id_context.get()
                    if hashed_learner_id:
                        span.set_attribute("user.id.hashed", hashed_learner_id)
                        
                    if user_id:
                        span.set_attribute("user.id.hashed", hash_learner_id(user_id))
                    
                    # Execute function
                    result = await func(*args, **kwargs)
                    
                    span.set_status(Status(StatusCode.OK))
                    return result
                    
                except Exception as e:
                    span.record_exception(e)
                    span.set_status(Status(StatusCode.ERROR, str(e)))
                    
                    # Add error context with session correlation
                    session_id = session_id_context.get()
                    if session_id:
                        span.set_attribute("error.session.id", session_id)
                        
                    logger.error(f"Error in {operation_name}: {e}", extra={
                        "session_id": session_id,
                        "service_instance_id": SERVICE_INSTANCE_ID,
                        "operation": operation_name,
                    })
                    raise
                    
        return wrapper
    return decorator

# Pydantic models
class UserProfile(BaseModel):
    user_id: str
    email: str
    role: str
    grade_band: Optional[str] = None
    tenant_id: str
    preferences: Dict[str, Any] = {}

class UserCreate(BaseModel):
    email: str
    role: str
    grade_band: Optional[str] = None
    tenant_id: str

class UserUpdate(BaseModel):
    email: Optional[str] = None
    role: Optional[str] = None
    grade_band: Optional[str] = None
    preferences: Optional[Dict[str, Any]] = None

# Mock database
mock_users: Dict[str, UserProfile] = {}

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan management"""
    # Startup
    logger.info("🚀 Starting User Service...")
    
    # Initialize tracing
    tracer = setup_tracing()
    app.state.tracer = tracer
    
    # Initialize mock data
    mock_users["test-user-1"] = UserProfile(
        user_id="test-user-1",
        email="student@example.com",
        role="student",
        grade_band="6-8",
        tenant_id="school-district-1"
    )
    
    logger.info("✅ User service initialized")
    
    yield
    
    # Shutdown
    logger.info("🛑 Shutting down User Service...")
    logger.info("✅ Cleanup completed")

# Create FastAPI app
app = FastAPI(
    title="Aivo User Service",
    description="User management with privacy-first observability",
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

# Routes
@app.get("/health")
async def health_check():
    """Health check endpoint"""
    return {
        "status": "healthy",
        "service": "user-svc",
        "version": "1.0.0",
        "instance_id": SERVICE_INSTANCE_ID
    }

@app.get("/users/{user_id}", response_model=UserProfile)
@trace_operation("get_user")
async def get_user(user_id: str):
    """Get user profile by ID"""
    if user_id not in mock_users:
        raise HTTPException(status_code=404, detail="User not found")
    
    return mock_users[user_id]

@app.post("/users", response_model=UserProfile)
@trace_operation("create_user")
async def create_user(user_data: UserCreate):
    """Create new user"""
    user_id = f"user-{len(mock_users) + 1}"
    
    user = UserProfile(
        user_id=user_id,
        **user_data.dict()
    )
    
    mock_users[user_id] = user
    
    # Track user creation with hashed ID
    if OTEL_AVAILABLE:
        span = trace.get_current_span()
        if span:
            span.set_attribute("user.created.id.hashed", hash_learner_id(user_id))
            span.set_attribute("user.created.role", user_data.role)
            span.set_attribute("user.created.grade_band", user_data.grade_band or "unknown")
    
    return user

@app.put("/users/{user_id}", response_model=UserProfile)
@trace_operation("update_user")
async def update_user(user_id: str, user_data: UserUpdate):
    """Update user profile"""
    if user_id not in mock_users:
        raise HTTPException(status_code=404, detail="User not found")
    
    user = mock_users[user_id]
    
    # Update fields
    if user_data.email is not None:
        user.email = user_data.email
    if user_data.role is not None:
        user.role = user_data.role
    if user_data.grade_band is not None:
        user.grade_band = user_data.grade_band
    if user_data.preferences is not None:
        user.preferences.update(user_data.preferences)
    
    return user

@app.delete("/users/{user_id}")
@trace_operation("delete_user")
async def delete_user(user_id: str):
    """Delete user"""
    if user_id not in mock_users:
        raise HTTPException(status_code=404, detail="User not found")
    
    del mock_users[user_id]
    
    return {"status": "deleted", "user_id": user_id}

@app.get("/users/{user_id}/sessions")
@trace_operation("get_user_sessions")
async def get_user_sessions(user_id: str):
    """Get user session analytics (demo endpoint)"""
    if user_id not in mock_users:
        raise HTTPException(status_code=404, detail="User not found")
    
    # Mock session data for demonstration
    return {
        "user_id": user_id,
        "user_id_hashed": hash_learner_id(user_id),
        "active_sessions": 2,
        "last_activity": "2024-01-20T15:30:00Z",
        "session_duration_avg": "25m",
        "interactions_count": 47
    }

if __name__ == "__main__":
    import uvicorn
    
    # Get configuration from environment
    host = os.getenv("HOST", "0.0.0.0")
    port = int(os.getenv("PORT", "8081"))
    debug = os.getenv("DEBUG", "false").lower() == "true"
    
    uvicorn.run(
        "main:app",
        host=host,
        port=port,
        reload=debug,
        log_level="info"
    )
