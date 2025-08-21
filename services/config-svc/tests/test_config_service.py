"""
Test suite for Feature Flag Service
"""

import pytest
import asyncio
from datetime import datetime, timezone
from unittest.mock import AsyncMock, patch
from fastapi.testclient import TestClient
import json

from app.main import app
from app.models import (
    FeatureFlag, 
    FlagType, 
    TargetingRule, 
    TargetingOperator,
    RolloutStrategy,
    RolloutType,
    ConfigCache,
    FlagEvaluator,
    EvaluationContext
)


@pytest.fixture
def client():
    """Test client fixture"""
    return TestClient(app)


@pytest.fixture
async def mock_cache():
    """Mock config cache fixture"""
    cache = ConfigCache()
    await cache.load_default_flags()
    return cache


@pytest.fixture
async def mock_evaluator(mock_cache):
    """Mock flag evaluator fixture"""
    return FlagEvaluator(mock_cache)


class TestTargetingRules:
    """Test targeting rule evaluation"""
    
    def test_equals_operator(self):
        rule = TargetingRule('role', TargetingOperator.EQUALS, ['teacher'])
        
        assert rule.evaluate({'role': 'teacher'}) == True
        assert rule.evaluate({'role': 'student'}) == False
        assert rule.evaluate({}) == False
    
    def test_in_operator(self):
        rule = TargetingRule('grade_band', TargetingOperator.IN, ['6-8', '9-12'])
        
        assert rule.evaluate({'grade_band': '6-8'}) == True
        assert rule.evaluate({'grade_band': '9-12'}) == True
        assert rule.evaluate({'grade_band': 'k-5'}) == False
        assert rule.evaluate({}) == False
    
    def test_not_in_operator(self):
        rule = TargetingRule('grade_band', TargetingOperator.NOT_IN, ['k-5'])
        
        assert rule.evaluate({'grade_band': '6-8'}) == True
        assert rule.evaluate({'grade_band': 'k-5'}) == False
        assert rule.evaluate({}) == False
    
    def test_contains_operator(self):
        rule = TargetingRule('user_agent', TargetingOperator.CONTAINS, ['Chrome'])
        
        assert rule.evaluate({'user_agent': 'Mozilla/5.0 Chrome/91.0'}) == True
        assert rule.evaluate({'user_agent': 'Mozilla/5.0 Firefox/89.0'}) == False
    
    def test_greater_than_operator(self):
        rule = TargetingRule('age', TargetingOperator.GREATER_THAN, [18])
        
        assert rule.evaluate({'age': 21}) == True
        assert rule.evaluate({'age': 18}) == False
        assert rule.evaluate({'age': 16}) == False
        assert rule.evaluate({'age': 'invalid'}) == False


class TestRolloutStrategies:
    """Test rollout strategy evaluation"""
    
    def test_percentage_rollout(self):
        strategy = RolloutStrategy(RolloutType.PERCENTAGE, percentage=50.0)
        
        # Test with consistent user_id
        context = {'user_id': 'test-user-123'}
        result = strategy.evaluate(context)
        
        # Result should be consistent for same user
        assert strategy.evaluate(context) == result
        
        # Test with different users
        results = []
        for i in range(100):
            ctx = {'user_id': f'user-{i}'}
            results.append(strategy.evaluate(ctx))
        
        # Should have roughly 50% true results (allow some variance)
        true_count = sum(results)
        assert 30 <= true_count <= 70  # 20% variance allowed
    
    def test_whitelist_rollout(self):
        strategy = RolloutStrategy(RolloutType.WHITELIST, user_list=['user1', 'user2'])
        
        assert strategy.evaluate({'user_id': 'user1'}) == True
        assert strategy.evaluate({'user_id': 'user2'}) == True
        assert strategy.evaluate({'user_id': 'user3'}) == False
        assert strategy.evaluate({}) == False
    
    def test_blacklist_rollout(self):
        strategy = RolloutStrategy(RolloutType.BLACKLIST, user_list=['blocked-user'])
        
        assert strategy.evaluate({'user_id': 'normal-user'}) == True
        assert strategy.evaluate({'user_id': 'blocked-user'}) == False
        assert strategy.evaluate({}) == True


class TestFeatureFlags:
    """Test feature flag evaluation"""
    
    def test_disabled_flag_returns_default(self):
        flag = FeatureFlag(
            key='test.flag',
            name='Test Flag',
            description='Test',
            flag_type=FlagType.BOOLEAN,
            enabled=False,
            default_value=False
        )
        
        assert flag.evaluate({}) == False
        assert flag.evaluate({'role': 'teacher'}) == False
    
    def test_enabled_boolean_flag_without_rules(self):
        flag = FeatureFlag(
            key='test.flag',
            name='Test Flag',
            description='Test',
            flag_type=FlagType.BOOLEAN,
            enabled=True,
            default_value=False
        )
        
        assert flag.evaluate({}) == True
    
    def test_flag_with_targeting_rules(self):
        flag = FeatureFlag(
            key='teacher.flag',
            name='Teacher Flag',
            description='Test',
            flag_type=FlagType.BOOLEAN,
            enabled=True,
            default_value=False,
            targeting_rules=[
                TargetingRule('role', TargetingOperator.EQUALS, ['teacher'])
            ]
        )
        
        assert flag.evaluate({'role': 'teacher'}) == True
        assert flag.evaluate({'role': 'student'}) == False
        assert flag.evaluate({}) == False
    
    def test_flag_with_rollout_strategy(self):
        flag = FeatureFlag(
            key='rollout.flag',
            name='Rollout Flag',
            description='Test',
            flag_type=FlagType.BOOLEAN,
            enabled=True,
            default_value=False,
            rollout_strategy=RolloutStrategy(RolloutType.WHITELIST, user_list=['user1'])
        )
        
        assert flag.evaluate({'user_id': 'user1'}) == True
        assert flag.evaluate({'user_id': 'user2'}) == False
    
    def test_flag_with_variations(self):
        flag = FeatureFlag(
            key='provider.flag',
            name='Provider Flag',
            description='Test',
            flag_type=FlagType.STRING,
            enabled=True,
            default_value='default',
            variations={
                'premium': 'azure-speech',
                'standard': 'whisper'
            }
        )
        
        assert flag.evaluate({'variation': 'premium'}) == 'azure-speech'
        assert flag.evaluate({'variation': 'standard'}) == 'whisper'
        assert flag.evaluate({'variation': 'unknown'}) == 'default'
        assert flag.evaluate({}) == 'default'


@pytest.mark.asyncio
class TestConfigCache:
    """Test config cache functionality"""
    
    async def test_cache_initialization(self):
        cache = ConfigCache()
        await cache.initialize()
        
        flags = await cache.get_all_flags()
        assert len(flags) > 0
        assert 'chat.streaming' in flags
        assert 'game.enabled' in flags
    
    async def test_get_flag(self):
        cache = ConfigCache()
        await cache.load_default_flags()
        
        flag = await cache.get_flag('chat.streaming')
        assert flag is not None
        assert flag.key == 'chat.streaming'
        
        flag = await cache.get_flag('nonexistent')
        assert flag is None
    
    async def test_health_check(self):
        cache = ConfigCache()
        await cache.load_default_flags()
        
        is_healthy = await cache.health_check()
        assert is_healthy == True


@pytest.mark.asyncio
class TestFlagEvaluator:
    """Test flag evaluator functionality"""
    
    async def test_evaluate_single_flag(self):
        cache = ConfigCache()
        await cache.load_default_flags()
        evaluator = FlagEvaluator(cache)
        
        # Test existing flag
        value = await evaluator.evaluate_flag('game.enabled', {'grade_band': 'k-5'})
        assert value == True
        
        value = await evaluator.evaluate_flag('game.enabled', {'grade_band': 'adult'})
        assert value == True  # Default value for non-matching rule
        
        # Test non-existent flag
        value = await evaluator.evaluate_flag('nonexistent', {})
        assert value is None
    
    async def test_evaluate_multiple_flags(self):
        cache = ConfigCache()
        await cache.load_default_flags()
        evaluator = FlagEvaluator(cache)
        
        context = {
            'role': 'teacher',
            'grade_band': 'k-5',
            'tenant_tier': 'premium'
        }
        
        flags = ['game.enabled', 'sel.enabled', 'slp.asrProvider']
        results = await evaluator.evaluate_flags(flags, context)
        
        assert 'game.enabled' in results
        assert 'sel.enabled' in results
        assert 'slp.asrProvider' in results
    
    async def test_get_user_flags(self):
        cache = ConfigCache()
        await cache.load_default_flags()
        evaluator = FlagEvaluator(cache)
        
        context = {
            'user_id': 'test-user',
            'role': 'teacher',
            'grade_band': 'k-5'
        }
        
        results = await evaluator.get_user_flags(context)
        
        # Should return all flags with their evaluated values
        assert len(results) > 0
        assert 'chat.streaming' in results
        assert 'game.enabled' in results


class TestAPIEndpoints:
    """Test API endpoints"""
    
    def test_health_endpoint(self, client):
        response = client.get("/health")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "healthy"
    
    def test_readiness_endpoint(self, client):
        response = client.get("/readiness")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "ready"
        assert "flag_count" in data
    
    def test_list_flags_endpoint(self, client):
        response = client.get("/flags")
        assert response.status_code == 200
        flags = response.json()
        assert isinstance(flags, list)
        assert len(flags) > 0
        
        # Check first flag structure
        flag = flags[0]
        assert "key" in flag
        assert "name" in flag
        assert "flag_type" in flag
    
    def test_get_flag_definition(self, client):
        response = client.get("/flags/chat.streaming")
        assert response.status_code == 200
        flag = response.json()
        assert flag["key"] == "chat.streaming"
        assert flag["name"] == "Chat Streaming"
    
    def test_get_nonexistent_flag(self, client):
        response = client.get("/flags/nonexistent")
        assert response.status_code == 404
    
    def test_evaluate_single_flag(self, client):
        headers = {
            'x-user-id': 'test-user',
            'x-role': 'teacher',
            'x-grade-band': 'k-5'
        }
        
        response = client.get("/flags/game.enabled/evaluate", headers=headers)
        assert response.status_code == 200
        data = response.json()
        assert data["flag"] == "game.enabled"
        assert "value" in data
    
    def test_evaluate_multiple_flags(self, client):
        payload = {
            "flags": ["chat.streaming", "game.enabled"],
            "context": {
                "user_id": "test-user",
                "role": "teacher",
                "grade_band": "k-5"
            }
        }
        
        response = client.post("/flags/evaluate", json=payload)
        assert response.status_code == 200
        data = response.json()
        assert "flags" in data
        assert "chat.streaming" in data["flags"]
        assert "game.enabled" in data["flags"]
    
    def test_get_user_flags(self, client):
        headers = {
            'x-user-id': 'test-user',
            'x-role': 'teacher'
        }
        
        response = client.get("/flags/user", headers=headers)
        assert response.status_code == 200
        data = response.json()
        assert "flags" in data
        assert len(data["flags"]) > 0
    
    def test_chat_config_endpoint(self, client):
        headers = {
            'x-grade-band': '9-12'
        }
        
        response = client.get("/config/chat", headers=headers)
        assert response.status_code == 200
        data = response.json()
        assert "streaming_enabled" in data
        assert "provider_order" in data
    
    def test_games_config_endpoint(self, client):
        headers = {
            'x-grade-band': 'k-5'
        }
        
        response = client.get("/config/games", headers=headers)
        assert response.status_code == 200
        data = response.json()
        assert "games_enabled" in data
    
    def test_debug_context_endpoint(self, client):
        headers = {
            'x-user-id': 'test-user',
            'x-role': 'teacher'
        }
        
        response = client.get("/debug/context", headers=headers)
        assert response.status_code == 200
        data = response.json()
        assert "context" in data
        assert data["context"]["user_id"] == "test-user"
        assert data["context"]["role"] == "teacher"


class TestEvaluationContext:
    """Test evaluation context validation"""
    
    def test_valid_grade_band(self):
        context = EvaluationContext(grade_band='k-5')
        assert context.grade_band == 'k-5'
        
        context = EvaluationContext(grade_band='6-8')
        assert context.grade_band == '6-8'
    
    def test_invalid_grade_band(self):
        with pytest.raises(ValueError):
            EvaluationContext(grade_band='invalid')
    
    def test_context_with_custom_attributes(self):
        context = EvaluationContext(
            user_id='test-user',
            custom_attributes={'feature_beta': True, 'region': 'us-east'}
        )
        
        assert context.user_id == 'test-user'
        assert context.custom_attributes['feature_beta'] == True
        assert context.custom_attributes['region'] == 'us-east'


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
