"""
Configuration for Guardian Identity Verification Service
Environment-based settings with vault integration
"""

import os
from typing import List, Optional
from pydantic import BaseModel, Field
from pydantic_settings import BaseSettings


class StripeConfig(BaseModel):
    """Stripe configuration for micro-charge verification"""
    secret_key: str
    publishable_key: str
    webhook_secret: str
    micro_charge_amount_cents: int = 10  # $0.10
    auto_refund: bool = True
    refund_delay_minutes: int = 5  # Delay before auto-refund


class KBAConfig(BaseModel):
    """KBA provider configuration"""
    provider_name: str = "lexisnexis"  # or "experian", "idanalytics"
    api_endpoint: str
    api_key: str
    username: str
    password: str
    timeout_seconds: int = 30
    min_score_threshold: int = 80
    max_questions: int = 5


class DatabaseConfig(BaseModel):
    """Database configuration"""
    url: str
    echo: bool = False
    pool_size: int = 10
    max_overflow: int = 20


class RedisConfig(BaseModel):
    """Redis configuration for rate limiting and caching"""
    url: str
    db: int = 0
    max_connections: int = 10


class Settings(BaseSettings):
    """Verification Service Settings with vault integration"""
    
    # Service configuration
    service_name: str = Field(default="verification-svc", description="Service name")
    version: str = Field(default="1.0.0", description="Service version")
    environment: str = Field(default="development", description="Environment")
    debug: bool = Field(default=False, description="Debug mode")
    
    # API configuration
    host: str = Field(default="0.0.0.0", description="Host address")
    port: int = Field(default=8010, description="Port number")
    cors_origins: List[str] = Field(
        default=["http://localhost:3000", "http://localhost:5173", "https://app.aivo.com"],
        description="CORS allowed origins"
    )
    
    # Database configuration
    database_url: str = Field(
        default="postgresql+asyncpg://verification:verification@localhost/verification_db",
        description="Database connection URL"
    )
    
    # Redis configuration (for rate limiting)
    redis_url: str = Field(
        default="redis://localhost:6379/0",
        description="Redis connection URL"
    )
    
    # Stripe configuration (for micro-charge verification)
    stripe_secret_key: str = Field(default="", description="Stripe secret key")
    stripe_publishable_key: str = Field(default="", description="Stripe publishable key")
    stripe_webhook_secret: str = Field(default="", description="Stripe webhook secret")
    micro_charge_amount_cents: int = Field(default=10, description="Micro-charge amount in cents")
    auto_refund: bool = Field(default=True, description="Auto-refund micro-charges")
    refund_delay_minutes: int = Field(default=5, description="Minutes to wait before refund")
    
    # KBA provider configuration
    kba_provider_enabled: bool = Field(default=True, description="Enable KBA verification")
    kba_provider_name: str = Field(default="lexisnexis", description="KBA provider name")
    kba_api_endpoint: str = Field(default="", description="KBA provider API endpoint")
    kba_api_key: str = Field(default="", description="KBA provider API key")
    kba_username: str = Field(default="", description="KBA provider username")
    kba_password: str = Field(default="", description="KBA provider password")
    kba_timeout_seconds: int = Field(default=30, description="KBA provider timeout")
    kba_min_score: int = Field(default=80, description="Minimum KBA score for verification")
    kba_max_questions: int = Field(default=5, description="Maximum KBA questions")
    
    # Rate limiting configuration
    max_attempts_per_day: int = Field(default=3, description="Max verification attempts per day")
    max_attempts_per_hour: int = Field(default=2, description="Max verification attempts per hour")
    lockout_duration_hours: int = Field(default=24, description="Lockout duration after max attempts")
    ip_rate_limit_per_hour: int = Field(default=10, description="IP-based rate limit per hour")
    
    # Geographic policies
    geo_restrictions_enabled: bool = Field(default=True, description="Enable geographic restrictions")
    allowed_countries: List[str] = Field(
        default=["US", "CA", "UK", "AU", "NZ"],
        description="Countries where verification is allowed"
    )
    eu_gdpr_countries: List[str] = Field(
        default=["AT", "BE", "BG", "CY", "CZ", "DE", "DK", "EE", "ES", "FI", "FR", "GR", "HR", "HU", "IE", "IT", "LT", "LU", "LV", "MT", "NL", "PL", "PT", "RO", "SE", "SI", "SK"],
        description="EU countries subject to GDPR"
    )
    
    # Privacy and compliance
    data_retention_days: int = Field(default=90, description="Data retention period in days")
    audit_log_retention_days: int = Field(default=365, description="Audit log retention in days")
    auto_pii_scrubbing: bool = Field(default=True, description="Automatically scrub PII")
    pii_scrub_delay_hours: int = Field(default=24, description="Hours to wait before PII scrubbing")
    
    # External service URLs
    user_service_url: str = Field(
        default="http://localhost:8001",
        description="User service URL"
    )
    consent_service_url: str = Field(
        default="http://localhost:8006",
        description="Consent service URL"
    )
    
    # Security settings
    verification_token_ttl_hours: int = Field(default=24, description="Verification token TTL")
    webhook_signature_required: bool = Field(default=True, description="Require webhook signatures")
    ip_whitelist: List[str] = Field(default=[], description="IP whitelist for admin endpoints")
    
    # Monitoring and observability
    sentry_dsn: str = Field(default="", description="Sentry DSN for error tracking")
    log_level: str = Field(default="INFO", description="Logging level")
    structured_logging: bool = Field(default=True, description="Enable structured logging")
    metrics_enabled: bool = Field(default=True, description="Enable metrics collection")
    
    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"
        case_sensitive = False
        extra = "ignore"
    
    @property
    def stripe_config(self) -> Optional[StripeConfig]:
        """Get Stripe configuration if available"""
        if not self.stripe_secret_key:
            return None
        
        return StripeConfig(
            secret_key=self.stripe_secret_key,
            publishable_key=self.stripe_publishable_key,
            webhook_secret=self.stripe_webhook_secret,
            micro_charge_amount_cents=self.micro_charge_amount_cents,
            auto_refund=self.auto_refund,
            refund_delay_minutes=self.refund_delay_minutes
        )
    
    @property
    def kba_config(self) -> Optional[KBAConfig]:
        """Get KBA configuration if available"""
        if not self.kba_provider_enabled or not self.kba_api_key:
            return None
        
        return KBAConfig(
            provider_name=self.kba_provider_name,
            api_endpoint=self.kba_api_endpoint,
            api_key=self.kba_api_key,
            username=self.kba_username,
            password=self.kba_password,
            timeout_seconds=self.kba_timeout_seconds,
            min_score_threshold=self.kba_min_score,
            max_questions=self.kba_max_questions
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
    
    @property
    def is_production(self) -> bool:
        """Check if running in production environment"""
        return self.environment.lower() == "production"
    
    @property
    def is_eu_country(self) -> str:
        """Check if country code is in EU/GDPR list"""
        def check_country(country_code: str) -> bool:
            return country_code.upper() in self.eu_gdpr_countries
        return check_country
    
    @property
    def is_allowed_country(self) -> str:
        """Check if country code is in allowed list"""
        def check_country(country_code: str) -> bool:
            return country_code.upper() in self.allowed_countries
        return check_country


def get_settings() -> Settings:
    """Get cached settings instance"""
    return Settings()


# Global settings instance
settings = get_settings()
