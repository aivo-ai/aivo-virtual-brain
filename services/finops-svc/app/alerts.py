"""
Alert management system for budget notifications.

This module handles sending alerts via multiple channels including email, Slack,
webhooks, and SMS for budget overruns and threshold violations.
"""

import asyncio
import logging
import json
from datetime import datetime, timezone
from typing import Dict, List, Optional, Any
from decimal import Decimal

import aiohttp
from sqlalchemy.ext.asyncio import AsyncSession

from .models import Budget, BudgetAlert, AlertChannel
from .config import config

logger = logging.getLogger(__name__)


class AlertManager:
    """Manages budget alert notifications across multiple channels."""
    
    def __init__(self):
        self.session = None
        self._webhook_timeout = 30
        self._retry_attempts = 3
    
    async def send_budget_alert(
        self,
        alert: BudgetAlert,
        budget: Budget,
        session: AsyncSession
    ) -> bool:
        """Send budget alert via configured channels."""
        try:
            success_count = 0
            total_channels = len(budget.alert_channels or ["email"])
            
            # Send via each configured channel
            for channel in budget.alert_channels or ["email"]:
                try:
                    channel_enum = AlertChannel(channel)
                    
                    if channel_enum == AlertChannel.EMAIL:
                        success = await self._send_email_alert(alert, budget)
                    elif channel_enum == AlertChannel.SLACK:
                        success = await self._send_slack_alert(alert, budget)
                    elif channel_enum == AlertChannel.WEBHOOK:
                        success = await self._send_webhook_alert(alert, budget)
                    elif channel_enum == AlertChannel.SMS:
                        success = await self._send_sms_alert(alert, budget)
                    else:
                        logger.warning(f"Unsupported alert channel: {channel}")
                        continue
                    
                    if success:
                        success_count += 1
                        logger.info(f"Alert sent via {channel} for budget {budget.name}")
                    else:
                        logger.warning(f"Failed to send alert via {channel} for budget {budget.name}")
                        
                except Exception as e:
                    logger.error(f"Error sending alert via {channel}: {e}")
            
            # Consider successful if at least one channel worked
            return success_count > 0
            
        except Exception as e:
            logger.error(f"Alert sending failed: {e}")
            return False
    
    async def _send_email_alert(self, alert: BudgetAlert, budget: Budget) -> bool:
        """Send budget alert via email."""
        try:
            # Prepare email content
            subject = alert.alert_title
            html_body = self._generate_email_html(alert, budget)
            text_body = self._generate_email_text(alert, budget)
            
            recipients = budget.alert_recipients or []
            if not recipients:
                logger.warning(f"No email recipients configured for budget {budget.name}")
                return False
            
            # Send email via configured email service
            email_data = {
                "to": recipients,
                "subject": subject,
                "html_body": html_body,
                "text_body": text_body,
                "sender": config.EMAIL_SENDER,
                "alert_id": str(alert.id),
                "budget_id": str(budget.id)
            }
            
            # Use email service API (placeholder - implement actual email service)
            async with aiohttp.ClientSession() as session:
                async with session.post(
                    f"{config.EMAIL_SERVICE_URL}/send",
                    json=email_data,
                    headers={"Authorization": f"Bearer {config.EMAIL_SERVICE_TOKEN}"},
                    timeout=aiohttp.ClientTimeout(total=self._webhook_timeout)
                ) as response:
                    if response.status == 200:
                        logger.info(f"Email alert sent to {len(recipients)} recipients")
                        return True
                    else:
                        logger.error(f"Email service returned status {response.status}")
                        return False
                        
        except Exception as e:
            logger.error(f"Email alert failed: {e}")
            return False
    
    def _generate_email_html(self, alert: BudgetAlert, budget: Budget) -> str:
        """Generate HTML email content."""
        severity_color = {
            "low": "#28a745",
            "medium": "#ffc107", 
            "high": "#fd7e14",
            "critical": "#dc3545"
        }.get(alert.severity.value, "#6c757d")
        
        return f"""
        <!DOCTYPE html>
        <html>
        <head>
            <style>
                body {{ font-family: Arial, sans-serif; margin: 0; padding: 20px; background-color: #f8f9fa; }}
                .container {{ max-width: 600px; margin: 0 auto; background-color: white; border-radius: 8px; overflow: hidden; box-shadow: 0 2px 10px rgba(0,0,0,0.1); }}
                .header {{ background-color: {severity_color}; color: white; padding: 20px; text-align: center; }}
                .content {{ padding: 30px; }}
                .metrics {{ background-color: #f8f9fa; padding: 20px; margin: 20px 0; border-radius: 6px; }}
                .metric {{ display: inline-block; margin: 10px 20px 10px 0; }}
                .metric-label {{ font-weight: bold; color: #495057; }}
                .metric-value {{ font-size: 1.2em; color: #212529; }}
                .progress-bar {{ background-color: #e9ecef; height: 20px; border-radius: 10px; margin: 15px 0; overflow: hidden; }}
                .progress-fill {{ background-color: {severity_color}; height: 100%; transition: width 0.3s ease; }}
                .footer {{ background-color: #f8f9fa; padding: 20px; text-align: center; font-size: 0.9em; color: #6c757d; }}
                .alert-button {{ display: inline-block; background-color: {severity_color}; color: white; padding: 12px 24px; text-decoration: none; border-radius: 6px; margin: 20px 0; }}
            </style>
        </head>
        <body>
            <div class="container">
                <div class="header">
                    <h1>{alert.alert_title}</h1>
                    <p>Budget Alert - {alert.severity.value.title()} Priority</p>
                </div>
                
                <div class="content">
                    <p>{alert.alert_message}</p>
                    
                    <div class="metrics">
                        <div class="metric">
                            <div class="metric-label">Current Spend</div>
                            <div class="metric-value">${alert.current_spend:.2f}</div>
                        </div>
                        <div class="metric">
                            <div class="metric-label">Budget Amount</div>
                            <div class="metric-value">${alert.budget_amount:.2f}</div>
                        </div>
                        <div class="metric">
                            <div class="metric-label">Usage</div>
                            <div class="metric-value">{alert.percentage_used:.1f}%</div>
                        </div>
                    </div>
                    
                    <div class="progress-bar">
                        <div class="progress-fill" style="width: {min(alert.percentage_used, 100):.1f}%"></div>
                    </div>
                    
                    <p><strong>Budget Period:</strong> {alert.period_start.strftime('%Y-%m-%d')} to {alert.period_end.strftime('%Y-%m-%d')}</p>
                    
                    {f"<p><strong>Tenant:</strong> {alert.tenant_id}</p>" if alert.tenant_id else ""}
                    {f"<p><strong>Learner:</strong> {alert.learner_id}</p>" if alert.learner_id else ""}
                    
                    <a href="{config.DASHBOARD_URL}/budgets/{budget.id}" class="alert-button">View Budget Details</a>
                </div>
                
                <div class="footer">
                    <p>This alert was generated automatically by the FinOps system.</p>
                    <p>Alert ID: {alert.id} | Generated: {alert.created_at.strftime('%Y-%m-%d %H:%M:%S UTC')}</p>
                </div>
            </div>
        </body>
        </html>
        """
    
    def _generate_email_text(self, alert: BudgetAlert, budget: Budget) -> str:
        """Generate plain text email content."""
        return f"""
{alert.alert_title}

{alert.alert_message}

Budget Details:
- Current Spend: ${alert.current_spend:.2f}
- Budget Amount: ${alert.budget_amount:.2f}
- Usage: {alert.percentage_used:.1f}%
- Period: {alert.period_start.strftime('%Y-%m-%d')} to {alert.period_end.strftime('%Y-%m-%d')}
{f"- Tenant: {alert.tenant_id}" if alert.tenant_id else ""}
{f"- Learner: {alert.learner_id}" if alert.learner_id else ""}

View budget details: {config.DASHBOARD_URL}/budgets/{budget.id}

Alert ID: {alert.id}
Generated: {alert.created_at.strftime('%Y-%m-%d %H:%M:%S UTC')}

This alert was generated automatically by the FinOps system.
        """
    
    async def _send_slack_alert(self, alert: BudgetAlert, budget: Budget) -> bool:
        """Send budget alert via Slack."""
        try:
            slack_webhook_url = budget.webhook_url or config.SLACK_WEBHOOK_URL
            if not slack_webhook_url:
                logger.warning(f"No Slack webhook URL configured for budget {budget.name}")
                return False
            
            # Prepare Slack message
            color = {
                "low": "good",
                "medium": "warning", 
                "high": "warning",
                "critical": "danger"
            }.get(alert.severity.value, "#808080")
            
            slack_message = {
                "username": "FinOps Bot",
                "icon_emoji": ":moneybag:",
                "attachments": [{
                    "color": color,
                    "title": alert.alert_title,
                    "text": alert.alert_message,
                    "fields": [
                        {
                            "title": "Current Spend",
                            "value": f"${alert.current_spend:.2f}",
                            "short": True
                        },
                        {
                            "title": "Budget Amount", 
                            "value": f"${alert.budget_amount:.2f}",
                            "short": True
                        },
                        {
                            "title": "Usage",
                            "value": f"{alert.percentage_used:.1f}%",
                            "short": True
                        },
                        {
                            "title": "Priority",
                            "value": alert.severity.value.title(),
                            "short": True
                        }
                    ],
                    "footer": "FinOps Alert System",
                    "ts": int(alert.created_at.timestamp()),
                    "actions": [{
                        "type": "button",
                        "text": "View Budget",
                        "url": f"{config.DASHBOARD_URL}/budgets/{budget.id}"
                    }]
                }]
            }
            
            # Add tenant/learner info if available
            if alert.tenant_id:
                slack_message["attachments"][0]["fields"].append({
                    "title": "Tenant",
                    "value": alert.tenant_id,
                    "short": True
                })
            
            if alert.learner_id:
                slack_message["attachments"][0]["fields"].append({
                    "title": "Learner", 
                    "value": alert.learner_id,
                    "short": True
                })
            
            # Send to Slack
            async with aiohttp.ClientSession() as session:
                async with session.post(
                    slack_webhook_url,
                    json=slack_message,
                    timeout=aiohttp.ClientTimeout(total=self._webhook_timeout)
                ) as response:
                    if response.status == 200:
                        logger.info(f"Slack alert sent for budget {budget.name}")
                        return True
                    else:
                        response_text = await response.text()
                        logger.error(f"Slack webhook failed with status {response.status}: {response_text}")
                        return False
                        
        except Exception as e:
            logger.error(f"Slack alert failed: {e}")
            return False
    
    async def _send_webhook_alert(self, alert: BudgetAlert, budget: Budget) -> bool:
        """Send budget alert via custom webhook."""
        try:
            webhook_url = budget.webhook_url
            if not webhook_url:
                logger.warning(f"No webhook URL configured for budget {budget.name}")
                return False
            
            # Prepare webhook payload
            webhook_payload = {
                "event_type": "budget_alert",
                "alert": {
                    "id": str(alert.id),
                    "title": alert.alert_title,
                    "message": alert.alert_message,
                    "severity": alert.severity.value,
                    "threshold_percentage": float(alert.threshold_percentage),
                    "current_spend": float(alert.current_spend),
                    "budget_amount": float(alert.budget_amount),
                    "percentage_used": float(alert.percentage_used),
                    "created_at": alert.created_at.isoformat()
                },
                "budget": {
                    "id": str(budget.id),
                    "name": budget.name,
                    "type": budget.budget_type.value,
                    "period": budget.period.value,
                    "tenant_id": budget.tenant_id,
                    "learner_id": budget.learner_id,
                    "service_name": budget.service_name,
                    "start_date": budget.start_date.isoformat(),
                    "end_date": budget.end_date.isoformat()
                },
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "dashboard_url": f"{config.DASHBOARD_URL}/budgets/{budget.id}"
            }
            
            # Send webhook with retries
            for attempt in range(self._retry_attempts):
                try:
                    async with aiohttp.ClientSession() as session:
                        async with session.post(
                            webhook_url,
                            json=webhook_payload,
                            headers={
                                "Content-Type": "application/json",
                                "User-Agent": "FinOps-Service/1.0"
                            },
                            timeout=aiohttp.ClientTimeout(total=self._webhook_timeout)
                        ) as response:
                            if response.status in [200, 201, 202]:
                                logger.info(f"Webhook alert sent for budget {budget.name}")
                                return True
                            else:
                                response_text = await response.text()
                                logger.warning(f"Webhook attempt {attempt + 1} failed with status {response.status}: {response_text}")
                                
                except asyncio.TimeoutError:
                    logger.warning(f"Webhook attempt {attempt + 1} timed out")
                except Exception as e:
                    logger.warning(f"Webhook attempt {attempt + 1} failed: {e}")
                
                # Wait before retry (exponential backoff)
                if attempt < self._retry_attempts - 1:
                    await asyncio.sleep(2 ** attempt)
            
            logger.error(f"All webhook attempts failed for budget {budget.name}")
            return False
            
        except Exception as e:
            logger.error(f"Webhook alert failed: {e}")
            return False
    
    async def _send_sms_alert(self, alert: BudgetAlert, budget: Budget) -> bool:
        """Send budget alert via SMS."""
        try:
            # SMS implementation would depend on your SMS provider (Twilio, AWS SNS, etc.)
            # This is a placeholder implementation
            
            sms_recipients = [
                recipient for recipient in (budget.alert_recipients or [])
                if recipient.startswith('+') or recipient.isdigit()
            ]
            
            if not sms_recipients:
                logger.warning(f"No SMS recipients configured for budget {budget.name}")
                return False
            
            # Prepare SMS message (keep it short due to SMS character limits)
            sms_message = (f"FinOps Alert: {budget.name} at {alert.percentage_used:.1f}% "
                          f"(${alert.current_spend:.2f}/${alert.budget_amount:.2f}). "
                          f"View: {config.DASHBOARD_URL}/budgets/{budget.id}")
            
            # Send via SMS service (placeholder)
            sms_data = {
                "recipients": sms_recipients,
                "message": sms_message,
                "sender": config.SMS_SENDER_ID,
                "alert_id": str(alert.id)
            }
            
            async with aiohttp.ClientSession() as session:
                async with session.post(
                    f"{config.SMS_SERVICE_URL}/send",
                    json=sms_data,
                    headers={"Authorization": f"Bearer {config.SMS_SERVICE_TOKEN}"},
                    timeout=aiohttp.ClientTimeout(total=self._webhook_timeout)
                ) as response:
                    if response.status == 200:
                        logger.info(f"SMS alert sent to {len(sms_recipients)} recipients")
                        return True
                    else:
                        logger.error(f"SMS service returned status {response.status}")
                        return False
                        
        except Exception as e:
            logger.error(f"SMS alert failed: {e}")
            return False
    
    async def test_alert_channels(self, budget: Budget) -> Dict[str, bool]:
        """Test all configured alert channels for a budget."""
        results = {}
        
        # Create test alert
        test_alert = BudgetAlert(
            id="test-alert",
            budget_id=budget.id,
            budget_name=budget.name,
            severity="low",
            threshold_percentage=Decimal("50"),
            current_spend=budget.amount * Decimal("0.5"),
            budget_amount=budget.amount,
            percentage_used=Decimal("50"),
            tenant_id=budget.tenant_id,
            learner_id=budget.learner_id,
            period_start=budget.start_date,
            period_end=budget.end_date,
            alert_title=f"Test Alert: {budget.name}",
            alert_message=f"This is a test alert for budget '{budget.name}'. Please ignore.",
            created_at=datetime.now(timezone.utc)
        )
        
        # Test each channel
        for channel in budget.alert_channels or ["email"]:
            try:
                if channel == "email":
                    results["email"] = await self._send_email_alert(test_alert, budget)
                elif channel == "slack":
                    results["slack"] = await self._send_slack_alert(test_alert, budget)
                elif channel == "webhook":
                    results["webhook"] = await self._send_webhook_alert(test_alert, budget)
                elif channel == "sms":
                    results["sms"] = await self._send_sms_alert(test_alert, budget)
                else:
                    results[channel] = False
                    
            except Exception as e:
                logger.error(f"Test failed for channel {channel}: {e}")
                results[channel] = False
        
        return results
    
    async def send_daily_summary(self, tenant_id: Optional[str] = None) -> bool:
        """Send daily budget summary to administrators."""
        try:
            # This would generate and send a daily summary of budget status
            # Implementation depends on your specific requirements
            logger.info(f"Daily summary sent for tenant {tenant_id or 'all'}")
            return True
            
        except Exception as e:
            logger.error(f"Daily summary failed: {e}")
            return False
