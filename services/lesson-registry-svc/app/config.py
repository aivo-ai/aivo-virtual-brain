"""
Configuration management for the Lesson Registry service.
"""
import os
from typing import List, Dict, Any
from functools import lru_cache
from pydantic import BaseSettings


class Settings(BaseSettings):
    """Application configuration with environment variable support."""
    
    # Basic service configuration
    environment: str = os.getenv("ENVIRONMENT", "development")
    port: int = int(os.getenv("PORT", "8000"))
    debug: bool = os.getenv("DEBUG", "false").lower() == "true"
    
    # Database configuration
    database_url: str = os.getenv(
        "DATABASE_URL",
        "postgresql://postgres:password@localhost:5432/lesson_registry"
    )
    
    # CORS configuration
    cors_origins: List[str] = [
        "http://localhost:3000",
        "http://localhost:8080",
        "https://app.aivo.com"
    ]
    
    # JWT configuration for authentication
    jwt_secret_key: str = os.getenv("JWT_SECRET_KEY", "lesson-registry-secret-key")
    jwt_algorithm: str = "HS256"
    jwt_expire_minutes: int = int(os.getenv("JWT_EXPIRE_MINUTES", "1440"))
    
    # CDN Configuration
    @property
    def cdn_config(self) -> Dict[str, Any]:
        """Get CDN configuration based on environment variables."""
        cdn_type = os.getenv("CDN_TYPE", "minio").lower()
        
        if cdn_type == "cloudfront":
            return {
                "type": "cloudfront",
                "distribution_domain": os.getenv("CLOUDFRONT_DOMAIN", "https://d123456.cloudfront.net"),
                "key_pair_id": os.getenv("CLOUDFRONT_KEY_PAIR_ID", ""),
                "private_key": os.getenv("CLOUDFRONT_PRIVATE_KEY", ""),
                "expires_seconds": int(os.getenv("CDN_EXPIRES_SECONDS", "600"))
            }
        else:
            return {
                "type": "minio",
                "endpoint_url": os.getenv("MINIO_ENDPOINT", "http://localhost:9000"),
                "access_key": os.getenv("MINIO_ACCESS_KEY", "minioadmin"),
                "secret_key": os.getenv("MINIO_SECRET_KEY", "minioadmin"),
                "bucket_name": os.getenv("MINIO_BUCKET", "lesson-assets"),
                "region_name": os.getenv("MINIO_REGION", "us-east-1"),
                "expires_seconds": int(os.getenv("CDN_EXPIRES_SECONDS", "600"))
            }
    
    # Logging configuration
    log_level: str = os.getenv("LOG_LEVEL", "INFO")
    log_format: str = "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
    
    class Config:
        env_file = ".env"
        case_sensitive = False


@lru_cache()
def get_settings() -> Settings:
    """Get cached settings instance."""
    return Settings()
