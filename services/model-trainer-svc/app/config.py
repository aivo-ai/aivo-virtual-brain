"""
Configuration management for Model Trainer Service
"""

from typing import List, Optional
from pydantic import Field
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    """Application settings"""
    
    # Environment
    environment: str = Field(default="development", description="Environment")
    
    # Database
    database_url: str = Field(
        default="postgresql://trainer:trainer@localhost:5433/model_trainer",
        description="Database connection URL"
    )
    test_database_url: str = Field(
        default="postgresql://trainer:trainer@localhost:5433/test_model_trainer",
        description="Test database connection URL"
    )
    
    # OpenAI Configuration
    openai_api_key: str = Field(description="OpenAI API key")
    openai_organization: Optional[str] = Field(default=None, description="OpenAI organization ID")
    
    # Model Registry Integration
    model_registry_url: str = Field(
        default="http://localhost:8001",
        description="Model Registry service URL"
    )
    model_registry_api_key: Optional[str] = Field(
        default=None,
        description="Model Registry API key"
    )
    
    # Redis (Job Queue)
    redis_url: str = Field(
        default="redis://localhost:6379/0",
        description="Redis connection URL"
    )
    
    # Service Configuration
    api_host: str = Field(default="0.0.0.0", description="API host")
    api_port: int = Field(default=8003, description="API port")
    workers: int = Field(default=1, description="Number of workers")
    
    # Logging
    log_level: str = Field(default="INFO", description="Log level")
    log_format: str = Field(default="json", description="Log format")
    
    # Training Configuration
    default_training_timeout: int = Field(default=3600, description="Default training timeout")
    max_concurrent_jobs: int = Field(default=5, description="Max concurrent training jobs")
    evaluation_timeout: int = Field(default=600, description="Evaluation timeout")
    
    # Storage Configuration
    dataset_storage_url: str = Field(
        default="s3://aivo-training-datasets",
        description="Dataset storage URL"
    )
    model_artifact_url: str = Field(
        default="s3://aivo-model-artifacts",
        description="Model artifact storage URL"
    )
    temp_storage_path: str = Field(
        default="/tmp/trainer",
        description="Temporary storage path"
    )
    
    # Evaluation Thresholds
    default_pedagogy_threshold: float = Field(default=0.8, description="Default pedagogy threshold")
    default_safety_threshold: float = Field(default=0.9, description="Default safety threshold")
    evaluation_retry_count: int = Field(default=3, description="Evaluation retry count")
    
    # Monitoring
    metrics_enabled: bool = Field(default=True, description="Enable Prometheus metrics")
    metrics_port: int = Field(default=9003, description="Metrics port")
    tracing_enabled: bool = Field(default=True, description="Enable tracing")
    tracing_endpoint: str = Field(
        default="http://localhost:4317",
        description="Tracing endpoint"
    )
    
    # Security
    allowed_origins: List[str] = Field(
        default=["http://localhost:3000", "http://localhost:8000"],
        description="Allowed CORS origins"
    )
    allowed_hosts: List[str] = Field(
        default=["localhost", "127.0.0.1"],
        description="Allowed hosts"
    )
    
    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"
        case_sensitive = False


# Global settings instance
settings = Settings()
