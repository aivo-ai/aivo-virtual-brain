"""
Budget monitoring and alerting system for the FinOps service.

This module provides real-time budget monitoring, threshold checking, and automated
alert generation for cost overruns and budget violations.
"""

import asyncio
import logging
from datetime import datetime, timezone, timedelta
from decimal import Decimal, ROUND_HALF_UP
from typing import Dict, List, Optional, Tuple, Any

from sqlalchemy import select, and_, or_, func, text
from sqlalchemy.ext.asyncio import AsyncSession

from .models import (
    Budget, BudgetAlert, UsageEvent, CostSummary,
    BudgetType, BudgetPeriod, AlertSeverity, AlertChannel
)
from .database import get_db_session
from .alerts import AlertManager

logger = logging.getLogger(__name__)


class BudgetMonitor:
    """Real-time budget monitoring and alerting system."""
    
    def __init__(self):
        self.alert_manager = AlertManager()
        self._monitored_budgets = set()
        self._alert_cooldown = {}  # Prevent alert spam
    
    async def check_all_budgets(self, session: Optional[AsyncSession] = None) -> Dict[str, Any]:
        """Check all active budgets and trigger alerts as needed."""
        if session:
            return await self._check_budgets_with_session(session)
        else:
            async with get_db_session() as db_session:
                return await self._check_budgets_with_session(db_session)
    
    async def _check_budgets_with_session(self, session: AsyncSession) -> Dict[str, Any]:
        """Check budgets with database session."""
        results = {
            "budgets_checked": 0,
            "alerts_triggered": 0,
            "budgets_exceeded": 0,
            "total_overage": Decimal('0'),
            "errors": []
        }
        
        try:
            # Get all active budgets
            query = select(Budget).where(Budget.is_active == True)
            result = await session.execute(query)
            active_budgets = result.scalars().all()
            
            results["budgets_checked"] = len(active_budgets)
            
            # Check each budget
            for budget in active_budgets:
                try:
                    budget_status = await self._check_budget(budget, session)
                    
                    if budget_status["alerts_sent"] > 0:
                        results["alerts_triggered"] += budget_status["alerts_sent"]
                    
                    if budget_status["is_exceeded"]:
                        results["budgets_exceeded"] += 1
                        results["total_overage"] += budget_status["overage_amount"]
                    
                    # Update budget status in database
                    budget.current_spend = budget_status["current_spend"]
                    budget.is_exceeded = budget_status["is_exceeded"]
                    budget.last_alert_sent = budget_status.get("last_alert_sent")
                    budget.last_alert_threshold = budget_status.get("last_alert_threshold")
                    
                except Exception as e:
                    logger.error(f"Error checking budget {budget.id}: {e}")
                    results["errors"].append(f"Budget {budget.id}: {str(e)}")
            
            await session.commit()
            
        except Exception as e:
            logger.error(f"Budget monitoring failed: {e}")
            results["errors"].append(f"General error: {str(e)}")
        
        return results
    
    async def _check_budget(self, budget: Budget, session: AsyncSession) -> Dict[str, Any]:
        """Check a specific budget and trigger alerts if needed."""
        # Calculate current spending for the budget period
        current_spend = await self._calculate_budget_spending(budget, session)
        
        # Calculate percentage used
        percentage_used = (current_spend / budget.amount * 100) if budget.amount > 0 else Decimal('0')
        
        # Check if budget is exceeded
        is_exceeded = current_spend > budget.amount
        overage_amount = max(current_spend - budget.amount, Decimal('0'))
        
        # Determine which alert thresholds have been crossed
        alerts_sent = 0
        last_alert_sent = budget.last_alert_sent
        last_alert_threshold = budget.last_alert_threshold
        
        for threshold in sorted(budget.alert_thresholds or [], reverse=True):
            threshold_decimal = Decimal(str(threshold))
            
            # Check if this threshold has been crossed
            if percentage_used >= threshold_decimal:
                # Check if we haven't already alerted for this threshold
                if (not last_alert_threshold or 
                    threshold_decimal > Decimal(str(last_alert_threshold))):
                    
                    # Check cooldown to prevent spam
                    if await self._should_send_alert(budget.id, threshold_decimal):
                        alert_sent = await self._send_budget_alert(
                            budget, current_spend, percentage_used, threshold_decimal, session
                        )
                        
                        if alert_sent:
                            alerts_sent += 1
                            last_alert_sent = datetime.now(timezone.utc)
                            last_alert_threshold = threshold_decimal
                            
                            # Update cooldown
                            self._alert_cooldown[f"{budget.id}:{threshold}"] = datetime.now(timezone.utc)
                
                # Only alert for the highest threshold crossed
                break
        
        return {
            "current_spend": current_spend,
            "percentage_used": percentage_used,
            "is_exceeded": is_exceeded,
            "overage_amount": overage_amount,
            "alerts_sent": alerts_sent,
            "last_alert_sent": last_alert_sent,
            "last_alert_threshold": last_alert_threshold
        }
    
    async def _calculate_budget_spending(self, budget: Budget, session: AsyncSession) -> Decimal:
        """Calculate current spending for a budget within its period."""
        # Build base query for usage events
        query = select(func.sum(UsageEvent.calculated_cost)).where(
            and_(
                UsageEvent.timestamp >= budget.start_date,
                UsageEvent.timestamp <= budget.end_date
            )
        )
        
        # Add budget-specific filters
        if budget.budget_type == BudgetType.TENANT and budget.tenant_id:
            query = query.where(UsageEvent.tenant_id == budget.tenant_id)
        elif budget.budget_type == BudgetType.LEARNER and budget.learner_id:
            query = query.where(UsageEvent.learner_id == budget.learner_id)
        elif budget.budget_type == BudgetType.SERVICE and budget.service_name:
            query = query.where(UsageEvent.service_name == budget.service_name)
        elif budget.budget_type == BudgetType.MODEL and budget.model_name:
            query = query.where(UsageEvent.model_name == budget.model_name)
        # GLOBAL budget includes all usage events (no additional filters)
        
        result = await session.execute(query)
        total_spend = result.scalar() or Decimal('0')
        
        return total_spend.quantize(Decimal('0.000001'), rounding=ROUND_HALF_UP)
    
    async def _should_send_alert(self, budget_id: str, threshold: Decimal) -> bool:
        """Check if an alert should be sent based on cooldown periods."""
        cooldown_key = f"{budget_id}:{threshold}"
        last_alert = self._alert_cooldown.get(cooldown_key)
        
        if not last_alert:
            return True
        
        # Different cooldown periods based on threshold
        cooldown_hours = 1  # Default 1 hour
        if threshold >= 100:  # Exceeded budget
            cooldown_hours = 0.5  # 30 minutes for exceeded budget
        elif threshold >= 90:  # Critical threshold
            cooldown_hours = 2   # 2 hours for critical
        elif threshold >= 75:  # High threshold
            cooldown_hours = 6   # 6 hours for high
        else:  # Lower thresholds
            cooldown_hours = 24  # 24 hours for lower thresholds
        
        time_since_alert = datetime.now(timezone.utc) - last_alert
        return time_since_alert.total_seconds() > (cooldown_hours * 3600)
    
    async def _send_budget_alert(
        self,
        budget: Budget,
        current_spend: Decimal,
        percentage_used: Decimal,
        threshold: Decimal,
        session: AsyncSession
    ) -> bool:
        """Send budget alert and record in database."""
        try:
            # Determine alert severity
            severity = self._determine_alert_severity(threshold)
            
            # Create alert record
            alert = BudgetAlert(
                budget_id=budget.id,
                budget_name=budget.name,
                severity=severity,
                threshold_percentage=threshold,
                current_spend=current_spend,
                budget_amount=budget.amount,
                percentage_used=percentage_used,
                tenant_id=budget.tenant_id,
                learner_id=budget.learner_id,
                period_start=budget.start_date,
                period_end=budget.end_date,
                alert_title=self._generate_alert_title(budget, percentage_used, threshold),
                alert_message=self._generate_alert_message(budget, current_spend, percentage_used, threshold)
            )
            
            # Save alert to database
            session.add(alert)
            await session.flush()  # Get the alert ID
            
            # Send notifications
            notification_sent = await self.alert_manager.send_budget_alert(
                alert, budget, session
            )
            
            if notification_sent:
                # Update alert with notification details
                alert.channels_sent = budget.alert_channels or ["email"]
                alert.recipients_notified = budget.alert_recipients or []
                
                logger.info(f"Budget alert sent for {budget.name}: {percentage_used:.1f}% used")
                return True
            else:
                logger.warning(f"Failed to send budget alert for {budget.name}")
                return False
                
        except Exception as e:
            logger.error(f"Error sending budget alert: {e}")
            return False
    
    def _determine_alert_severity(self, threshold: Decimal) -> AlertSeverity:
        """Determine alert severity based on threshold."""
        if threshold >= 100:
            return AlertSeverity.CRITICAL
        elif threshold >= 90:
            return AlertSeverity.HIGH
        elif threshold >= 75:
            return AlertSeverity.MEDIUM
        else:
            return AlertSeverity.LOW
    
    def _generate_alert_title(
        self, 
        budget: Budget, 
        percentage_used: Decimal, 
        threshold: Decimal
    ) -> str:
        """Generate alert title."""
        if threshold >= 100:
            return f"Budget Exceeded: {budget.name}"
        else:
            return f"Budget Alert: {budget.name} at {percentage_used:.1f}% usage"
    
    def _generate_alert_message(
        self,
        budget: Budget,
        current_spend: Decimal,
        percentage_used: Decimal,
        threshold: Decimal
    ) -> str:
        """Generate detailed alert message."""
        if threshold >= 100:
            overage = current_spend - budget.amount
            message = (f"Budget '{budget.name}' has been exceeded by ${overage:.2f} "
                      f"({percentage_used:.1f}% usage). "
                      f"Current spend: ${current_spend:.2f} of ${budget.amount:.2f} budget.")
        else:
            remaining = budget.amount - current_spend
            message = (f"Budget '{budget.name}' has reached {percentage_used:.1f}% usage. "
                      f"Current spend: ${current_spend:.2f} of ${budget.amount:.2f} budget. "
                      f"Remaining: ${remaining:.2f}")
        
        # Add period information
        period_end = budget.end_date.strftime("%Y-%m-%d")
        message += f" Budget period ends: {period_end}."
        
        # Add recommendations
        if threshold >= 90:
            message += " Consider reducing usage or requesting budget increase."
        elif threshold >= 75:
            message += " Monitor usage closely to avoid budget overrun."
        
        return message
    
    async def check_budget_by_id(
        self, 
        budget_id: str, 
        session: Optional[AsyncSession] = None
    ) -> Optional[Dict[str, Any]]:
        """Check a specific budget by ID."""
        if session:
            return await self._check_budget_by_id_with_session(budget_id, session)
        else:
            async with get_db_session() as db_session:
                return await self._check_budget_by_id_with_session(budget_id, db_session)
    
    async def _check_budget_by_id_with_session(
        self, 
        budget_id: str, 
        session: AsyncSession
    ) -> Optional[Dict[str, Any]]:
        """Check specific budget with database session."""
        # Get budget
        query = select(Budget).where(Budget.id == budget_id, Budget.is_active == True)
        result = await session.execute(query)
        budget = result.scalar_one_or_none()
        
        if not budget:
            return None
        
        # Check budget status
        budget_status = await self._check_budget(budget, session)
        
        # Add forecast information
        forecast = await self._get_budget_forecast(budget, session)
        budget_status.update(forecast)
        
        return budget_status
    
    async def _get_budget_forecast(self, budget: Budget, session: AsyncSession) -> Dict[str, Any]:
        """Get budget forecast for remaining period."""
        try:
            now = datetime.now(timezone.utc)
            
            # Calculate days elapsed and remaining
            total_days = (budget.end_date - budget.start_date).days
            days_elapsed = (now - budget.start_date).days
            days_remaining = (budget.end_date - now).days
            
            if days_remaining <= 0:
                return {
                    "days_remaining": 0,
                    "projected_spend": budget.current_spend,
                    "projected_overage": max(budget.current_spend - budget.amount, Decimal('0')),
                    "burn_rate": Decimal('0')
                }
            
            # Calculate daily burn rate
            if days_elapsed > 0:
                daily_burn_rate = budget.current_spend / days_elapsed
            else:
                daily_burn_rate = Decimal('0')
            
            # Project spending for remaining period
            projected_additional_spend = daily_burn_rate * days_remaining
            projected_total_spend = budget.current_spend + projected_additional_spend
            projected_overage = max(projected_total_spend - budget.amount, Decimal('0'))
            
            return {
                "days_remaining": days_remaining,
                "days_elapsed": days_elapsed,
                "total_period_days": total_days,
                "daily_burn_rate": daily_burn_rate,
                "projected_spend": projected_total_spend,
                "projected_overage": projected_overage,
                "projected_additional_spend": projected_additional_spend
            }
            
        except Exception as e:
            logger.error(f"Error calculating budget forecast: {e}")
            return {}
    
    async def get_budget_alerts(
        self,
        tenant_id: Optional[str] = None,
        learner_id: Optional[str] = None,
        severity: Optional[AlertSeverity] = None,
        is_acknowledged: Optional[bool] = None,
        limit: int = 50,
        offset: int = 0,
        session: Optional[AsyncSession] = None
    ) -> Tuple[List[BudgetAlert], int]:
        """Get budget alerts with filtering."""
        if session:
            return await self._get_alerts_with_session(
                tenant_id, learner_id, severity, is_acknowledged, limit, offset, session
            )
        else:
            async with get_db_session() as db_session:
                return await self._get_alerts_with_session(
                    tenant_id, learner_id, severity, is_acknowledged, limit, offset, db_session
                )
    
    async def _get_alerts_with_session(
        self,
        tenant_id: Optional[str],
        learner_id: Optional[str],
        severity: Optional[AlertSeverity],
        is_acknowledged: Optional[bool],
        limit: int,
        offset: int,
        session: AsyncSession
    ) -> Tuple[List[BudgetAlert], int]:
        """Get alerts with database session."""
        # Build query
        query = select(BudgetAlert)
        count_query = select(func.count(BudgetAlert.id))
        
        conditions = []
        if tenant_id:
            conditions.append(BudgetAlert.tenant_id == tenant_id)
        if learner_id:
            conditions.append(BudgetAlert.learner_id == learner_id)
        if severity:
            conditions.append(BudgetAlert.severity == severity)
        if is_acknowledged is not None:
            conditions.append(BudgetAlert.is_acknowledged == is_acknowledged)
        
        if conditions:
            query = query.where(and_(*conditions))
            count_query = count_query.where(and_(*conditions))
        
        # Get total count
        count_result = await session.execute(count_query)
        total_count = count_result.scalar()
        
        # Get alerts with pagination
        query = query.order_by(BudgetAlert.created_at.desc()).offset(offset).limit(limit)
        result = await session.execute(query)
        alerts = result.scalars().all()
        
        return list(alerts), total_count
    
    async def acknowledge_alert(
        self,
        alert_id: str,
        acknowledged_by: str,
        session: Optional[AsyncSession] = None
    ) -> bool:
        """Acknowledge a budget alert."""
        if session:
            return await self._acknowledge_alert_with_session(alert_id, acknowledged_by, session)
        else:
            async with get_db_session() as db_session:
                return await self._acknowledge_alert_with_session(alert_id, acknowledged_by, db_session)
    
    async def _acknowledge_alert_with_session(
        self,
        alert_id: str,
        acknowledged_by: str,
        session: AsyncSession
    ) -> bool:
        """Acknowledge alert with database session."""
        try:
            # Get alert
            query = select(BudgetAlert).where(BudgetAlert.id == alert_id)
            result = await session.execute(query)
            alert = result.scalar_one_or_none()
            
            if not alert:
                return False
            
            # Update alert
            alert.is_acknowledged = True
            alert.acknowledged_by = acknowledged_by
            alert.acknowledged_at = datetime.now(timezone.utc)
            
            await session.commit()
            
            logger.info(f"Alert {alert_id} acknowledged by {acknowledged_by}")
            return True
            
        except Exception as e:
            logger.error(f"Error acknowledging alert {alert_id}: {e}")
            return False
    
    async def get_budget_status_summary(
        self,
        tenant_id: Optional[str] = None,
        session: Optional[AsyncSession] = None
    ) -> Dict[str, Any]:
        """Get summary of budget statuses."""
        if session:
            return await self._get_status_summary_with_session(tenant_id, session)
        else:
            async with get_db_session() as db_session:
                return await self._get_status_summary_with_session(tenant_id, db_session)
    
    async def _get_status_summary_with_session(
        self,
        tenant_id: Optional[str],
        session: AsyncSession
    ) -> Dict[str, Any]:
        """Get status summary with database session."""
        # Build budget query
        budget_query = select(Budget).where(Budget.is_active == True)
        if tenant_id:
            budget_query = budget_query.where(Budget.tenant_id == tenant_id)
        
        budget_result = await session.execute(budget_query)
        budgets = budget_result.scalars().all()
        
        summary = {
            "total_budgets": len(budgets),
            "budgets_exceeded": 0,
            "budgets_at_risk": 0,  # >75% usage
            "total_budget_amount": Decimal('0'),
            "total_current_spend": Decimal('0'),
            "total_overage": Decimal('0'),
            "pending_alerts": 0
        }
        
        # Analyze each budget
        for budget in budgets:
            summary["total_budget_amount"] += budget.amount
            summary["total_current_spend"] += budget.current_spend or Decimal('0')
            
            if budget.is_exceeded:
                summary["budgets_exceeded"] += 1
                summary["total_overage"] += max(
                    (budget.current_spend or Decimal('0')) - budget.amount,
                    Decimal('0')
                )
            else:
                # Check if at risk (>75% usage)
                percentage_used = ((budget.current_spend or Decimal('0')) / budget.amount * 100) if budget.amount > 0 else Decimal('0')
                if percentage_used > 75:
                    summary["budgets_at_risk"] += 1
        
        # Get pending alerts count
        alert_query = select(func.count(BudgetAlert.id)).where(
            BudgetAlert.is_acknowledged == False
        )
        if tenant_id:
            alert_query = alert_query.where(BudgetAlert.tenant_id == tenant_id)
        
        alert_result = await session.execute(alert_query)
        summary["pending_alerts"] = alert_result.scalar()
        
        return summary
