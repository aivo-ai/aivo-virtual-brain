"""
FinOps Service Data Models
Comprehensive cost tracking and budget management for AI inference services
"""

from datetime import datetime, timedelta
from decimal import Decimal
from enum import Enum
from typing import Dict, List, Optional, Any
from uuid import uuid4

from pydantic import BaseModel, Field, validator
import structlog

logger = structlog.get_logger(__name__)


class ProviderType(str, Enum):
    """AI inference providers supported for cost tracking"""
    OPENAI = "openai"
    GEMINI = "gemini" 
    BEDROCK = "bedrock"
    AZURE_OPENAI = "azure_openai"
    ANTHROPIC = "anthropic"
    COHERE = "cohere"
    LOCAL = "local"  # Self-hosted models


class ModelType(str, Enum):
    """Model categories for cost differentiation"""
    TEXT_GENERATION = "text_generation"
    TEXT_EMBEDDING = "text_embedding"
    IMAGE_GENERATION = "image_generation"
    IMAGE_ANALYSIS = "image_analysis"
    SPEECH_TO_TEXT = "speech_to_text"
    TEXT_TO_SPEECH = "text_to_speech"
    FINE_TUNING = "fine_tuning"


class CostCategory(str, Enum):
    """Cost categorization for reporting and budgeting"""
    INFERENCE = "inference"
    TRAINING = "training"
    STORAGE = "storage"
    COMPUTE = "compute"
    BANDWIDTH = "bandwidth"
    API_CALLS = "api_calls"


class BudgetType(str, Enum):
    """Budget scope and hierarchy"""
    GLOBAL = "global"
    TENANT = "tenant"
    LEARNER = "learner"
    SERVICE = "service"
    MODEL = "model"


class BudgetPeriod(str, Enum):
    """Budget time periods"""
    DAILY = "daily"
    WEEKLY = "weekly"
    MONTHLY = "monthly"
    QUARTERLY = "quarterly"
    YEARLY = "yearly"


class AlertSeverity(str, Enum):
    """Budget alert severity levels"""
    LOW = "low"          # 50% of budget
    MEDIUM = "medium"    # 75% of budget
    HIGH = "high"        # 90% of budget
    CRITICAL = "critical"  # 100% or over budget


class AlertChannel(str, Enum):
    """Alert delivery channels"""
    EMAIL = "email"
    SLACK = "slack"
    WEBHOOK = "webhook"
    SMS = "sms"


# === Core Data Models ===

class ProviderPricing(BaseModel):
    """Provider pricing information per model"""
    id: str = Field(default_factory=lambda: str(uuid4()))
    provider: ProviderType
    model_name: str
    model_type: ModelType
    
    # Pricing structure
    input_token_price: Decimal = Field(description="Cost per 1K input tokens")
    output_token_price: Decimal = Field(description="Cost per 1K output tokens")
    image_price: Optional[Decimal] = Field(None, description="Cost per image")
    audio_price: Optional[Decimal] = Field(None, description="Cost per minute")
    
    # Additional costs
    request_price: Decimal = Field(default=Decimal("0"), description="Cost per API request")
    storage_price: Optional[Decimal] = Field(None, description="Cost per GB/month")
    
    # Metadata
    currency: str = Field(default="USD")
    effective_date: datetime = Field(default_factory=datetime.utcnow)
    expires_date: Optional[datetime] = None
    is_active: bool = True
    
    # Rate limits and quotas
    rate_limit_rpm: Optional[int] = Field(None, description="Requests per minute")
    rate_limit_tpm: Optional[int] = Field(None, description="Tokens per minute")
    
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)

    @validator('input_token_price', 'output_token_price', 'image_price', 'audio_price', 'request_price')
    def validate_positive_pricing(cls, v):
        if v is not None and v < 0:
            raise ValueError("Pricing must be non-negative")
        return v


class UsageEvent(BaseModel):
    """Individual usage event for cost calculation"""
    id: str = Field(default_factory=lambda: str(uuid4()))
    
    # Context
    tenant_id: str
    learner_id: Optional[str] = None
    service_name: str
    session_id: Optional[str] = None
    
    # Provider details
    provider: ProviderType
    model_name: str
    model_type: ModelType
    
    # Usage metrics
    input_tokens: int = 0
    output_tokens: int = 0
    total_tokens: int = 0
    request_count: int = 1
    
    # Additional metrics
    images_processed: int = 0
    audio_minutes: Decimal = Decimal("0")
    storage_gb: Decimal = Decimal("0")
    
    # Cost calculation
    calculated_cost: Decimal = Field(default=Decimal("0"))
    cost_category: CostCategory = CostCategory.INFERENCE
    currency: str = "USD"
    
    # Timing
    timestamp: datetime = Field(default_factory=datetime.utcnow)
    processing_duration_ms: Optional[int] = None
    
    # Metadata
    metadata: Dict[str, Any] = Field(default_factory=dict)
    created_at: datetime = Field(default_factory=datetime.utcnow)

    @validator('total_tokens', always=True)
    def calculate_total_tokens(cls, v, values):
        if 'input_tokens' in values and 'output_tokens' in values:
            return values['input_tokens'] + values['output_tokens']
        return v


class CostSummary(BaseModel):
    """Aggregated cost summary for reporting"""
    id: str = Field(default_factory=lambda: str(uuid4()))
    
    # Scope
    tenant_id: Optional[str] = None
    learner_id: Optional[str] = None
    service_name: Optional[str] = None
    
    # Time period
    period_start: datetime
    period_end: datetime
    period_type: str  # hour, day, week, month
    
    # Cost breakdowns
    total_cost: Decimal = Decimal("0")
    cost_by_provider: Dict[str, Decimal] = Field(default_factory=dict)
    cost_by_model: Dict[str, Decimal] = Field(default_factory=dict)
    cost_by_category: Dict[str, Decimal] = Field(default_factory=dict)
    
    # Usage metrics
    total_tokens: int = 0
    total_requests: int = 0
    unique_sessions: int = 0
    
    # Performance metrics
    avg_cost_per_token: Decimal = Decimal("0")
    avg_cost_per_request: Decimal = Decimal("0")
    avg_cost_per_session: Decimal = Decimal("0")
    
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)


class Budget(BaseModel):
    """Budget configuration and tracking"""
    id: str = Field(default_factory=lambda: str(uuid4()))
    
    # Budget scope
    budget_type: BudgetType
    name: str
    description: Optional[str] = None
    
    # Scope identifiers
    tenant_id: Optional[str] = None
    learner_id: Optional[str] = None
    service_name: Optional[str] = None
    model_name: Optional[str] = None
    
    # Budget configuration
    amount: Decimal = Field(description="Budget amount in USD")
    period: BudgetPeriod
    currency: str = "USD"
    
    # Time configuration
    start_date: datetime
    end_date: Optional[datetime] = None
    is_recurring: bool = True
    
    # Alert thresholds (percentage of budget)
    alert_thresholds: List[Decimal] = Field(
        default_factory=lambda: [Decimal("50"), Decimal("75"), Decimal("90"), Decimal("100")]
    )
    
    # Alert configuration
    alert_channels: List[AlertChannel] = Field(default_factory=list)
    alert_recipients: List[str] = Field(default_factory=list)
    webhook_url: Optional[str] = None
    
    # Current period tracking
    current_spend: Decimal = Decimal("0")
    last_alert_sent: Optional[datetime] = None
    last_alert_threshold: Optional[Decimal] = None
    
    # Status
    is_active: bool = True
    is_exceeded: bool = False
    
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)

    @validator('amount')
    def validate_positive_amount(cls, v):
        if v <= 0:
            raise ValueError("Budget amount must be positive")
        return v

    @validator('alert_thresholds')
    def validate_alert_thresholds(cls, v):
        if not v:
            return v
        # Ensure thresholds are sorted and reasonable
        sorted_thresholds = sorted(v)
        if any(t <= 0 or t > 200 for t in sorted_thresholds):
            raise ValueError("Alert thresholds must be between 0 and 200 percent")
        return sorted_thresholds


class BudgetAlert(BaseModel):
    """Budget alert record"""
    id: str = Field(default_factory=lambda: str(uuid4()))
    
    # Associated budget
    budget_id: str
    budget_name: str
    
    # Alert details
    severity: AlertSeverity
    threshold_percentage: Decimal
    current_spend: Decimal
    budget_amount: Decimal
    percentage_used: Decimal
    
    # Context
    tenant_id: Optional[str] = None
    learner_id: Optional[str] = None
    period_start: datetime
    period_end: datetime
    
    # Alert delivery
    channels_sent: List[AlertChannel] = Field(default_factory=list)
    recipients_notified: List[str] = Field(default_factory=list)
    
    # Message details
    alert_title: str
    alert_message: str
    
    # Status
    is_acknowledged: bool = False
    acknowledged_by: Optional[str] = None
    acknowledged_at: Optional[datetime] = None
    
    created_at: datetime = Field(default_factory=datetime.utcnow)


class CostForecast(BaseModel):
    """Cost forecasting based on usage trends"""
    id: str = Field(default_factory=lambda: str(uuid4()))
    
    # Scope
    tenant_id: Optional[str] = None
    learner_id: Optional[str] = None
    service_name: Optional[str] = None
    
    # Forecast period
    forecast_start: datetime
    forecast_end: datetime
    
    # Historical baseline
    baseline_start: datetime
    baseline_end: datetime
    baseline_cost: Decimal
    
    # Forecast results
    predicted_cost: Decimal
    confidence_interval_low: Decimal
    confidence_interval_high: Decimal
    confidence_level: Decimal = Decimal("0.95")
    
    # Trend analysis
    growth_rate: Decimal  # Percentage growth
    trend_direction: str  # increasing, decreasing, stable
    seasonality_factor: Optional[Decimal] = None
    
    # Model details
    forecast_model: str  # linear, exponential, arima, etc.
    model_accuracy: Optional[Decimal] = None
    
    created_at: datetime = Field(default_factory=datetime.utcnow)


class CostOptimization(BaseModel):
    """Cost optimization recommendations"""
    id: str = Field(default_factory=lambda: str(uuid4()))
    
    # Scope
    tenant_id: Optional[str] = None
    service_name: Optional[str] = None
    
    # Recommendation details
    recommendation_type: str  # model_swap, rate_limiting, caching, etc.
    title: str
    description: str
    
    # Cost impact
    current_monthly_cost: Decimal
    projected_monthly_cost: Decimal
    potential_savings: Decimal
    savings_percentage: Decimal
    
    # Implementation details
    implementation_effort: str  # low, medium, high
    implementation_time: str  # days, weeks, months
    risk_level: str  # low, medium, high
    
    # Specific recommendations
    recommended_models: List[str] = Field(default_factory=list)
    recommended_settings: Dict[str, Any] = Field(default_factory=dict)
    
    # Status
    status: str = "pending"  # pending, approved, implemented, rejected
    approved_by: Optional[str] = None
    implemented_at: Optional[datetime] = None
    
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)


# === Request/Response Models ===

class CreateBudgetRequest(BaseModel):
    """Request to create a new budget"""
    budget_type: BudgetType
    name: str
    description: Optional[str] = None
    amount: Decimal
    period: BudgetPeriod
    
    # Optional scope
    tenant_id: Optional[str] = None
    learner_id: Optional[str] = None
    service_name: Optional[str] = None
    model_name: Optional[str] = None
    
    # Alert configuration
    alert_thresholds: Optional[List[Decimal]] = None
    alert_channels: List[AlertChannel] = Field(default_factory=list)
    alert_recipients: List[str] = Field(default_factory=list)
    webhook_url: Optional[str] = None
    
    start_date: Optional[datetime] = None
    is_recurring: bool = True


class UpdateBudgetRequest(BaseModel):
    """Request to update an existing budget"""
    name: Optional[str] = None
    description: Optional[str] = None
    amount: Optional[Decimal] = None
    alert_thresholds: Optional[List[Decimal]] = None
    alert_channels: Optional[List[AlertChannel]] = None
    alert_recipients: Optional[List[str]] = None
    webhook_url: Optional[str] = None
    is_active: Optional[bool] = None


class CostQueryRequest(BaseModel):
    """Request for cost data"""
    # Time range
    start_date: datetime
    end_date: datetime
    
    # Scope filters
    tenant_id: Optional[str] = None
    learner_id: Optional[str] = None
    service_name: Optional[str] = None
    provider: Optional[ProviderType] = None
    model_name: Optional[str] = None
    
    # Aggregation
    group_by: List[str] = Field(default_factory=list)  # provider, model, service, learner, day, hour
    include_breakdown: bool = True
    
    # Pagination
    limit: int = Field(default=100, ge=1, le=1000)
    offset: int = Field(default=0, ge=0)


class CostResponse(BaseModel):
    """Cost query response"""
    total_cost: Decimal
    total_tokens: int
    total_requests: int
    period_start: datetime
    period_end: datetime
    
    # Breakdowns
    cost_by_provider: Dict[str, Decimal] = Field(default_factory=dict)
    cost_by_model: Dict[str, Decimal] = Field(default_factory=dict)
    cost_by_service: Dict[str, Decimal] = Field(default_factory=dict)
    cost_by_day: Dict[str, Decimal] = Field(default_factory=dict)
    
    # Details
    summaries: List[CostSummary] = Field(default_factory=list)
    
    # Pagination
    has_more: bool = False
    total_count: int = 0


class UsageStatsResponse(BaseModel):
    """Usage statistics response"""
    period_start: datetime
    period_end: datetime
    
    # Token statistics
    total_tokens: int = 0
    input_tokens: int = 0
    output_tokens: int = 0
    avg_tokens_per_request: Decimal = Decimal("0")
    
    # Request statistics
    total_requests: int = 0
    unique_sessions: int = 0
    avg_requests_per_session: Decimal = Decimal("0")
    
    # Cost efficiency
    cost_per_token: Decimal = Decimal("0")
    cost_per_request: Decimal = Decimal("0")
    cost_per_session: Decimal = Decimal("0")
    
    # Provider breakdown
    provider_stats: Dict[str, Dict[str, int]] = Field(default_factory=dict)
    model_stats: Dict[str, Dict[str, int]] = Field(default_factory=dict)


# === Health and System Models ===

class FinOpsHealth(BaseModel):
    """FinOps service health status"""
    status: str = "healthy"
    timestamp: datetime = Field(default_factory=datetime.utcnow)
    
    # Service status
    database_connected: bool = True
    pricing_data_current: bool = True
    last_usage_sync: Optional[datetime] = None
    
    # Data freshness
    latest_usage_event: Optional[datetime] = None
    budgets_monitored: int = 0
    alerts_pending: int = 0
    
    # Performance metrics
    avg_cost_calculation_time_ms: Optional[float] = None
    daily_events_processed: int = 0
    
    # System info
    version: str = "1.0.0"
    uptime_seconds: int = 0
