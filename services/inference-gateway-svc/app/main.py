"""
AIVO Inference Gateway - Main Application
S2-01 Implementation: FastAPI app with multi-provider inference, PII scrub, routing
"""

import os
import sys
import time
import logging
from contextlib import asynccontextmanager
from typing import Dict, Any, Optional

from fastapi import FastAPI, HTTPException, Request, Depends
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.trustedhost import TrustedHostMiddleware
from fastapi.responses import JSONResponse
from opentelemetry import trace
from opentelemetry.exporter.otlp.proto.grpc.trace_exporter import OTLPSpanExporter
from opentelemetry.instrumentation.fastapi import FastAPIInstrumentor
from opentelemetry.instrumentation.httpx import HTTPXInstrumentor
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import BatchSpanProcessor
from opentelemetry.sdk.resources import Resource

from .providers.base import ProviderType
from .providers.openai import OpenAIProvider
from .providers.vertex_gemini import VertexGeminiProvider
from .providers.bedrock_anthropic import BedrockAnthropicProvider
from .policy import PolicyEngine
from .pii import PIIScrubber, DEFAULT_CONFIG as DEFAULT_PII_CONFIG
from .routers import generate, embed, moderate, checkpoints

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)

# Global state
providers: Dict[ProviderType, Any] = {}
policy_engine: Optional[PolicyEngine] = None
pii_scrubber: Optional[PIIScrubber] = None


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan manager"""
    # Startup
    logger.info("Starting AIVO Inference Gateway...")
    
    # Initialize OpenTelemetry
    await initialize_telemetry()
    
    # Initialize providers
    await initialize_providers()
    
    # Initialize policy engine
    await initialize_policy_engine()
    
    # Initialize PII scrubber
    await initialize_pii_scrubber()
    
    # Initialize router services
    await initialize_router_services()
    
    logger.info("AIVO Inference Gateway started successfully")
    
    yield
    
    # Shutdown
    logger.info("Shutting down AIVO Inference Gateway...")
    
    # Cleanup providers
    for provider in providers.values():
        try:
            if hasattr(provider, '_client'):
                await provider._client.aclose()
        except:
            pass
    
    logger.info("AIVO Inference Gateway shut down")


async def initialize_telemetry():
    """Initialize OpenTelemetry tracing"""
    try:
        # Configure resource
        resource = Resource.create({
            "service.name": "aivo-inference-gateway",
            "service.version": "1.0.0",
            "deployment.environment": os.getenv("ENVIRONMENT", "development")
        })
        
        # Configure tracer provider
        tracer_provider = TracerProvider(resource=resource)
        trace.set_tracer_provider(tracer_provider)
        
        # Configure OTLP exporter if endpoint is provided
        otlp_endpoint = os.getenv("OTLP_ENDPOINT")
        if otlp_endpoint:
            otlp_exporter = OTLPSpanExporter(endpoint=otlp_endpoint, insecure=True)
            span_processor = BatchSpanProcessor(otlp_exporter)
            tracer_provider.add_span_processor(span_processor)
            logger.info(f"Configured OTLP exporter: {otlp_endpoint}")
        
        logger.info("OpenTelemetry initialized")
    
    except Exception as e:
        logger.warning(f"Failed to initialize OpenTelemetry: {e}")


async def initialize_providers():
    """Initialize AI providers"""
    global providers
    
    # OpenAI Provider (default)
    openai_key = os.getenv("OPENAI_API_KEY")
    if openai_key:
        try:
            openai_provider = OpenAIProvider(
                api_key=openai_key,
                config={
                    "base_url": os.getenv("OPENAI_BASE_URL", "https://api.openai.com/v1"),
                    "organization": os.getenv("OPENAI_ORGANIZATION"),
                    "timeout": int(os.getenv("OPENAI_TIMEOUT", "60"))
                }
            )
            await openai_provider.initialize()
            providers[ProviderType.OPENAI] = openai_provider
            logger.info("OpenAI provider initialized")
        except Exception as e:
            logger.error(f"Failed to initialize OpenAI provider: {e}")
    
    # Vertex AI Provider (behind feature flag)
    if os.getenv("ENABLE_VERTEX", "false").lower() == "true":
        vertex_project = os.getenv("VERTEX_PROJECT")
        vertex_location = os.getenv("VERTEX_LOCATION", "us-central1")
        
        if vertex_project:
            try:
                vertex_provider = VertexGeminiProvider(
                    api_key="",  # Uses service account authentication
                    config={
                        "project_id": vertex_project,
                        "location": vertex_location,
                        "service_account_path": os.getenv("VERTEX_SERVICE_ACCOUNT_PATH")
                    }
                )
                await vertex_provider.initialize()
                providers[ProviderType.VERTEX_GEMINI] = vertex_provider
                logger.info("Vertex AI provider initialized")
            except Exception as e:
                logger.error(f"Failed to initialize Vertex AI provider: {e}")
    
    # Bedrock Provider (behind feature flag)
    if os.getenv("ENABLE_BEDROCK", "false").lower() == "true":
        bedrock_access_key = os.getenv("AWS_ACCESS_KEY_ID")
        bedrock_secret_key = os.getenv("AWS_SECRET_ACCESS_KEY")
        
        if bedrock_access_key and bedrock_secret_key:
            try:
                bedrock_provider = BedrockAnthropicProvider(
                    api_key=bedrock_secret_key,
                    config={
                        "access_key": bedrock_access_key,
                        "region": os.getenv("AWS_REGION", "us-east-1")
                    }
                )
                await bedrock_provider.initialize()
                providers[ProviderType.BEDROCK_ANTHROPIC] = bedrock_provider
                logger.info("Bedrock provider initialized")
            except Exception as e:
                logger.error(f"Failed to initialize Bedrock provider: {e}")
    
    if not providers:
        raise RuntimeError("No providers initialized. Check environment variables.")
    
    logger.info(f"Initialized {len(providers)} provider(s): {list(providers.keys())}")


async def initialize_policy_engine():
    """Initialize policy engine"""
    global policy_engine
    
    # Load policy configuration
    policy_config = {
        "routing_policies": [
            {
                "subject_pattern": "enterprise/*",
                "preferred_providers": ["openai", "vertex_gemini"],
                "fallback_providers": ["bedrock_anthropic"],
                "strategy": "least_latency",
                "sla_tiers": ["premium", "enterprise"]
            },
            {
                "subject_pattern": "research/*", 
                "preferred_providers": ["vertex_gemini", "bedrock_anthropic"],
                "fallback_providers": ["openai"],
                "strategy": "lowest_cost"
            }
        ]
    }
    
    policy_engine = PolicyEngine(config=policy_config)
    logger.info("Policy engine initialized")


async def initialize_pii_scrubber():
    """Initialize PII scrubber"""
    global pii_scrubber
    
    # Load PII configuration
    pii_config = DEFAULT_PII_CONFIG.copy()
    
    # Override with environment settings
    if os.getenv("PII_SCRUB_MODE"):
        pii_config["scrub_mode"] = os.getenv("PII_SCRUB_MODE")
    
    pii_scrubber = PIIScrubber(config=pii_config)
    logger.info("PII scrubber initialized")


async def initialize_router_services():
    """Initialize router service dependencies"""
    # Initialize generation service
    generate.generation_service = generate.GenerationService(
        providers=providers,
        policy_engine=policy_engine,
        pii_scrubber=pii_scrubber
    )
    
    # Initialize embedding service
    embed.embedding_service = embed.EmbeddingService(
        providers=providers,
        policy_engine=policy_engine,
        pii_scrubber=pii_scrubber
    )
    
    # Initialize moderation service
    moderate.moderation_service = moderate.ModerationService(
        providers=providers,
        policy_engine=policy_engine
    )
    
    logger.info("Router services initialized")


# Create FastAPI app
app = FastAPI(
    title="AIVO Inference Gateway",
    description="Multi-provider AI inference service with PII scrubbing and intelligent routing",
    version="2.0.1",
    docs_url="/docs",
    redoc_url="/redoc",
    lifespan=lifespan
)

# Configure CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=os.getenv("ALLOWED_ORIGINS", "*").split(","),
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE"],
    allow_headers=["*"],
)

# Configure trusted hosts
if os.getenv("TRUSTED_HOSTS"):
    app.add_middleware(
        TrustedHostMiddleware,
        allowed_hosts=os.getenv("TRUSTED_HOSTS").split(",")
    )


@app.middleware("http")
async def request_logging_middleware(request: Request, call_next):
    """Log all requests with timing"""
    start_time = time.time()
    
    # Generate request ID if not provided
    request_id = request.headers.get("x-request-id", f"req_{int(time.time())}")
    
    logger.info(f"Request {request_id}: {request.method} {request.url.path}")
    
    # Add request ID to response headers
    response = await call_next(request)
    response.headers["x-request-id"] = request_id
    
    # Log completion
    duration = time.time() - start_time
    logger.info(f"Request {request_id} completed in {duration:.3f}s - Status: {response.status_code}")
    
    return response


@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    """Global exception handler"""
    request_id = request.headers.get("x-request-id", "unknown")
    logger.error(f"Request {request_id} failed with exception: {type(exc).__name__}: {str(exc)}")
    
    if isinstance(exc, HTTPException):
        return JSONResponse(
            status_code=exc.status_code,
            content={
                "error": exc.detail,
                "request_id": request_id,
                "type": "http_exception"
            }
        )
    
    return JSONResponse(
        status_code=500,
        content={
            "error": "Internal server error",
            "request_id": request_id,
            "type": "internal_error"
        }
    )


# Include routers
app.include_router(generate.router)
app.include_router(embed.router) 
app.include_router(moderate.router)
app.include_router(checkpoints.router)


@app.get("/")
async def root():
    """Root endpoint"""
    return {
        "service": "AIVO Inference Gateway",
        "version": "2.0.1",
        "description": "Multi-provider AI inference with PII scrubbing and intelligent routing",
        "endpoints": {
            "generation": "/v1/generate/chat/completions",
            "embeddings": "/v1/embeddings", 
            "moderation": "/v1/moderations",
            "checkpoints": "/v1/checkpoints/{learner_id}/{subject}",
            "health": "/health",
            "metrics": "/metrics"
        }
    }


@app.get("/health")
async def health_check():
    """Service health check"""
    # Check provider health
    provider_status = {}
    healthy_providers = 0
    
    for ptype, provider in providers.items():
        try:
            is_healthy = await provider.health_check()
            provider_status[ptype.value] = "healthy" if is_healthy else "unhealthy"
            if is_healthy:
                healthy_providers += 1
        except:
            provider_status[ptype.value] = "unhealthy"
    
    overall_healthy = healthy_providers > 0
    
    return {
        "status": "healthy" if overall_healthy else "degraded",
        "timestamp": time.time(),
        "providers": provider_status,
        "healthy_providers": healthy_providers,
        "total_providers": len(providers),
        "policy_engine": "healthy" if policy_engine else "unavailable",
        "pii_scrubber": "healthy" if pii_scrubber else "unavailable"
    }


@app.get("/metrics")
async def get_metrics():
    """Get service metrics"""
    if not policy_engine:
        raise HTTPException(status_code=503, detail="Policy engine not available")
    
    return {
        "provider_health": policy_engine.get_provider_health_status(),
        "timestamp": time.time()
    }


@app.get("/providers")
async def list_providers():
    """List available providers and their status"""
    provider_info = {}
    
    for ptype, provider in providers.items():
        try:
            health = await provider.health_check()
            provider_info[ptype.value] = {
                "type": ptype.value,
                "healthy": health,
                "models_supported": getattr(provider, 'SUPPORTED_MODELS', []),
                "features": {
                    "generation": True,
                    "streaming": True,
                    "embeddings": hasattr(provider, 'embed'),
                    "moderation": hasattr(provider, 'moderate')
                }
            }
        except:
            provider_info[ptype.value] = {
                "type": ptype.value,
                "healthy": False,
                "error": "Health check failed"
            }
    
    return {
        "providers": provider_info,
        "count": len(provider_info)
    }


# Configure telemetry instrumentation
if __name__ == "__main__":
    # Auto-instrument FastAPI and httpx
    FastAPIInstrumentor.instrument_app(app)
    HTTPXInstrumentor().instrument()
    
    import uvicorn
    uvicorn.run(
        app,
        host="0.0.0.0",
        port=int(os.getenv("PORT", "8000")),
        log_level="info"
    )
