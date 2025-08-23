"""
Configuration settings for Tenant Service.
"""

import os
from typing import List, Optional
from pydantic import BaseSettings, Field


class Settings(BaseSettings):
    """Application settings."""
    
    # Database
    database_url: str = Field(
        default="postgresql://localhost:5432/tenant_db",
        env="DATABASE_URL"
    )
    
    # JWT
    jwt_secret_key: str = Field(
        default="your-secret-key-change-in-production",
        env="JWT_SECRET_KEY"
    )
    jwt_algorithm: str = Field(default="HS256", env="JWT_ALGORITHM")
    jwt_expiration_hours: int = Field(default=24, env="JWT_EXPIRATION_HOURS")
    
    # CORS
    allowed_origins: List[str] = Field(
        default=["*"],
        env="ALLOWED_ORIGINS"
    )
    
    # Environment
    environment: str = Field(default="development", env="ENVIRONMENT")
    
    # Vault (for SIS secrets)
    vault_url: Optional[str] = Field(default=None, env="VAULT_URL")
    vault_token: Optional[str] = Field(default=None, env="VAULT_TOKEN")
    
    # Redis (for rate limiting and caching)
    redis_url: Optional[str] = Field(default=None, env="REDIS_URL")
    
    # Logging
    log_level: str = Field(default="INFO", env="LOG_LEVEL")
    
    # SCIM Configuration
    scim_max_results: int = Field(default=200, env="SCIM_MAX_RESULTS")
    scim_default_page_size: int = Field(default=20, env="SCIM_DEFAULT_PAGE_SIZE")
    
    # Rate Limiting
    rate_limit_requests: int = Field(default=100, env="RATE_LIMIT_REQUESTS")
    rate_limit_window: int = Field(default=60, env="RATE_LIMIT_WINDOW")
    
    class Config:
        env_file = ".env"
        case_sensitive = False


_settings = None


def get_settings() -> Settings:
    """Get application settings (singleton)."""
    global _settings
    if _settings is None:
        _settings = Settings()
    return _settings