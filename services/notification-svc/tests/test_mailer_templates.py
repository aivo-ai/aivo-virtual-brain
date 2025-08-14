# AIVO Notification Service - Mailer and Templates Tests
# S2-16 Implementation - MJML, i18n, SMTP/SES Testing

import pytest
import asyncio
import json
import tempfile
from unittest.mock import Mock, AsyncMock, patch, MagicMock
from pathlib import Path
from datetime import datetime, timezone, timedelta
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart

import boto3
from moto import mock_ses

from app.mailer import (
    EmailMailer, SMTPProvider, SESProvider, I18nManager, MJMLRenderer,
    EmailAddress, EmailTemplate, EmailAttachment, EmailProvider
)


class TestI18nManager:
    """Test internationalization manager."""
    
    def test_load_translations(self, tmp_path):
        """Test loading translation files."""
        # Create test locale files
        en_file = tmp_path / "en.json"
        es_file = tmp_path / "es.json"
        
        en_data = {
            "email": {
                "greeting": "Hello {name}",
                "nested": {
                    "deep": "Deep message"
                }
            },
            "common": {
                "yes": "Yes"
            }
        }
        
        es_data = {
            "email": {
                "greeting": "Hola {name}",
                "nested": {
                    "deep": "Mensaje profundo"
                }
            },
            "common": {
                "yes": "Sí"
            }
        }
        
        en_file.write_text(json.dumps(en_data))
        es_file.write_text(json.dumps(es_data))
        
        # Test I18n manager
        i18n = I18nManager(str(tmp_path))
        
        # Test translations
        assert i18n.translate("email.greeting", "en", name="John") == "Hello John"
        assert i18n.translate("email.greeting", "es", name="Juan") == "Hola Juan"
        assert i18n.translate("email.nested.deep", "en") == "Deep message"
        assert i18n.translate("email.nested.deep", "es") == "Mensaje profundo"
    
    def test_translation_fallbacks(self, tmp_path):
        """Test translation fallback behavior."""
        en_file = tmp_path / "en.json"
        en_data = {"test": {"key": "Test value"}}
        en_file.write_text(json.dumps(en_data))
        
        i18n = I18nManager(str(tmp_path))
        
        # Test key fallback
        assert i18n.translate("nonexistent.key", "en") == "nonexistent.key"
        
        # Test locale fallback
        assert i18n.translate("test.key", "fr") == "Test value"  # Falls back to en
        
        # Test missing variable
        assert i18n.translate("test.key", "en", missing_var="test") == "Test value"
    
    def test_invalid_locale_file(self, tmp_path):
        """Test handling of invalid JSON locale files."""
        invalid_file = tmp_path / "invalid.json"
        invalid_file.write_text("{ invalid json }")
        
        # Should not crash
        i18n = I18nManager(str(tmp_path))
        assert i18n.translate("any.key", "invalid") == "any.key"


class TestMJMLRenderer:
    """Test MJML template renderer."""
    
    @pytest.fixture
    def templates_dir(self, tmp_path):
        """Create test templates directory."""
        templates_dir = tmp_path / "templates"
        templates_dir.mkdir()
        
        # Create test MJML template
        test_template = templates_dir / "test.mjml"
        test_template.write_text("""
        <mjml>
          <mj-body>
            <mj-section>
              <mj-column>
                <mj-text>Hello {{ name }}!</mj-text>
                <mj-text>{{ message }}</mj-text>
              </mj-column>
            </mj-section>
          </mj-body>
        </mjml>
        """)
        
        return str(templates_dir)
    
    @pytest.mark.asyncio
    async def test_render_template(self, templates_dir):
        """Test basic Jinja2 template rendering."""
        renderer = MJMLRenderer(templates_dir)
        
        result = await renderer.render_template("test.mjml", {
            "name": "John",
            "message": "Welcome to the system!"
        })
        
        assert "Hello John!" in result
        assert "Welcome to the system!" in result
    
    @pytest.mark.asyncio
    async def test_jinja_filters(self, templates_dir):
        """Test custom Jinja2 filters."""
        # Create template with filters
        templates_path = Path(templates_dir)
        filter_template = templates_path / "filters.mjml"
        filter_template.write_text("""
        Currency: {{ price|currency }}
        Date: {{ test_date|date('%B %d, %Y') }}
        Plural: {{ count }} {{ 'item'|pluralize(count) }}
        """)
        
        renderer = MJMLRenderer(templates_dir)
        
        result = await renderer.render_template("filters.mjml", {
            "price": 99.95,
            "test_date": datetime(2025, 1, 15),
            "count": 5
        })
        
        assert "$99.95" in result
        assert "January 15, 2025" in result
        assert "5 items" in result
    
    @pytest.mark.asyncio
    @patch('subprocess.run')
    async def test_mjml_to_html_conversion(self, mock_subprocess, templates_dir):
        """Test MJML to HTML conversion."""
        # Mock MJML CLI response
        mock_subprocess.return_value = Mock(
            returncode=0,
            stdout="<html><body>Converted HTML</body></html>",
            stderr=""
        )
        
        renderer = MJMLRenderer(templates_dir)
        
        mjml_content = """
        <mjml>
          <mj-body>
            <mj-section>
              <mj-column>
                <mj-text>Test email</mj-text>
              </mj-column>
            </mj-section>
          </mj-body>
        </mjml>
        """
        
        result = await renderer.render_mjml_to_html(mjml_content)
        
        assert "Converted HTML" in result
        mock_subprocess.assert_called_once()
    
    @pytest.mark.asyncio
    @patch('subprocess.run')
    async def test_mjml_cli_error(self, mock_subprocess, templates_dir):
        """Test MJML CLI error handling."""
        mock_subprocess.return_value = Mock(
            returncode=1,
            stdout="",
            stderr="MJML compilation failed"
        )
        
        renderer = MJMLRenderer(templates_dir)
        
        with pytest.raises(RuntimeError, match="MJML compilation failed"):
            await renderer.render_mjml_to_html("<mjml></mjml>")
    
    @pytest.mark.asyncio
    async def test_render_email_template(self, templates_dir):
        """Test complete email template rendering."""
        renderer = MJMLRenderer(templates_dir)
        
        template = EmailTemplate(
            name="test_email",
            subject_template="Subject: {{ title }}",
            mjml_template="test.mjml"
        )
        
        with patch.object(renderer, 'render_mjml_to_html') as mock_mjml:
            mock_mjml.return_value = "<html>Converted</html>"
            
            result = await renderer.render_email_template(template, {
                "title": "Test Email",
                "name": "John",
                "message": "Test message"
            })
            
            assert result['subject'] == "Subject: Test Email"
            assert result['html'] == "<html>Converted</html>"
            assert "Hello John!" in result['mjml']


class TestSMTPProvider:
    """Test SMTP email provider."""
    
    @pytest.mark.asyncio
    @patch('smtplib.SMTP')
    async def test_send_email_success(self, mock_smtp_class):
        """Test successful SMTP email sending."""
        mock_server = Mock()
        mock_smtp_class.return_value.__enter__.return_value = mock_server
        
        provider = SMTPProvider(
            host="smtp.test.com",
            port=587,
            username="test@test.com",
            password="password"
        )
        
        from_addr = EmailAddress("sender@test.com", "Test Sender")
        to_addrs = [EmailAddress("recipient@test.com", "Test Recipient")]
        
        result = await provider.send_email(
            from_addr=from_addr,
            to_addrs=to_addrs,
            subject="Test Subject",
            html_content="<h1>Test HTML</h1>",
            text_content="Test text"
        )
        
        assert result['success'] is True
        assert result['provider'] == 'smtp'
        mock_server.starttls.assert_called_once()
        mock_server.login.assert_called_once_with("test@test.com", "password")
        mock_server.send_message.assert_called_once()
    
    @pytest.mark.asyncio
    @patch('smtplib.SMTP')
    async def test_send_email_with_attachments(self, mock_smtp_class):
        """Test SMTP email with attachments."""
        mock_server = Mock()
        mock_smtp_class.return_value.__enter__.return_value = mock_server
        
        provider = SMTPProvider("smtp.test.com")
        
        attachment = EmailAttachment(
            filename="test.pdf",
            content=b"PDF content",
            content_type="application/pdf"
        )
        
        result = await provider.send_email(
            from_addr=EmailAddress("sender@test.com"),
            to_addrs=[EmailAddress("recipient@test.com")],
            subject="With Attachment",
            html_content="<p>Email with attachment</p>",
            attachments=[attachment]
        )
        
        assert result['success'] is True
        # Verify attachment was included in message
        mock_server.send_message.assert_called_once()
        sent_message = mock_server.send_message.call_args[0][0]
        assert sent_message.is_multipart()
    
    @pytest.mark.asyncio
    @patch('smtplib.SMTP')
    async def test_smtp_error_handling(self, mock_smtp_class):
        """Test SMTP error handling."""
        mock_smtp_class.side_effect = smtplib.SMTPException("Connection failed")
        
        provider = SMTPProvider("smtp.test.com")
        
        result = await provider.send_email(
            from_addr=EmailAddress("sender@test.com"),
            to_addrs=[EmailAddress("recipient@test.com")],
            subject="Test",
            html_content="<p>Test</p>"
        )
        
        assert result['success'] is False
        assert "Connection failed" in result['error']
        assert result['provider'] == 'smtp'


class TestSESProvider:
    """Test Amazon SES email provider."""
    
    @mock_ses
    @pytest.mark.asyncio
    async def test_send_email_success(self):
        """Test successful SES email sending."""
        # Setup mock SES
        client = boto3.client('ses', region_name='us-east-1')
        client.verify_email_identity(EmailAddress="sender@test.com")
        
        provider = SESProvider(region='us-east-1')
        provider.ses_client = client
        
        result = await provider.send_email(
            from_addr=EmailAddress("sender@test.com", "Test Sender"),
            to_addrs=[EmailAddress("recipient@test.com")],
            subject="SES Test",
            html_content="<h1>SES HTML</h1>",
            text_content="SES text"
        )
        
        assert result['success'] is True
        assert result['provider'] == 'ses'
        assert 'message_id' in result
        assert result['recipients'] == ['recipient@test.com']
    
    @mock_ses
    @pytest.mark.asyncio
    async def test_send_email_with_attachments(self):
        """Test SES email with attachments (raw email)."""
        client = boto3.client('ses', region_name='us-east-1')
        client.verify_email_identity(EmailAddress="sender@test.com")
        
        provider = SESProvider(region='us-east-1')
        provider.ses_client = client
        
        attachment = EmailAttachment(
            filename="document.pdf",
            content=b"PDF document content",
            content_type="application/pdf"
        )
        
        result = await provider.send_email(
            from_addr=EmailAddress("sender@test.com"),
            to_addrs=[EmailAddress("recipient@test.com")],
            subject="SES with Attachment",
            html_content="<p>Document attached</p>",
            attachments=[attachment]
        )
        
        assert result['success'] is True
        assert result['provider'] == 'ses'
    
    @pytest.mark.asyncio
    async def test_ses_client_error(self):
        """Test SES client error handling."""
        mock_client = Mock()
        mock_client.send_email.side_effect = Exception("SES error")
        
        provider = SESProvider()
        provider.ses_client = mock_client
        
        result = await provider.send_email(
            from_addr=EmailAddress("sender@test.com"),
            to_addrs=[EmailAddress("recipient@test.com")],
            subject="Test",
            html_content="<p>Test</p>"
        )
        
        assert result['success'] is False
        assert "SES error" in result['error']
        assert result['provider'] == 'ses'


class TestEmailMailer:
    """Test main EmailMailer class."""
    
    @pytest.fixture
    def setup_mailer(self, tmp_path):
        """Setup test mailer with mock provider."""
        # Create test templates directory
        templates_dir = tmp_path / "templates"
        templates_dir.mkdir()
        
        # Create template config
        config_data = {
            "templates": [
                {
                    "name": "test_template",
                    "subject_template": "Test: {{ title }}",
                    "mjml_template": "test.mjml",
                    "text_template": "test.txt",
                    "locale": "en"
                }
            ]
        }
        
        config_file = templates_dir / "config.json"
        config_file.write_text(json.dumps(config_data))
        
        # Create test MJML template
        mjml_template = templates_dir / "test.mjml"
        mjml_template.write_text("""
        <mjml>
          <mj-body>
            <mj-section>
              <mj-column>
                <mj-text>{{ t('email.greeting', name=name) }}</mj-text>
              </mj-column>
            </mj-section>
          </mj-body>
        </mjml>
        """)
        
        # Create text template
        text_template = templates_dir / "test.txt"
        text_template.write_text("{{ t('email.greeting', name=name) }}")
        
        # Create i18n directory
        i18n_dir = tmp_path / "i18n"
        i18n_dir.mkdir()
        
        en_file = i18n_dir / "en.json"
        en_data = {
            "email": {
                "greeting": "Hello {name}!"
            }
        }
        en_file.write_text(json.dumps(en_data))
        
        # Create mock provider
        mock_provider = Mock()
        
        # Create mailer
        mailer = EmailMailer(
            provider=mock_provider,
            templates_dir=str(templates_dir),
            locales_dir=str(i18n_dir)
        )
        
        return mailer, mock_provider, templates_dir
    
    @pytest.mark.asyncio
    async def test_load_templates(self, setup_mailer):
        """Test template loading from config."""
        mailer, mock_provider, templates_dir = setup_mailer
        
        # Wait for templates to load
        await mailer._load_templates()
        
        assert "test_template" in mailer.templates
        template = mailer.templates["test_template"]
        assert template.name == "test_template"
        assert template.subject_template == "Test: {{ title }}"
    
    @pytest.mark.asyncio
    async def test_send_template_email(self, setup_mailer):
        """Test sending templated email."""
        mailer, mock_provider, templates_dir = setup_mailer
        
        # Mock provider response
        mock_provider.send_email = AsyncMock(return_value={
            'success': True,
            'message_id': 'test-123',
            'provider': 'mock'
        })
        
        # Mock MJML rendering
        with patch.object(mailer.renderer, 'render_mjml_to_html') as mock_mjml:
            mock_mjml.return_value = "<html><body>Hello John!</body></html>"
            
            # Register and send template
            template = EmailTemplate(
                name="greeting",
                subject_template="Hello {{ name }}",
                mjml_template="test.mjml",
                text_template="test.txt"
            )
            mailer.register_template(template)
            
            result = await mailer.send_template_email(
                template_name="greeting",
                from_addr=EmailAddress("sender@test.com"),
                to_addrs=[EmailAddress("recipient@test.com")],
                context={"name": "John", "title": "Welcome"},
                locale="en"
            )
            
            assert result['success'] is True
            assert result['template'] == "greeting"
            assert result['locale'] == "en"
            mock_provider.send_email.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_send_approval_notification(self, setup_mailer):
        """Test approval notification helper."""
        mailer, mock_provider, templates_dir = setup_mailer
        
        mock_provider.send_email = AsyncMock(return_value={'success': True})
        
        # Mock template rendering
        with patch.object(mailer, 'send_template_email') as mock_send:
            mock_send.return_value = {'success': True}
            
            result = await mailer.send_approval_notification(
                approver_email=EmailAddress("approver@test.com"),
                requester_name="John Doe",
                item_type="IEP Document",
                item_title="Math Goals Update",
                approval_url="https://app.test.com/approve/123",
                due_date=datetime.now() + timedelta(days=7)
            )
            
            mock_send.assert_called_once()
            call_args = mock_send.call_args[1]
            assert call_args['template_name'] == 'approval_request'
            assert 'requester_name' in call_args['context']
            assert call_args['context']['requester_name'] == "John Doe"
    
    @pytest.mark.asyncio
    async def test_send_digest_email(self, setup_mailer):
        """Test digest email helper."""
        mailer, mock_provider, templates_dir = setup_mailer
        
        with patch.object(mailer, 'send_template_email') as mock_send:
            mock_send.return_value = {'success': True}
            
            digest_data = {
                'notifications': [
                    {'title': 'Test Notification', 'message': 'Test message'}
                ],
                'stats': {
                    'active_learners': 25,
                    'completed_assessments': 15
                }
            }
            
            result = await mailer.send_digest_email(
                recipient_email=EmailAddress("user@test.com"),
                digest_data=digest_data,
                period="daily"
            )
            
            mock_send.assert_called_once()
            call_args = mock_send.call_args[1]
            assert call_args['template_name'] == 'daily_digest'
            assert 'notifications' in call_args['context']
    
    @pytest.mark.asyncio
    async def test_send_dunning_notice(self, setup_mailer):
        """Test dunning notice helper."""
        mailer, mock_provider, templates_dir = setup_mailer
        
        with patch.object(mailer, 'send_template_email') as mock_send:
            mock_send.return_value = {'success': True}
            
            account_info = {
                'customer_name': 'Jane Smith',
                'account_number': 'ACC-12345',
                'outstanding_balance': 150.75,
                'past_due_amount': 75.50,
                'past_due_days': 15
            }
            
            result = await mailer.send_dunning_notice(
                customer_email=EmailAddress("customer@test.com"),
                account_info=account_info,
                dunning_level=2
            )
            
            mock_send.assert_called_once()
            call_args = mock_send.call_args[1]
            assert call_args['template_name'] == 'dunning_notice'
            assert call_args['context']['dunning_level'] == 2
    
    @pytest.mark.asyncio 
    async def test_template_not_found(self, setup_mailer):
        """Test error handling for missing template."""
        mailer, mock_provider, templates_dir = setup_mailer
        
        result = await mailer.send_template_email(
            template_name="nonexistent",
            from_addr=EmailAddress("sender@test.com"),
            to_addrs=[EmailAddress("recipient@test.com")],
            context={}
        )
        
        assert result['success'] is False
        assert "Template not found" in result['error']
    
    @pytest.mark.asyncio
    async def test_i18n_context_injection(self, setup_mailer):
        """Test i18n function injection into template context."""
        mailer, mock_provider, templates_dir = setup_mailer
        
        mock_provider.send_email = AsyncMock(return_value={'success': True})
        
        template = EmailTemplate(
            name="i18n_test",
            subject_template="{{ t('email.greeting', name=name) }}",
            mjml_template="test.mjml"
        )
        mailer.register_template(template)
        
        with patch.object(mailer.renderer, 'render_email_template') as mock_render:
            mock_render.return_value = {
                'subject': 'Hello John!',
                'html': '<html>Hello John!</html>'
            }
            
            await mailer.send_template_email(
                template_name="i18n_test",
                from_addr=EmailAddress("sender@test.com"),
                to_addrs=[EmailAddress("recipient@test.com")],
                context={"name": "John"},
                locale="en"
            )
            
            # Verify context has i18n function
            render_call_args = mock_render.call_args[0]
            context = render_call_args[1]
            assert 't' in context
            assert context['locale'] == 'en'
            assert context['current_year'] == datetime.now().year


class TestEmailClasses:
    """Test email utility classes."""
    
    def test_email_address_str(self):
        """Test EmailAddress string representation."""
        # With name
        addr_with_name = EmailAddress("test@test.com", "Test User")
        assert str(addr_with_name) == '"Test User" <test@test.com>'
        
        # Without name
        addr_no_name = EmailAddress("test@test.com")
        assert str(addr_no_name) == "test@test.com"
    
    def test_email_template_defaults(self):
        """Test EmailTemplate default values."""
        template = EmailTemplate(
            name="test",
            subject_template="Test",
            mjml_template="test.mjml"
        )
        
        assert template.text_template is None
        assert template.locale == "en"
        assert template.partials == []
    
    def test_email_attachment_defaults(self):
        """Test EmailAttachment default values."""
        attachment = EmailAttachment(
            filename="test.pdf",
            content=b"content"
        )
        
        assert attachment.content_type == "application/octet-stream"
        assert attachment.disposition == "attachment"


# Integration Tests
class TestMailerIntegration:
    """Integration tests for complete email workflows."""
    
    @pytest.mark.asyncio
    async def test_complete_approval_workflow(self, tmp_path):
        """Test complete approval email workflow."""
        # Setup complete environment
        templates_dir = tmp_path / "templates"
        templates_dir.mkdir()
        i18n_dir = tmp_path / "i18n"
        i18n_dir.mkdir()
        
        # Create approval template files
        self._create_approval_templates(templates_dir, i18n_dir)
        
        # Mock SMTP provider
        mock_provider = Mock()
        mock_provider.send_email = AsyncMock(return_value={
            'success': True,
            'message_id': 'approval-123',
            'provider': 'smtp'
        })
        
        # Create mailer
        mailer = EmailMailer(
            provider=mock_provider,
            templates_dir=str(templates_dir),
            locales_dir=str(i18n_dir)
        )
        
        # Register approval template
        approval_template = EmailTemplate(
            name="approval_request",
            subject_template="Action Required: {{ item_type }} - {{ item_title }}",
            mjml_template="approval.mjml",
            text_template="approval.txt"
        )
        mailer.register_template(approval_template)
        
        # Mock MJML rendering
        with patch.object(mailer.renderer, 'render_mjml_to_html') as mock_mjml:
            mock_mjml.return_value = "<html><body>Approval email</body></html>"
            
            # Send approval email
            result = await mailer.send_approval_notification(
                approver_email=EmailAddress("approver@school.edu", "Principal"),
                requester_name="Teacher Jane",
                item_type="IEP Document",
                item_title="Mathematics Goals Update",
                approval_url="https://app.aivo.com/approve/iep-456"
            )
            
            # Verify success
            assert result['success'] is True
            mock_provider.send_email.assert_called_once()
            
            # Verify email content
            call_args = mock_provider.send_email.call_args[1]
            assert "Action Required" in call_args['subject']
            assert "IEP Document" in call_args['subject']
    
    def _create_approval_templates(self, templates_dir, i18n_dir):
        """Helper to create approval template files."""
        # MJML template
        mjml_file = templates_dir / "approval.mjml"
        mjml_file.write_text("""
        <mjml>
          <mj-body>
            <mj-section>
              <mj-column>
                <mj-text font-size="20px">Approval Required</mj-text>
                <mj-text>{{ requester_name }} requests approval for:</mj-text>
                <mj-text>{{ item_type }}: {{ item_title }}</mj-text>
                <mj-button href="{{ approval_url }}">Review & Approve</mj-button>
              </mj-column>
            </mj-section>
          </mj-body>
        </mjml>
        """)
        
        # Text template
        text_file = templates_dir / "approval.txt"
        text_file.write_text("""
        Approval Required
        
        {{ requester_name }} requests approval for:
        {{ item_type }}: {{ item_title }}
        
        Review & Approve: {{ approval_url }}
        """)
        
        # English translations
        en_file = i18n_dir / "en.json"
        en_data = {
            "email": {
                "approval": {
                    "title": "Approval Required",
                    "subject": "Action Required: {item_type} - {item_title}"
                }
            }
        }
        en_file.write_text(json.dumps(en_data))


# Fixtures and Utilities
@pytest.fixture
def mock_mjml_cli():
    """Mock MJML CLI for testing."""
    with patch('subprocess.run') as mock_run:
        mock_run.return_value = Mock(
            returncode=0,
            stdout="<html><body>Mocked MJML output</body></html>",
            stderr=""
        )
        yield mock_run


@pytest.fixture  
def sample_notification_data():
    """Sample notification data for testing."""
    return {
        'notifications': [
            {
                'title': 'IEP Goal Updated',
                'message': 'Mathematics goal progress has been updated for Student A.',
                'notification_type': Mock(value='iep_update'),
                'created_at': datetime.now(timezone.utc),
                'action_url': 'https://app.aivo.com/iep/123'
            },
            {
                'title': 'Assessment Complete',
                'message': 'Reading comprehension assessment has been completed.',
                'notification_type': Mock(value='assessment_complete'),
                'created_at': datetime.now(timezone.utc) - timedelta(hours=2),
                'action_url': 'https://app.aivo.com/assessment/456'
            }
        ],
        'urgent_notifications': [
            {
                'title': 'Signature Required',
                'message': 'IEP document requires parent signature before deadline.',
                'notification_type': Mock(value='signature_request'),
                'created_at': datetime.now(timezone.utc) - timedelta(minutes=30),
                'action_url': 'https://app.aivo.com/sign/789'
            }
        ],
        'stats': {
            'active_learners': 28,
            'completed_assessments': 12,
            'avg_session_minutes': 35,
            'pending_approvals': 3
        },
        'action_items': [
            {
                'title': 'Review pending IEP modifications',
                'url': 'https://app.aivo.com/pending-reviews',
                'due_date': datetime.now() + timedelta(days=2)
            }
        ]
    }


if __name__ == "__main__":
    pytest.main([__file__])
