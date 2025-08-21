"""
AIVO Inference Gateway - Policy Engine
S2-01 Implementation: Provider routing based on subject/locale/SLA with failover logic
S4-12 Implementation: Content moderation & safety filters with subject-aware rules
"""

import json
import time
import re
from typing import Dict, List, Optional, Any, Tuple, Set, Union
from dataclasses import dataclass, field
from enum import Enum
from datetime import datetime, timedelta
from opentelemetry import trace

# Import provider types - handle both absolute and relative imports
try:
    from .providers.base import ProviderType, SLATier
except ImportError:
    try:
        from providers.base import ProviderType, SLATier
    except ImportError:
        # Define locally if imports fail
        from enum import Enum
        class ProviderType(str, Enum):
            OPENAI = "openai"
            VERTEX_GEMINI = "vertex"
            BEDROCK_ANTHROPIC = "bedrock"
        
        class SLATier(str, Enum):
            STANDARD = "standard"
            PREMIUM = "premium"
            ENTERPRISE = "enterprise"

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


class GradeBand(Enum):
    """K-12 grade band classifications"""
    ELEMENTARY = "elementary"    # K-5
    MIDDLE = "middle"           # 6-8
    HIGH = "high"               # 9-12
    ADULT = "adult"             # Adult education/post-secondary


class ContentSeverity(Enum):
    """Content severity levels for moderation"""
    SAFE = "safe"                    # Appropriate for all ages
    MINOR_CONCERN = "minor_concern"  # Mild concern, may need review
    MODERATE = "moderate"            # Requires attention/filtering
    SEVERE = "severe"               # Block immediately
    CRITICAL = "critical"           # Block + escalate to guardian/teacher


class ModerationAction(Enum):
    """Actions to take based on moderation results"""
    ALLOW = "allow"
    WARN = "warn"                   # Show warning but allow
    FILTER = "filter"               # Remove/replace content
    BLOCK = "block"                 # Block request entirely
    ESCALATE = "escalate"           # Block + notify guardian/teacher
    AUDIT = "audit"                 # Allow but log for review


class Subject(Enum):
    """Academic subject classifications"""
    MATH = "math"
    SCIENCE = "science"
    ENGLISH = "english"
    HISTORY = "history"
    ARTS = "arts"
    MUSIC = "music"
    PHYSICAL_EDUCATION = "physical_education"
    FOREIGN_LANGUAGE = "foreign_language"
    COMPUTER_SCIENCE = "computer_science"
    SEL = "sel"                     # Social-Emotional Learning
    GENERAL = "general"
    ADMINISTRATIVE = "administrative"


class SELCategory(Enum):
    """Social-Emotional Learning sensitive categories"""
    SELF_AWARENESS = "self_awareness"
    SELF_MANAGEMENT = "self_management"
    SOCIAL_AWARENESS = "social_awareness"
    RELATIONSHIP_SKILLS = "relationship_skills"
    RESPONSIBLE_DECISION_MAKING = "responsible_decision_making"
    MENTAL_HEALTH = "mental_health"
    FAMILY_DYNAMICS = "family_dynamics"
    PEER_PRESSURE = "peer_pressure"
    IDENTITY_ISSUES = "identity_issues"
    TRAUMA = "trauma"


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
class ModerationRule:
    """Content moderation rule definition"""
    name: str
    description: str
    grade_bands: List[GradeBand] = field(default_factory=list)
    subjects: List[Subject] = field(default_factory=list)
    blocked_keywords: List[str] = field(default_factory=list)
    blocked_patterns: List[str] = field(default_factory=list)  # Regex patterns
    severity_thresholds: Dict[str, float] = field(default_factory=dict)
    action: ModerationAction = ModerationAction.WARN
    requires_guardian_review: bool = False
    sel_sensitive: bool = False
    audit_log: bool = True
    enabled: bool = True


@dataclass
class SafetyPolicy:
    """Subject-aware safety policy configuration"""
    subject: Subject
    grade_band: GradeBand
    base_rules: List[ModerationRule] = field(default_factory=list)
    custom_thresholds: Dict[str, float] = field(default_factory=dict)
    allowed_topics: List[str] = field(default_factory=list)
    blocked_topics: List[str] = field(default_factory=list)
    sel_escalation_enabled: bool = True
    guardian_notification_webhook: Optional[str] = None
    teacher_notification_webhook: Optional[str] = None
    enabled: bool = True


@dataclass
class ModerationResult:
    """Result of content moderation analysis"""
    content: str
    flagged: bool
    severity: ContentSeverity
    action: ModerationAction
    triggered_rules: List[str] = field(default_factory=list)
    category_scores: Dict[str, float] = field(default_factory=dict)
    categories_flagged: Dict[str, bool] = field(default_factory=dict)
    sel_categories: List[SELCategory] = field(default_factory=list)
    requires_escalation: bool = False
    guardian_notification: bool = False
    teacher_notification: bool = False
    audit_required: bool = False
    confidence: float = 0.0
    provider_used: Optional[str] = None
    processing_time_ms: int = 0


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


class SafetyEngine:
    """Subject-aware content moderation and safety filter engine"""
    
    def __init__(self, config: Dict[str, Any] = None):
        self.config = config or {}
        self.safety_policies: Dict[Tuple[Subject, GradeBand], SafetyPolicy] = {}
        self.moderation_rules: Dict[str, ModerationRule] = {}
        self.block_lists: Dict[str, Set[str]] = {}
        self.audit_logger = None  # Will be set by dependency injection
        
        # Default grade-band thresholds
        self.grade_band_thresholds = {
            GradeBand.ELEMENTARY: {
                "harassment": 0.3,
                "hate": 0.2,
                "self-harm": 0.1,
                "sexual": 0.1,
                "violence": 0.2,
                "profanity": 0.2
            },
            GradeBand.MIDDLE: {
                "harassment": 0.5,
                "hate": 0.3,
                "self-harm": 0.2,
                "sexual": 0.2,
                "violence": 0.3,
                "profanity": 0.4
            },
            GradeBand.HIGH: {
                "harassment": 0.7,
                "hate": 0.5,
                "self-harm": 0.3,
                "sexual": 0.4,
                "violence": 0.5,
                "profanity": 0.6
            },
            GradeBand.ADULT: {
                "harassment": 0.8,
                "hate": 0.7,
                "self-harm": 0.5,
                "sexual": 0.7,
                "violence": 0.7,
                "profanity": 0.8
            }
        }
        
        # SEL-sensitive patterns and keywords
        self.sel_patterns = {
            SELCategory.MENTAL_HEALTH: [
                r'\b(depressed?|depression|anxiety|panic|suicidal?)\b',
                r'\b(self.?harm|cutting|suicide)\b',
                r'\b(therapy|counselor|medication)\b'
            ],
            SELCategory.FAMILY_DYNAMICS: [
                r'\b(divorce|abuse|neglect|domestic)\b',
                r'\b(family.?problem|parent.?issue)\b',
                r'\b(custody|separation)\b'
            ],
            SELCategory.PEER_PRESSURE: [
                r'\b(bullying|bullied|bully)\b',
                r'\b(peer.?pressure|social.?pressure)\b',
                r'\b(excluded|isolation|lonely)\b'
            ],
            SELCategory.IDENTITY_ISSUES: [
                r'\b(identity|belonging|self.?worth)\b',
                r'\b(confidence|self.?esteem)\b',
                r'\b(gender|sexuality|orientation)\b'
            ],
            SELCategory.TRAUMA: [
                r'\b(trauma|ptsd|flashback)\b',
                r'\b(abuse|assault|violence)\b',
                r'\b(grief|loss|death)\b'
            ]
        }
        
        self._load_default_policies()
        self._load_custom_policies()
    
    def _load_default_policies(self):
        """Load default safety policies for all subject/grade combinations"""
        
        # Elementary school policies (K-5)
        elementary_base_rules = [
            ModerationRule(
                name="elementary_safe_content",
                description="Strict content filtering for K-5",
                grade_bands=[GradeBand.ELEMENTARY],
                subjects=[Subject.GENERAL],
                blocked_keywords=[
                    "violence", "weapon", "gun", "knife", "kill", "death", "die",
                    "sex", "sexual", "rape", "abuse", "drugs", "alcohol", "smoking",
                    "hate", "stupid", "dumb", "idiot", "loser", "shut up"
                ],
                blocked_patterns=[
                    r'\b(damn|hell|crap|suck)\b',
                    r'\b(kill|die|death|dead)\b',
                    r'\b(sex|sexy|sexual)\b'
                ],
                severity_thresholds={
                    "harassment": 0.3,
                    "hate": 0.2,
                    "sexual": 0.1,
                    "violence": 0.2
                },
                action=ModerationAction.BLOCK,
                audit_log=True
            ),
            ModerationRule(
                name="elementary_sel_escalation",
                description="SEL-sensitive content escalation for K-5",
                grade_bands=[GradeBand.ELEMENTARY],
                subjects=[Subject.SEL, Subject.GENERAL],
                blocked_keywords=[
                    "sad", "scared", "hurt", "angry", "family problems",
                    "bullying", "mean kids", "don't like me"
                ],
                action=ModerationAction.ESCALATE,
                sel_sensitive=True,
                requires_guardian_review=True,
                audit_log=True
            )
        ]
        
        # Middle school policies (6-8)
        middle_base_rules = [
            ModerationRule(
                name="middle_content_filter",
                description="Age-appropriate filtering for grades 6-8",
                grade_bands=[GradeBand.MIDDLE],
                subjects=[Subject.GENERAL],
                blocked_keywords=[
                    "explicit violence", "graphic content", "sexual content",
                    "drug use", "substance abuse", "self-harm"
                ],
                severity_thresholds={
                    "harassment": 0.5,
                    "hate": 0.3,
                    "sexual": 0.2,
                    "violence": 0.3
                },
                action=ModerationAction.FILTER,
                audit_log=True
            ),
            ModerationRule(
                name="middle_sel_review",
                description="SEL content requiring teacher review for grades 6-8",
                grade_bands=[GradeBand.MIDDLE],
                subjects=[Subject.SEL],
                sel_sensitive=True,
                action=ModerationAction.ESCALATE,
                requires_guardian_review=False,  # Teacher review only
                audit_log=True
            )
        ]
        
        # High school policies (9-12)
        high_base_rules = [
            ModerationRule(
                name="high_mature_content",
                description="Mature content guidelines for grades 9-12",
                grade_bands=[GradeBand.HIGH],
                subjects=[Subject.GENERAL],
                severity_thresholds={
                    "harassment": 0.7,
                    "hate": 0.5,
                    "sexual": 0.4,
                    "violence": 0.5
                },
                action=ModerationAction.WARN,
                audit_log=True
            ),
            ModerationRule(
                name="high_sel_sensitive",
                description="SEL-sensitive topics for high school",
                grade_bands=[GradeBand.HIGH],
                subjects=[Subject.SEL],
                sel_sensitive=True,
                action=ModerationAction.AUDIT,
                audit_log=True
            )
        ]
        
        # Create safety policies for each subject/grade combination
        for subject in Subject:
            for grade_band in GradeBand:
                if grade_band == GradeBand.ELEMENTARY:
                    base_rules = elementary_base_rules
                elif grade_band == GradeBand.MIDDLE:
                    base_rules = middle_base_rules
                elif grade_band == GradeBand.HIGH:
                    base_rules = high_base_rules
                else:  # ADULT
                    base_rules = []  # Minimal restrictions for adult education
                
                policy = SafetyPolicy(
                    subject=subject,
                    grade_band=grade_band,
                    base_rules=base_rules,
                    custom_thresholds=self.grade_band_thresholds[grade_band],
                    sel_escalation_enabled=(grade_band in [GradeBand.ELEMENTARY, GradeBand.MIDDLE])
                )
                
                self.safety_policies[(subject, grade_band)] = policy
    
    def _load_custom_policies(self):
        """Load custom safety policies from configuration"""
        custom_policies = self.config.get("custom_safety_policies", [])
        
        for policy_config in custom_policies:
            subject = Subject(policy_config.get("subject", "general"))
            grade_band = GradeBand(policy_config.get("grade_band", "adult"))
            
            if (subject, grade_band) in self.safety_policies:
                policy = self.safety_policies[(subject, grade_band)]
                
                # Override thresholds if provided
                if "custom_thresholds" in policy_config:
                    policy.custom_thresholds.update(policy_config["custom_thresholds"])
                
                # Add custom blocked topics
                if "blocked_topics" in policy_config:
                    policy.blocked_topics.extend(policy_config["blocked_topics"])
                
                # Add notification webhooks
                policy.guardian_notification_webhook = policy_config.get("guardian_webhook")
                policy.teacher_notification_webhook = policy_config.get("teacher_webhook")
    
    async def moderate_content(self, content: str, subject: Subject = Subject.GENERAL,
                              grade_band: GradeBand = GradeBand.ADULT,
                              user_id: Optional[str] = None,
                              tenant_id: Optional[str] = None) -> ModerationResult:
        """Perform subject-aware content moderation"""
        start_time = time.time()
        
        with tracer.start_as_current_span("safety_moderate_content") as span:
            span.set_attribute("subject", subject.value)
            span.set_attribute("grade_band", grade_band.value)
            span.set_attribute("content_length", len(content))
            
            # Get applicable safety policy
            policy = self.safety_policies.get((subject, grade_band))
            if not policy or not policy.enabled:
                # Fallback to general adult policy
                policy = self.safety_policies.get((Subject.GENERAL, GradeBand.ADULT))
            
            # Initialize result
            result = ModerationResult(
                content=content,
                flagged=False,
                severity=ContentSeverity.SAFE,
                action=ModerationAction.ALLOW
            )
            
            # Apply moderation rules
            await self._apply_moderation_rules(content, policy, result)
            
            # Check SEL sensitivity
            await self._check_sel_sensitivity(content, policy, result)
            
            # Determine final action
            self._determine_final_action(policy, result)
            
            # Log audit if required
            if result.audit_required:
                await self._log_audit_event(result, subject, grade_band, user_id, tenant_id)
            
            result.processing_time_ms = int((time.time() - start_time) * 1000)
            span.set_attribute("processing_time_ms", result.processing_time_ms)
            span.set_attribute("final_action", result.action.value)
            span.set_attribute("severity", result.severity.value)
            
            return result
    
    async def _apply_moderation_rules(self, content: str, policy: SafetyPolicy, 
                                    result: ModerationResult):
        """Apply moderation rules from the safety policy"""
        content_lower = content.lower()
        
        for rule in policy.base_rules:
            if not rule.enabled:
                continue
            
            # Check blocked keywords
            for keyword in rule.blocked_keywords:
                if keyword.lower() in content_lower:
                    result.flagged = True
                    result.triggered_rules.append(f"{rule.name}:keyword:{keyword}")
                    
                    if rule.action.value in ["block", "escalate"]:
                        result.severity = ContentSeverity.SEVERE
                    elif rule.action.value == "filter":
                        result.severity = ContentSeverity.MODERATE
            
            # Check blocked patterns (regex)
            for pattern in rule.blocked_patterns:
                if re.search(pattern, content, re.IGNORECASE):
                    result.flagged = True
                    result.triggered_rules.append(f"{rule.name}:pattern:{pattern}")
                    
                    if rule.action.value in ["block", "escalate"]:
                        result.severity = ContentSeverity.SEVERE
            
            # Apply rule-specific action if triggered
            if any(rule.name in triggered for triggered in result.triggered_rules):
                if rule.action.value in ["escalate", "block"] and result.action.value == "allow":
                    result.action = rule.action
                elif rule.action.value == "filter" and result.action.value == "allow":
                    result.action = rule.action
                
                if rule.requires_guardian_review:
                    result.guardian_notification = True
                
                if rule.audit_log:
                    result.audit_required = True
    
    async def _check_sel_sensitivity(self, content: str, policy: SafetyPolicy, 
                                   result: ModerationResult):
        """Check for SEL-sensitive content that requires special handling"""
        if not policy.sel_escalation_enabled:
            return
        
        for sel_category, patterns in self.sel_patterns.items():
            for pattern in patterns:
                if re.search(pattern, content, re.IGNORECASE):
                    result.sel_categories.append(sel_category)
                    result.flagged = True
                    result.requires_escalation = True
                    result.triggered_rules.append(f"sel:{sel_category.value}:{pattern}")
                    
                    # SEL content escalates to teacher/guardian review
                    if sel_category in [SELCategory.MENTAL_HEALTH, SELCategory.TRAUMA]:
                        result.guardian_notification = True
                        result.teacher_notification = True
                        result.action = ModerationAction.ESCALATE
                        result.severity = ContentSeverity.CRITICAL
                    else:
                        result.teacher_notification = True
                        if result.action.value == "allow":
                            result.action = ModerationAction.AUDIT
                        if result.severity.value == "safe":
                            result.severity = ContentSeverity.MINOR_CONCERN
    
    def _determine_final_action(self, policy: SafetyPolicy, result: ModerationResult):
        """Determine the final action based on all moderation checks"""
        # If already escalating, keep that action
        if result.action == ModerationAction.ESCALATE:
            return
        
        # If SEL categories detected and escalation enabled
        if result.sel_categories and policy.sel_escalation_enabled:
            if any(cat in [SELCategory.MENTAL_HEALTH, SELCategory.TRAUMA] 
                   for cat in result.sel_categories):
                result.action = ModerationAction.ESCALATE
                result.severity = ContentSeverity.CRITICAL
                return
        
        # Based on severity level
        if result.severity == ContentSeverity.CRITICAL:
            result.action = ModerationAction.ESCALATE
        elif result.severity == ContentSeverity.SEVERE:
            result.action = ModerationAction.BLOCK
        elif result.severity == ContentSeverity.MODERATE:
            result.action = ModerationAction.FILTER
        elif result.severity == ContentSeverity.MINOR_CONCERN:
            result.action = ModerationAction.WARN
        # else: ContentSeverity.SAFE -> ModerationAction.ALLOW (default)
    
    async def _log_audit_event(self, result: ModerationResult, subject: Subject,
                             grade_band: GradeBand, user_id: Optional[str],
                             tenant_id: Optional[str]):
        """Log audit event for blocked/flagged content"""
        audit_data = {
            "timestamp": datetime.now().isoformat(),
            "content_hash": hash(result.content) % (10**8),  # Anonymized content reference
            "content_length": len(result.content),
            "subject": subject.value,
            "grade_band": grade_band.value,
            "user_id": user_id,
            "tenant_id": tenant_id,
            "flagged": result.flagged,
            "severity": result.severity.value,
            "action": result.action.value,
            "triggered_rules": result.triggered_rules,
            "sel_categories": [cat.value for cat in result.sel_categories],
            "requires_escalation": result.requires_escalation,
            "guardian_notification": result.guardian_notification,
            "teacher_notification": result.teacher_notification,
            "processing_time_ms": result.processing_time_ms
        }
        
        # Log audit event (implementation depends on audit system)
        if self.audit_logger:
            await self.audit_logger.log_moderation_event(audit_data)
        else:
            # Fallback: log to console/file
            print(f"AUDIT LOG: {json.dumps(audit_data)}")
    
    def add_block_list(self, name: str, keywords: List[str]):
        """Add a custom block list"""
        self.block_lists[name] = set(keywords)
    
    def remove_block_list(self, name: str):
        """Remove a block list"""
        if name in self.block_lists:
            del self.block_lists[name]
    
    def update_safety_policy(self, subject: Subject, grade_band: GradeBand,
                           updates: Dict[str, Any]):
        """Update an existing safety policy"""
        key = (subject, grade_band)
        if key in self.safety_policies:
            policy = self.safety_policies[key]
            
            if "custom_thresholds" in updates:
                policy.custom_thresholds.update(updates["custom_thresholds"])
            
            if "blocked_topics" in updates:
                policy.blocked_topics.extend(updates["blocked_topics"])
            
            if "sel_escalation_enabled" in updates:
                policy.sel_escalation_enabled = updates["sel_escalation_enabled"]
    
    def get_safety_policy(self, subject: Subject, grade_band: GradeBand) -> Optional[SafetyPolicy]:
        """Get safety policy for subject/grade combination"""
        return self.safety_policies.get((subject, grade_band))
    
    def get_moderation_stats(self) -> Dict[str, Any]:
        """Get moderation statistics and health metrics"""
        total_policies = len(self.safety_policies)
        enabled_policies = sum(1 for p in self.safety_policies.values() if p.enabled)
        
        return {
            "total_policies": total_policies,
            "enabled_policies": enabled_policies,
            "grade_bands": [gb.value for gb in GradeBand],
            "subjects": [s.value for s in Subject],
            "sel_categories": [cat.value for cat in SELCategory],
            "block_lists_count": len(self.block_lists),
            "default_thresholds": self.grade_band_thresholds
        }


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
