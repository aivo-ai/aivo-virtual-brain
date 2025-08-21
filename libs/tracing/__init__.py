"""
OpenTelemetry tracing utilities for microservices
Provides consistent service instance IDs and session correlation
"""

import os
import uuid
import hashlib
from typing import Optional, Dict, Any
from contextvars import ContextVar
from opentelemetry import trace, context
from opentelemetry.exporter.otlp.proto.grpc.trace_exporter import OTLPSpanExporter
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import BatchSpanProcessor
from opentelemetry.sdk.resources import Resource
from opentelemetry.semconv.resource import ResourceAttributes
from opentelemetry.instrumentation.fastapi import FastAPIInstrumentor
from opentelemetry.instrumentation.httpx import HTTPXClientInstrumentor
from opentelemetry.instrumentation.psycopg2 import Psycopg2Instrumentor
from opentelemetry.instrumentation.redis import RedisInstrumentor
from opentelemetry.propagate import set_global_textmap
from opentelemetry.propagators.b3 import B3MultiFormat
from opentelemetry.trace import Status, StatusCode
from fastapi import Request
import logging

logger = logging.getLogger(__name__)

# Context variables for request-scoped data
session_id_context: ContextVar[Optional[str]] = ContextVar('session_id', default=None)
hashed_learner_id_context: ContextVar[Optional[str]] = ContextVar('hashed_learner_id', default=None)
user_role_context: ContextVar[Optional[str]] = ContextVar('user_role', default=None)
grade_band_context: ContextVar[Optional[str]] = ContextVar('grade_band', default=None)
tenant_id_context: ContextVar[Optional[str]] = ContextVar('tenant_id', default=None)

class ServiceTracing:
    """Centralized tracing configuration for microservices"""
    
    def __init__(self, service_name: str, service_version: str = "1.0.0"):
        self.service_name = service_name
        self.service_version = service_version
        self.service_instance_id = self._generate_instance_id()
        self.tracer = None
        
    def setup_tracing(self) -> None:
        """Initialize OpenTelemetry tracing"""
        try:
            # Configure resource
            resource = Resource.create({
                ResourceAttributes.SERVICE_NAME: self.service_name,
                ResourceAttributes.SERVICE_VERSION: self.service_version,
                ResourceAttributes.SERVICE_INSTANCE_ID: self.service_instance_id,
                ResourceAttributes.DEPLOYMENT_ENVIRONMENT: os.getenv("ENVIRONMENT", "development"),
                "service.namespace": "aivo-virtual-brains",
            })
            
            # Set up tracer provider
            provider = TracerProvider(resource=resource)
            trace.set_tracer_provider(provider)
            
            # Configure OTLP exporter
            otlp_exporter = OTLPSpanExporter(
                endpoint=os.getenv("OTEL_EXPORTER_OTLP_ENDPOINT", "http://localhost:4317"),
                headers=self._get_auth_headers(),
            )
            
            # Add span processor
            span_processor = BatchSpanProcessor(
                otlp_exporter,
                export_timeout_millis=5000,
                schedule_delay_millis=1000,
                max_export_batch_size=50,
            )
            provider.add_span_processor(span_processor)
            
            # Set up propagators
            set_global_textmap(B3MultiFormat())
            
            # Get tracer
            self.tracer = trace.get_tracer(self.service_name, self.service_version)
            
            logger.info(f"OpenTelemetry initialized for {self.service_name}", extra={
                "service_instance_id": self.service_instance_id
            })
            
        except Exception as e:
            logger.error(f"Failed to initialize OpenTelemetry: {e}")
            
    def instrument_fastapi(self, app) -> None:
        """Instrument FastAPI application"""
        try:
            FastAPIInstrumentor.instrument_app(
                app,
                tracer_provider=trace.get_tracer_provider(),
                excluded_urls="health,metrics,favicon.ico",
            )
            
            # Add custom middleware for session/user context
            @app.middleware("http")
            async def tracing_middleware(request: Request, call_next):
                # Extract session and user context from headers
                session_id = request.headers.get("x-session-id")
                hashed_learner_id = request.headers.get("x-learner-id-hash")
                user_role = request.headers.get("x-user-role")
                grade_band = request.headers.get("x-grade-band")
                tenant_id = request.headers.get("x-tenant-id")
                
                # Set context variables
                token_session = session_id_context.set(session_id)
                token_learner = hashed_learner_id_context.set(hashed_learner_id)
                token_role = user_role_context.set(user_role)
                token_grade = grade_band_context.set(grade_band)
                token_tenant = tenant_id_context.set(tenant_id)
                
                try:
                    # Add attributes to current span
                    span = trace.get_current_span()
                    if span and span.is_recording():
                        self._add_context_attributes(span)
                        
                    response = await call_next(request)
                    return response
                    
                finally:
                    # Reset context variables
                    session_id_context.reset(token_session)
                    hashed_learner_id_context.reset(token_learner)
                    user_role_context.reset(token_role)
                    grade_band_context.reset(token_grade)
                    tenant_id_context.reset(token_tenant)
                    
            logger.info(f"FastAPI instrumentation enabled for {self.service_name}")
            
        except Exception as e:
            logger.error(f"Failed to instrument FastAPI: {e}")
            
    def instrument_dependencies(self) -> None:
        """Instrument common dependencies"""
        try:
            # HTTP client instrumentation
            HTTPXClientInstrumentor().instrument()
            
            # Database instrumentation
            if os.getenv("DATABASE_URL"):
                Psycopg2Instrumentor().instrument()
                
            # Redis instrumentation
            if os.getenv("REDIS_URL"):
                RedisInstrumentor().instrument()
                
            logger.info("Dependency instrumentation enabled")
            
        except Exception as e:
            logger.error(f"Failed to instrument dependencies: {e}")
            
    def create_span(self, name: str, attributes: Optional[Dict[str, Any]] = None) -> trace.Span:
        """Create a new span with service context"""
        if not self.tracer:
            return trace.NonRecordingSpan(trace.SpanContext(0, 0, False))
            
        span = self.tracer.start_span(name)
        
        if span.is_recording():
            # Add service instance ID
            span.set_attribute("service.instance.id", self.service_instance_id)
            
            # Add context attributes
            self._add_context_attributes(span)
            
            # Add custom attributes
            if attributes:
                for key, value in attributes.items():
                    if value is not None:
                        span.set_attribute(key, str(value))
                        
        return span
        
    def trace_error(self, span: trace.Span, error: Exception, context_data: Optional[Dict[str, Any]] = None) -> None:
        """Record an error in a span with session correlation"""
        if not span.is_recording():
            return
            
        # Record exception
        span.record_exception(error)
        span.set_status(Status(StatusCode.ERROR, str(error)))
        
        # Add error context
        span.set_attribute("error.type", type(error).__name__)
        span.set_attribute("error.message", str(error))
        
        # Add session correlation for error tracking
        session_id = session_id_context.get()
        if session_id:
            span.set_attribute("error.session.id", session_id)
            
        # Add custom context
        if context_data:
            for key, value in context_data.items():
                if value is not None:
                    span.set_attribute(f"error.{key}", str(value))
                    
        logger.error(f"Error traced in {self.service_name}: {error}", extra={
            "session_id": session_id,
            "service_instance_id": self.service_instance_id,
            "error_type": type(error).__name__,
        })
        
    def _add_context_attributes(self, span: trace.Span) -> None:
        """Add context attributes to a span"""
        if not span.is_recording():
            return
            
        # Service instance
        span.set_attribute("service.instance.id", self.service_instance_id)
        
        # Session context
        session_id = session_id_context.get()
        if session_id:
            span.set_attribute("session.id", session_id)
            
        # User context (hashed for privacy)
        hashed_learner_id = hashed_learner_id_context.get()
        if hashed_learner_id:
            span.set_attribute("user.id.hashed", hashed_learner_id)
            
        user_role = user_role_context.get()
        if user_role:
            span.set_attribute("user.role", user_role)
            
        grade_band = grade_band_context.get()
        if grade_band:
            span.set_attribute("user.grade_band", grade_band)
            
        tenant_id = tenant_id_context.get()
        if tenant_id:
            span.set_attribute("tenant.id", tenant_id)
            
    def _generate_instance_id(self) -> str:
        """Generate unique service instance ID"""
        hostname = os.getenv("HOSTNAME", "unknown")
        pid = os.getpid()
        random_part = str(uuid.uuid4())[:8]
        return f"{self.service_name}-{hostname}-{pid}-{random_part}"
        
    def _get_auth_headers(self) -> Dict[str, str]:
        """Get authentication headers for OTLP exporter"""
        headers = {}
        
        # Add authentication if configured
        if os.getenv("OTEL_EXPORTER_OTLP_HEADERS"):
            headers.update(dict(
                item.split("=", 1) 
                for item in os.getenv("OTEL_EXPORTER_OTLP_HEADERS", "").split(",")
                if "=" in item
            ))
            
        return headers

# Utility functions for session/user correlation
def hash_learner_id(learner_id: str) -> str:
    """Hash learner ID for privacy protection"""
    return hashlib.sha256(f"learner:{learner_id}".encode()).hexdigest()[:16]

def set_session_context(session_id: str, hashed_learner_id: Optional[str] = None, 
                       user_role: Optional[str] = None, grade_band: Optional[str] = None,
                       tenant_id: Optional[str] = None) -> None:
    """Set session context for current request"""
    session_id_context.set(session_id)
    if hashed_learner_id:
        hashed_learner_id_context.set(hashed_learner_id)
    if user_role:
        user_role_context.set(user_role)
    if grade_band:
        grade_band_context.set(grade_band)
    if tenant_id:
        tenant_id_context.set(tenant_id)

def get_session_context() -> Dict[str, Optional[str]]:
    """Get current session context"""
    return {
        "session_id": session_id_context.get(),
        "hashed_learner_id": hashed_learner_id_context.get(),
        "user_role": user_role_context.get(),
        "grade_band": grade_band_context.get(),
        "tenant_id": tenant_id_context.get(),
    }

def trace_operation(operation_name: str):
    """Decorator for tracing operations"""
    def decorator(func):
        def wrapper(*args, **kwargs):
            # Get tracer from current span context
            tracer = trace.get_tracer(__name__)
            
            with tracer.start_as_current_span(operation_name) as span:
                try:
                    # Add operation attributes
                    span.set_attribute("operation.name", operation_name)
                    span.set_attribute("operation.function", func.__name__)
                    
                    # Execute function
                    result = func(*args, **kwargs)
                    
                    span.set_status(Status(StatusCode.OK))
                    return result
                    
                except Exception as e:
                    span.record_exception(e)
                    span.set_status(Status(StatusCode.ERROR, str(e)))
                    raise
                    
        return wrapper
    return decorator
