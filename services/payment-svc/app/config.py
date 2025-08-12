"""
Payment Service Configuration
Handles Stripe secrets and database configuration with vault integration
"""

import os
from typing import List, Optional
from pydantic import BaseModel, Field
from pydantic_settings import BaseSettings


class StripeConfig(BaseModel):
    """Stripe configuration with secret management"""
    publishable_key: str = Field(..., description="Stripe publishable key")
    secret_key: str = Field(..., description="Stripe secret key", repr=False)
    webhook_secret: str = Field(..., description="Stripe webhook secret", repr=False)
    api_version: str = Field(default="2023-10-16", description="Stripe API version")


class DatabaseConfig(BaseModel):
    """Database configuration"""
    url: str = Field(..., description="Database connection URL")
    echo: bool = Field(default=False, description="SQLAlchemy echo")
    pool_size: int = Field(default=10, description="Connection pool size")
    max_overflow: int = Field(default=20, description="Max overflow connections")


class RedisConfig(BaseModel):
    """Redis configuration for caching and tasks"""
    url: str = Field(default="redis://localhost:6379/0", description="Redis URL")
    max_connections: int = Field(default=10, description="Max Redis connections")


class Settings(BaseSettings):
    """Payment Service Settings with vault integration"""
    
    # Service Configuration
    service_name: str = Field(default="payment-svc", description="Service name")
    version: str = Field(default="1.0.0", description="Service version")
    environment: str = Field(default="development", description="Environment")
    debug: bool = Field(default=False, description="Debug mode")
    
    # API Configuration
    host: str = Field(default="0.0.0.0", description="API host")
    port: int = Field(default=8004, description="API port")
    cors_origins: List[str] = Field(
        default=["*"], 
        description="CORS allowed origins"
    )
    
    # Stripe Configuration (from vault/env)
    stripe_publishable_key: str = Field(
        default="pk_test_...",
        description="Stripe publishable key"
    )
    stripe_secret_key: str = Field(
        default="sk_test_...",
        description="Stripe secret key"
    )
    stripe_webhook_secret: str = Field(
        default="whsec_...",
        description="Stripe webhook endpoint secret"
    )
    
    # Database Configuration
    database_url: str = Field(
        default="postgresql+asyncpg://payment:payment@localhost/payment",
        description="Database connection URL"
    )
    
    # Redis Configuration
    redis_url: str = Field(
        default="redis://localhost:6379/0",
        description="Redis connection URL"
    )
    
    # Business Configuration
    trial_duration_days: int = Field(default=30, description="Trial duration in days")
    grace_period_days: int = Field(default=7, description="Payment grace period")
    dunning_failure_days: List[int] = Field(
        default=[3, 7, 14],
        description="Days to send dunning emails after payment failure"
    )
    cancellation_day: int = Field(
        default=21,
        description="Day to cancel subscription after payment failure"
    )
    
    # Discount Configuration
    quarterly_discount: float = Field(default=0.20, description="3-month discount")
    half_year_discount: float = Field(default=0.30, description="6-month discount")
    yearly_discount: float = Field(default=0.50, description="12-month discount")
    sibling_discount: float = Field(default=0.10, description="Sibling discount")
    
    # External Service URLs
    tenant_service_url: str = Field(
        default="http://localhost:8002",
        description="Tenant service URL"
    )
    user_service_url: str = Field(
        default="http://localhost:8001", 
        description="User service URL"
    )
    
    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"
        case_sensitive = False
        extra = "ignore"

    @property
    def stripe_config(self) -> StripeConfig:
        """Get Stripe configuration"""
        return StripeConfig(
            publishable_key=self.stripe_publishable_key,
            secret_key=self.stripe_secret_key,
            webhook_secret=self.stripe_webhook_secret
        )
    
    @property
    def database_config(self) -> DatabaseConfig:
        """Get database configuration"""
        return DatabaseConfig(
            url=self.database_url,
            echo=self.debug
        )
    
    @property
    def redis_config(self) -> RedisConfig:
        """Get Redis configuration"""
        return RedisConfig(
            url=self.redis_url
        )


def get_settings() -> Settings:
    """Get cached settings instance"""
    return Settings()


# Global settings instance
settings = get_settings()
