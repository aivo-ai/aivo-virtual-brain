"""
Configuration settings for AIVO Admin Service
"""

import os
from typing import List
from pydantic import BaseSettings, Field


class Settings(BaseSettings):
    """Application settings"""
    
    # Service Configuration
    SERVICE_NAME: str = "admin-svc"
    VERSION: str = "1.0.0"
    ENVIRONMENT: str = Field(default="development", env="ENV")
    LOG_LEVEL: str = Field(default="INFO", env="LOG_LEVEL")
    
    # Security
    JWT_SECRET: str = Field(..., env="JWT_SECRET")
    JWT_ALGORITHM: str = Field(default="HS256", env="JWT_ALGORITHM")
    JWT_EXPIRES_HOURS: int = Field(default=8, env="JWT_EXPIRES_HOURS")
    
    # Database
    DATABASE_URL: str = Field(..., env="DATABASE_URL")
    DATABASE_POOL_SIZE: int = Field(default=10, env="DATABASE_POOL_SIZE")
    DATABASE_MAX_OVERFLOW: int = Field(default=20, env="DATABASE_MAX_OVERFLOW")
    
    # Redis (for session management and caching)
    REDIS_URL: str = Field(default="redis://localhost:6379", env="REDIS_URL")
    
    # External Services
    APPROVAL_SERVICE_URL: str = Field(
        default="http://localhost:8010", 
        env="APPROVAL_SERVICE_URL"
    )
    ORCHESTRATOR_SERVICE_URL: str = Field(
        default="http://localhost:8005", 
        env="ORCHESTRATOR_SERVICE_URL"
    )
    INGEST_SERVICE_URL: str = Field(
        default="http://localhost:8006", 
        env="INGEST_SERVICE_URL"
    )
    LEARNER_SERVICE_URL: str = Field(
        default="http://localhost:8008", 
        env="LEARNER_SERVICE_URL"
    )
    USER_SERVICE_URL: str = Field(
        default="http://localhost:8001", 
        env="USER_SERVICE_URL"
    )
    AUDIT_SERVICE_URL: str = Field(
        default="http://localhost:8015", 
        env="AUDIT_SERVICE_URL"
    )
    
    # CORS and Security
    CORS_ORIGINS: List[str] = Field(
        default=["http://localhost:3000", "https://admin.aivo.local"],
        env="CORS_ORIGINS"
    )
    ALLOWED_HOSTS: List[str] = Field(
        default=["localhost", "admin.aivo.local", "*.aivo.com"],
        env="ALLOWED_HOSTS"
    )
    
    # Admin Session Settings
    ADMIN_SESSION_TIMEOUT_MINUTES: int = Field(
        default=30, 
        env="ADMIN_SESSION_TIMEOUT_MINUTES"
    )
    SUPPORT_SESSION_TIMEOUT_MINUTES: int = Field(
        default=30, 
        env="SUPPORT_SESSION_TIMEOUT_MINUTES"
    )
    MAX_CONCURRENT_ADMIN_SESSIONS: int = Field(
        default=10, 
        env="MAX_CONCURRENT_ADMIN_SESSIONS"
    )
    
    # Consent and Data Access
    CONSENT_TOKEN_EXPIRES_MINUTES: int = Field(
        default=60, 
        env="CONSENT_TOKEN_EXPIRES_MINUTES"
    )
    JIT_CONSENT_EXPIRES_MINUTES: int = Field(
        default=15, 
        env="JIT_CONSENT_EXPIRES_MINUTES"
    )
    EMERGENCY_ACCESS_REQUIRES_APPROVAL: bool = Field(
        default=True, 
        env="EMERGENCY_ACCESS_REQUIRES_APPROVAL"
    )
    
    # Rate Limiting
    RATE_LIMIT_REQUESTS_PER_MINUTE: int = Field(
        default=60, 
        env="RATE_LIMIT_REQUESTS_PER_MINUTE"
    )
    RATE_LIMIT_BURST_SIZE: int = Field(
        default=10, 
        env="RATE_LIMIT_BURST_SIZE"
    )
    
    # Monitoring and Health
    HEALTH_CHECK_INTERVAL_SECONDS: int = Field(
        default=30, 
        env="HEALTH_CHECK_INTERVAL_SECONDS"
    )
    METRICS_ENABLED: bool = Field(default=True, env="METRICS_ENABLED")
    AUDIT_LOG_RETENTION_DAYS: int = Field(
        default=90, 
        env="AUDIT_LOG_RETENTION_DAYS"
    )
    
    # Job Queue Configuration
    JOB_QUEUE_RETRY_ATTEMPTS: int = Field(
        default=3, 
        env="JOB_QUEUE_RETRY_ATTEMPTS"
    )
    JOB_QUEUE_TIMEOUT_SECONDS: int = Field(
        default=300, 
        env="JOB_QUEUE_TIMEOUT_SECONDS"
    )
    
    # Feature Flags
    ENABLE_EMERGENCY_ACCESS: bool = Field(
        default=False, 
        env="ENABLE_EMERGENCY_ACCESS"
    )
    ENABLE_QUEUE_MANAGEMENT: bool = Field(
        default=True, 
        env="ENABLE_QUEUE_MANAGEMENT"
    )
    ENABLE_LEARNER_INSPECTION: bool = Field(
        default=True, 
        env="ENABLE_LEARNER_INSPECTION"
    )
    ENABLE_AUDIT_EXPORT: bool = Field(
        default=True, 
        env="ENABLE_AUDIT_EXPORT"
    )
    
    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"


# Global settings instance
settings = Settings()


def get_database_url() -> str:
    """Get the database URL for the current environment"""
    return settings.DATABASE_URL


def get_redis_url() -> str:
    """Get the Redis URL for the current environment"""
    return settings.REDIS_URL


def is_development() -> bool:
    """Check if running in development mode"""
    return settings.ENVIRONMENT.lower() in ["development", "dev", "local"]


def is_production() -> bool:
    """Check if running in production mode"""
    return settings.ENVIRONMENT.lower() in ["production", "prod"]


def get_cors_origins() -> List[str]:
    """Get CORS origins based on environment"""
    if is_development():
        return [
            "http://localhost:3000",
            "http://localhost:3001", 
            "http://127.0.0.1:3000",
            "https://admin.aivo.local"
        ]
    return settings.CORS_ORIGINS


def get_allowed_hosts() -> List[str]:
    """Get allowed hosts based on environment"""
    if is_development():
        return ["localhost", "127.0.0.1", "admin.aivo.local"]
    return settings.ALLOWED_HOSTS


# Validation
def validate_settings():
    """Validate critical settings"""
    errors = []
    
    if not settings.JWT_SECRET:
        errors.append("JWT_SECRET is required")
    
    if not settings.DATABASE_URL:
        errors.append("DATABASE_URL is required")
    
    if len(settings.JWT_SECRET) < 32:
        errors.append("JWT_SECRET must be at least 32 characters")
    
    if not settings.CORS_ORIGINS:
        errors.append("CORS_ORIGINS must be configured")
    
    if errors:
        raise ValueError(f"Configuration errors: {', '.join(errors)}")


# Validate on import
validate_settings()
