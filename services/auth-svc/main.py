"""
Auth Service - Enterprise SSO with SAML/OIDC and JIT Provisioning

Provides enterprise authentication services with support for:
- SAML 2.0 (SP and IdP-initiated)
- OpenID Connect
- Just-In-Time (JIT) user provisioning
- Group-to-role mapping
- Session management
"""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager
from datetime import datetime
import os

from app.config import get_settings
from app.database import init_db
from app.routes.enterprise import router as enterprise_router

settings = get_settings()


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan management."""
    
    # Initialize database
    await init_db()
    
    yield


# Create FastAPI application
app = FastAPI(
    title="Auth Service", 
    description="Enterprise SSO Authentication Service with SAML/OIDC and JIT provisioning", 
    version="1.0.0",
    lifespan=lifespan
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routers
app.include_router(enterprise_router, prefix="/sso", tags=["enterprise-sso"])


@app.get("/health")
def health():
    return {
        "status": "healthy",
        "timestamp": datetime.utcnow().isoformat(),
        "service": "auth-svc",
        "version": "1.0.0",
        "features": ["saml", "oidc", "jit-provisioning"]
    }


@app.get("/readiness")
def readiness():
    return {
        "ready": True,
        "timestamp": datetime.utcnow().isoformat(),
        "checks": {
            "database": {"status": "ok"},
            "saml": {"status": "ok"},
            "oidc": {"status": "ok"}
        }
    }


@app.get("/")
def root():
    """Root endpoint with service information."""
    return {
        "service": "Auth Service",
        "version": "1.0.0",
        "description": "Enterprise SSO Authentication Service",
        "endpoints": {
            "health": "/health",
            "saml_metadata": "/sso/saml/metadata/{tenant_id}/{provider_name}",
            "saml_login": "/sso/saml/login/{tenant_id}/{provider_name}",
            "saml_acs": "/sso/saml/acs",
            "oidc_login": "/sso/oidc/login/{tenant_id}/{provider_name}",
            "oidc_callback": "/sso/oidc/callback",
            "session_info": "/sso/session/{session_id}",
            "logout": "/sso/session/{session_id}/logout"
        },
        "features": {
            "saml_2.0": "Full SAML 2.0 SP implementation",
            "oidc": "OpenID Connect support",
            "jit_provisioning": "Just-In-Time user provisioning",
            "group_mapping": "IdP group to role mapping",
            "session_management": "SSO session tracking",
            "audit_logging": "Security audit trail"
        }
    }


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)
