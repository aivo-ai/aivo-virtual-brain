"""
Configuration settings for SIS Bridge Service.
"""

import os
from typing import List, Optional
from pydantic_settings import BaseSettings
from pydantic import Field


class Settings(BaseSettings):
    """Application settings."""
    
    # Database
    database_url: str = Field(
        default="postgresql://localhost:5432/sis_bridge_db",
        env="DATABASE_URL"
    )
    
    # External Services
    tenant_service_url: str = Field(
        default="http://localhost:8000",
        env="TENANT_SERVICE_URL"
    )
    tenant_service_token: str = Field(
        default="your-service-token",
        env="TENANT_SERVICE_TOKEN"
    )
    
    # Vault (for SIS credentials)
    vault_url: Optional[str] = Field(default=None, env="VAULT_URL")
    vault_token: Optional[str] = Field(default=None, env="VAULT_TOKEN")
    
    # Redis (for job queue)
    redis_url: str = Field(
        default="redis://localhost:6379",
        env="REDIS_URL"
    )
    
    # CORS
    allowed_origins: List[str] = Field(
        default=["*"],
        env="ALLOWED_ORIGINS"
    )
    
    # Environment
    environment: str = Field(default="development", env="ENVIRONMENT")
    
    # Logging
    log_level: str = Field(default="INFO", env="LOG_LEVEL")
    
    # Sync Configuration
    default_sync_interval: int = Field(default=3600, env="DEFAULT_SYNC_INTERVAL")  # 1 hour
    max_retry_attempts: int = Field(default=3, env="MAX_RETRY_ATTEMPTS")
    batch_size: int = Field(default=100, env="BATCH_SIZE")
    sync_timeout: int = Field(default=1800, env="SYNC_TIMEOUT")  # 30 minutes
    
    # Webhook Configuration
    webhook_timeout: int = Field(default=30, env="WEBHOOK_TIMEOUT")
    webhook_retry_attempts: int = Field(default=3, env="WEBHOOK_RETRY_ATTEMPTS")
    
    # SIS Provider Limits
    clever_api_rate_limit: int = Field(default=100, env="CLEVER_API_RATE_LIMIT")
    classlink_api_rate_limit: int = Field(default=60, env="CLASSLINK_API_RATE_LIMIT")
    
    # Security
    webhook_secret_key: str = Field(
        default="your-webhook-secret-change-in-production",
        env="WEBHOOK_SECRET_KEY"
    )
    
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
