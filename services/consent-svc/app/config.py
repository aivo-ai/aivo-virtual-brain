"""
Consent Service Configuration
Settings and configuration management with environment variables
"""

import os
from typing import List, Optional
from pydantic import BaseModel, Field
from pydantic_settings import BaseSettings


class DatabaseConfig(BaseModel):
    """Database configuration"""
    url: str = Field(..., description="Database connection URL")
    echo: bool = Field(default=False, description="SQLAlchemy echo")
    pool_size: int = Field(default=10, description="Connection pool size")
    max_overflow: int = Field(default=20, description="Max overflow connections")
    pool_timeout: int = Field(default=30, description="Pool timeout seconds")


class RedisConfig(BaseModel):
    """Redis configuration for caching"""
    url: str = Field(default="redis://localhost:6379/0", description="Redis URL")
    max_connections: int = Field(default=10, description="Max Redis connections")
    consent_cache_ttl: int = Field(default=300, description="Consent cache TTL in seconds")
    key_prefix: str = Field(default="consent:", description="Redis key prefix")


class SecurityConfig(BaseModel):
    """Security configuration"""
    require_actor_validation: bool = Field(default=True, description="Validate actor permissions")
    allow_self_consent: bool = Field(default=False, description="Allow learners to change own consent")
    log_ip_addresses: bool = Field(default=True, description="Log IP addresses in consent log")
    audit_retention_days: int = Field(default=2555, description="Audit log retention period (7 years)")


class Settings(BaseSettings):
    """Consent Service Settings"""
    
    # Service Configuration
    service_name: str = Field(default="consent-svc", description="Service name")
    version: str = Field(default="1.0.0", description="Service version")
    environment: str = Field(default="development", description="Environment")
    debug: bool = Field(default=False, description="Debug mode")
    
    # API Configuration
    host: str = Field(default="0.0.0.0", description="API host")
    port: int = Field(default=8005, description="API port")
    cors_origins: List[str] = Field(
        default=["*"], 
        description="CORS allowed origins"
    )
    
    # Database Configuration
    database_url: str = Field(
        default="postgresql+asyncpg://consent:consent@localhost/consent_db",
        description="Database connection URL"
    )
    database_echo: bool = Field(default=False, description="SQLAlchemy echo")
    
    # Redis Configuration
    redis_url: str = Field(
        default="redis://localhost:6379/0",
        description="Redis connection URL"
    )
    consent_cache_ttl: int = Field(
        default=300,
        description="Consent state cache TTL in seconds"
    )
    redis_key_prefix: str = Field(
        default="consent:",
        description="Redis key prefix for consent data"
    )
    
    # Security Configuration
    require_actor_validation: bool = Field(
        default=True,
        description="Require actor permission validation"
    )
    allow_self_consent: bool = Field(
        default=False,
        description="Allow learners to modify their own consent"
    )
    log_ip_addresses: bool = Field(
        default=True,
        description="Log IP addresses in consent audit trail"
    )
    audit_retention_days: int = Field(
        default=2555,
        description="Consent audit log retention period (7 years default)"
    )
    
    # Gateway Integration
    gateway_plugin_enabled: bool = Field(
        default=True,
        description="Enable gateway consent_gate plugin integration"
    )
    gateway_cache_enabled: bool = Field(
        default=True,
        description="Enable Redis caching for gateway checks"
    )
    
    # External Service URLs
    user_service_url: str = Field(
        default="http://localhost:8001",
        description="User service URL for actor validation"
    )
    tenant_service_url: str = Field(
        default="http://localhost:8002",
        description="Tenant service URL for institutional consent"
    )
    
    # Monitoring Configuration
    log_level: str = Field(default="INFO", description="Logging level")
    structured_logging: bool = Field(default=True, description="Use structured JSON logging")
    metrics_enabled: bool = Field(default=True, description="Enable metrics collection")
    
    # Default Consent Values
    default_media_consent: bool = Field(
        default=False,
        description="Default media consent for new learners"
    )
    default_chat_consent: bool = Field(
        default=False,
        description="Default chat consent for new learners"
    )
    default_third_party_consent: bool = Field(
        default=False,
        description="Default third-party consent for new learners"
    )
    
    # Bulk Operations
    max_bulk_size: int = Field(
        default=100,
        description="Maximum number of learners in bulk operations"
    )
    bulk_cache_refresh: bool = Field(
        default=True,
        description="Refresh cache after bulk consent updates"
    )
    
    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"
        case_sensitive = False
        extra = "ignore"

    @property
    def database_config(self) -> DatabaseConfig:
        """Get database configuration"""
        return DatabaseConfig(
            url=self.database_url,
            echo=self.database_echo
        )
    
    @property
    def redis_config(self) -> RedisConfig:
        """Get Redis configuration"""
        return RedisConfig(
            url=self.redis_url,
            consent_cache_ttl=self.consent_cache_ttl,
            key_prefix=self.redis_key_prefix
        )
    
    @property
    def security_config(self) -> SecurityConfig:
        """Get security configuration"""
        return SecurityConfig(
            require_actor_validation=self.require_actor_validation,
            allow_self_consent=self.allow_self_consent,
            log_ip_addresses=self.log_ip_addresses,
            audit_retention_days=self.audit_retention_days
        )
    
    def get_redis_key(self, learner_id: str) -> str:
        """Generate Redis key for learner consent"""
        return f"{self.redis_key_prefix}state:{learner_id}"
    
    def get_cache_key(self, learner_id: str, consent_type: str) -> str:
        """Generate cache key for specific consent check"""
        return f"{self.redis_key_prefix}check:{learner_id}:{consent_type}"


def get_settings() -> Settings:
    """Get cached settings instance"""
    return Settings()


# Global settings instance
settings = get_settings()
