"""
Configuration management for AIVO Model Providers.
"""

import os
from typing import Dict, Optional, Any
from pydantic import BaseModel, Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class ProviderConfig(BaseModel):
    """Base configuration for a provider."""
    enabled: bool = Field(default=True, description="Whether the provider is enabled")
    timeout: int = Field(default=30, description="Request timeout in seconds")
    max_retries: int = Field(default=3, description="Maximum number of retries")
    retry_delay: float = Field(default=1.0, description="Delay between retries in seconds")


class OpenAIConfig(ProviderConfig):
    """OpenAI provider configuration."""
    api_key: Optional[str] = Field(default=None, description="OpenAI API key")
    base_url: Optional[str] = Field(default=None, description="Custom base URL")
    organization: Optional[str] = Field(default=None, description="OpenAI organization ID")
    
    @property
    def is_configured(self) -> bool:
        """Check if provider is properly configured."""
        return bool(self.api_key)


class VertexAIConfig(ProviderConfig):
    """Vertex AI provider configuration."""
    project_id: Optional[str] = Field(default=None, description="Google Cloud project ID")
    location: str = Field(default="us-central1", description="Vertex AI location")
    credentials_path: Optional[str] = Field(default=None, description="Path to service account key")
    
    @property
    def is_configured(self) -> bool:
        """Check if provider is properly configured."""
        return bool(self.project_id and (self.credentials_path or os.getenv("GOOGLE_APPLICATION_CREDENTIALS")))


class BedrockConfig(ProviderConfig):
    """AWS Bedrock provider configuration."""
    region: str = Field(default="us-east-1", description="AWS region")
    access_key_id: Optional[str] = Field(default=None, description="AWS access key ID")
    secret_access_key: Optional[str] = Field(default=None, description="AWS secret access key")
    session_token: Optional[str] = Field(default=None, description="AWS session token")
    role_arn: Optional[str] = Field(default=None, description="IAM role ARN for Bedrock")
    
    @property
    def is_configured(self) -> bool:
        """Check if provider is properly configured."""
        return bool(self.access_key_id and self.secret_access_key)


class GlobalConfig(BaseSettings):
    """Global configuration for all providers."""
    model_config = SettingsConfigDict(
        env_prefix="AIVO_",
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
    )
    
    # Global settings
    log_level: str = Field(default="INFO", description="Logging level")
    cache_ttl: int = Field(default=300, description="Cache TTL in seconds")
    default_provider: str = Field(default="auto", description="Default provider to use")
    
    # Feature flags
    enable_caching: bool = Field(default=True, description="Enable response caching")
    enable_metrics: bool = Field(default=False, description="Enable metrics collection")
    enable_tracing: bool = Field(default=False, description="Enable request tracing")
    
    # Provider configurations
    openai: OpenAIConfig = Field(default_factory=OpenAIConfig)
    vertex_ai: VertexAIConfig = Field(default_factory=VertexAIConfig)
    bedrock: BedrockConfig = Field(default_factory=BedrockConfig)
    
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        
        # Load provider-specific environment variables
        self._load_provider_configs()
    
    def _load_provider_configs(self):
        """Load provider configurations from environment variables."""
        # OpenAI
        self.openai.api_key = os.getenv("OPENAI_API_KEY", self.openai.api_key)
        self.openai.base_url = os.getenv("OPENAI_BASE_URL", self.openai.base_url)
        self.openai.organization = os.getenv("OPENAI_ORGANIZATION", self.openai.organization)
        
        # Vertex AI
        self.vertex_ai.project_id = os.getenv("GOOGLE_CLOUD_PROJECT", self.vertex_ai.project_id)
        self.vertex_ai.location = os.getenv("GOOGLE_CLOUD_LOCATION", self.vertex_ai.location)
        self.vertex_ai.credentials_path = os.getenv("GOOGLE_APPLICATION_CREDENTIALS", self.vertex_ai.credentials_path)
        
        # Bedrock
        self.bedrock.region = os.getenv("AWS_DEFAULT_REGION", self.bedrock.region)
        self.bedrock.access_key_id = os.getenv("AWS_ACCESS_KEY_ID", self.bedrock.access_key_id)
        self.bedrock.secret_access_key = os.getenv("AWS_SECRET_ACCESS_KEY", self.bedrock.secret_access_key)
        self.bedrock.session_token = os.getenv("AWS_SESSION_TOKEN", self.bedrock.session_token)
        self.bedrock.role_arn = os.getenv("AWS_BEDROCK_ROLE_ARN", self.bedrock.role_arn)
    
    def get_available_providers(self) -> Dict[str, bool]:
        """Get availability status of all providers."""
        return {
            "openai": self.openai.is_configured and self.openai.enabled,
            "vertex_ai": self.vertex_ai.is_configured and self.vertex_ai.enabled,
            "bedrock": self.bedrock.is_configured and self.bedrock.enabled,
        }
    
    def get_provider_config(self, provider_name: str) -> Optional[ProviderConfig]:
        """Get configuration for a specific provider."""
        provider_configs = {
            "openai": self.openai,
            "vertex_ai": self.vertex_ai,
            "bedrock": self.bedrock,
        }
        return provider_configs.get(provider_name)


# Global configuration instance
config = GlobalConfig()


def get_config() -> GlobalConfig:
    """Get the global configuration instance."""
    return config


def reload_config():
    """Reload configuration from environment."""
    global config
    config = GlobalConfig()


def update_config(**kwargs) -> GlobalConfig:
    """Update configuration with new values."""
    global config
    for key, value in kwargs.items():
        if hasattr(config, key):
            setattr(config, key, value)
    return config
