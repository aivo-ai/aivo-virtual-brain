"""
Tests for Weekly Digest Notification Sending (S5-07)
"""
import pytest
import asyncio
from datetime import datetime, timedelta
from unittest.mock import Mock, patch, AsyncMock, MagicMock
from uuid import uuid4
import json

from services.notification_svc.app.cron_weekly_digest import WeeklyDigestScheduler
from services.notification_svc.app.models import (
    DigestSubscription, NotificationType, NotificationPriority, User
)

class TestWeeklyDigestScheduler:
    """Test cases for Weekly Digest Scheduler."""
    
    @pytest.fixture
    def mock_analytics_service_url(self):
        """Mock analytics service URL."""
        return "http://analytics-service:8000"
    
    @pytest.fixture
    def mock_scheduler(self):
        """Mock APScheduler instance."""
        return Mock()
    
    @pytest.fixture
    def mock_mailer(self):
        """Mock mailer service."""
        return Mock()
    
    @pytest.fixture
    def digest_scheduler(self, mock_analytics_service_url, mock_scheduler):
        """Create WeeklyDigestScheduler instance."""
        return WeeklyDigestScheduler(mock_analytics_service_url, mock_scheduler)
    
    @pytest.fixture
    def sample_subscribers(self):
        """Sample subscriber data."""
        return [
            {
                'user_id': str(uuid4()),
                'email': 'parent1@example.com',
                'full_name': 'Parent One',
                'tenant_id': str(uuid4()),
                'timezone': 'America/New_York',
                'locale': 'en',
                'grade_band': 'elementary',
                'delivery_channels': ['email']
            },
            {
                'user_id': str(uuid4()),
                'email': 'guardian2@example.com',
                'full_name': 'Guardian Two',
                'tenant_id': str(uuid4()),
                'timezone': 'America/New_York',
                'locale': 'es',
                'grade_band': 'middle',
                'delivery_channels': ['email', 'push']
            }
        ]
    
    def test_schedule_weekly_digests(self, digest_scheduler, mock_scheduler):
        """Test scheduling of weekly digest jobs."""
        digest_scheduler.schedule_weekly_digests()
        
        # Verify jobs were added for major timezones
        assert mock_scheduler.add_job.call_count >= 8  # At least 8 major timezones
        
        # Check that jobs were scheduled for Sunday at 17:00
        calls = mock_scheduler.add_job.call_args_list
        for call in calls:
            args, kwargs = call
            assert 'day_of_week' in str(kwargs.get('trigger', ''))
            assert 'id' in kwargs
            assert kwargs['id'].startswith('weekly_digest_')
    
    @patch('services.notification_svc.app.cron_weekly_digest.get_db_session')
    def test_get_weekly_digest_subscribers(self, mock_get_db, digest_scheduler):
        """Test getting weekly digest subscribers."""
        # Mock database session and query
        mock_db = Mock()
        mock_get_db.return_value.__next__.return_value = mock_db
        
        # Mock query results
        mock_user = Mock()
        mock_user.user_id = uuid4()
        mock_user.email = 'test@example.com'
        mock_user.full_name = 'Test User'
        mock_user.tenant_id = uuid4()
        mock_user.timezone = 'America/New_York'
        mock_user.locale = 'en'
        mock_user.grade_band = 'elementary'
        mock_user.delivery_channels = ['email']
        
        mock_db.query.return_value.join.return_value.join.return_value.filter.return_value.all.return_value = [mock_user]
        
        subscribers = digest_scheduler._get_weekly_digest_subscribers(mock_db, 'America/New_York')
        
        assert len(subscribers) == 1
        assert subscribers[0]['email'] == 'test@example.com'
        assert subscribers[0]['timezone'] == 'America/New_York'
    
    @pytest.mark.asyncio
    async def test_process_subscriber_batch(self, digest_scheduler, sample_subscribers):
        """Test processing a batch of subscribers."""
        mock_db = Mock()
        
        # Mock the individual digest generation
        with patch.object(digest_scheduler, '_generate_and_send_weekly_digest', new_callable=AsyncMock) as mock_generate:
            mock_generate.return_value = True
            
            await digest_scheduler._process_subscriber_batch(sample_subscribers, 'America/New_York', mock_db)
            
            # Verify all subscribers were processed
            assert mock_generate.call_count == len(sample_subscribers)
    
    @pytest.mark.asyncio
    async def test_generate_and_send_weekly_digest_success(self, digest_scheduler, sample_subscribers):
        """Test successful weekly digest generation and sending."""
        subscriber = sample_subscribers[0]
        mock_db = Mock()
        
        # Mock learner retrieval
        with patch.object(digest_scheduler, '_get_user_learners', new_callable=AsyncMock) as mock_get_learners:
            mock_get_learners.return_value = ['learner1', 'learner2']
            
            # Mock weekly wins fetching
            with patch.object(digest_scheduler, '_fetch_learner_weekly_wins', new_callable=AsyncMock) as mock_fetch_wins:
                mock_fetch_wins.return_value = {
                    'learner_id': 'learner1',
                    'minutes_learned': {'total_minutes': 120, 'hours_learned': 2.0},
                    'subjects_advanced': {'subjects_count': 3},
                    'completed_goals': {'goals_count': 2}
                }
                
                # Mock notification sending
                with patch.object(digest_scheduler, '_send_digest_notification', new_callable=AsyncMock) as mock_send:
                    mock_send.return_value = None
                    
                    result = await digest_scheduler._generate_and_send_weekly_digest(subscriber, mock_db)
                    
                    assert result == True
                    mock_get_learners.assert_called_once()
                    mock_send.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_generate_and_send_weekly_digest_no_learners(self, digest_scheduler, sample_subscribers):
        """Test digest generation when user has no learners."""
        subscriber = sample_subscribers[0]
        mock_db = Mock()
        
        # Mock no learners found
        with patch.object(digest_scheduler, '_get_user_learners', new_callable=AsyncMock) as mock_get_learners:
            mock_get_learners.return_value = []
            
            result = await digest_scheduler._generate_and_send_weekly_digest(subscriber, mock_db)
            
            assert result == True  # Should succeed but skip sending
    
    @pytest.mark.asyncio
    async def test_get_user_learners_success(self, digest_scheduler):
        """Test successful learner retrieval."""
        user_id = str(uuid4())
        tenant_id = str(uuid4())
        
        # Mock HTTP response
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            'learners': [
                {'id': 'learner1', 'name': 'Student One'},
                {'id': 'learner2', 'name': 'Student Two'}
            ]
        }
        
        with patch.object(digest_scheduler.http_client, 'get') as mock_get:
            mock_get.return_value.__aenter__.return_value = mock_response
            
            learners = await digest_scheduler._get_user_learners(user_id, tenant_id)
            
            assert len(learners) == 2
            assert learners[0] == 'learner1'
            assert learners[1] == 'learner2'
    
    @pytest.mark.asyncio
    async def test_get_user_learners_service_error(self, digest_scheduler):
        """Test learner retrieval when service returns error."""
        user_id = str(uuid4())
        tenant_id = str(uuid4())
        
        # Mock HTTP error response
        mock_response = Mock()
        mock_response.status_code = 500
        
        with patch.object(digest_scheduler.http_client, 'get') as mock_get:
            mock_get.return_value.__aenter__.return_value = mock_response
            
            learners = await digest_scheduler._get_user_learners(user_id, tenant_id)
            
            assert learners == []
    
    @pytest.mark.asyncio
    async def test_fetch_learner_weekly_wins_success(self, digest_scheduler):
        """Test successful weekly wins fetching."""
        learner_id = str(uuid4())
        tenant_id = str(uuid4())
        
        # Mock successful response
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            'learner_id': learner_id,
            'minutes_learned': {'total_minutes': 150, 'hours_learned': 2.5},
            'subjects_advanced': {'subjects_count': 2},
            'completed_goals': {'goals_count': 1}
        }
        
        with patch.object(digest_scheduler.http_client, 'post') as mock_post:
            mock_post.return_value.__aenter__.return_value = mock_response
            
            wins_data = await digest_scheduler._fetch_learner_weekly_wins(
                learner_id, tenant_id, 'America/New_York', 'en', 'elementary'
            )
            
            assert wins_data is not None
            assert wins_data['learner_id'] == learner_id
            assert wins_data['minutes_learned']['hours_learned'] == 2.5
    
    @pytest.mark.asyncio
    async def test_fetch_learner_weekly_wins_not_found(self, digest_scheduler):
        """Test weekly wins fetching when no data available."""
        learner_id = str(uuid4())
        tenant_id = str(uuid4())
        
        # Mock 404 response
        mock_response = Mock()
        mock_response.status_code = 404
        
        with patch.object(digest_scheduler.http_client, 'post') as mock_post:
            mock_post.return_value.__aenter__.return_value = mock_response
            
            wins_data = await digest_scheduler._fetch_learner_weekly_wins(
                learner_id, tenant_id, 'America/New_York', 'en', 'elementary'
            )
            
            assert wins_data is None
    
    @pytest.mark.asyncio
    async def test_send_digest_notification(self, digest_scheduler):
        """Test sending digest notification."""
        mock_db = Mock()
        
        digest_data = {
            'user_id': str(uuid4()),
            'tenant_id': str(uuid4()),
            'email': 'test@example.com',
            'full_name': 'Test User',
            'delivery_channels': ['email'],
            'learners': [{
                'minutes_learned': {'hours_learned': 2.0},
                'subjects_advanced': {'subjects_count': 3}
            }]
        }
        
        # Mock notification creation
        mock_notification = Mock()
        mock_notification.id = str(uuid4())
        
        with patch('services.notification_svc.app.cron_weekly_digest.create_notification') as mock_create:
            mock_create.return_value = mock_notification
            
            # Mock email sending
            with patch.object(digest_scheduler, '_send_email_digest', new_callable=AsyncMock) as mock_send_email:
                mock_send_email.return_value = None
                
                await digest_scheduler._send_digest_notification(digest_data, mock_db)
                
                mock_create.assert_called_once()
                mock_send_email.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_send_email_digest(self, digest_scheduler):
        """Test email digest sending."""
        digest_data = {
            'user_id': str(uuid4()),
            'email': 'test@example.com',
            'full_name': 'Test User',
            'locale': 'en',
            'grade_band': 'elementary',
            'learners': [{
                'minutes_learned': {'total_minutes': 120, 'hours_learned': 2.0},
                'subjects_advanced': {'subjects_count': 2},
                'completed_goals': {'goals_count': 1},
                'week_start': '2023-10-01',
                'week_end': '2023-10-07'
            }]
        }
        
        notification_id = str(uuid4())
        
        # Mock mailer
        with patch.object(digest_scheduler.mailer, 'send_templated_email', new_callable=AsyncMock) as mock_send:
            mock_send.return_value = None
            
            await digest_scheduler._send_email_digest(digest_data, notification_id)
            
            mock_send.assert_called_once()
            args, kwargs = mock_send.call_args
            assert kwargs['template_name'] == 'weekly_wins'
            assert kwargs['to_email'] == 'test@example.com'
            assert kwargs['to_name'] == 'Test User'
            assert kwargs['notification_id'] == notification_id
    
    def test_prepare_email_template_vars(self, digest_scheduler):
        """Test email template variable preparation."""
        digest_data = {
            'user_id': str(uuid4()),
            'email': 'test@example.com',
            'full_name': 'Test User',
            'locale': 'en',
            'grade_band': 'elementary',
            'learners': [
                {
                    'learner_name': 'Student One',
                    'week_start': '2023-10-01',
                    'week_end': '2023-10-07',
                    'minutes_learned': {'total_minutes': 120, 'hours_learned': 2.0},
                    'subjects_advanced': {'subjects_count': 2, 'subjects': []},
                    'completed_goals': {'goals_count': 1, 'goals': []},
                    'slp_streaks': {'current_streak_days': 5},
                    'sel_progress': {'skills_count': 1},
                    'celebration_highlight': {'message_key': 'Great progress!'},
                    'encouragement_message': {'message_key': 'Keep it up!'}
                }
            ]
        }
        
        template_vars = digest_scheduler._prepare_email_template_vars(digest_data)
        
        assert template_vars['learner_name'] == 'Student One'
        assert template_vars['hours_learned'] == 2.0
        assert template_vars['subjects_advanced'] == 2
        assert template_vars['goals_completed'] == 1
        assert template_vars['streak_days'] == 5
        assert template_vars['grade_band'] == 'elementary'
        assert 'dashboard_url' in template_vars
        assert 'continue_learning_url' in template_vars
        assert 'preferences_url' in template_vars
        assert 'unsubscribe_url' in template_vars
    
    def test_prepare_email_template_vars_multiple_learners(self, digest_scheduler):
        """Test template vars with multiple learners (aggregation)."""
        digest_data = {
            'user_id': str(uuid4()),
            'locale': 'en',
            'grade_band': 'elementary',
            'learners': [
                {
                    'minutes_learned': {'hours_learned': 1.5},
                    'subjects_advanced': {'subjects_count': 2},
                    'completed_goals': {'goals_count': 1}
                },
                {
                    'minutes_learned': {'hours_learned': 2.0},
                    'subjects_advanced': {'subjects_count': 1},
                    'completed_goals': {'goals_count': 2}
                }
            ]
        }
        
        template_vars = digest_scheduler._prepare_email_template_vars(digest_data)
        
        # Should aggregate across learners
        assert template_vars['hours_learned'] == 3.5  # 1.5 + 2.0
        assert template_vars['subjects_advanced'] == 3  # 2 + 1
        assert template_vars['goals_completed'] == 3  # 1 + 2
        assert template_vars['learner_name'] == 'Your 2 learners'
    
    def test_get_learner_display_name(self, digest_scheduler):
        """Test learner display name generation."""
        # Single learner
        learners = [{'learner_name': 'Alice'}]
        name = digest_scheduler._get_learner_display_name(learners)
        assert name == 'Alice'
        
        # Multiple learners
        learners = [{'learner_name': 'Alice'}, {'learner_name': 'Bob'}]
        name = digest_scheduler._get_learner_display_name(learners)
        assert name == 'Your 2 learners'
        
        # No learners
        learners = []
        name = digest_scheduler._get_learner_display_name(learners)
        assert name == 'Your learner'
    
    def test_format_date_english(self, digest_scheduler):
        """Test date formatting for English locale."""
        date_str = '2023-10-15'
        formatted = digest_scheduler._format_date(date_str, 'en')
        assert 'October' in formatted
        assert '15' in formatted
    
    def test_format_date_spanish(self, digest_scheduler):
        """Test date formatting for Spanish locale."""
        date_str = '2023-10-15'
        formatted = digest_scheduler._format_date(date_str, 'es')
        assert 'de' in formatted  # Spanish date format includes 'de'
    
    def test_generate_email_subject_with_goals(self, digest_scheduler):
        """Test email subject generation when goals completed."""
        digest_data = {
            'learners': [{
                'learner_name': 'Alice',
                'completed_goals': {'goals_count': 2}
            }]
        }
        
        subject = digest_scheduler._generate_email_subject(digest_data)
        assert '🎉' in subject
        assert 'Alice' in subject
        assert '2 goals' in subject
    
    def test_generate_email_subject_without_goals(self, digest_scheduler):
        """Test email subject generation when no goals completed."""
        digest_data = {
            'learners': [{
                'learner_name': 'Bob',
                'completed_goals': {'goals_count': 0}
            }]
        }
        
        subject = digest_scheduler._generate_email_subject(digest_data)
        assert '📚' in subject
        assert 'Bob' in subject
        assert 'Learning Progress' in subject
    
    def test_calculate_week_comparison_improvement(self, digest_scheduler):
        """Test week comparison calculation with improvement."""
        learner_data = {
            'minutes_learned': {'total_minutes': 150},
            'week_comparison': {'last_week_minutes': 100}
        }
        
        comparison = digest_scheduler._calculate_week_comparison(learner_data)
        
        assert comparison['has_comparison'] == True
        assert comparison['improvement'] == 50  # 150 - 100
        assert comparison['improvement_percentage'] == 50.0  # 50/100 * 100
    
    def test_calculate_week_comparison_decline(self, digest_scheduler):
        """Test week comparison calculation with decline."""
        learner_data = {
            'minutes_learned': {'total_minutes': 80},
            'week_comparison': {'last_week_minutes': 120}
        }
        
        comparison = digest_scheduler._calculate_week_comparison(learner_data)
        
        assert comparison['has_comparison'] == True
        assert comparison['improvement'] == -40  # 80 - 120
        assert comparison['decline_percentage'] == 33.3  # Round to 1 decimal


# Error handling tests
class TestWeeklyDigestErrorHandling:
    """Test error handling scenarios."""
    
    @pytest.fixture
    def digest_scheduler(self):
        return WeeklyDigestScheduler("http://analytics:8000", Mock())
    
    @pytest.mark.asyncio
    async def test_database_error_handling(self, digest_scheduler):
        """Test handling of database errors."""
        mock_db = Mock()
        mock_db.query.side_effect = Exception("Database connection failed")
        
        subscribers = digest_scheduler._get_weekly_digest_subscribers(mock_db, 'UTC')
        
        # Should return empty list on error
        assert subscribers == []
    
    @pytest.mark.asyncio
    async def test_analytics_service_timeout(self, digest_scheduler):
        """Test handling of analytics service timeout."""
        with patch.object(digest_scheduler.http_client, 'post') as mock_post:
            mock_post.side_effect = asyncio.TimeoutError("Request timeout")
            
            result = await digest_scheduler._fetch_learner_weekly_wins(
                'learner1', 'tenant1', 'UTC', 'en', 'elementary'
            )
            
            assert result is None
    
    @pytest.mark.asyncio
    async def test_email_sending_failure(self, digest_scheduler):
        """Test handling of email sending failures."""
        digest_data = {
            'user_id': str(uuid4()),
            'email': 'test@example.com',
            'full_name': 'Test User',
            'learners': []
        }
        
        # Mock mailer failure
        with patch.object(digest_scheduler.mailer, 'send_templated_email', new_callable=AsyncMock) as mock_send:
            mock_send.side_effect = Exception("SMTP server error")
            
            with pytest.raises(Exception) as exc_info:
                await digest_scheduler._send_email_digest(digest_data, 'notification_id')
            
            assert "SMTP server error" in str(exc_info.value)


# Performance tests
class TestWeeklyDigestPerformance:
    """Test performance aspects of weekly digest generation."""
    
    @pytest.fixture
    def digest_scheduler(self):
        return WeeklyDigestScheduler("http://analytics:8000", Mock())
    
    @pytest.mark.asyncio
    async def test_batch_processing_limits(self, digest_scheduler):
        """Test that batch processing respects size limits."""
        # Create large subscriber list
        large_subscriber_list = []
        for i in range(100):
            large_subscriber_list.append({
                'user_id': str(uuid4()),
                'email': f'user{i}@example.com',
                'full_name': f'User {i}',
                'tenant_id': str(uuid4()),
                'timezone': 'UTC',
                'locale': 'en',
                'grade_band': 'elementary',
                'delivery_channels': ['email']
            })
        
        mock_db = Mock()
        
        with patch.object(digest_scheduler, '_generate_and_send_weekly_digest', new_callable=AsyncMock) as mock_generate:
            mock_generate.return_value = True
            
            await digest_scheduler._process_subscriber_batch(large_subscriber_list, 'UTC', mock_db)
            
            # Should process all subscribers
            assert mock_generate.call_count == 100
