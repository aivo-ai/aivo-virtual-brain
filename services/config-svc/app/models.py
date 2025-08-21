"""
Feature Flag Models and Data Structures
"""

from enum import Enum
from typing import Dict, List, Optional, Any, Union
from datetime import datetime, timezone
from dataclasses import dataclass, field
from pydantic import BaseModel, Field, field_validator
import hashlib
import json
import asyncio
import logging
from redis import asyncio as aioredis


logger = logging.getLogger(__name__)


class FlagType(str, Enum):
    """Feature flag types"""
    BOOLEAN = "boolean"
    STRING = "string"
    NUMBER = "number"
    JSON = "json"


class TargetingOperator(str, Enum):
    """Targeting rule operators"""
    EQUALS = "equals"
    NOT_EQUALS = "not_equals"
    IN = "in"
    NOT_IN = "not_in"
    CONTAINS = "contains"
    STARTS_WITH = "starts_with"
    ENDS_WITH = "ends_with"
    GREATER_THAN = "greater_than"
    LESS_THAN = "less_than"
    REGEX_MATCH = "regex_match"


class RolloutType(str, Enum):
    """Rollout strategy types"""
    PERCENTAGE = "percentage"
    USER_ID_HASH = "user_id_hash"
    TENANT_HASH = "tenant_hash"
    WHITELIST = "whitelist"
    BLACKLIST = "blacklist"


@dataclass
class TargetingRule:
    """Individual targeting rule"""
    attribute: str
    operator: TargetingOperator
    values: List[Any]
    
    def evaluate(self, context: Dict[str, Any]) -> bool:
        """Evaluate rule against context"""
        try:
            context_value = context.get(self.attribute)
            
            if context_value is None:
                return False
            
            if self.operator == TargetingOperator.EQUALS:
                return context_value == self.values[0]
            elif self.operator == TargetingOperator.NOT_EQUALS:
                return context_value != self.values[0]
            elif self.operator == TargetingOperator.IN:
                return context_value in self.values
            elif self.operator == TargetingOperator.NOT_IN:
                return context_value not in self.values
            elif self.operator == TargetingOperator.CONTAINS:
                return str(self.values[0]) in str(context_value)
            elif self.operator == TargetingOperator.STARTS_WITH:
                return str(context_value).startswith(str(self.values[0]))
            elif self.operator == TargetingOperator.ENDS_WITH:
                return str(context_value).endswith(str(self.values[0]))
            elif self.operator == TargetingOperator.GREATER_THAN:
                return float(context_value) > float(self.values[0])
            elif self.operator == TargetingOperator.LESS_THAN:
                return float(context_value) < float(self.values[0])
            elif self.operator == TargetingOperator.REGEX_MATCH:
                import re
                return bool(re.match(str(self.values[0]), str(context_value)))
            
            return False
        except (ValueError, TypeError, IndexError) as e:
            logger.warning(f"Error evaluating targeting rule: {e}")
            return False


@dataclass
class RolloutStrategy:
    """Rollout strategy configuration"""
    type: RolloutType
    percentage: Optional[float] = None
    hash_attribute: Optional[str] = None
    user_list: Optional[List[str]] = None
    
    def evaluate(self, context: Dict[str, Any]) -> bool:
        """Evaluate rollout strategy"""
        try:
            if self.type == RolloutType.PERCENTAGE:
                if self.percentage is None:
                    return False
                
                # Use consistent hashing based on user_id or session_id
                hash_key = context.get('user_id') or context.get('session_id') or 'anonymous'
                hash_value = int(hashlib.md5(str(hash_key).encode()).hexdigest(), 16)
                bucket = (hash_value % 100) + 1
                return bucket <= self.percentage
                
            elif self.type == RolloutType.USER_ID_HASH:
                if not self.hash_attribute or not self.percentage:
                    return False
                
                hash_value = context.get(self.hash_attribute)
                if not hash_value:
                    return False
                
                hash_int = int(hashlib.md5(str(hash_value).encode()).hexdigest(), 16)
                bucket = (hash_int % 100) + 1
                return bucket <= self.percentage
                
            elif self.type == RolloutType.TENANT_HASH:
                tenant_id = context.get('tenant_id')
                if not tenant_id or not self.percentage:
                    return False
                
                hash_int = int(hashlib.md5(str(tenant_id).encode()).hexdigest(), 16)
                bucket = (hash_int % 100) + 1
                return bucket <= self.percentage
                
            elif self.type == RolloutType.WHITELIST:
                if not self.user_list:
                    return False
                
                user_id = context.get('user_id')
                return user_id in self.user_list
                
            elif self.type == RolloutType.BLACKLIST:
                if not self.user_list:
                    return True
                
                user_id = context.get('user_id')
                return user_id not in self.user_list
            
            return False
        except Exception as e:
            logger.error(f"Error evaluating rollout strategy: {e}")
            return False


@dataclass
class FeatureFlag:
    """Feature flag configuration"""
    key: str
    name: str
    description: str
    flag_type: FlagType
    enabled: bool
    default_value: Any
    targeting_rules: List[TargetingRule] = field(default_factory=list)
    rollout_strategy: Optional[RolloutStrategy] = None
    variations: Dict[str, Any] = field(default_factory=dict)
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    tags: List[str] = field(default_factory=list)
    
    def evaluate(self, context: Dict[str, Any]) -> Any:
        """Evaluate flag against context and return value"""
        try:
            # If flag is disabled, return default value
            if not self.enabled:
                return self.default_value
            
            # Check targeting rules (all must pass)
            if self.targeting_rules:
                for rule in self.targeting_rules:
                    if not rule.evaluate(context):
                        return self.default_value
            
            # Check rollout strategy
            if self.rollout_strategy:
                if not self.rollout_strategy.evaluate(context):
                    return self.default_value
            
            # Check for variation based on context
            variation_key = context.get('variation')
            if variation_key and variation_key in self.variations:
                return self.variations[variation_key]
            
            # Return enabled value or default
            return True if self.flag_type == FlagType.BOOLEAN else self.default_value
            
        except Exception as e:
            logger.error(f"Error evaluating flag {self.key}: {e}")
            return self.default_value


class ConfigCache:
    """In-memory cache for feature flags with Redis backing"""
    
    def __init__(self):
        self.flags: Dict[str, FeatureFlag] = {}
        self.redis: Optional[aioredis.Redis] = None
        self.cache_ttl = 300  # 5 minutes
        self.refresh_interval = 60  # 1 minute
        
    async def initialize(self):
        """Initialize cache and load initial data"""
        try:
            # Connect to Redis
            redis_url = "redis://localhost:6379/0"  # Configure from env
            self.redis = aioredis.from_url(redis_url)
            
            # Load initial flags
            await self.refresh_flags()
            
            logger.info("✅ Config cache initialized successfully")
        except Exception as e:
            logger.error(f"Failed to initialize config cache: {e}")
            # Continue without Redis if needed
            await self.load_default_flags()
    
    async def load_default_flags(self):
        """Load default feature flags"""
        default_flags = {
            'chat.streaming': FeatureFlag(
                key='chat.streaming',
                name='Chat Streaming',
                description='Enable streaming responses in AI chat',
                flag_type=FlagType.BOOLEAN,
                enabled=True,
                default_value=False,
                targeting_rules=[
                    TargetingRule('grade_band', TargetingOperator.IN, ['6-8', '9-12', 'adult'])
                ],
                rollout_strategy=RolloutStrategy(RolloutType.PERCENTAGE, percentage=50.0)
            ),
            'game.enabled': FeatureFlag(
                key='game.enabled',
                name='Educational Games',
                description='Enable educational game features',
                flag_type=FlagType.BOOLEAN,
                enabled=True,
                default_value=True,
                targeting_rules=[
                    TargetingRule('grade_band', TargetingOperator.IN, ['k-5', '6-8'])
                ]
            ),
            'slp.asrProvider': FeatureFlag(
                key='slp.asrProvider',
                name='Speech Recognition Provider',
                description='ASR provider for speech-language pathology',
                flag_type=FlagType.STRING,
                enabled=True,
                default_value='whisper',
                variations={
                    'premium': 'azure-speech',
                    'standard': 'whisper',
                    'basic': 'web-speech'
                },
                targeting_rules=[
                    TargetingRule('tenant_tier', TargetingOperator.EQUALS, ['premium'])
                ]
            ),
            'sel.enabled': FeatureFlag(
                key='sel.enabled',
                name='SEL Features',
                description='Social-Emotional Learning features',
                flag_type=FlagType.BOOLEAN,
                enabled=True,
                default_value=False,
                targeting_rules=[
                    TargetingRule('role', TargetingOperator.IN, ['teacher', 'counselor'])
                ],
                rollout_strategy=RolloutStrategy(RolloutType.TENANT_HASH, percentage=30.0)
            ),
            'provider.order': FeatureFlag(
                key='provider.order',
                name='AI Provider Order',
                description='Order of AI model providers to try',
                flag_type=FlagType.JSON,
                enabled=True,
                default_value=['openai', 'anthropic', 'azure'],
                variations={
                    'cost_optimized': ['azure', 'openai', 'anthropic'],
                    'quality_first': ['anthropic', 'openai', 'azure'],
                    'speed_first': ['openai', 'azure', 'anthropic']
                }
            )
        }
        
        self.flags = default_flags
        logger.info(f"Loaded {len(default_flags)} default flags")
    
    async def refresh_flags(self):
        """Refresh flags from data source"""
        try:
            if self.redis:
                # Try to load from Redis first
                cached_flags = await self.redis.get("feature_flags")
                if cached_flags:
                    flags_data = json.loads(cached_flags)
                    # Deserialize flags (simplified for demo)
                    logger.info("Loaded flags from Redis cache")
                    return
            
            # Fallback to default flags
            await self.load_default_flags()
            
        except Exception as e:
            logger.error(f"Error refreshing flags: {e}")
            await self.load_default_flags()
    
    async def start_refresh_loop(self):
        """Background task to refresh flags periodically"""
        while True:
            try:
                await asyncio.sleep(self.refresh_interval)
                await self.refresh_flags()
                logger.debug("Flags refreshed successfully")
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Error in refresh loop: {e}")
    
    async def get_flag(self, key: str) -> Optional[FeatureFlag]:
        """Get a feature flag by key"""
        return self.flags.get(key)
    
    async def get_all_flags(self) -> Dict[str, FeatureFlag]:
        """Get all feature flags"""
        return self.flags.copy()
    
    async def health_check(self) -> bool:
        """Check cache health"""
        try:
            if self.redis:
                await self.redis.ping()
            return len(self.flags) > 0
        except Exception:
            return len(self.flags) > 0
    
    async def close(self):
        """Close cache connections"""
        if self.redis:
            await self.redis.close()


class FlagEvaluator:
    """Service for evaluating feature flags"""
    
    def __init__(self, cache: ConfigCache):
        self.cache = cache
    
    async def evaluate_flag(self, key: str, context: Dict[str, Any]) -> Any:
        """Evaluate a feature flag and return its value"""
        try:
            flag = await self.cache.get_flag(key)
            if not flag:
                logger.warning(f"Flag not found: {key}")
                return None
            
            return flag.evaluate(context)
            
        except Exception as e:
            logger.error(f"Error evaluating flag {key}: {e}")
            return None
    
    async def evaluate_flags(self, keys: List[str], context: Dict[str, Any]) -> Dict[str, Any]:
        """Evaluate multiple feature flags"""
        results = {}
        
        for key in keys:
            try:
                value = await self.evaluate_flag(key, context)
                if value is not None:
                    results[key] = value
            except Exception as e:
                logger.error(f"Error evaluating flag {key}: {e}")
        
        return results
    
    async def get_user_flags(self, context: Dict[str, Any]) -> Dict[str, Any]:
        """Get all applicable flags for a user context"""
        try:
            all_flags = await self.cache.get_all_flags()
            results = {}
            
            for key, flag in all_flags.items():
                try:
                    value = flag.evaluate(context)
                    results[key] = value
                except Exception as e:
                    logger.error(f"Error evaluating flag {key}: {e}")
                    results[key] = flag.default_value
            
            return results
            
        except Exception as e:
            logger.error(f"Error getting user flags: {e}")
            return {}


# Pydantic models for API
class EvaluationContext(BaseModel):
    """Context for flag evaluation"""
    user_id: Optional[str] = None
    session_id: Optional[str] = None
    tenant_id: Optional[str] = None
    role: Optional[str] = None
    grade_band: Optional[str] = None
    tenant_tier: Optional[str] = None
    variation: Optional[str] = None
    custom_attributes: Dict[str, Any] = Field(default_factory=dict)
    
    @field_validator('grade_band')
    @classmethod
    def validate_grade_band(cls, v):
        if v and v not in ['k-5', '6-8', '9-12', 'adult']:
            raise ValueError('Invalid grade band')
        return v


class FlagEvaluationRequest(BaseModel):
    """Request for flag evaluation"""
    flags: List[str]
    context: EvaluationContext


class FlagEvaluationResponse(BaseModel):
    """Response for flag evaluation"""
    flags: Dict[str, Any]
    evaluated_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    cache_hit: bool = True


class FlagDefinitionResponse(BaseModel):
    """Response for flag definition"""
    key: str
    name: str
    description: str
    flag_type: FlagType
    enabled: bool
    default_value: Any
    tags: List[str]
    created_at: datetime
    updated_at: datetime
