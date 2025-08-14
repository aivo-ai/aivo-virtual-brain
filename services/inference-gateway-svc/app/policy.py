"""
AIVO Inference Gateway - Policy Engine
S2-01 Implementation: Provider routing based on subject/locale/SLA with failover logic
"""

import json
import time
from typing import Dict, List, Optional, Any, Tuple, Set
from dataclasses import dataclass, field
from enum import Enum
from datetime import datetime, timedelta
from opentelemetry import trace

from .providers.base import ProviderType, SLATier

tracer = trace.get_tracer(__name__)


class RoutingStrategy(Enum):
    """Provider routing strategies"""
    ROUND_ROBIN = "round_robin"
    LEAST_LATENCY = "least_latency"
    LOWEST_COST = "lowest_cost"
    LOAD_BALANCE = "load_balance"
    PRIORITY_BASED = "priority_based"


class FailoverMode(Enum):
    """Failover behavior modes"""
    IMMEDIATE = "immediate"      # Try next provider immediately on failure
    CIRCUIT_BREAKER = "circuit_breaker"  # Stop using failed providers temporarily
    RETRY_BACKOFF = "retry_backoff"  # Exponential backoff before retries


@dataclass
class ProviderHealth:
    """Provider health tracking"""
    provider: ProviderType
    is_healthy: bool = True
    last_check: datetime = field(default_factory=datetime.now)
    success_count: int = 0
    failure_count: int = 0
    avg_latency_ms: float = 0.0
    circuit_breaker_open: bool = False
    circuit_breaker_open_until: Optional[datetime] = None


@dataclass
class RoutingPolicy:
    """Provider routing policy configuration"""
    subject_pattern: str  # Subject/user pattern to match
    locale_patterns: List[str] = field(default_factory=list)
    sla_tiers: List[SLATier] = field(default_factory=list)
    preferred_providers: List[ProviderType] = field(default_factory=list)
    fallback_providers: List[ProviderType] = field(default_factory=list)
    strategy: RoutingStrategy = RoutingStrategy.PRIORITY_BASED
    failover_mode: FailoverMode = FailoverMode.CIRCUIT_BREAKER
    max_retries: int = 2
    timeout_multiplier: float = 1.0
    cost_limit_usd: Optional[float] = None
    enabled: bool = True


@dataclass
class RoutingContext:
    """Request routing context"""
    subject: Optional[str] = None
    locale: Optional[str] = None  
    sla_tier: SLATier = SLATier.STANDARD
    model: Optional[str] = None
    request_type: str = "generate"  # generate, embed, moderate
    user_id: Optional[str] = None
    tenant_id: Optional[str] = None
    budget_remaining: Optional[float] = None
    priority: int = 5  # 1-10, higher = more priority


class PolicyEngine:
    """Provider routing and policy enforcement engine"""
    
    def __init__(self, config: Dict[str, Any] = None):
        self.config = config or {}
        self.policies: List[RoutingPolicy] = []
        self.provider_health: Dict[ProviderType, ProviderHealth] = {}
        self.round_robin_counters: Dict[str, int] = {}
        
        # Default routing policy
        self.default_policy = RoutingPolicy(
            subject_pattern="*",
            preferred_providers=[ProviderType.OPENAI],
            fallback_providers=[ProviderType.VERTEX_GEMINI, ProviderType.BEDROCK_ANTHROPIC],
            strategy=RoutingStrategy.PRIORITY_BASED,
            failover_mode=FailoverMode.CIRCUIT_BREAKER
        )
        
        # Initialize provider health tracking
        for provider in ProviderType:
            self.provider_health[provider] = ProviderHealth(provider=provider)
        
        self._load_policies()
    
    def _load_policies(self):
        """Load routing policies from configuration"""
        policy_configs = self.config.get("routing_policies", [])
        
        for policy_config in policy_configs:
            policy = RoutingPolicy(
                subject_pattern=policy_config.get("subject_pattern", "*"),
                locale_patterns=policy_config.get("locale_patterns", []),
                sla_tiers=[SLATier(t) for t in policy_config.get("sla_tiers", [])],
                preferred_providers=[ProviderType(p) for p in policy_config.get("preferred_providers", [])],
                fallback_providers=[ProviderType(p) for p in policy_config.get("fallback_providers", [])],
                strategy=RoutingStrategy(policy_config.get("strategy", "priority_based")),
                failover_mode=FailoverMode(policy_config.get("failover_mode", "circuit_breaker")),
                max_retries=policy_config.get("max_retries", 2),
                timeout_multiplier=policy_config.get("timeout_multiplier", 1.0),
                cost_limit_usd=policy_config.get("cost_limit_usd"),
                enabled=policy_config.get("enabled", True)
            )
            self.policies.append(policy)
    
    def route_request(self, context: RoutingContext) -> List[ProviderType]:
        """Determine provider routing order for a request"""
        with tracer.start_as_current_span("route_request") as span:
            span.set_attribute("subject", context.subject or "unknown")
            span.set_attribute("locale", context.locale or "unknown")
            span.set_attribute("sla_tier", context.sla_tier.value)
            span.set_attribute("request_type", context.request_type)
            
            # Find matching policy
            policy = self._find_matching_policy(context)
            span.set_attribute("policy_matched", policy.subject_pattern)
            
            # Get available healthy providers
            available_providers = self._get_healthy_providers(policy)
            
            if not available_providers:
                # Emergency fallback - return all providers ignoring health
                available_providers = policy.preferred_providers + policy.fallback_providers
                span.set_attribute("emergency_fallback", True)
            
            # Apply routing strategy
            ordered_providers = self._apply_routing_strategy(
                available_providers, policy, context
            )
            
            span.set_attribute("provider_order", [p.value for p in ordered_providers])
            span.set_attribute("provider_count", len(ordered_providers))
            
            return ordered_providers
    
    def _find_matching_policy(self, context: RoutingContext) -> RoutingPolicy:
        """Find the first matching routing policy"""
        for policy in self.policies:
            if not policy.enabled:
                continue
            
            # Check subject pattern
            if not self._matches_pattern(context.subject, policy.subject_pattern):
                continue
            
            # Check locale patterns
            if policy.locale_patterns and context.locale:
                if not any(self._matches_pattern(context.locale, pattern) 
                          for pattern in policy.locale_patterns):
                    continue
            
            # Check SLA tier
            if policy.sla_tiers and context.sla_tier not in policy.sla_tiers:
                continue
            
            return policy
        
        return self.default_policy
    
    def _matches_pattern(self, value: Optional[str], pattern: str) -> bool:
        """Simple pattern matching with wildcards"""
        if not value:
            return pattern == "*"
        
        if pattern == "*":
            return True
        
        # Simple prefix/suffix matching
        if pattern.startswith("*") and pattern.endswith("*"):
            return pattern[1:-1] in value
        elif pattern.startswith("*"):
            return value.endswith(pattern[1:])
        elif pattern.endswith("*"):
            return value.startswith(pattern[:-1])
        else:
            return value == pattern
    
    def _get_healthy_providers(self, policy: RoutingPolicy) -> List[ProviderType]:
        """Get list of healthy providers from policy"""
        all_providers = policy.preferred_providers + policy.fallback_providers
        healthy_providers = []
        
        for provider in all_providers:
            health = self.provider_health.get(provider)
            if health and self._is_provider_available(health):
                healthy_providers.append(provider)
        
        return healthy_providers
    
    def _is_provider_available(self, health: ProviderHealth) -> bool:
        """Check if provider is currently available"""
        # Circuit breaker check
        if health.circuit_breaker_open:
            if (health.circuit_breaker_open_until and 
                datetime.now() < health.circuit_breaker_open_until):
                return False
            else:
                # Reset circuit breaker
                health.circuit_breaker_open = False
                health.circuit_breaker_open_until = None
        
        return health.is_healthy
    
    def _apply_routing_strategy(self, providers: List[ProviderType], 
                              policy: RoutingPolicy, context: RoutingContext) -> List[ProviderType]:
        """Apply routing strategy to order providers"""
        if not providers:
            return providers
        
        strategy = policy.strategy
        
        if strategy == RoutingStrategy.PRIORITY_BASED:
            # Maintain order from preferred -> fallback
            preferred = [p for p in policy.preferred_providers if p in providers]
            fallback = [p for p in policy.fallback_providers if p in providers]
            return preferred + fallback
        
        elif strategy == RoutingStrategy.ROUND_ROBIN:
            # Round robin within available providers
            key = f"{context.subject}_{context.request_type}"
            counter = self.round_robin_counters.get(key, 0)
            self.round_robin_counters[key] = (counter + 1) % len(providers)
            
            # Rotate providers list
            return providers[counter:] + providers[:counter]
        
        elif strategy == RoutingStrategy.LEAST_LATENCY:
            # Sort by average latency
            return sorted(providers, 
                         key=lambda p: self.provider_health[p].avg_latency_ms)
        
        elif strategy == RoutingStrategy.LOWEST_COST:
            # Sort by estimated cost (simplified)
            cost_order = {
                ProviderType.OPENAI: 1,
                ProviderType.VERTEX_GEMINI: 2,
                ProviderType.BEDROCK_ANTHROPIC: 3
            }
            return sorted(providers, 
                         key=lambda p: cost_order.get(p, 999))
        
        elif strategy == RoutingStrategy.LOAD_BALANCE:
            # Balance based on success/failure ratio
            return sorted(providers,
                         key=lambda p: self._get_load_score(self.provider_health[p]),
                         reverse=True)
        
        return providers
    
    def _get_load_score(self, health: ProviderHealth) -> float:
        """Calculate load balancing score (higher = better)"""
        total_requests = health.success_count + health.failure_count
        if total_requests == 0:
            return 1.0
        
        success_rate = health.success_count / total_requests
        latency_score = max(0, 1.0 - (health.avg_latency_ms / 10000))  # Normalize latency
        
        return success_rate * 0.7 + latency_score * 0.3
    
    def should_retry(self, provider: ProviderType, attempt: int, policy: RoutingPolicy) -> bool:
        """Determine if request should be retried with same provider"""
        if attempt >= policy.max_retries:
            return False
        
        health = self.provider_health.get(provider)
        if not health:
            return False
        
        # Check circuit breaker
        if health.circuit_breaker_open:
            return False
        
        # Exponential backoff for retry mode
        if policy.failover_mode == FailoverMode.RETRY_BACKOFF:
            return True
        
        return False
    
    def record_success(self, provider: ProviderType, latency_ms: int, cost_usd: float = 0):
        """Record successful provider request"""
        with tracer.start_as_current_span("record_success") as span:
            health = self.provider_health.get(provider)
            if health:
                health.success_count += 1
                health.last_check = datetime.now()
                health.is_healthy = True
                
                # Update running average latency
                if health.avg_latency_ms == 0:
                    health.avg_latency_ms = latency_ms
                else:
                    health.avg_latency_ms = (health.avg_latency_ms * 0.9 + latency_ms * 0.1)
                
                # Reset circuit breaker if it was open
                if health.circuit_breaker_open:
                    health.circuit_breaker_open = False
                    health.circuit_breaker_open_until = None
            
            span.set_attribute("provider", provider.value)
            span.set_attribute("latency_ms", latency_ms)
            span.set_attribute("cost_usd", cost_usd)
    
    def record_failure(self, provider: ProviderType, error_type: str = "unknown"):
        """Record failed provider request"""
        with tracer.start_as_current_span("record_failure") as span:
            health = self.provider_health.get(provider)
            if health:
                health.failure_count += 1
                health.last_check = datetime.now()
                
                # Calculate failure rate
                total_requests = health.success_count + health.failure_count
                failure_rate = health.failure_count / total_requests if total_requests > 0 else 0
                
                # Open circuit breaker if failure rate is too high
                if failure_rate > 0.5 and total_requests >= 5:
                    health.circuit_breaker_open = True
                    health.circuit_breaker_open_until = datetime.now() + timedelta(minutes=5)
                    health.is_healthy = False
                    span.set_attribute("circuit_breaker_opened", True)
            
            span.set_attribute("provider", provider.value)
            span.set_attribute("error_type", error_type)
    
    def get_provider_health_status(self) -> Dict[str, Dict[str, Any]]:
        """Get current health status of all providers"""
        status = {}
        for provider, health in self.provider_health.items():
            total_requests = health.success_count + health.failure_count
            status[provider.value] = {
                "healthy": health.is_healthy,
                "success_count": health.success_count,
                "failure_count": health.failure_count,
                "success_rate": (
                    health.success_count / total_requests if total_requests > 0 else 0
                ),
                "avg_latency_ms": health.avg_latency_ms,
                "circuit_breaker_open": health.circuit_breaker_open,
                "last_check": health.last_check.isoformat()
            }
        return status
    
    def add_policy(self, policy: RoutingPolicy):
        """Add a new routing policy"""
        self.policies.append(policy)
    
    def remove_policy(self, subject_pattern: str):
        """Remove routing policy by subject pattern"""
        self.policies = [p for p in self.policies if p.subject_pattern != subject_pattern]
    
    def reset_provider_health(self, provider: ProviderType):
        """Reset health tracking for a provider"""
        if provider in self.provider_health:
            self.provider_health[provider] = ProviderHealth(provider=provider)


# Predefined policy configurations
ENTERPRISE_POLICIES = [
    RoutingPolicy(
        subject_pattern="enterprise/*",
        sla_tiers=[SLATier.PREMIUM, SLATier.ENTERPRISE],
        preferred_providers=[ProviderType.OPENAI, ProviderType.VERTEX_GEMINI],
        fallback_providers=[ProviderType.BEDROCK_ANTHROPIC],
        strategy=RoutingStrategy.LEAST_LATENCY,
        timeout_multiplier=0.8,
        cost_limit_usd=10.0
    ),
    RoutingPolicy(
        subject_pattern="research/*",
        preferred_providers=[ProviderType.VERTEX_GEMINI, ProviderType.BEDROCK_ANTHROPIC],
        fallback_providers=[ProviderType.OPENAI],
        strategy=RoutingStrategy.LOWEST_COST
    )
]
