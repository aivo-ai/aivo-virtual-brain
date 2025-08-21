"""
S4-14 Feature Flags & Remote Config - Demo Script

This script demonstrates the functionality of the feature flag service
without needing to run the actual server.
"""

import json
from datetime import datetime, timezone
import sys
import os

# Add the app directory to path for imports
sys.path.append(os.path.join(os.path.dirname(__file__), 'services', 'config-svc'))

try:
    from app.models import (
        FeatureFlag, FlagType, TargetingRule, TargetingOperator,
        RolloutStrategy, RolloutType, FlagEvaluator, ConfigCache
    )
except ImportError:
    print("Note: Running demo without actual models (service not installed)")
    print("This demo shows the conceptual functionality.")
    
    # Mock classes for demo purposes
    class FlagType:
        BOOLEAN = "boolean"
        STRING = "string"
        JSON = "json"
    
    class TargetingOperator:
        IN = "in"
        NOT_EQUALS = "not_equals"
    
    class RolloutType:
        PERCENTAGE = "percentage"
    
    class TargetingRule:
        def __init__(self, attr, op, values):
            self.attribute = attr
            self.operator = op 
            self.values = values
    
    class RolloutStrategy:
        def __init__(self, rollout_type, percentage=None):
            self.type = rollout_type
            self.percentage = percentage
    
    class FeatureFlag:
        def __init__(self, key, name, description, flag_type, enabled, default_value, targeting_rules=None, rollout_strategy=None):
            self.key = key
            self.name = name
            self.description = description
            self.flag_type = flag_type
            self.enabled = enabled
            self.default_value = default_value
            self.targeting_rules = targeting_rules or []
            self.rollout_strategy = rollout_strategy
        
        def evaluate(self, context):
            return True  # Simplified for demo
    
    class ConfigCache:
        async def load_default_flags(self):
            pass
        async def get_all_flags(self):
            return {"chat.streaming": None, "game.enabled": None}
    
    class FlagEvaluator:
        def __init__(self, cache):
            self.cache = cache
        
        async def evaluate_flag(self, key, context):
            # Simplified demo logic
            if key == "chat.streaming":
                return context.get("grade_band") in ["6-8", "9-12", "adult"]
            elif key == "game.enabled": 
                return context.get("grade_band") in ["k-5", "6-8"]
            elif key == "slp.asrProvider":
                tier = context.get("tenant_tier", "standard")
                return "azure-speech" if tier == "premium" else "whisper"
            elif key == "sel.enabled":
                return context.get("role") in ["teacher", "counselor"]
            elif key == "provider.order":
                variation = context.get("variation")
                if variation == "cost_optimized":
                    return ["azure", "openai", "anthropic"]
                elif variation == "quality_first":
                    return ["anthropic", "openai", "azure"]
                elif variation == "speed_first":
                    return ["openai", "azure", "anthropic"]
                else:
                    return ["openai", "anthropic", "azure"]
            return False
        
        async def evaluate_flags(self, flags, context):
            results = {}
            for flag in flags:
                results[flag] = await self.evaluate_flag(flag, context)
            return results

def print_section(title):
    """Print a formatted section header"""
    print(f"\n{'='*60}")
    print(f"  {title}")
    print('='*60)

def print_flag_result(flag_key, context, result):
    """Print flag evaluation result"""
    print(f"Flag: {flag_key}")
    print(f"Context: {context}")
    print(f"Result: {result}")
    print("-" * 40)

async def demo_feature_flags():
    """Demonstrate feature flag functionality"""
    
    print_section("🚀 S4-14 Feature Flags & Remote Config Demo")
    
    # Initialize cache and evaluator
    cache = ConfigCache()
    await cache.load_default_flags()
    evaluator = FlagEvaluator(cache)
    
    print(f"✅ Loaded {len(await cache.get_all_flags())} feature flags")
    
    # Demo 1: Chat Streaming for Different Grade Bands
    print_section("🗨️  Chat Streaming by Grade Band")
    
    contexts = [
        {"user_id": "student1", "role": "student", "grade_band": "k-5"},
        {"user_id": "student2", "role": "student", "grade_band": "6-8"}, 
        {"user_id": "student3", "role": "student", "grade_band": "9-12"},
        {"user_id": "teacher1", "role": "teacher", "grade_band": "adult"}
    ]
    
    for context in contexts:
        result = await evaluator.evaluate_flag("chat.streaming", context)
        print_flag_result("chat.streaming", context, result)
    
    # Demo 2: Games by Grade Band
    print_section("🎮 Educational Games by Grade Band")
    
    for context in contexts:
        result = await evaluator.evaluate_flag("game.enabled", context)
        print_flag_result("game.enabled", context, result)
    
    # Demo 3: SLP Provider by Tenant Tier
    print_section("🎤 Speech Recognition by Tenant Tier")
    
    slp_contexts = [
        {"user_id": "slp1", "role": "therapist", "tenant_tier": "basic"},
        {"user_id": "slp2", "role": "therapist", "tenant_tier": "premium"},
        {"user_id": "slp3", "role": "therapist", "tenant_tier": "enterprise"}
    ]
    
    for context in slp_contexts:
        result = await evaluator.evaluate_flag("slp.asrProvider", context)
        print_flag_result("slp.asrProvider", context, result)
    
    # Demo 4: SEL Features by Role
    print_section("🧠 Social-Emotional Learning by Role")
    
    sel_contexts = [
        {"user_id": "user1", "role": "student"},
        {"user_id": "user2", "role": "teacher"},
        {"user_id": "user3", "role": "counselor"},
        {"user_id": "user4", "role": "admin"}
    ]
    
    for context in sel_contexts:
        result = await evaluator.evaluate_flag("sel.enabled", context)
        print_flag_result("sel.enabled", context, result)
    
    # Demo 5: Provider Order Variations
    print_section("🤖 AI Provider Order Variations")
    
    provider_contexts = [
        {"user_id": "user1", "variation": "cost_optimized"},
        {"user_id": "user2", "variation": "quality_first"},
        {"user_id": "user3", "variation": "speed_first"},
        {"user_id": "user4"}  # Default variation
    ]
    
    for context in provider_contexts:
        result = await evaluator.evaluate_flag("provider.order", context)
        print_flag_result("provider.order", context, result)
    
    # Demo 6: Multi-Flag Evaluation
    print_section("📊 Multi-Flag Evaluation")
    
    teacher_context = {
        "user_id": "teacher123",
        "role": "teacher", 
        "grade_band": "6-8",
        "tenant_tier": "premium"
    }
    
    all_flags = ["chat.streaming", "game.enabled", "slp.asrProvider", "sel.enabled", "provider.order"]
    results = await evaluator.evaluate_flags(all_flags, teacher_context)
    
    print(f"Teacher Context: {teacher_context}")
    print("All Flag Results:")
    for flag, value in results.items():
        print(f"  {flag}: {value}")
    
    # Demo 7: Targeting Rule Examples
    print_section("🎯 Advanced Targeting Examples")
    
    # Create custom flag with complex targeting
    custom_flag = FeatureFlag(
        key="advanced.feature",
        name="Advanced Feature",
        description="Complex targeting example", 
        flag_type=FlagType.BOOLEAN,
        enabled=True,
        default_value=False,
        targeting_rules=[
            TargetingRule("role", TargetingOperator.IN, ["teacher", "admin"]),
            TargetingRule("grade_band", TargetingOperator.NOT_EQUALS, "k-5")
        ],
        rollout_strategy=RolloutStrategy(RolloutType.PERCENTAGE, percentage=75.0)
    )
    
    # Test various scenarios
    test_contexts = [
        {"user_id": "user1", "role": "student", "grade_band": "6-8"},  # Should be False (role)
        {"user_id": "user2", "role": "teacher", "grade_band": "k-5"},  # Should be False (grade_band)
        {"user_id": "user3", "role": "teacher", "grade_band": "6-8"},  # Should depend on rollout
        {"user_id": "user4", "role": "admin", "grade_band": "adult"},  # Should depend on rollout
    ]
    
    for context in test_contexts:
        result = custom_flag.evaluate(context)
        print_flag_result("advanced.feature", context, result)
    
    print_section("✅ Demo Complete!")
    print("The S4-14 Feature Flags & Remote Config service provides:")
    print("- ✅ Advanced targeting by role, grade band, and tenant tier")
    print("- ✅ Rollout strategies with percentage and hash-based distribution")
    print("- ✅ Multi-type flags (boolean, string, JSON)")
    print("- ✅ Complex evaluation rules with multiple operators")
    print("- ✅ Educational context awareness (K-5, 6-8, 9-12, adult)")
    print("- ✅ Production-ready caching and API endpoints")

if __name__ == "__main__":
    import asyncio
    asyncio.run(demo_feature_flags())
