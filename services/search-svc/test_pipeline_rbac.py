import pytest
import asyncio
from unittest.mock import AsyncMock, Mock, patch, MagicMock
from datetime import datetime, timezone
import json
from typing import Dict, Any, List

from pipeline.cdc_consumer import CDCConsumer
from pipeline.transform import DataTransformer, RBACFilter


class TestCDCConsumer:
    """Test suite for CDC consumer pipeline."""
    
    @pytest.fixture
    def consumer(self):
        """Create a test CDC consumer instance."""
        config = {
            "postgres": {
                "host": "localhost",
                "port": 5432,
                "database": "test_db",
                "user": "test_user",
                "password": "test_pass"
            },
            "opensearch": {
                "host": "localhost",
                "port": 9200
            },
            "batch_size": 10,
            "checkpoint_interval": 5
        }
        return CDCConsumer(config)
    
    @pytest.fixture
    def sample_events(self):
        """Sample outbox events for testing."""
        return [
            {
                "id": 1,
                "aggregate_type": "lesson",
                "aggregate_id": "lesson-123",
                "event_type": "lesson_created",
                "event_data": {
                    "id": "lesson-123",
                    "title": "Introduction to Algebra",
                    "subject": "mathematics",
                    "grade_levels": [8, 9],
                    "content": "Learn basic algebraic equations and solve for x.",
                    "difficulty": "intermediate",
                    "created_by": "teacher-456",
                    "tenant_id": "school-789"
                },
                "created_at": datetime.now(timezone.utc),
                "processed": False
            },
            {
                "id": 2,
                "aggregate_type": "lesson",
                "aggregate_id": "lesson-124", 
                "event_type": "lesson_updated",
                "event_data": {
                    "id": "lesson-124",
                    "title": "Shakespeare's Romeo and Juliet",
                    "subject": "english",
                    "grade_levels": [9, 10, 11],
                    "content": "Analyze themes and characters in Romeo and Juliet.",
                    "difficulty": "advanced",
                    "created_by": "teacher-789",
                    "tenant_id": "school-789"
                },
                "created_at": datetime.now(timezone.utc),
                "processed": False
            }
        ]
    
    @pytest.mark.asyncio
    async def test_fetch_events_success(self, consumer, sample_events):
        """Test successful event fetching from outbox."""
        with patch.object(consumer, '_get_pg_connection') as mock_conn:
            mock_cursor = AsyncMock()
            mock_cursor.fetchall.return_value = sample_events
            mock_conn.return_value.cursor.return_value.__aenter__.return_value = mock_cursor
            
            events = await consumer._fetch_events()
            
            assert len(events) == 2
            assert events[0]['aggregate_type'] == 'lesson'
            assert events[1]['subject'] == 'english'
    
    @pytest.mark.asyncio
    async def test_fetch_events_empty(self, consumer):
        """Test fetching when no events are available."""
        with patch.object(consumer, '_get_pg_connection') as mock_conn:
            mock_cursor = AsyncMock()
            mock_cursor.fetchall.return_value = []
            mock_conn.return_value.cursor.return_value.__aenter__.return_value = mock_cursor
            
            events = await consumer._fetch_events()
            
            assert events == []
    
    @pytest.mark.asyncio
    async def test_process_events_success(self, consumer, sample_events):
        """Test successful event processing pipeline."""
        with patch.object(consumer, '_transform_event') as mock_transform, \
             patch.object(consumer, '_index_documents') as mock_index:
            
            mock_transform.side_effect = lambda event: {
                "id": event["event_data"]["id"],
                "title": event["event_data"]["title"],
                "subject": event["event_data"]["subject"],
                "content": event["event_data"]["content"],
                "grade_levels": event["event_data"]["grade_levels"],
                "tenant_id": event["event_data"]["tenant_id"]
            }
            mock_index.return_value = True
            
            result = await consumer._process_events(sample_events)
            
            assert result == True
            assert mock_transform.call_count == 2
            mock_index.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_transform_event_with_rbac(self, consumer):
        """Test event transformation with RBAC filtering."""
        event = {
            "event_type": "lesson_created",
            "event_data": {
                "id": "lesson-123",
                "title": "Math Lesson",
                "subject": "mathematics", 
                "content": "Basic algebra concepts",
                "created_by": "teacher-456",
                "tenant_id": "school-789",
                "sensitive_data": "PII information"
            }
        }
        
        consumer.transformer = Mock()
        consumer.rbac_filter = Mock()
        
        transformed_data = {"transformed": "data"}
        filtered_data = {"filtered": "data"}
        
        consumer.transformer.transform.return_value = transformed_data
        consumer.rbac_filter.apply_rbac.return_value = filtered_data
        
        result = await consumer._transform_event(event)
        
        assert result == filtered_data
        consumer.transformer.transform.assert_called_once_with(event["event_data"])
        consumer.rbac_filter.apply_rbac.assert_called_once()


class TestDataTransformer:
    """Test suite for data transformation pipeline."""
    
    @pytest.fixture
    def transformer(self):
        """Create a test data transformer."""
        return DataTransformer()
    
    def test_transform_math_content(self, transformer):
        """Test transformation of mathematics content."""
        lesson_data = {
            "id": "lesson-123",
            "title": "Algebra Basics",
            "subject": "mathematics",
            "content": "Solve for x: 2x + 5 = 15",
            "grade_levels": [8, 9],
            "difficulty": "intermediate"
        }
        
        result = transformer.transform(lesson_data)
        
        assert result["subject"] == "mathematics"
        assert "algebra" in result["processed_content"].lower()
        assert result["search_keywords"] == ["algebra", "equation", "solve", "variable"]
        assert result["content_type"] == "math_problem"
    
    def test_transform_ela_content(self, transformer):
        """Test transformation of English Language Arts content."""
        lesson_data = {
            "id": "lesson-124", 
            "title": "Literary Analysis",
            "subject": "english",
            "content": "Analyze the metaphors in Shakespeare's sonnets.",
            "grade_levels": [10, 11],
            "difficulty": "advanced"
        }
        
        result = transformer.transform(lesson_data)
        
        assert result["subject"] == "english"
        assert "literature" in result["processed_content"].lower()
        assert "metaphor" in result["search_keywords"]
        assert result["content_type"] == "literary_analysis"
    
    def test_normalize_content(self, transformer):
        """Test content normalization."""
        content = "This has   extra   spaces\nand\nnewlines."
        
        result = transformer._normalize_content(content)
        
        assert "extra   spaces" not in result
        assert "\n" not in result
        assert result == "This has extra spaces and newlines."
    
    def test_extract_math_keywords(self, transformer):
        """Test mathematical keyword extraction."""
        content = "Find the area of a triangle with base 10 and height 5."
        
        keywords = transformer._extract_math_keywords(content)
        
        expected = ["area", "triangle", "base", "height", "geometry"]
        assert all(kw in keywords for kw in expected)
    
    def test_extract_ela_keywords(self, transformer):
        """Test ELA keyword extraction.""" 
        content = "The protagonist struggles with internal conflict throughout the narrative."
        
        keywords = transformer._extract_ela_keywords(content)
        
        expected = ["protagonist", "conflict", "narrative", "character", "story"]
        assert all(kw in keywords for kw in expected)


class TestRBACFilter:
    """Test suite for RBAC filtering."""
    
    @pytest.fixture
    def rbac_filter(self):
        """Create a test RBAC filter."""
        rules = {
            "student": {
                "allowed_fields": ["id", "title", "subject", "content", "grade_levels"],
                "forbidden_fields": ["created_by", "sensitive_data"],
                "masking_strategy": "remove"
            },
            "teacher": {
                "allowed_fields": ["id", "title", "subject", "content", "grade_levels", "created_by", "difficulty"],
                "forbidden_fields": ["sensitive_data"],
                "masking_strategy": "hash"
            },
            "admin": {
                "allowed_fields": "*",
                "forbidden_fields": [],
                "masking_strategy": "none"
            }
        }
        return RBACFilter(rules)
    
    def test_student_access_filtering(self, rbac_filter):
        """Test RBAC filtering for student role."""
        document = {
            "id": "lesson-123",
            "title": "Math Lesson",
            "subject": "mathematics",
            "content": "Learn algebra",
            "grade_levels": [8, 9],
            "created_by": "teacher-456",
            "sensitive_data": "PII information"
        }
        
        result = rbac_filter.apply_rbac(document, "student", "school-789")
        
        assert "created_by" not in result
        assert "sensitive_data" not in result
        assert result["title"] == "Math Lesson"
        assert result["tenant_access"]["school-789"] == True
    
    def test_teacher_access_filtering(self, rbac_filter):
        """Test RBAC filtering for teacher role."""
        document = {
            "id": "lesson-123",
            "title": "Math Lesson", 
            "subject": "mathematics",
            "content": "Learn algebra",
            "created_by": "teacher-456",
            "sensitive_data": "PII information"
        }
        
        result = rbac_filter.apply_rbac(document, "teacher", "school-789")
        
        assert result["created_by"] == "teacher-456"
        assert "sensitive_data" not in result
        assert result["rbac_hash"] is not None
    
    def test_admin_full_access(self, rbac_filter):
        """Test RBAC filtering for admin role."""
        document = {
            "id": "lesson-123",
            "title": "Math Lesson",
            "sensitive_data": "PII information",
            "created_by": "teacher-456"
        }
        
        result = rbac_filter.apply_rbac(document, "admin", "school-789")
        
        assert result["sensitive_data"] == "PII information"
        assert result["created_by"] == "teacher-456"
        assert result["rbac_level"] == "admin"
    
    def test_field_masking_strategies(self, rbac_filter):
        """Test different field masking strategies."""
        # Test remove strategy
        data = {"field": "sensitive"}
        masked = rbac_filter._mask_field(data, "field", "remove")
        assert "field" not in masked
        
        # Test hash strategy
        data = {"field": "sensitive"}
        masked = rbac_filter._mask_field(data, "field", "hash")
        assert masked["field"] != "sensitive"
        assert len(masked["field"]) == 64  # SHA-256 hex length
        
        # Test redact strategy
        data = {"field": "sensitive"}
        masked = rbac_filter._mask_field(data, "field", "redact")
        assert masked["field"] == "[REDACTED]"
    
    def test_tenant_isolation(self, rbac_filter):
        """Test tenant-based access control."""
        document = {"id": "lesson-123", "tenant_id": "school-789"}
        
        # Same tenant access
        result = rbac_filter.apply_rbac(document, "student", "school-789")
        assert result["tenant_access"]["school-789"] == True
        
        # Different tenant access 
        result = rbac_filter.apply_rbac(document, "student", "school-456")
        assert result["tenant_access"]["school-456"] == False
    
    def test_sensitivity_classification(self, rbac_filter):
        """Test automatic sensitivity classification."""
        # High sensitivity
        document = {"ssn": "123-45-6789", "email": "user@example.com"}
        classification = rbac_filter._classify_sensitivity(document)
        assert classification == "high"
        
        # Medium sensitivity
        document = {"created_by": "user-123", "phone": "555-1234"}
        classification = rbac_filter._classify_sensitivity(document)
        assert classification == "medium"
        
        # Low sensitivity
        document = {"title": "Public Lesson", "subject": "math"}
        classification = rbac_filter._classify_sensitivity(document)
        assert classification == "low"


class TestPipelineIntegration:
    """Integration tests for the complete pipeline."""
    
    @pytest.mark.asyncio
    async def test_end_to_end_processing(self):
        """Test complete end-to-end pipeline processing."""
        config = {
            "postgres": {"host": "localhost"},
            "opensearch": {"host": "localhost"},
            "batch_size": 5
        }
        
        consumer = CDCConsumer(config)
        
        # Mock external dependencies
        with patch.object(consumer, '_get_pg_connection') as mock_pg, \
             patch.object(consumer, '_get_opensearch_client') as mock_os:
            
            # Setup mock data
            events = [
                {
                    "id": 1,
                    "event_type": "lesson_created",
                    "event_data": {
                        "id": "lesson-123",
                        "title": "Test Lesson",
                        "subject": "mathematics",
                        "content": "Test content"
                    }
                }
            ]
            
            mock_cursor = AsyncMock()
            mock_cursor.fetchall.return_value = events
            mock_pg.return_value.cursor.return_value.__aenter__.return_value = mock_cursor
            
            mock_os_client = AsyncMock()
            mock_os_client.bulk.return_value = {"errors": False}
            mock_os.return_value = mock_os_client
            
            # Run pipeline
            await consumer.start()
            
            # Verify calls
            mock_os_client.bulk.assert_called()
    
    @pytest.mark.asyncio 
    async def test_error_handling_and_recovery(self):
        """Test pipeline error handling and recovery."""
        config = {"postgres": {"host": "localhost"}, "opensearch": {"host": "localhost"}}
        consumer = CDCConsumer(config)
        
        with patch.object(consumer, '_fetch_events') as mock_fetch:
            mock_fetch.side_effect = [
                Exception("Database connection error"),
                [{"id": 1, "event_type": "test"}]  # Recovery
            ]
            
            # Should handle error gracefully
            with patch('asyncio.sleep'):  # Speed up test
                await consumer._run_once()
                
            # Should retry and succeed
            assert consumer.is_healthy == True
    
    def test_rbac_integration_with_transformation(self):
        """Test RBAC integration with data transformation."""
        transformer = DataTransformer()
        rbac_filter = RBACFilter({
            "student": {
                "allowed_fields": ["id", "title", "content"],
                "forbidden_fields": ["created_by"],
                "masking_strategy": "remove"
            }
        })
        
        # Transform data
        lesson_data = {
            "id": "lesson-123",
            "title": "Math Lesson",
            "subject": "mathematics", 
            "content": "2 + 2 = 4",
            "created_by": "teacher-456"
        }
        
        transformed = transformer.transform(lesson_data)
        filtered = rbac_filter.apply_rbac(transformed, "student", "school-789")
        
        # Verify transformation and RBAC
        assert "created_by" not in filtered
        assert filtered["title"] == "Math Lesson"
        assert "search_keywords" in filtered
    
    @pytest.mark.asyncio
    async def test_checkpoint_management(self):
        """Test CDC checkpoint management."""
        consumer = CDCConsumer({"checkpoint_interval": 2})
        
        with patch.object(consumer, '_save_checkpoint') as mock_save:
            # Process events that should trigger checkpoint
            events = [{"id": i} for i in range(5)]
            await consumer._process_events(events)
            
            # Verify checkpoint was saved
            mock_save.assert_called()
    
    @pytest.mark.asyncio
    async def test_bulk_indexing_optimization(self):
        """Test bulk indexing performance optimization."""
        consumer = CDCConsumer({"batch_size": 100})
        
        # Create large batch of documents
        docs = [{"id": f"doc-{i}", "content": f"Content {i}"} for i in range(100)]
        
        with patch.object(consumer, '_get_opensearch_client') as mock_client:
            mock_client.return_value.bulk.return_value = {"errors": False}
            
            result = await consumer._index_documents(docs)
            
            # Verify bulk operation
            assert result == True
            mock_client.return_value.bulk.assert_called_once()


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
