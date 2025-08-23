"""
Tenant Service - SCIM 2.0 Provider

FastAPI application providing SCIM 2.0 endpoints for user and group management
with SIS integration capabilities.
"""

import uvicorn
from fastapi import FastAPI, Request, Response
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from contextlib import asynccontextmanager

from app.database import init_db
from app.routes.scim import users_router, groups_router, schemas_router
from app.routes import auth
from app.config import get_settings

settings = get_settings()


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan manager."""
    # Startup
    init_db()
    yield
    # Shutdown
    pass


# Create FastAPI application
app = FastAPI(
    title="Tenant Service - SCIM 2.0 Provider",
    description="SCIM 2.0 compliant user and group provisioning API with SIS integration",
    version="1.0.0",
    docs_url="/docs" if settings.environment != "production" else None,
    redoc_url="/redoc" if settings.environment != "production" else None,
    lifespan=lifespan
)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.allowed_origins,
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "PATCH", "DELETE", "OPTIONS"],
    allow_headers=["*"],
)


# Health check endpoint
@app.get("/health")
async def health_check():
    """Health check endpoint."""
    return {"status": "healthy", "service": "tenant-svc"}


# SCIM Service Provider Configuration
@app.get("/.well-known/scim_configuration")
async def scim_well_known(request: Request):
    """SCIM well-known configuration endpoint."""
    base_url = f"{request.url.scheme}://{request.url.netloc}"
    
    return {
        "issuer": base_url,
        "scim_endpoint": f"{base_url}/scim/v2",
        "authorization_endpoint": f"{base_url}/oauth/authorize",
        "token_endpoint": f"{base_url}/oauth/token",
        "supported_schemas": [
            "urn:ietf:params:scim:schemas:core:2.0:User",
            "urn:ietf:params:scim:schemas:core:2.0:Group",
            "urn:ietf:params:scim:schemas:extension:enterprise:2.0:User"
        ],
        "supported_operations": [
            "GET", "POST", "PUT", "PATCH", "DELETE"
        ],
        "filter_support": {
            "supported": True,
            "max_results": 200
        },
        "sort_support": {
            "supported": True
        },
        "patch_support": {
            "supported": True
        },
        "bulk_support": {
            "supported": False
        },
        "etag_support": {
            "supported": True
        }
    }


# Error handlers
@app.exception_handler(404)
async def not_found_handler(request: Request, exc):
    """Handle 404 errors with SCIM format."""
    return JSONResponse(
        status_code=404,
        content={
            "schemas": ["urn:ietf:params:scim:api:messages:2.0:Error"],
            "status": "404",
            "detail": "Resource not found"
        }
    )


@app.exception_handler(500)
async def internal_error_handler(request: Request, exc):
    """Handle 500 errors with SCIM format."""
    return JSONResponse(
        status_code=500,
        content={
            "schemas": ["urn:ietf:params:scim:api:messages:2.0:Error"],
            "status": "500",
            "detail": "Internal server error"
        }
    )


# Include SCIM routers
app.include_router(users_router)
app.include_router(groups_router)
app.include_router(schemas_router)


if __name__ == "__main__":
    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=8000,
        reload=settings.environment == "development"
    )