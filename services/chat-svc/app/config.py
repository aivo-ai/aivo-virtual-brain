"""
Chat Service Configuration
Environment-based configuration with security and privacy settings
"""

from pydantic_settings import BaseSettings
from typing import Optional
import os


class Settings(BaseSettings):
    """Chat service configuration settings"""
    
    # Service Configuration
    service_name: str = "chat-svc"
    version: str = "1.0.0"
    debug: bool = False
    environment: str = "production"
    
    # Server Configuration
    host: str = "0.0.0.0"
    port: int = 8000
    workers: int = 1
    
    # Database Configuration
    database_url: str = "postgresql+asyncpg://chat:password@localhost/chat_db"
    database_pool_size: int = 10
    database_max_overflow: int = 20
    database_pool_timeout: int = 30
    
    # Redis Configuration (for caching and sessions)
    redis_url: str = "redis://localhost:6379/0"
    redis_ttl: int = 3600  # 1 hour default TTL
    
    # Kafka Configuration
    kafka_bootstrap_servers: str = "localhost:9092"
    kafka_topic_prefix: str = "aivo"
    kafka_client_id: str = "chat-svc"
    kafka_enable_ssl: bool = False
    kafka_security_protocol: str = "PLAINTEXT"
    
    # Authentication & Authorization
    jwt_secret_key: str = "your-secret-key-change-in-production"
    jwt_algorithm: str = "HS256"
    jwt_expiration_hours: int = 24
    
    # Privacy & Compliance
    tenant_isolation_enabled: bool = True
    data_retention_days: int = 2555  # ~7 years default
    export_expiration_hours: int = 24
    max_export_size_mb: int = 100
    
    # Rate Limiting
    rate_limit_requests_per_minute: int = 100
    rate_limit_burst: int = 10
    
    # Logging
    log_level: str = "INFO"
    log_format: str = "json"
    enable_sql_logging: bool = False
    
    # CORS
    cors_origins: list[str] = ["*"]
    cors_allow_credentials: bool = True
    cors_allow_methods: list[str] = ["GET", "POST", "PUT", "DELETE", "OPTIONS"]
    cors_allow_headers: list[str] = ["*"]
    
    # OpenTelemetry
    otel_service_name: str = "aivo-chat-svc"
    otel_exporter_otlp_endpoint: Optional[str] = None
    otel_exporter_otlp_headers: Optional[str] = None
    otel_resource_attributes: str = "service.name=aivo-chat-svc,service.version=1.0.0"
    
    # Feature Flags
    enable_message_encryption: bool = False
    enable_content_moderation: bool = True
    enable_automatic_cleanup: bool = True
    enable_export_api: bool = True
    enable_deletion_api: bool = True
    enable_rate_limiting: bool = True
    privacy_enabled: bool = True
    create_tables_on_startup: bool = False
    
    # Message and Thread Settings
    message_retention_days: int = 365
    max_messages_per_thread: int = 1000
    
    # Database settings used by database.py
    db_pool_size: int = 10
    db_max_overflow: int = 20
    
    # Performance
    max_thread_length: int = 1000  # Maximum messages per thread
    max_message_size_kb: int = 100  # Maximum message content size
    default_page_size: int = 20
    max_page_size: int = 100
    
    class Config:
        env_file = ".env"
        env_prefix = "CHAT_"
        case_sensitive = False


# Create global settings instance
settings = Settings()


# Database URL for Alembic
DATABASE_URL = settings.database_url


# Kafka Topics
KAFKA_TOPICS = {
    "chat_message_created": f"{settings.kafka_topic_prefix}.chat.message.created",
    "chat_message_updated": f"{settings.kafka_topic_prefix}.chat.message.updated", 
    "chat_message_deleted": f"{settings.kafka_topic_prefix}.chat.message.deleted",
    "chat_thread_created": f"{settings.kafka_topic_prefix}.chat.thread.created",
    "chat_thread_updated": f"{settings.kafka_topic_prefix}.chat.thread.updated",
    "chat_thread_archived": f"{settings.kafka_topic_prefix}.chat.thread.archived",
    "privacy_export_requested": f"{settings.kafka_topic_prefix}.privacy.export.requested",
    "privacy_deletion_requested": f"{settings.kafka_topic_prefix}.privacy.deletion.requested",
}


def get_database_url() -> str:
    """Get database URL for the current environment"""
    return settings.database_url


def get_redis_url() -> str:
    """Get Redis URL for the current environment"""
    return settings.redis_url


def is_development() -> bool:
    """Check if running in development environment"""
    return settings.environment.lower() in ["development", "dev", "local"]


def is_production() -> bool:
    """Check if running in production environment"""
    return settings.environment.lower() in ["production", "prod"]
