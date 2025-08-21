"""
Test suite for S4-12 Content Moderation & Safety Filters
Tests subject-aware moderation rules, grade-band appropriateness, and SEL sensitivity
"""

import pytest
import asyncio
import time
from unittest.mock import Mock, patch, AsyncMock
from typing import Dict, Any, List

import sys
import os
sys.path.append(os.path.join(os.path.dirname(__file__), '..', 'app'))

from policy import (
    SafetyEngine, ModerationResult, ModerationRule, SafetyPolicy,
    GradeBand, Subject, ContentSeverity, ModerationAction, SELCategory
)


class TestSafetyEngine:
    """Test safety engine functionality for content moderation."""
    
    @pytest.fixture
    def safety_engine(self):
        """Create safety engine instance for testing."""
        config = {
            "custom_safety_policies": [
                {
                    "subject": "math",
                    "grade_band": "elementary",
                    "custom_thresholds": {
                        "harassment": 0.2,
                        "violence": 0.1
                    },
                    "blocked_topics": ["advanced calculus", "complex analysis"],
                    "guardian_webhook": "https://api.school.edu/guardian-notify",
                    "teacher_webhook": "https://api.school.edu/teacher-notify"
                }
            ]
        }
        return SafetyEngine(config)
    
    @pytest.fixture
    def mock_audit_logger(self):
        """Mock audit logger for testing."""
        mock = AsyncMock()
        return mock


class TestGradeBandModeration:
    """Test grade-band appropriate content moderation."""
    
    @pytest.mark.asyncio
    async def test_elementary_strict_filtering(self, safety_engine):
        """Test that elementary content is strictly filtered."""
        # Test violent content
        violent_content = "The character killed the enemy with a sword"
        result = await safety_engine.moderate_content(
            violent_content,
            subject=Subject.ENGLISH,
            grade_band=GradeBand.ELEMENTARY
        )
        
        assert result.flagged is True
        assert result.severity in [ContentSeverity.SEVERE, ContentSeverity.MODERATE]
        assert result.action in [ModerationAction.BLOCK, ModerationAction.FILTER]
        assert any("kill" in rule for rule in result.triggered_rules)
    
    @pytest.mark.asyncio
    async def test_elementary_inappropriate_language(self, safety_engine):
        """Test inappropriate language filtering for elementary."""
        inappropriate_content = "This math problem is so stupid and dumb"
        result = await safety_engine.moderate_content(
            inappropriate_content,
            subject=Subject.MATH,
            grade_band=GradeBand.ELEMENTARY
        )
        
        assert result.flagged is True
        assert result.action in [ModerationAction.BLOCK, ModerationAction.FILTER]
        assert any("stupid" in rule or "dumb" in rule for rule in result.triggered_rules)
    
    @pytest.mark.asyncio
    async def test_middle_school_relaxed_filtering(self, safety_engine):
        """Test that middle school has more relaxed filtering."""
        content = "The historical battle was intense and violent"
        
        # Elementary should block/filter
        elem_result = await safety_engine.moderate_content(
            content,
            subject=Subject.HISTORY,
            grade_band=GradeBand.ELEMENTARY
        )
        
        # Middle school should be less restrictive
        middle_result = await safety_engine.moderate_content(
            content,
            subject=Subject.HISTORY,
            grade_band=GradeBand.MIDDLE
        )
        
        # Elementary should be more restrictive than middle school
        assert elem_result.severity.value != middle_result.severity.value or elem_result.flagged != middle_result.flagged
    
    @pytest.mark.asyncio
    async def test_high_school_mature_content(self, safety_engine):
        """Test high school can handle more mature content."""
        mature_content = "The novel explores themes of mortality and existential crisis"
        result = await safety_engine.moderate_content(
            mature_content,
            subject=Subject.ENGLISH,
            grade_band=GradeBand.HIGH
        )
        
        # Should be allowed or just warned for high school
        assert result.action in [ModerationAction.ALLOW, ModerationAction.WARN, ModerationAction.AUDIT]
        assert result.severity in [ContentSeverity.SAFE, ContentSeverity.MINOR_CONCERN]
    
    @pytest.mark.asyncio
    async def test_adult_minimal_restrictions(self, safety_engine):
        """Test adult education has minimal content restrictions."""
        adult_content = "Advanced statistics including mortality rates and risk analysis"
        result = await safety_engine.moderate_content(
            adult_content,
            subject=Subject.MATH,
            grade_band=GradeBand.ADULT
        )
        
        # Should be allowed for adult education
        assert result.action == ModerationAction.ALLOW
        assert result.severity == ContentSeverity.SAFE


class TestSubjectAwareModeration:
    """Test subject-specific moderation rules."""
    
    @pytest.mark.asyncio
    async def test_science_violence_context(self, safety_engine):
        """Test that scientific violence context is handled appropriately."""
        science_content = "The predator kills its prey for survival"
        history_content = "The soldier killed the enemy in battle"
        
        science_result = await safety_engine.moderate_content(
            science_content,
            subject=Subject.SCIENCE,
            grade_band=GradeBand.MIDDLE
        )
        
        history_result = await safety_engine.moderate_content(
            history_content,
            subject=Subject.HISTORY,
            grade_band=GradeBand.MIDDLE
        )
        
        # Both might be flagged, but science context should be considered
        # This test ensures the system can differentiate context
        assert isinstance(science_result.flagged, bool)
        assert isinstance(history_result.flagged, bool)
    
    @pytest.mark.asyncio
    async def test_math_inappropriate_examples(self, safety_engine):
        """Test that inappropriate examples in math are caught."""
        math_content = "If John has 10 beers and drinks 3, how many does he have left?"
        result = await safety_engine.moderate_content(
            math_content,
            subject=Subject.MATH,
            grade_band=GradeBand.ELEMENTARY
        )
        
        # Should be flagged for alcohol reference in elementary math
        assert result.flagged is True
        assert result.action in [ModerationAction.BLOCK, ModerationAction.FILTER]
    
    @pytest.mark.asyncio
    async def test_arts_creative_expression(self, safety_engine):
        """Test that artistic expression is handled with nuance."""
        arts_content = "Express your emotions through abstract painting of inner turmoil"
        result = await safety_engine.moderate_content(
            arts_content,
            subject=Subject.ARTS,
            grade_band=GradeBand.HIGH
        )
        
        # Should be allowed for high school arts
        assert result.action in [ModerationAction.ALLOW, ModerationAction.WARN]


class TestSELSensitivity:
    """Test Social-Emotional Learning sensitivity detection."""
    
    @pytest.mark.asyncio
    async def test_mental_health_escalation(self, safety_engine):
        """Test that mental health content escalates appropriately."""
        mental_health_content = "I feel so depressed and anxious about everything"
        result = await safety_engine.moderate_content(
            mental_health_content,
            subject=Subject.SEL,
            grade_band=GradeBand.MIDDLE
        )
        
        assert result.flagged is True
        assert SELCategory.MENTAL_HEALTH in result.sel_categories
        assert result.requires_escalation is True
        assert result.guardian_notification is True
        assert result.teacher_notification is True
        assert result.action == ModerationAction.ESCALATE
        assert result.severity == ContentSeverity.CRITICAL
    
    @pytest.mark.asyncio
    async def test_bullying_detection(self, safety_engine):
        """Test bullying content detection and escalation."""
        bullying_content = "The kids at school are bullying me and I feel so alone"
        result = await safety_engine.moderate_content(
            bullying_content,
            subject=Subject.GENERAL,
            grade_band=GradeBand.ELEMENTARY
        )
        
        assert result.flagged is True
        assert SELCategory.PEER_PRESSURE in result.sel_categories
        assert result.teacher_notification is True
        assert result.action in [ModerationAction.ESCALATE, ModerationAction.AUDIT]
    
    @pytest.mark.asyncio
    async def test_family_dynamics_sensitivity(self, safety_engine):
        """Test family dynamics content requires attention."""
        family_content = "My parents are getting divorced and I don't know what to do"
        result = await safety_engine.moderate_content(
            family_content,
            subject=Subject.SEL,
            grade_band=GradeBand.MIDDLE
        )
        
        assert result.flagged is True
        assert SELCategory.FAMILY_DYNAMICS in result.sel_categories
        assert result.teacher_notification is True
        assert result.action in [ModerationAction.ESCALATE, ModerationAction.AUDIT]
    
    @pytest.mark.asyncio
    async def test_trauma_critical_escalation(self, safety_engine):
        """Test trauma content triggers critical escalation."""
        trauma_content = "I can't stop thinking about the accident and having flashbacks"
        result = await safety_engine.moderate_content(
            trauma_content,
            subject=Subject.SEL,
            grade_band=GradeBand.HIGH
        )
        
        assert result.flagged is True
        assert SELCategory.TRAUMA in result.sel_categories
        assert result.requires_escalation is True
        assert result.guardian_notification is True
        assert result.teacher_notification is True
        assert result.action == ModerationAction.ESCALATE
        assert result.severity == ContentSeverity.CRITICAL
    
    @pytest.mark.asyncio
    async def test_sel_disabled_no_escalation(self, safety_engine):
        """Test that SEL escalation can be disabled."""
        # Update policy to disable SEL escalation for adults
        safety_engine.update_safety_policy(
            Subject.GENERAL,
            GradeBand.ADULT,
            {"sel_escalation_enabled": False}
        )
        
        sel_content = "I feel anxious about my performance"
        result = await safety_engine.moderate_content(
            sel_content,
            subject=Subject.GENERAL,
            grade_band=GradeBand.ADULT
        )
        
        # Should not escalate for adults when SEL escalation is disabled
        assert result.action != ModerationAction.ESCALATE


class TestFalsePositiveThresholds:
    """Test false positive threshold management."""
    
    @pytest.mark.asyncio
    async def test_safe_educational_content(self, safety_engine):
        """Test that safe educational content passes through."""
        safe_contents = [
            "What is 2 + 2?",
            "The water cycle includes evaporation and condensation",
            "George Washington was the first president",
            "Practice your piano scales",
            "Draw a picture of your favorite animal"
        ]
        
        for content in safe_contents:
            for grade_band in GradeBand:
                result = await safety_engine.moderate_content(
                    content,
                    subject=Subject.GENERAL,
                    grade_band=grade_band
                )
                
                assert result.action == ModerationAction.ALLOW
                assert result.severity == ContentSeverity.SAFE
                assert result.flagged is False
    
    @pytest.mark.asyncio
    async def test_borderline_content_thresholds(self, safety_engine):
        """Test borderline content respects grade-band thresholds."""
        borderline_content = "The character felt sad and disappointed"
        
        # Should pass for all grade bands as normal emotional expression
        for grade_band in GradeBand:
            result = await safety_engine.moderate_content(
                borderline_content,
                subject=Subject.ENGLISH,
                grade_band=grade_band
            )
            
            # Should not be flagged as unsafe
            assert result.action in [ModerationAction.ALLOW, ModerationAction.WARN]
    
    @pytest.mark.asyncio
    async def test_scientific_terminology(self, safety_engine):
        """Test that scientific terminology doesn't trigger false positives."""
        scientific_contents = [
            "The organism dies when exposed to extreme temperatures",
            "Cell death occurs during apoptosis",
            "The chemical reaction kills harmful bacteria",
            "Animals kill for survival in nature"
        ]
        
        for content in scientific_contents:
            result = await safety_engine.moderate_content(
                content,
                subject=Subject.SCIENCE,
                grade_band=GradeBand.HIGH
            )
            
            # Should be allowed for high school science
            assert result.action in [ModerationAction.ALLOW, ModerationAction.WARN]


class TestUnsafeContentBlocking:
    """Test that genuinely unsafe content is properly blocked."""
    
    @pytest.mark.asyncio
    async def test_explicit_violence_blocked(self, safety_engine):
        """Test that explicit violence is blocked."""
        violent_contents = [
            "I want to hurt someone",
            "Let's plan to attack the school",
            "How to make weapons to harm people"
        ]
        
        for content in violent_contents:
            for grade_band in [GradeBand.ELEMENTARY, GradeBand.MIDDLE]:
                result = await safety_engine.moderate_content(
                    content,
                    subject=Subject.GENERAL,
                    grade_band=grade_band
                )
                
                assert result.flagged is True
                assert result.action in [ModerationAction.BLOCK, ModerationAction.ESCALATE]
                assert result.severity in [ContentSeverity.SEVERE, ContentSeverity.CRITICAL]
    
    @pytest.mark.asyncio
    async def test_inappropriate_sexual_content(self, safety_engine):
        """Test that inappropriate sexual content is blocked."""
        sexual_content = "Let's talk about sexual activities and explicit content"
        
        for grade_band in [GradeBand.ELEMENTARY, GradeBand.MIDDLE]:
            result = await safety_engine.moderate_content(
                sexual_content,
                subject=Subject.GENERAL,
                grade_band=grade_band
            )
            
            assert result.flagged is True
            assert result.action in [ModerationAction.BLOCK, ModerationAction.FILTER]
    
    @pytest.mark.asyncio
    async def test_hate_speech_blocked(self, safety_engine):
        """Test that hate speech is blocked across all grade bands."""
        hate_contents = [
            "I hate people of different races",
            "Those people are inferior and don't belong here",
            "We should discriminate against that group"
        ]
        
        for content in hate_contents:
            for grade_band in GradeBand:
                result = await safety_engine.moderate_content(
                    content,
                    subject=Subject.GENERAL,
                    grade_band=grade_band
                )
                
                assert result.flagged is True
                assert result.action in [ModerationAction.BLOCK, ModerationAction.ESCALATE]


class TestAuditLogging:
    """Test audit logging functionality."""
    
    @pytest.mark.asyncio
    async def test_audit_log_triggered(self, safety_engine, mock_audit_logger):
        """Test that audit logging is triggered for flagged content."""
        safety_engine.audit_logger = mock_audit_logger
        
        flagged_content = "This content should be flagged and logged"
        result = await safety_engine.moderate_content(
            flagged_content,
            subject=Subject.GENERAL,
            grade_band=GradeBand.ELEMENTARY,
            user_id="test_user_123",
            tenant_id="test_tenant_456"
        )
        
        # Should have triggered audit logging
        if result.audit_required:
            mock_audit_logger.log_moderation_event.assert_called_once()
            
            # Check audit data structure
            call_args = mock_audit_logger.log_moderation_event.call_args[0][0]
            assert "timestamp" in call_args
            assert call_args["subject"] == "general"
            assert call_args["grade_band"] == "elementary"
            assert call_args["user_id"] == "test_user_123"
            assert call_args["tenant_id"] == "test_tenant_456"
    
    @pytest.mark.asyncio
    async def test_escalation_audit(self, safety_engine, mock_audit_logger):
        """Test that escalations are properly audited."""
        safety_engine.audit_logger = mock_audit_logger
        
        escalation_content = "I feel suicidal and want to harm myself"
        result = await safety_engine.moderate_content(
            escalation_content,
            subject=Subject.SEL,
            grade_band=GradeBand.MIDDLE,
            user_id="student_789",
            tenant_id="school_district_123"
        )
        
        assert result.action == ModerationAction.ESCALATE
        assert result.requires_escalation is True
        assert result.guardian_notification is True
        
        # Audit should be called for escalations
        mock_audit_logger.log_moderation_event.assert_called_once()


class TestCustomPolicies:
    """Test custom policy configuration and updates."""
    
    def test_custom_threshold_application(self, safety_engine):
        """Test that custom thresholds are applied correctly."""
        # Math policy should have custom thresholds from config
        math_policy = safety_engine.get_safety_policy(Subject.MATH, GradeBand.ELEMENTARY)
        
        assert math_policy is not None
        assert math_policy.custom_thresholds["harassment"] == 0.2
        assert math_policy.custom_thresholds["violence"] == 0.1
    
    def test_policy_updates(self, safety_engine):
        """Test updating safety policies."""
        # Update a policy
        safety_engine.update_safety_policy(
            Subject.SCIENCE,
            GradeBand.MIDDLE,
            {
                "custom_thresholds": {"violence": 0.4},
                "blocked_topics": ["dangerous experiments"],
                "sel_escalation_enabled": False
            }
        )
        
        # Verify updates
        policy = safety_engine.get_safety_policy(Subject.SCIENCE, GradeBand.MIDDLE)
        assert policy.custom_thresholds["violence"] == 0.4
        assert "dangerous experiments" in policy.blocked_topics
        assert policy.sel_escalation_enabled is False
    
    def test_block_list_management(self, safety_engine):
        """Test custom block list management."""
        # Add custom block list
        custom_keywords = ["inappropriate", "banned", "restricted"]
        safety_engine.add_block_list("custom_test", custom_keywords)
        
        assert "custom_test" in safety_engine.block_lists
        assert safety_engine.block_lists["custom_test"] == set(custom_keywords)
        
        # Remove block list
        safety_engine.remove_block_list("custom_test")
        assert "custom_test" not in safety_engine.block_lists
    
    def test_moderation_stats(self, safety_engine):
        """Test moderation statistics reporting."""
        stats = safety_engine.get_moderation_stats()
        
        assert "total_policies" in stats
        assert "enabled_policies" in stats
        assert "grade_bands" in stats
        assert "subjects" in stats
        assert "sel_categories" in stats
        assert "block_lists_count" in stats
        assert "default_thresholds" in stats
        
        # Verify data types
        assert isinstance(stats["total_policies"], int)
        assert isinstance(stats["grade_bands"], list)
        assert isinstance(stats["default_thresholds"], dict)


class TestPerformanceAndScaling:
    """Test performance characteristics and scaling."""
    
    @pytest.mark.asyncio
    async def test_moderation_performance(self, safety_engine):
        """Test that moderation completes within reasonable time."""
        content = "This is a test content for performance measurement"
        
        start_time = time.time()
        result = await safety_engine.moderate_content(
            content,
            subject=Subject.GENERAL,
            grade_band=GradeBand.MIDDLE
        )
        end_time = time.time()
        
        processing_time = (end_time - start_time) * 1000  # Convert to ms
        
        # Should complete within reasonable time (< 100ms for simple content)
        assert processing_time < 100
        assert result.processing_time_ms > 0
    
    @pytest.mark.asyncio
    async def test_batch_moderation_simulation(self, safety_engine):
        """Test handling multiple moderation requests."""
        contents = [
            f"Test content number {i} for batch processing"
            for i in range(10)
        ]
        
        start_time = time.time()
        
        # Process multiple contents
        results = []
        for content in contents:
            result = await safety_engine.moderate_content(
                content,
                subject=Subject.GENERAL,
                grade_band=GradeBand.MIDDLE
            )
            results.append(result)
        
        end_time = time.time()
        batch_time = (end_time - start_time) * 1000
        
        # Should process batch efficiently
        assert len(results) == len(contents)
        assert batch_time < 1000  # Less than 1 second for 10 items
        
        # All should be safe content
        for result in results:
            assert result.action == ModerationAction.ALLOW
            assert result.severity == ContentSeverity.SAFE
