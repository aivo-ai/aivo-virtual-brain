# AIVO Notification Service - Email Mailer with MJML Templates
# S2-16 Implementation - MJML Templates, i18n, SMTP/SES Provider

import os
import json
import smtplib
import logging
from datetime import datetime
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from email.mime.base import MIMEBase
from email import encoders
from pathlib import Path
from typing import Dict, Any, Optional, List, Union
from dataclasses import dataclass
from enum import Enum
import aiofiles
import asyncio

import boto3
from botocore.exceptions import ClientError
from jinja2 import Environment, FileSystemLoader, select_autoescape
import subprocess
import tempfile

logger = logging.getLogger(__name__)

class EmailProvider(Enum):
    """Supported email providers."""
    SMTP = "smtp"
    SES = "ses"
    SENDGRID = "sendgrid"

class EmailPriority(Enum):
    """Email priority levels."""
    LOW = "low"
    NORMAL = "normal"
    HIGH = "high"
    URGENT = "urgent"

@dataclass
class EmailAddress:
    """Email address with optional name."""
    email: str
    name: Optional[str] = None
    
    def __str__(self) -> str:
        if self.name:
            return f'"{self.name}" <{self.email}>'
        return self.email

@dataclass
class EmailAttachment:
    """Email attachment with metadata."""
    filename: str
    content: bytes
    content_type: str = "application/octet-stream"
    disposition: str = "attachment"

@dataclass 
class EmailTemplate:
    """Email template configuration."""
    name: str
    subject_template: str
    mjml_template: str
    text_template: Optional[str] = None
    locale: str = "en"
    partials: List[str] = None
    
    def __post_init__(self):
        if self.partials is None:
            self.partials = []

class I18nManager:
    """Internationalization manager for email templates."""
    
    def __init__(self, locales_dir: str = "app/i18n"):
        self.locales_dir = Path(locales_dir)
        self._translations: Dict[str, Dict[str, str]] = {}
        self._load_translations()
    
    def _load_translations(self) -> None:
        """Load translation files for all supported locales."""
        try:
            if not self.locales_dir.exists():
                logger.warning(f"Locales directory not found: {self.locales_dir}")
                return
                
            for locale_file in self.locales_dir.glob("*.json"):
                locale = locale_file.stem
                try:
                    with open(locale_file, 'r', encoding='utf-8') as f:
                        self._translations[locale] = json.load(f)
                    logger.info(f"Loaded translations for locale: {locale}")
                except json.JSONDecodeError as e:
                    logger.error(f"Invalid JSON in {locale_file}: {e}")
                except Exception as e:
                    logger.error(f"Error loading {locale_file}: {e}")
        except Exception as e:
            logger.error(f"Error loading translations: {e}")
    
    def translate(self, key: str, locale: str = "en", **kwargs) -> str:
        """Translate a key for the given locale with variable substitution."""
        try:
            translations = self._translations.get(locale, self._translations.get("en", {}))
            
            # Get translation with dot notation support
            translation = translations
            for part in key.split('.'):
                if isinstance(translation, dict) and part in translation:
                    translation = translation[part]
                else:
                    translation = key  # Fallback to key
                    break
            
            if not isinstance(translation, str):
                translation = key
                
            # Variable substitution
            if kwargs:
                try:
                    translation = translation.format(**kwargs)
                except KeyError as e:
                    logger.warning(f"Missing variable in translation {key}: {e}")
                except Exception as e:
                    logger.error(f"Error formatting translation {key}: {e}")
                    
            return translation
            
        except Exception as e:
            logger.error(f"Translation error for key '{key}', locale '{locale}': {e}")
            return key

class MJMLRenderer:
    """MJML template renderer with partial support."""
    
    def __init__(self, templates_dir: str = "app/templates"):
        self.templates_dir = Path(templates_dir)
        self.jinja_env = Environment(
            loader=FileSystemLoader(str(self.templates_dir)),
            autoescape=select_autoescape(['html', 'xml', 'mjml']),
            enable_async=True
        )
        self._setup_jinja_filters()
    
    def _setup_jinja_filters(self) -> None:
        """Setup custom Jinja2 filters for email templates."""
        
        def format_currency(value: float, currency: str = "USD") -> str:
            """Format currency values."""
            symbols = {"USD": "$", "EUR": "€", "GBP": "£"}
            symbol = symbols.get(currency, currency)
            return f"{symbol}{value:,.2f}"
        
        def format_date(value: datetime, format_str: str = "%B %d, %Y") -> str:
            """Format datetime values."""
            if isinstance(value, str):
                try:
                    value = datetime.fromisoformat(value.replace('Z', '+00:00'))
                except ValueError:
                    return value
            return value.strftime(format_str)
        
        def pluralize(value: int, singular: str, plural: str = None) -> str:
            """Pluralize words based on count."""
            if plural is None:
                plural = singular + "s"
            return singular if value == 1 else plural
        
        self.jinja_env.filters['currency'] = format_currency
        self.jinja_env.filters['date'] = format_date
        self.jinja_env.filters['pluralize'] = pluralize
    
    async def render_mjml_to_html(self, mjml_content: str) -> str:
        """Render MJML content to HTML using MJML CLI."""
        try:
            # Check if MJML CLI is available
            result = subprocess.run(['mjml', '--version'], 
                                  capture_output=True, text=True, timeout=10)
            if result.returncode != 0:
                raise RuntimeError("MJML CLI not available. Install with: npm install -g mjml")
            
            # Create temporary files
            with tempfile.NamedTemporaryFile(mode='w', suffix='.mjml', delete=False) as mjml_file:
                mjml_file.write(mjml_content)
                mjml_path = mjml_file.name
            
            try:
                # Run MJML CLI to convert to HTML
                result = subprocess.run([
                    'mjml', mjml_path, '--stdout'
                ], capture_output=True, text=True, timeout=30)
                
                if result.returncode != 0:
                    raise RuntimeError(f"MJML compilation failed: {result.stderr}")
                
                return result.stdout
                
            finally:
                # Clean up temp file
                os.unlink(mjml_path)
                
        except subprocess.TimeoutExpired:
            raise RuntimeError("MJML compilation timed out")
        except FileNotFoundError:
            raise RuntimeError("MJML CLI not found. Install with: npm install -g mjml")
        except Exception as e:
            logger.error(f"MJML rendering error: {e}")
            raise RuntimeError(f"Failed to render MJML: {e}")
    
    async def render_template(self, template_name: str, context: Dict[str, Any]) -> str:
        """Render a Jinja2 template with the given context."""
        try:
            template = self.jinja_env.get_template(template_name)
            return await template.render_async(**context)
        except Exception as e:
            logger.error(f"Template rendering error for {template_name}: {e}")
            raise
    
    async def render_email_template(self, template: EmailTemplate, 
                                  context: Dict[str, Any]) -> Dict[str, str]:
        """Render complete email template (subject + MJML to HTML)."""
        try:
            # Render subject
            subject_template = self.jinja_env.from_string(template.subject_template)
            subject = await subject_template.render_async(**context)
            
            # Render MJML template
            mjml_content = await self.render_template(template.mjml_template, context)
            
            # Convert MJML to HTML
            html_content = await self.render_mjml_to_html(mjml_content)
            
            result = {
                'subject': subject.strip(),
                'html': html_content,
                'mjml': mjml_content
            }
            
            # Render text template if available
            if template.text_template:
                text_content = await self.render_template(template.text_template, context)
                result['text'] = text_content
            
            return result
            
        except Exception as e:
            logger.error(f"Email template rendering error: {e}")
            raise

class SMTPProvider:
    """SMTP email provider."""
    
    def __init__(self, host: str, port: int = 587, username: str = None, 
                 password: str = None, use_tls: bool = True):
        self.host = host
        self.port = port
        self.username = username
        self.password = password
        self.use_tls = use_tls
    
    async def send_email(self, from_addr: EmailAddress, to_addrs: List[EmailAddress],
                        subject: str, html_content: str, text_content: str = None,
                        attachments: List[EmailAttachment] = None) -> Dict[str, Any]:
        """Send email via SMTP."""
        try:
            # Create message
            msg = MIMEMultipart('alternative')
            msg['From'] = str(from_addr)
            msg['To'] = ', '.join([str(addr) for addr in to_addrs])
            msg['Subject'] = subject
            
            # Add text part
            if text_content:
                text_part = MIMEText(text_content, 'plain', 'utf-8')
                msg.attach(text_part)
            
            # Add HTML part
            if html_content:
                html_part = MIMEText(html_content, 'html', 'utf-8')
                msg.attach(html_part)
            
            # Add attachments
            if attachments:
                for attachment in attachments:
                    part = MIMEBase('application', 'octet-stream')
                    part.set_payload(attachment.content)
                    encoders.encode_base64(part)
                    part.add_header(
                        'Content-Disposition',
                        f'{attachment.disposition}; filename= "{attachment.filename}"'
                    )
                    msg.attach(part)
            
            # Send via SMTP
            def _send_sync():
                with smtplib.SMTP(self.host, self.port) as server:
                    if self.use_tls:
                        server.starttls()
                    if self.username and self.password:
                        server.login(self.username, self.password)
                    
                    recipient_emails = [addr.email for addr in to_addrs]
                    server.send_message(msg, to_addrs=recipient_emails)
                    
                    return {
                        'success': True,
                        'provider': 'smtp',
                        'message_id': msg.get('Message-ID'),
                        'recipients': recipient_emails
                    }
            
            # Run SMTP operation in thread pool
            loop = asyncio.get_event_loop()
            return await loop.run_in_executor(None, _send_sync)
            
        except Exception as e:
            logger.error(f"SMTP send error: {e}")
            return {
                'success': False,
                'error': str(e),
                'provider': 'smtp'
            }

class SESProvider:
    """Amazon SES email provider."""
    
    def __init__(self, region: str = 'us-east-1', access_key: str = None,
                 secret_key: str = None):
        self.region = region
        if access_key and secret_key:
            self.ses_client = boto3.client(
                'ses',
                region_name=region,
                aws_access_key_id=access_key,
                aws_secret_access_key=secret_key
            )
        else:
            # Use default credential chain
            self.ses_client = boto3.client('ses', region_name=region)
    
    async def send_email(self, from_addr: EmailAddress, to_addrs: List[EmailAddress],
                        subject: str, html_content: str, text_content: str = None,
                        attachments: List[EmailAttachment] = None) -> Dict[str, Any]:
        """Send email via Amazon SES."""
        try:
            # Prepare destination
            destinations = [addr.email for addr in to_addrs]
            
            # Prepare message
            message = {
                'Subject': {'Data': subject, 'Charset': 'UTF-8'},
                'Body': {}
            }
            
            if html_content:
                message['Body']['Html'] = {'Data': html_content, 'Charset': 'UTF-8'}
            
            if text_content:
                message['Body']['Text'] = {'Data': text_content, 'Charset': 'UTF-8'}
            
            # Send via SES (simple send for now, raw for attachments)
            if attachments:
                # Use raw email for attachments
                raw_message = await self._build_raw_message(
                    from_addr, to_addrs, subject, html_content, text_content, attachments
                )
                
                def _send_raw_sync():
                    return self.ses_client.send_raw_email(
                        Source=from_addr.email,
                        Destinations=destinations,
                        RawMessage={'Data': raw_message}
                    )
                
                loop = asyncio.get_event_loop()
                response = await loop.run_in_executor(None, _send_raw_sync)
            else:
                # Use simple send
                def _send_sync():
                    return self.ses_client.send_email(
                        Source=str(from_addr),
                        Destination={'ToAddresses': destinations},
                        Message=message
                    )
                
                loop = asyncio.get_event_loop()
                response = await loop.run_in_executor(None, _send_sync)
            
            return {
                'success': True,
                'provider': 'ses',
                'message_id': response['MessageId'],
                'recipients': destinations
            }
            
        except ClientError as e:
            error_code = e.response['Error']['Code']
            logger.error(f"SES send error: {error_code} - {e}")
            return {
                'success': False,
                'error': f"SES Error: {error_code}",
                'provider': 'ses'
            }
        except Exception as e:
            logger.error(f"SES send error: {e}")
            return {
                'success': False,
                'error': str(e),
                'provider': 'ses'
            }
    
    async def _build_raw_message(self, from_addr: EmailAddress, to_addrs: List[EmailAddress],
                               subject: str, html_content: str, text_content: str,
                               attachments: List[EmailAttachment]) -> bytes:
        """Build raw email message with attachments."""
        msg = MIMEMultipart()
        msg['From'] = str(from_addr)
        msg['To'] = ', '.join([str(addr) for addr in to_addrs])
        msg['Subject'] = subject
        
        # Create multipart body
        body = MIMEMultipart('alternative')
        
        if text_content:
            body.attach(MIMEText(text_content, 'plain', 'utf-8'))
        
        if html_content:
            body.attach(MIMEText(html_content, 'html', 'utf-8'))
        
        msg.attach(body)
        
        # Add attachments
        for attachment in attachments:
            part = MIMEBase('application', 'octet-stream')
            part.set_payload(attachment.content)
            encoders.encode_base64(part)
            part.add_header(
                'Content-Disposition',
                f'{attachment.disposition}; filename="{attachment.filename}"'
            )
            msg.attach(part)
        
        return msg.as_bytes()

class EmailMailer:
    """Main email mailer with template rendering and provider abstraction."""
    
    def __init__(self, provider: Union[SMTPProvider, SESProvider],
                 templates_dir: str = "app/templates",
                 locales_dir: str = "app/i18n"):
        self.provider = provider
        self.renderer = MJMLRenderer(templates_dir)
        self.i18n = I18nManager(locales_dir)
        self.templates: Dict[str, EmailTemplate] = {}
        
        # Load template configurations
        asyncio.create_task(self._load_templates())
    
    async def _load_templates(self) -> None:
        """Load email template configurations."""
        try:
            config_path = Path(self.renderer.templates_dir) / "config.json"
            if config_path.exists():
                async with aiofiles.open(config_path, 'r') as f:
                    content = await f.read()
                    config = json.loads(content)
                    
                    for template_config in config.get('templates', []):
                        template = EmailTemplate(**template_config)
                        self.templates[template.name] = template
                        
                logger.info(f"Loaded {len(self.templates)} email templates")
        except Exception as e:
            logger.error(f"Error loading email templates: {e}")
    
    def register_template(self, template: EmailTemplate) -> None:
        """Register a new email template."""
        self.templates[template.name] = template
    
    async def send_template_email(self, 
                                template_name: str,
                                from_addr: EmailAddress,
                                to_addrs: List[EmailAddress],
                                context: Dict[str, Any],
                                locale: str = "en",
                                attachments: List[EmailAttachment] = None) -> Dict[str, Any]:
        """Send templated email with i18n support."""
        try:
            # Get template
            template = self.templates.get(template_name)
            if not template:
                raise ValueError(f"Template not found: {template_name}")
            
            # Add i18n function to context
            def t(key: str, **kwargs) -> str:
                return self.i18n.translate(key, locale, **kwargs)
            
            context['t'] = t
            context['locale'] = locale
            context['current_year'] = datetime.now().year
            
            # Render template
            rendered = await self.renderer.render_email_template(template, context)
            
            # Send email
            result = await self.provider.send_email(
                from_addr=from_addr,
                to_addrs=to_addrs,
                subject=rendered['subject'],
                html_content=rendered['html'],
                text_content=rendered.get('text'),
                attachments=attachments or []
            )
            
            return {
                **result,
                'template': template_name,
                'locale': locale
            }
            
        except Exception as e:
            logger.error(f"Template email send error: {e}")
            return {
                'success': False,
                'error': str(e),
                'template': template_name,
                'locale': locale
            }
    
    async def send_approval_notification(self, 
                                       approver_email: EmailAddress,
                                       requester_name: str,
                                       item_type: str,
                                       item_title: str,
                                       approval_url: str,
                                       due_date: datetime = None,
                                       locale: str = "en") -> Dict[str, Any]:
        """Send approval request notification."""
        context = {
            'requester_name': requester_name,
            'item_type': item_type,
            'item_title': item_title,
            'approval_url': approval_url,
            'due_date': due_date,
            'company_name': os.getenv('COMPANY_NAME', 'AIVO Virtual Brains')
        }
        
        from_addr = EmailAddress(
            email=os.getenv('FROM_EMAIL', 'noreply@aivo-virtualbrains.com'),
            name=os.getenv('FROM_NAME', 'AIVO Virtual Brains')
        )
        
        return await self.send_template_email(
            template_name='approval_request',
            from_addr=from_addr,
            to_addrs=[approver_email],
            context=context,
            locale=locale
        )
    
    async def send_digest_email(self,
                              recipient_email: EmailAddress,
                              digest_data: Dict[str, Any],
                              period: str = "daily",
                              locale: str = "en") -> Dict[str, Any]:
        """Send digest notification email."""
        context = {
            'period': period,
            'digest_date': datetime.now(),
            'company_name': os.getenv('COMPANY_NAME', 'AIVO Virtual Brains'),
            **digest_data
        }
        
        from_addr = EmailAddress(
            email=os.getenv('FROM_EMAIL', 'noreply@aivo-virtualbrains.com'),
            name=os.getenv('FROM_NAME', 'AIVO Virtual Brains')
        )
        
        template_name = f'{period}_digest'
        return await self.send_template_email(
            template_name=template_name,
            from_addr=from_addr,
            to_addrs=[recipient_email],
            context=context,
            locale=locale
        )
    
    async def send_dunning_notice(self,
                                customer_email: EmailAddress,
                                account_info: Dict[str, Any],
                                dunning_level: int = 1,
                                locale: str = "en") -> Dict[str, Any]:
        """Send payment dunning notice."""
        context = {
            'dunning_level': dunning_level,
            'company_name': os.getenv('COMPANY_NAME', 'AIVO Virtual Brains'),
            **account_info
        }
        
        from_addr = EmailAddress(
            email=os.getenv('BILLING_EMAIL', 'billing@aivo-virtualbrains.com'),
            name=os.getenv('FROM_NAME', 'AIVO Billing')
        )
        
        return await self.send_template_email(
            template_name='dunning_notice',
            from_addr=from_addr,
            to_addrs=[customer_email],
            context=context,
            locale=locale
        )
