"""
Configuration settings for the Data Residency Service
"""

import os
from typing import List, Dict, Any, Optional
from pydantic import BaseSettings, validator
from enum import Enum


class LogLevel(str, Enum):
    DEBUG = "DEBUG"
    INFO = "INFO"
    WARNING = "WARNING"
    ERROR = "ERROR"


class Settings(BaseSettings):
    """Application settings"""
    
    # Application
    app_name: str = "Data Residency Service"
    app_version: str = "1.0.0"
    debug: bool = False
    log_level: LogLevel = LogLevel.INFO
    
    # Server
    host: str = "0.0.0.0"
    port: int = 8000
    workers: int = 1
    
    # Database
    database_url: str = "postgresql+asyncpg://postgres:postgres@localhost:5432/residency"
    database_pool_size: int = 10
    database_max_overflow: int = 20
    
    # Redis (for caching)
    redis_url: str = "redis://localhost:6379/0"
    cache_ttl_seconds: int = 300  # 5 minutes
    
    # Security
    secret_key: str = "your-secret-key-change-in-production"
    access_token_expire_minutes: int = 30
    cors_origins: List[str] = ["*"]
    cors_methods: List[str] = ["GET", "POST", "PUT", "DELETE", "OPTIONS"]
    cors_headers: List[str] = ["*"]
    
    # Regional Infrastructure
    supported_regions: List[str] = [
        "us-east", "us-west", "eu-west", "eu-central", 
        "apac-south", "apac-east", "ca-central"
    ]
    
    default_region: str = "us-east"
    
    # AWS Configuration
    aws_access_key_id: Optional[str] = None
    aws_secret_access_key: Optional[str] = None
    aws_region: str = "us-east-1"
    
    # Regional S3 Configuration
    regional_s3_config: Dict[str, Dict[str, str]] = {
        "us-east": {
            "bucket": "aivo-data-us-east",
            "region": "us-east-1",
            "backup_bucket": "aivo-backup-us-east"
        },
        "us-west": {
            "bucket": "aivo-data-us-west",
            "region": "us-west-2",
            "backup_bucket": "aivo-backup-us-west"
        },
        "eu-west": {
            "bucket": "aivo-data-eu-west",
            "region": "eu-west-1",
            "backup_bucket": "aivo-backup-eu-west"
        },
        "eu-central": {
            "bucket": "aivo-data-eu-central",
            "region": "eu-central-1",
            "backup_bucket": "aivo-backup-eu-central"
        },
        "apac-south": {
            "bucket": "aivo-data-apac-south",
            "region": "ap-south-1",
            "backup_bucket": "aivo-backup-apac-south"
        },
        "apac-east": {
            "bucket": "aivo-data-apac-east",
            "region": "ap-northeast-1",
            "backup_bucket": "aivo-backup-apac-east"
        },
        "ca-central": {
            "bucket": "aivo-data-ca-central",
            "region": "ca-central-1",
            "backup_bucket": "aivo-backup-ca-central"
        }
    }
    
    # Regional OpenSearch Configuration
    regional_opensearch_config: Dict[str, Dict[str, str]] = {
        "us-east": {
            "domain": "aivo-search-us-east",
            "endpoint": "https://search-aivo-us-east.us-east-1.es.amazonaws.com"
        },
        "us-west": {
            "domain": "aivo-search-us-west",
            "endpoint": "https://search-aivo-us-west.us-west-2.es.amazonaws.com"
        },
        "eu-west": {
            "domain": "aivo-search-eu-west",
            "endpoint": "https://search-aivo-eu-west.eu-west-1.es.amazonaws.com"
        },
        "eu-central": {
            "domain": "aivo-search-eu-central",
            "endpoint": "https://search-aivo-eu-central.eu-central-1.es.amazonaws.com"
        },
        "apac-south": {
            "domain": "aivo-search-apac-south",
            "endpoint": "https://search-aivo-apac-south.ap-south-1.es.amazonaws.com"
        },
        "apac-east": {
            "domain": "aivo-search-apac-east",
            "endpoint": "https://search-aivo-apac-east.ap-northeast-1.es.amazonaws.com"
        },
        "ca-central": {
            "domain": "aivo-search-ca-central",
            "endpoint": "https://search-aivo-ca-central.ca-central-1.es.amazonaws.com"
        }
    }
    
    # Regional Inference Provider Configuration
    regional_inference_config: Dict[str, List[Dict[str, Any]]] = {
        "us-east": [
            {
                "provider": "aws-bedrock",
                "region": "us-east-1",
                "models": ["claude-3-haiku", "claude-3-sonnet", "titan-text"],
                "endpoint": "https://bedrock-runtime.us-east-1.amazonaws.com"
            },
            {
                "provider": "openai",
                "region": "us-east-1",
                "models": ["gpt-4", "gpt-3.5-turbo"],
                "endpoint": "https://api.openai.com/v1"
            }
        ],
        "us-west": [
            {
                "provider": "aws-bedrock",
                "region": "us-west-2",
                "models": ["claude-3-haiku", "claude-3-sonnet"],
                "endpoint": "https://bedrock-runtime.us-west-2.amazonaws.com"
            }
        ],
        "eu-west": [
            {
                "provider": "aws-bedrock",
                "region": "eu-west-1",
                "models": ["claude-3-haiku"],
                "endpoint": "https://bedrock-runtime.eu-west-1.amazonaws.com"
            },
            {
                "provider": "anthropic-eu",
                "region": "eu-west-1",
                "models": ["claude-3-sonnet"],
                "endpoint": "https://api.anthropic.com/v1"
            }
        ],
        "eu-central": [
            {
                "provider": "aws-bedrock",
                "region": "eu-central-1",
                "models": ["claude-3-haiku"],
                "endpoint": "https://bedrock-runtime.eu-central-1.amazonaws.com"
            }
        ],
        "apac-south": [
            {
                "provider": "aws-bedrock",
                "region": "ap-south-1",
                "models": ["claude-3-haiku"],
                "endpoint": "https://bedrock-runtime.ap-south-1.amazonaws.com"
            }
        ],
        "apac-east": [
            {
                "provider": "aws-bedrock",
                "region": "ap-northeast-1",
                "models": ["claude-3-haiku"],
                "endpoint": "https://bedrock-runtime.ap-northeast-1.amazonaws.com"
            }
        ],
        "ca-central": [
            {
                "provider": "aws-bedrock",
                "region": "ca-central-1",
                "models": ["claude-3-haiku"],
                "endpoint": "https://bedrock-runtime.ca-central-1.amazonaws.com"
            }
        ]
    }
    
    # Compliance Configuration
    compliance_frameworks: Dict[str, Dict[str, Any]] = {
        "gdpr": {
            "name": "General Data Protection Regulation",
            "applicable_regions": ["eu-west", "eu-central"],
            "data_retention_max_days": 365,
            "cross_region_prohibited": True,
            "encryption_required": True,
            "audit_required": True
        },
        "ccpa": {
            "name": "California Consumer Privacy Act",
            "applicable_regions": ["us-west"],
            "data_retention_max_days": 365,
            "cross_region_prohibited": False,
            "encryption_required": True,
            "audit_required": True
        },
        "coppa": {
            "name": "Children's Online Privacy Protection Act",
            "applicable_regions": ["us-east", "us-west"],
            "data_retention_max_days": 180,
            "cross_region_prohibited": True,
            "encryption_required": True,
            "audit_required": True,
            "parental_consent_required": True
        },
        "ferpa": {
            "name": "Family Educational Rights and Privacy Act",
            "applicable_regions": ["us-east", "us-west", "ca-central"],
            "data_retention_max_days": 2555,  # 7 years
            "cross_region_prohibited": False,
            "encryption_required": True,
            "audit_required": True,
            "educational_purpose_only": True
        },
        "pipeda": {
            "name": "Personal Information Protection and Electronic Documents Act",
            "applicable_regions": ["ca-central"],
            "data_retention_max_days": 365,
            "cross_region_prohibited": False,
            "encryption_required": True,
            "audit_required": True
        },
        "lgpd": {
            "name": "Lei Geral de Proteção de Dados",
            "applicable_regions": [],  # Not currently supported
            "data_retention_max_days": 365,
            "cross_region_prohibited": True,
            "encryption_required": True,
            "audit_required": True
        }
    }
    
    # Emergency Override Configuration
    emergency_override_max_duration_hours: int = 72  # 3 days
    emergency_override_approval_required: bool = True
    emergency_override_audit_required: bool = True
    emergency_override_notification_channels: List[str] = ["email", "slack", "pagerduty"]
    
    # Health Check Configuration
    health_check_timeout_seconds: int = 30
    health_check_interval_seconds: int = 60
    health_check_failure_threshold: int = 3
    
    # Rate Limiting
    rate_limit_requests_per_minute: int = 1000
    rate_limit_burst_size: int = 100
    
    # Monitoring and Observability
    enable_metrics: bool = True
    enable_tracing: bool = True
    metrics_port: int = 8001
    jaeger_endpoint: Optional[str] = None
    
    # External Services
    inference_gateway_url: str = "http://localhost:8080"
    auth_service_url: str = "http://localhost:8081"
    tenant_service_url: str = "http://localhost:8082"
    
    @validator("supported_regions")
    def validate_supported_regions(cls, v):
        """Validate that supported regions have corresponding infrastructure config"""
        if not v:
            raise ValueError("At least one region must be supported")
        return v
    
    @validator("regional_s3_config")
    def validate_s3_config(cls, v, values):
        """Validate S3 configuration for all supported regions"""
        supported_regions = values.get("supported_regions", [])
        missing_regions = set(supported_regions) - set(v.keys())
        if missing_regions:
            raise ValueError(f"Missing S3 config for regions: {missing_regions}")
        return v
    
    @validator("regional_opensearch_config")
    def validate_opensearch_config(cls, v, values):
        """Validate OpenSearch configuration for all supported regions"""
        supported_regions = values.get("supported_regions", [])
        missing_regions = set(supported_regions) - set(v.keys())
        if missing_regions:
            raise ValueError(f"Missing OpenSearch config for regions: {missing_regions}")
        return v
    
    @validator("regional_inference_config")
    def validate_inference_config(cls, v, values):
        """Validate inference configuration for all supported regions"""
        supported_regions = values.get("supported_regions", [])
        missing_regions = set(supported_regions) - set(v.keys())
        if missing_regions:
            raise ValueError(f"Missing inference config for regions: {missing_regions}")
        return v
    
    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"
        case_sensitive = False
        
        # Map environment variables
        fields = {
            "database_url": {"env": "DATABASE_URL"},
            "redis_url": {"env": "REDIS_URL"},
            "secret_key": {"env": "SECRET_KEY"},
            "aws_access_key_id": {"env": "AWS_ACCESS_KEY_ID"},
            "aws_secret_access_key": {"env": "AWS_SECRET_ACCESS_KEY"},
            "jaeger_endpoint": {"env": "JAEGER_ENDPOINT"},
        }


# Global settings instance
settings = Settings()


def get_region_infrastructure(region_code: str) -> Dict[str, Any]:
    """Get infrastructure configuration for a specific region"""
    if region_code not in settings.supported_regions:
        raise ValueError(f"Unsupported region: {region_code}")
    
    return {
        "s3": settings.regional_s3_config.get(region_code, {}),
        "opensearch": settings.regional_opensearch_config.get(region_code, {}),
        "inference": settings.regional_inference_config.get(region_code, []),
    }


def get_compliance_requirements(frameworks: List[str]) -> Dict[str, Any]:
    """Get combined compliance requirements for multiple frameworks"""
    requirements = {
        "data_retention_max_days": None,
        "cross_region_prohibited": False,
        "encryption_required": True,
        "audit_required": True,
        "special_requirements": []
    }
    
    for framework in frameworks:
        if framework in settings.compliance_frameworks:
            framework_config = settings.compliance_frameworks[framework]
            
            # Most restrictive retention period
            if framework_config.get("data_retention_max_days"):
                if requirements["data_retention_max_days"] is None:
                    requirements["data_retention_max_days"] = framework_config["data_retention_max_days"]
                else:
                    requirements["data_retention_max_days"] = min(
                        requirements["data_retention_max_days"],
                        framework_config["data_retention_max_days"]
                    )
            
            # Any framework prohibiting cross-region makes it prohibited
            if framework_config.get("cross_region_prohibited"):
                requirements["cross_region_prohibited"] = True
            
            # Collect special requirements
            for key, value in framework_config.items():
                if key not in ["data_retention_max_days", "cross_region_prohibited", "encryption_required", "audit_required"]:
                    if value is True:
                        requirements["special_requirements"].append(f"{framework}:{key}")
    
    return requirements


def is_region_compliant(region_code: str, compliance_frameworks: List[str]) -> bool:
    """Check if a region is compliant with required frameworks"""
    for framework in compliance_frameworks:
        if framework in settings.compliance_frameworks:
            applicable_regions = settings.compliance_frameworks[framework].get("applicable_regions", [])
            if applicable_regions and region_code not in applicable_regions:
                return False
    return True
