"""
Enterprise SSO Configuration and Settings
"""

from pydantic import BaseSettings, Field
from typing import List, Dict, Any, Optional
import os


class Settings(BaseSettings):
    """Application settings."""
    
    # Database
    database_url: str = Field(
        default="postgresql://auth_user:auth_pass@localhost:5432/auth_db",
        env="DATABASE_URL"
    )
    
    # Redis
    redis_url: str = Field(
        default="redis://localhost:6379/0",
        env="REDIS_URL"
    )
    
    # JWT Configuration
    jwt_secret_key: str = Field(
        default="your-secret-key-change-in-production",
        env="JWT_SECRET_KEY"
    )
    jwt_algorithm: str = Field(default="HS256", env="JWT_ALGORITHM")
    jwt_access_token_expire_minutes: int = Field(default=30, env="JWT_ACCESS_TOKEN_EXPIRE_MINUTES")
    jwt_refresh_token_expire_days: int = Field(default=7, env="JWT_REFRESH_TOKEN_EXPIRE_DAYS")
    
    # SAML Configuration
    saml_sp_entity_id: str = Field(
        default="https://auth.aivo.local/saml/sp",
        env="SAML_SP_ENTITY_ID"
    )
    saml_sp_acs_url: str = Field(
        default="https://auth.aivo.local/sso/saml/acs",
        env="SAML_SP_ACS_URL"
    )
    saml_sp_sls_url: str = Field(
        default="https://auth.aivo.local/sso/saml/sls",
        env="SAML_SP_SLS_URL"
    )
    saml_sp_x509_cert: Optional[str] = Field(default=None, env="SAML_SP_X509_CERT")
    saml_sp_private_key: Optional[str] = Field(default=None, env="SAML_SP_PRIVATE_KEY")
    
    # OIDC Configuration
    oidc_client_id: Optional[str] = Field(default=None, env="OIDC_CLIENT_ID")
    oidc_client_secret: Optional[str] = Field(default=None, env="OIDC_CLIENT_SECRET")
    oidc_redirect_uri: str = Field(
        default="https://auth.aivo.local/sso/oidc/callback",
        env="OIDC_REDIRECT_URI"
    )
    oidc_scopes: List[str] = Field(
        default=["openid", "profile", "email", "groups"],
        env="OIDC_SCOPES"
    )
    
    # External Services
    user_service_url: str = Field(
        default="http://localhost:8002",
        env="USER_SERVICE_URL"
    )
    approval_service_url: str = Field(
        default="http://localhost:8005",
        env="APPROVAL_SERVICE_URL"
    )
    
    # SSO Session Configuration
    sso_session_ttl_minutes: int = Field(default=480, env="SSO_SESSION_TTL_MINUTES")  # 8 hours
    jit_support_token_ttl_minutes: int = Field(default=60, env="JIT_SUPPORT_TOKEN_TTL_MINUTES")  # 1 hour
    
    # Security
    cors_origins: List[str] = Field(
        default=["http://localhost:3000", "https://app.aivo.local"],
        env="CORS_ORIGINS"
    )
    
    # Clock skew tolerance for SAML (in seconds)
    saml_clock_skew_tolerance: int = Field(default=300, env="SAML_CLOCK_SKEW_TOLERANCE")
    
    # Audit and logging
    audit_sso_assertions: bool = Field(default=True, env="AUDIT_SSO_ASSERTIONS")
    log_level: str = Field(default="INFO", env="LOG_LEVEL")
    
    class Config:
        env_file = ".env"
        case_sensitive = False


_settings = None


def get_settings() -> Settings:
    """Get application settings singleton."""
    global _settings
    if _settings is None:
        _settings = Settings()
    return _settings
