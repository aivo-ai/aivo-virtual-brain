"""
AIVO Model Registry - FastAPI Application
S2-02 Implementation: Main application with API routes
"""

import os
from datetime import datetime
from typing import Optional
from contextlib import asynccontextmanager

from fastapi import FastAPI, Depends, HTTPException, Query, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from opentelemetry.instrumentation.fastapi import FastAPIInstrumentor
from opentelemetry.instrumentation.sqlalchemy import SQLAlchemyInstrumentor

from .database import create_all_tables, check_db_connection, engine
from .service import ModelRegistryService, get_model_registry_service
from .schemas import (
    # Model schemas
    ModelCreate, ModelUpdate, ModelResponse, ModelListResponse,
    # Version schemas  
    ModelVersionCreate, ModelVersionUpdate, ModelVersionResponse, ModelVersionListResponse,
    # Binding schemas
    ProviderBindingCreate, ProviderBindingUpdate, ProviderBindingResponse, ProviderBindingListResponse,
    # Filter schemas
    ModelFilterParams, ModelVersionFilterParams, ProviderBindingFilterParams,
    # Utility schemas
    RetentionPolicyRequest, RetentionStatsResponse, ModelStatsResponse,
    HealthCheckResponse
)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan management"""
    # Startup
    print("🚀 Starting AIVO Model Registry Service...")
    
    # Create database tables
    create_all_tables()
    
    # Check database connection
    if not check_db_connection():
        raise RuntimeError("Failed to connect to database")
    
    print("✅ Database connected and tables created")
    print("🔄 Model Registry Service is ready")
    
    yield
    
    # Shutdown
    print("🛑 Shutting down Model Registry Service...")


# Create FastAPI application
app = FastAPI(
    title="AIVO Model Registry",
    description="S2-02 Model lifecycle management with version tracking and provider bindings",
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

# Instrument with OpenTelemetry
FastAPIInstrumentor.instrument_app(app)
SQLAlchemyInstrumentor().instrument(engine=engine)


# Health check endpoint
@app.get("/health", response_model=HealthCheckResponse, tags=["Health"])
async def health_check(service: ModelRegistryService = Depends(get_model_registry_service)):
    """Health check endpoint"""
    try:
        stats = service.get_model_stats()
        
        return HealthCheckResponse(
            status="healthy",
            version="1.0.0",
            database_connected=True,
            model_count=stats.model_count,
            version_count=stats.version_count
        )
    except Exception as e:
        return HealthCheckResponse(
            status="unhealthy",
            version="1.0.0", 
            database_connected=False,
            model_count=0,
            version_count=0
        )


# Model endpoints
@app.post("/models", response_model=ModelResponse, status_code=status.HTTP_201_CREATED, tags=["Models"])
async def create_model(
    model_data: ModelCreate,
    service: ModelRegistryService = Depends(get_model_registry_service)
):
    """Create a new model"""
    return service.create_model(model_data)


@app.get("/models/{model_id}", response_model=ModelResponse, tags=["Models"])
async def get_model(
    model_id: int,
    service: ModelRegistryService = Depends(get_model_registry_service)
):
    """Get a model by ID"""
    return service.get_model(model_id)


@app.get("/models/name/{name}", response_model=ModelResponse, tags=["Models"])
async def get_model_by_name(
    name: str,
    service: ModelRegistryService = Depends(get_model_registry_service)
):
    """Get a model by name"""
    return service.get_model_by_name(name)


@app.get("/models", response_model=ModelListResponse, tags=["Models"])
async def list_models(
    task: Optional[str] = Query(None, description="Filter by task type"),
    subject: Optional[str] = Query(None, description="Filter by subject"),
    name_contains: Optional[str] = Query(None, description="Filter by name substring"),
    page: int = Query(1, ge=1, description="Page number"),
    size: int = Query(20, ge=1, le=100, description="Page size"),
    service: ModelRegistryService = Depends(get_model_registry_service)
):
    """List models with filtering and pagination"""
    filters = ModelFilterParams(
        task=task,
        subject=subject,
        name_contains=name_contains
    )
    return service.list_models(filters, page, size)


@app.put("/models/{model_id}", response_model=ModelResponse, tags=["Models"])
async def update_model(
    model_id: int,
    update_data: ModelUpdate,
    service: ModelRegistryService = Depends(get_model_registry_service)
):
    """Update a model"""
    return service.update_model(model_id, update_data)


@app.delete("/models/{model_id}", tags=["Models"])
async def delete_model(
    model_id: int,
    service: ModelRegistryService = Depends(get_model_registry_service)
):
    """Delete a model and all its versions"""
    return service.delete_model(model_id)


# Model version endpoints
@app.post("/versions", response_model=ModelVersionResponse, status_code=status.HTTP_201_CREATED, tags=["Versions"])
async def create_model_version(
    version_data: ModelVersionCreate,
    service: ModelRegistryService = Depends(get_model_registry_service)
):
    """Create a new model version"""
    return service.create_model_version(version_data)


@app.get("/versions/{version_id}", response_model=ModelVersionResponse, tags=["Versions"])
async def get_model_version(
    version_id: int,
    service: ModelRegistryService = Depends(get_model_registry_service)
):
    """Get a model version by ID"""
    return service.get_model_version(version_id)


@app.get("/versions", response_model=ModelVersionListResponse, tags=["Versions"])
async def list_model_versions(
    model_id: Optional[int] = Query(None, description="Filter by model ID"),
    region: Optional[str] = Query(None, description="Filter by region"),
    min_eval_score: Optional[float] = Query(None, ge=0, le=1, description="Minimum eval score"),
    max_cost_per_1k: Optional[float] = Query(None, ge=0, description="Maximum cost per 1K"),
    slo_ok: Optional[bool] = Query(None, description="Filter by SLO compliance"),
    include_archived: bool = Query(False, description="Include archived versions"),
    page: int = Query(1, ge=1, description="Page number"),
    size: int = Query(20, ge=1, le=100, description="Page size"),
    service: ModelRegistryService = Depends(get_model_registry_service)
):
    """List model versions with filtering and pagination"""
    filters = ModelVersionFilterParams(
        model_id=model_id,
        region=region,
        min_eval_score=min_eval_score,
        max_cost_per_1k=max_cost_per_1k,
        slo_ok=slo_ok,
        include_archived=include_archived
    )
    return service.list_model_versions(filters, page, size)


@app.put("/versions/{version_id}", response_model=ModelVersionResponse, tags=["Versions"])
async def update_model_version(
    version_id: int,
    update_data: ModelVersionUpdate,
    service: ModelRegistryService = Depends(get_model_registry_service)
):
    """Update a model version"""
    return service.update_model_version(version_id, update_data)


@app.delete("/versions/{version_id}", tags=["Versions"])
async def delete_model_version(
    version_id: int,
    service: ModelRegistryService = Depends(get_model_registry_service)
):
    """Delete a model version"""
    return service.delete_model_version(version_id)


# Provider binding endpoints
@app.post("/bindings", response_model=ProviderBindingResponse, status_code=status.HTTP_201_CREATED, tags=["Bindings"])
async def create_provider_binding(
    binding_data: ProviderBindingCreate,
    service: ModelRegistryService = Depends(get_model_registry_service)
):
    """Create a new provider binding"""
    return service.create_provider_binding(binding_data)


@app.get("/bindings/{binding_id}", response_model=ProviderBindingResponse, tags=["Bindings"])
async def get_provider_binding(
    binding_id: int,
    service: ModelRegistryService = Depends(get_model_registry_service)
):
    """Get a provider binding by ID"""
    return service.get_provider_binding(binding_id)


@app.get("/bindings", response_model=ProviderBindingListResponse, tags=["Bindings"])
async def list_provider_bindings(
    version_id: Optional[int] = Query(None, description="Filter by version ID"),
    provider: Optional[str] = Query(None, description="Filter by provider"),
    status: Optional[str] = Query(None, description="Filter by status"),
    min_success_rate: Optional[float] = Query(None, ge=0, le=1, description="Minimum success rate"),
    page: int = Query(1, ge=1, description="Page number"),
    size: int = Query(20, ge=1, le=100, description="Page size"),
    service: ModelRegistryService = Depends(get_model_registry_service)
):
    """List provider bindings with filtering and pagination"""
    filters = ProviderBindingFilterParams(
        version_id=version_id,
        provider=provider,
        status=status,
        min_success_rate=min_success_rate
    )
    return service.list_provider_bindings(filters, page, size)


@app.put("/bindings/{binding_id}", response_model=ProviderBindingResponse, tags=["Bindings"])
async def update_provider_binding(
    binding_id: int,
    update_data: ProviderBindingUpdate,
    service: ModelRegistryService = Depends(get_model_registry_service)
):
    """Update a provider binding"""
    return service.update_provider_binding(binding_id, update_data)


@app.delete("/bindings/{binding_id}", tags=["Bindings"])
async def delete_provider_binding(
    binding_id: int,
    service: ModelRegistryService = Depends(get_model_registry_service)
):
    """Delete a provider binding"""
    return service.delete_provider_binding(binding_id)


# Retention policy endpoints
@app.post("/retention/apply", tags=["Retention"])
async def apply_retention_policy(
    request: RetentionPolicyRequest,
    service: ModelRegistryService = Depends(get_model_registry_service)
):
    """Apply retention policy to a model"""
    return service.apply_retention_policy(request)


@app.get("/retention/stats", response_model=RetentionStatsResponse, tags=["Retention"])
async def get_retention_stats(
    model_id: Optional[int] = Query(None, description="Model ID for specific stats"),
    service: ModelRegistryService = Depends(get_model_registry_service)
):
    """Get retention statistics"""
    return service.get_retention_stats(model_id)


# Statistics endpoints
@app.get("/stats", response_model=ModelStatsResponse, tags=["Statistics"])
async def get_model_stats(service: ModelRegistryService = Depends(get_model_registry_service)):
    """Get overall model registry statistics"""
    return service.get_model_stats()


# Model-specific version endpoints
@app.get("/models/{model_id}/versions", response_model=ModelVersionListResponse, tags=["Models"])
async def list_versions_for_model(
    model_id: int,
    include_archived: bool = Query(False, description="Include archived versions"),
    page: int = Query(1, ge=1, description="Page number"),
    size: int = Query(20, ge=1, le=100, description="Page size"),
    service: ModelRegistryService = Depends(get_model_registry_service)
):
    """List all versions for a specific model"""
    filters = ModelVersionFilterParams(
        model_id=model_id,
        include_archived=include_archived
    )
    return service.list_model_versions(filters, page, size)


@app.post("/models/{model_id}/retention", tags=["Models"])
async def apply_model_retention_policy(
    model_id: int,
    retention_count: int = Query(3, ge=1, le=10, description="Number of versions to keep"),
    service: ModelRegistryService = Depends(get_model_registry_service)
):
    """Apply retention policy to a specific model"""
    request = RetentionPolicyRequest(
        model_id=model_id,
        retention_count=retention_count
    )
    return service.apply_retention_policy(request)


# Version-specific binding endpoints
@app.get("/versions/{version_id}/bindings", response_model=ProviderBindingListResponse, tags=["Versions"])
async def list_bindings_for_version(
    version_id: int,
    page: int = Query(1, ge=1, description="Page number"),
    size: int = Query(20, ge=1, le=100, description="Page size"),
    service: ModelRegistryService = Depends(get_model_registry_service)
):
    """List all provider bindings for a specific version"""
    filters = ProviderBindingFilterParams(version_id=version_id)
    return service.list_provider_bindings(filters, page, size)


# Exception handlers
@app.exception_handler(HTTPException)
async def http_exception_handler(request, exc: HTTPException):
    """Handle HTTP exceptions"""
    return JSONResponse(
        status_code=exc.status_code,
        content={
            "error": exc.detail,
            "status_code": exc.status_code,
            "timestamp": datetime.now().isoformat()
        }
    )


@app.exception_handler(ValueError)
async def value_error_handler(request, exc: ValueError):
    """Handle validation errors"""
    return JSONResponse(
        status_code=400,
        content={
            "error": str(exc),
            "status_code": 400,
            "timestamp": datetime.now().isoformat()
        }
    )


@app.exception_handler(Exception)
async def general_exception_handler(request, exc: Exception):
    """Handle general exceptions"""
    return JSONResponse(
        status_code=500,
        content={
            "error": "Internal server error",
            "status_code": 500,
            "timestamp": datetime.now().isoformat()
        }
    )


if __name__ == "__main__":
    import uvicorn
    
    port = int(os.getenv("PORT", "8003"))
    host = os.getenv("HOST", "0.0.0.0")
    
    uvicorn.run(
        "app.main:app",
        host=host,
        port=port,
        reload=os.getenv("ENVIRONMENT") == "development",
        log_level="info"
    )
