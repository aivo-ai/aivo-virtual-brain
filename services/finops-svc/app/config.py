"""
Configuration management for the FinOps service.

This module handles all configuration settings including database connections,
authentication, external service integrations, and environment-specific settings.
"""

import os
import logging
from typing import List, Optional
from decimal import Decimal

from pydantic import BaseSettings, Field, validator


class FinOpsConfig(BaseSettings):
    """FinOps service configuration."""
    
    # Application Settings
    APP_NAME: str = "FinOps Service"
    APP_VERSION: str = "1.0.0"
    DEBUG: bool = Field(default=False, env="DEBUG")
    LOG_LEVEL: str = Field(default="INFO", env="LOG_LEVEL")
    
    # Server Configuration
    HOST: str = Field(default="0.0.0.0", env="HOST")
    PORT: int = Field(default=8000, env="PORT")
    WORKERS: int = Field(default=1, env="WORKERS")
    
    # Database Configuration
    DATABASE_URL: str = Field(..., env="DATABASE_URL")
    DATABASE_POOL_SIZE: int = Field(default=20, env="DATABASE_POOL_SIZE")
    DATABASE_MAX_OVERFLOW: int = Field(default=30, env="DATABASE_MAX_OVERFLOW")
    DATABASE_POOL_TIMEOUT: int = Field(default=30, env="DATABASE_POOL_TIMEOUT")
    
    # Authentication & Authorization
    JWT_SECRET: str = Field(..., env="JWT_SECRET")
    JWT_ALGORITHM: str = Field(default="HS256", env="JWT_ALGORITHM")
    JWT_EXPIRATION_HOURS: int = Field(default=24, env="JWT_EXPIRATION_HOURS")
    
    # API Keys for service-to-service communication
    VALID_API_KEYS: List[str] = Field(default_factory=list, env="VALID_API_KEYS")
    
    @validator("VALID_API_KEYS", pre=True)
    def parse_api_keys(cls, v):
        if isinstance(v, str):
            return [key.strip() for key in v.split(",") if key.strip()]
        return v
    
    # Email Service Configuration
    EMAIL_SERVICE_URL: str = Field(default="", env="EMAIL_SERVICE_URL")
    EMAIL_SERVICE_TOKEN: str = Field(default="", env="EMAIL_SERVICE_TOKEN")
    EMAIL_SENDER: str = Field(default="finops@aivo.com", env="EMAIL_SENDER")
    
    # Slack Integration
    SLACK_WEBHOOK_URL: str = Field(default="", env="SLACK_WEBHOOK_URL")
    SLACK_BOT_TOKEN: str = Field(default="", env="SLACK_BOT_TOKEN")
    
    # SMS Service Configuration
    SMS_SERVICE_URL: str = Field(default="", env="SMS_SERVICE_URL")
    SMS_SERVICE_TOKEN: str = Field(default="", env="SMS_SERVICE_TOKEN")
    SMS_SENDER_ID: str = Field(default="FinOps", env="SMS_SENDER_ID")
    
    # Dashboard and UI
    DASHBOARD_URL: str = Field(default="https://dashboard.aivo.com", env="DASHBOARD_URL")
    CORS_ORIGINS: List[str] = Field(default=["*"], env="CORS_ORIGINS")
    
    @validator("CORS_ORIGINS", pre=True)
    def parse_cors_origins(cls, v):
        if isinstance(v, str):
            return [origin.strip() for origin in v.split(",") if origin.strip()]
        return v
    
    # Budget Monitoring Configuration
    BUDGET_CHECK_INTERVAL_MINUTES: int = Field(default=15, env="BUDGET_CHECK_INTERVAL_MINUTES")
    ALERT_COOLDOWN_HOURS: int = Field(default=1, env="ALERT_COOLDOWN_HOURS")
    MAX_ALERTS_PER_BUDGET_PER_DAY: int = Field(default=10, env="MAX_ALERTS_PER_BUDGET_PER_DAY")
    
    # Cost Calculation Configuration
    DEFAULT_CURRENCY: str = Field(default="USD", env="DEFAULT_CURRENCY")
    COST_PRECISION_DECIMALS: int = Field(default=6, env="COST_PRECISION_DECIMALS")
    PRICING_UPDATE_INTERVAL_HOURS: int = Field(default=24, env="PRICING_UPDATE_INTERVAL_HOURS")
    
    # Data Retention Configuration
    DATA_RETENTION_DAYS: int = Field(default=365, env="DATA_RETENTION_DAYS")
    ALERT_RETENTION_DAYS: int = Field(default=90, env="ALERT_RETENTION_DAYS")
    SUMMARY_RETENTION_DAYS: int = Field(default=730, env="SUMMARY_RETENTION_DAYS")  # 2 years
    
    # Background Task Configuration
    ENABLE_BACKGROUND_TASKS: bool = Field(default=True, env="ENABLE_BACKGROUND_TASKS")
    COST_AGGREGATION_INTERVAL_MINUTES: int = Field(default=60, env="COST_AGGREGATION_INTERVAL_MINUTES")
    PRICING_SYNC_INTERVAL_HOURS: int = Field(default=24, env="PRICING_SYNC_INTERVAL_HOURS")
    DATA_CLEANUP_INTERVAL_HOURS: int = Field(default=168, env="DATA_CLEANUP_INTERVAL_HOURS")  # Weekly
    
    # External Service Timeouts
    HTTP_TIMEOUT_SECONDS: int = Field(default=30, env="HTTP_TIMEOUT_SECONDS")
    WEBHOOK_TIMEOUT_SECONDS: int = Field(default=10, env="WEBHOOK_TIMEOUT_SECONDS")
    EMAIL_TIMEOUT_SECONDS: int = Field(default=30, env="EMAIL_TIMEOUT_SECONDS")
    
    # Rate Limiting
    RATE_LIMIT_PER_MINUTE: int = Field(default=1000, env="RATE_LIMIT_PER_MINUTE")
    RATE_LIMIT_BURST: int = Field(default=2000, env="RATE_LIMIT_BURST")
    
    # Monitoring and Metrics
    METRICS_ENABLED: bool = Field(default=True, env="METRICS_ENABLED")
    HEALTH_CHECK_INTERVAL_SECONDS: int = Field(default=30, env="HEALTH_CHECK_INTERVAL_SECONDS")
    
    # Provider-Specific Configuration
    OPENAI_API_KEY: str = Field(default="", env="OPENAI_API_KEY")
    GEMINI_API_KEY: str = Field(default="", env="GEMINI_API_KEY")
    AWS_ACCESS_KEY_ID: str = Field(default="", env="AWS_ACCESS_KEY_ID")
    AWS_SECRET_ACCESS_KEY: str = Field(default="", env="AWS_SECRET_ACCESS_KEY")
    AWS_REGION: str = Field(default="us-east-1", env="AWS_REGION")
    
    # Cost Optimization Configuration
    ENABLE_COST_OPTIMIZATION: bool = Field(default=True, env="ENABLE_COST_OPTIMIZATION")
    OPTIMIZATION_ANALYSIS_INTERVAL_HOURS: int = Field(default=24, env="OPTIMIZATION_ANALYSIS_INTERVAL_HOURS")
    MIN_SAVINGS_THRESHOLD: Decimal = Field(default=Decimal("10.00"), env="MIN_SAVINGS_THRESHOLD")
    
    @validator("MIN_SAVINGS_THRESHOLD", pre=True)
    def parse_decimal(cls, v):
        if isinstance(v, str):
            return Decimal(v)
        return v
    
    # Forecasting Configuration
    ENABLE_FORECASTING: bool = Field(default=True, env="ENABLE_FORECASTING")
    FORECAST_DAYS_LOOKBACK: int = Field(default=30, env="FORECAST_DAYS_LOOKBACK")
    FORECAST_CONFIDENCE_LEVEL: float = Field(default=0.95, env="FORECAST_CONFIDENCE_LEVEL")
    
    # Security Configuration
    ALLOWED_HOSTS: List[str] = Field(default=["*"], env="ALLOWED_HOSTS")
    
    @validator("ALLOWED_HOSTS", pre=True)
    def parse_hosts(cls, v):
        if isinstance(v, str):
            return [host.strip() for host in v.split(",") if host.strip()]
        return v
    
    # Feature Flags
    ENABLE_BUDGET_ALERTS: bool = Field(default=True, env="ENABLE_BUDGET_ALERTS")
    ENABLE_COST_FORECASTING: bool = Field(default=True, env="ENABLE_COST_FORECASTING")
    ENABLE_USAGE_ANALYTICS: bool = Field(default=True, env="ENABLE_USAGE_ANALYTICS")
    ENABLE_PROVIDER_OPTIMIZATION: bool = Field(default=True, env="ENABLE_PROVIDER_OPTIMIZATION")
    
    # Batch Processing Configuration
    MAX_BATCH_SIZE: int = Field(default=1000, env="MAX_BATCH_SIZE")
    BATCH_PROCESSING_WORKERS: int = Field(default=4, env="BATCH_PROCESSING_WORKERS")
    
    # Caching Configuration
    ENABLE_CACHING: bool = Field(default=True, env="ENABLE_CACHING")
    CACHE_TTL_SECONDS: int = Field(default=300, env="CACHE_TTL_SECONDS")  # 5 minutes
    PRICING_CACHE_TTL_SECONDS: int = Field(default=3600, env="PRICING_CACHE_TTL_SECONDS")  # 1 hour
    
    # Validation and Error Handling
    ENABLE_STRICT_VALIDATION: bool = Field(default=True, env="ENABLE_STRICT_VALIDATION")
    MAX_RETRY_ATTEMPTS: int = Field(default=3, env="MAX_RETRY_ATTEMPTS")
    RETRY_BACKOFF_SECONDS: int = Field(default=2, env="RETRY_BACKOFF_SECONDS")
    
    class Config:
        """Pydantic configuration."""
        env_file = ".env"
        env_file_encoding = "utf-8"
        case_sensitive = True
        
        # Custom field validators
        @validator("LOG_LEVEL")
        def validate_log_level(cls, v):
            valid_levels = ["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"]
            if v.upper() not in valid_levels:
                raise ValueError(f"LOG_LEVEL must be one of {valid_levels}")
            return v.upper()
        
        @validator("JWT_ALGORITHM")
        def validate_jwt_algorithm(cls, v):
            valid_algorithms = ["HS256", "HS384", "HS512", "RS256", "RS384", "RS512"]
            if v not in valid_algorithms:
                raise ValueError(f"JWT_ALGORITHM must be one of {valid_algorithms}")
            return v
        
        @validator("DEFAULT_CURRENCY")
        def validate_currency(cls, v):
            valid_currencies = ["USD", "EUR", "GBP", "JPY", "CAD", "AUD"]
            if v.upper() not in valid_currencies:
                raise ValueError(f"DEFAULT_CURRENCY must be one of {valid_currencies}")
            return v.upper()
    
    def get_database_config(self) -> dict:
        """Get database configuration dictionary."""
        return {
            "url": self.DATABASE_URL,
            "pool_size": self.DATABASE_POOL_SIZE,
            "max_overflow": self.DATABASE_MAX_OVERFLOW,
            "pool_timeout": self.DATABASE_POOL_TIMEOUT,
            "echo": self.DEBUG
        }
    
    def get_alert_config(self) -> dict:
        """Get alert configuration dictionary."""
        return {
            "email_service_url": self.EMAIL_SERVICE_URL,
            "email_service_token": self.EMAIL_SERVICE_TOKEN,
            "email_sender": self.EMAIL_SENDER,
            "slack_webhook_url": self.SLACK_WEBHOOK_URL,
            "sms_service_url": self.SMS_SERVICE_URL,
            "sms_service_token": self.SMS_SERVICE_TOKEN,
            "dashboard_url": self.DASHBOARD_URL,
            "cooldown_hours": self.ALERT_COOLDOWN_HOURS,
            "max_alerts_per_day": self.MAX_ALERTS_PER_BUDGET_PER_DAY
        }
    
    def get_provider_config(self) -> dict:
        """Get provider configuration dictionary."""
        return {
            "openai_api_key": self.OPENAI_API_KEY,
            "gemini_api_key": self.GEMINI_API_KEY,
            "aws_access_key_id": self.AWS_ACCESS_KEY_ID,
            "aws_secret_access_key": self.AWS_SECRET_ACCESS_KEY,
            "aws_region": self.AWS_REGION
        }
    
    def is_feature_enabled(self, feature: str) -> bool:
        """Check if a feature is enabled."""
        feature_flags = {
            "budget_alerts": self.ENABLE_BUDGET_ALERTS,
            "cost_forecasting": self.ENABLE_COST_FORECASTING,
            "usage_analytics": self.ENABLE_USAGE_ANALYTICS,
            "provider_optimization": self.ENABLE_PROVIDER_OPTIMIZATION,
            "cost_optimization": self.ENABLE_COST_OPTIMIZATION,
            "forecasting": self.ENABLE_FORECASTING,
            "background_tasks": self.ENABLE_BACKGROUND_TASKS,
            "caching": self.ENABLE_CACHING,
            "metrics": self.METRICS_ENABLED
        }
        return feature_flags.get(feature, False)


# Load configuration
config = FinOpsConfig()

# Configure logging based on settings
def setup_logging():
    """Configure logging for the application."""
    logging.basicConfig(
        level=getattr(logging, config.LOG_LEVEL),
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S"
    )
    
    # Set specific logger levels
    if config.DEBUG:
        logging.getLogger("sqlalchemy.engine").setLevel(logging.INFO)
        logging.getLogger("aiohttp").setLevel(logging.DEBUG)
    else:
        logging.getLogger("sqlalchemy.engine").setLevel(logging.WARNING)
        logging.getLogger("aiohttp").setLevel(logging.WARNING)
    
    # Create logger for this module
    logger = logging.getLogger(__name__)
    logger.info(f"Logging configured at {config.LOG_LEVEL} level")


# Environment-specific configuration overrides
def get_environment() -> str:
    """Get current environment (development, staging, production)."""
    return os.getenv("ENVIRONMENT", "development").lower()


def is_development() -> bool:
    """Check if running in development environment."""
    return get_environment() == "development"


def is_production() -> bool:
    """Check if running in production environment."""
    return get_environment() == "production"


def is_staging() -> bool:
    """Check if running in staging environment."""
    return get_environment() == "staging"


# Initialize logging
setup_logging()

# Log configuration summary (excluding sensitive values)
logger = logging.getLogger(__name__)
logger.info(f"FinOps service configuration loaded for {get_environment()} environment")
logger.info(f"Debug mode: {config.DEBUG}")
logger.info(f"Database pool size: {config.DATABASE_POOL_SIZE}")
logger.info(f"Budget check interval: {config.BUDGET_CHECK_INTERVAL_MINUTES} minutes")
logger.info(f"Enabled features: budget_alerts={config.ENABLE_BUDGET_ALERTS}, "
           f"cost_forecasting={config.ENABLE_COST_FORECASTING}, "
           f"usage_analytics={config.ENABLE_USAGE_ANALYTICS}")

# Validate critical configuration
def validate_config():
    """Validate critical configuration settings."""
    errors = []
    
    if not config.DATABASE_URL:
        errors.append("DATABASE_URL is required")
    
    if not config.JWT_SECRET:
        errors.append("JWT_SECRET is required")
    
    if config.ENABLE_BUDGET_ALERTS and not config.EMAIL_SERVICE_URL:
        logger.warning("Budget alerts enabled but EMAIL_SERVICE_URL not configured")
    
    if errors:
        logger.error(f"Configuration validation failed: {errors}")
        raise ValueError(f"Invalid configuration: {', '.join(errors)}")
    
    logger.info("Configuration validation passed")


# Validate configuration on import
validate_config()
