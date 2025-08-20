"""
FinOps Service API Routes
Comprehensive cost tracking, budget management, and financial operations endpoints
"""

from datetime import datetime, timedelta
from decimal import Decimal
from typing import List, Optional, Dict, Any
from uuid import uuid4

from fastapi import APIRouter, HTTPException, Depends, Query, Path, Body
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
import structlog

from .models import (
    # Core models
    UsageEvent, Budget, BudgetAlert, CostSummary, ProviderPricing,
    CostForecast, CostOptimization,
    
    # Request/Response models
    CreateBudgetRequest, UpdateBudgetRequest,
    CostQueryRequest, CostResponse, UsageStatsResponse,
    
    # Enums
    BudgetType, BudgetPeriod, ProviderType, AlertSeverity,
    CostCategory, ModelType
)
from .database import get_db_connection, log_usage_event
from .cost_calculator import CostCalculator
from .budget_monitor import BudgetMonitor
from .pricing_updater import PricingUpdater
from .auth import verify_token, get_current_user, require_permissions

logger = structlog.get_logger(__name__)
router = APIRouter()
security = HTTPBearer()


# Dependency injection
async def get_cost_calculator() -> CostCalculator:
    """Get cost calculator instance"""
    from .main import app_state
    if not app_state["cost_calculator"]:
        raise HTTPException(status_code=503, detail="Cost calculator not available")
    return app_state["cost_calculator"]


async def get_budget_monitor() -> BudgetMonitor:
    """Get budget monitor instance"""
    from .main import app_state
    if not app_state["budget_monitor"]:
        raise HTTPException(status_code=503, detail="Budget monitor not available")
    return app_state["budget_monitor"]


async def get_pricing_updater() -> PricingUpdater:
    """Get pricing updater instance"""
    from .main import app_state
    if not app_state["pricing_updater"]:
        raise HTTPException(status_code=503, detail="Pricing updater not available")
    return app_state["pricing_updater"]


# === Usage Events & Cost Tracking ===

@router.post("/usage-events", response_model=UsageEvent, tags=["usage"])
async def record_usage_event(
    event: UsageEvent,
    calculator: CostCalculator = Depends(get_cost_calculator),
    current_user: dict = Depends(get_current_user)
):
    """
    Record a usage event for cost calculation
    
    This endpoint receives usage events from AI inference services and calculates
    associated costs based on current provider pricing.
    """
    try:
        # Validate tenant access
        if event.tenant_id and not await verify_tenant_access(current_user, event.tenant_id):
            raise HTTPException(status_code=403, detail="Access denied to tenant")
        
        # Calculate cost for the event
        calculated_event = await calculator.calculate_event_cost(event)
        
        # Store the event
        await log_usage_event(calculated_event)
        
        # Check budget implications
        budget_monitor = await get_budget_monitor()
        await budget_monitor.check_budget_impact(calculated_event)
        
        logger.info(
            "Usage event recorded",
            event_id=calculated_event.id,
            tenant_id=calculated_event.tenant_id,
            cost=float(calculated_event.calculated_cost),
            provider=calculated_event.provider
        )
        
        return calculated_event
        
    except Exception as e:
        logger.error("Failed to record usage event", error=str(e), exc_info=True)
        raise HTTPException(status_code=500, detail=f"Failed to record usage event: {str(e)}")


@router.post("/usage-events/batch", response_model=List[UsageEvent], tags=["usage"])
async def record_usage_events_batch(
    events: List[UsageEvent],
    calculator: CostCalculator = Depends(get_cost_calculator),
    current_user: dict = Depends(get_current_user)
):
    """
    Record multiple usage events in batch for better performance
    """
    try:
        calculated_events = []
        
        for event in events:
            # Validate tenant access
            if event.tenant_id and not await verify_tenant_access(current_user, event.tenant_id):
                continue  # Skip unauthorized events
            
            # Calculate cost
            calculated_event = await calculator.calculate_event_cost(event)
            calculated_events.append(calculated_event)
        
        # Batch store events
        await calculator.store_events_batch(calculated_events)
        
        # Check budget implications for all events
        budget_monitor = await get_budget_monitor()
        await budget_monitor.check_budget_impact_batch(calculated_events)
        
        logger.info(
            "Batch usage events recorded",
            event_count=len(calculated_events),
            total_cost=sum(float(e.calculated_cost) for e in calculated_events)
        )
        
        return calculated_events
        
    except Exception as e:
        logger.error("Failed to record batch usage events", error=str(e), exc_info=True)
        raise HTTPException(status_code=500, detail=f"Failed to record batch events: {str(e)}")


# === Cost Queries and Reporting ===

@router.post("/costs/query", response_model=CostResponse, tags=["costs"])
async def query_costs(
    query: CostQueryRequest,
    calculator: CostCalculator = Depends(get_cost_calculator),
    current_user: dict = Depends(get_current_user)
):
    """
    Query cost data with flexible filtering and aggregation
    """
    try:
        # Validate tenant access if specified
        if query.tenant_id and not await verify_tenant_access(current_user, query.tenant_id):
            raise HTTPException(status_code=403, detail="Access denied to tenant")
        
        # Execute cost query
        cost_response = await calculator.query_costs(query)
        
        logger.info(
            "Cost query executed",
            tenant_id=query.tenant_id,
            period_days=(query.end_date - query.start_date).days,
            total_cost=float(cost_response.total_cost)
        )
        
        return cost_response
        
    except Exception as e:
        logger.error("Cost query failed", error=str(e), exc_info=True)
        raise HTTPException(status_code=500, detail=f"Cost query failed: {str(e)}")


@router.get("/costs/summary", response_model=List[CostSummary], tags=["costs"])
async def get_cost_summaries(
    start_date: datetime = Query(..., description="Start date for summaries"),
    end_date: datetime = Query(..., description="End date for summaries"),
    tenant_id: Optional[str] = Query(None, description="Filter by tenant"),
    service_name: Optional[str] = Query(None, description="Filter by service"),
    group_by: str = Query("day", description="Grouping period: hour, day, week, month"),
    calculator: CostCalculator = Depends(get_cost_calculator),
    current_user: dict = Depends(get_current_user)
):
    """
    Get pre-calculated cost summaries for reporting and dashboards
    """
    try:
        # Validate tenant access
        if tenant_id and not await verify_tenant_access(current_user, tenant_id):
            raise HTTPException(status_code=403, detail="Access denied to tenant")
        
        summaries = await calculator.get_cost_summaries(
            start_date=start_date,
            end_date=end_date,
            tenant_id=tenant_id,
            service_name=service_name,
            group_by=group_by
        )
        
        return summaries
        
    except Exception as e:
        logger.error("Failed to get cost summaries", error=str(e), exc_info=True)
        raise HTTPException(status_code=500, detail=f"Failed to get cost summaries: {str(e)}")


@router.get("/costs/usage-stats", response_model=UsageStatsResponse, tags=["costs"])
async def get_usage_statistics(
    start_date: datetime = Query(..., description="Start date for statistics"),
    end_date: datetime = Query(..., description="End date for statistics"),
    tenant_id: Optional[str] = Query(None, description="Filter by tenant"),
    learner_id: Optional[str] = Query(None, description="Filter by learner"),
    calculator: CostCalculator = Depends(get_cost_calculator),
    current_user: dict = Depends(get_current_user)
):
    """
    Get usage statistics for cost efficiency analysis
    """
    try:
        # Validate access
        if tenant_id and not await verify_tenant_access(current_user, tenant_id):
            raise HTTPException(status_code=403, detail="Access denied to tenant")
        
        stats = await calculator.get_usage_statistics(
            start_date=start_date,
            end_date=end_date,
            tenant_id=tenant_id,
            learner_id=learner_id
        )
        
        return stats
        
    except Exception as e:
        logger.error("Failed to get usage statistics", error=str(e), exc_info=True)
        raise HTTPException(status_code=500, detail=f"Failed to get usage statistics: {str(e)}")


# === Budget Management ===

@router.post("/budgets", response_model=Budget, tags=["budgets"])
async def create_budget(
    budget_request: CreateBudgetRequest,
    monitor: BudgetMonitor = Depends(get_budget_monitor),
    current_user: dict = Depends(get_current_user)
):
    """
    Create a new budget with alert configuration
    """
    try:
        # Validate permissions
        await require_permissions(current_user, ["finops:budget:create"])
        
        # Validate tenant access if specified
        if budget_request.tenant_id and not await verify_tenant_access(current_user, budget_request.tenant_id):
            raise HTTPException(status_code=403, detail="Access denied to tenant")
        
        # Create budget
        budget = await monitor.create_budget(budget_request)
        
        logger.info(
            "Budget created",
            budget_id=budget.id,
            budget_type=budget.budget_type,
            amount=float(budget.amount),
            tenant_id=budget.tenant_id
        )
        
        return budget
        
    except Exception as e:
        logger.error("Failed to create budget", error=str(e), exc_info=True)
        raise HTTPException(status_code=500, detail=f"Failed to create budget: {str(e)}")


@router.get("/budgets", response_model=List[Budget], tags=["budgets"])
async def list_budgets(
    budget_type: Optional[BudgetType] = Query(None, description="Filter by budget type"),
    tenant_id: Optional[str] = Query(None, description="Filter by tenant"),
    is_active: Optional[bool] = Query(None, description="Filter by active status"),
    monitor: BudgetMonitor = Depends(get_budget_monitor),
    current_user: dict = Depends(get_current_user)
):
    """
    List budgets with optional filtering
    """
    try:
        # Validate tenant access
        if tenant_id and not await verify_tenant_access(current_user, tenant_id):
            raise HTTPException(status_code=403, detail="Access denied to tenant")
        
        budgets = await monitor.list_budgets(
            budget_type=budget_type,
            tenant_id=tenant_id,
            is_active=is_active
        )
        
        return budgets
        
    except Exception as e:
        logger.error("Failed to list budgets", error=str(e), exc_info=True)
        raise HTTPException(status_code=500, detail=f"Failed to list budgets: {str(e)}")


@router.get("/budgets/{budget_id}", response_model=Budget, tags=["budgets"])
async def get_budget(
    budget_id: str = Path(..., description="Budget ID"),
    monitor: BudgetMonitor = Depends(get_budget_monitor),
    current_user: dict = Depends(get_current_user)
):
    """
    Get a specific budget by ID
    """
    try:
        budget = await monitor.get_budget(budget_id)
        
        if not budget:
            raise HTTPException(status_code=404, detail="Budget not found")
        
        # Validate tenant access
        if budget.tenant_id and not await verify_tenant_access(current_user, budget.tenant_id):
            raise HTTPException(status_code=403, detail="Access denied to budget")
        
        return budget
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error("Failed to get budget", budget_id=budget_id, error=str(e), exc_info=True)
        raise HTTPException(status_code=500, detail=f"Failed to get budget: {str(e)}")


@router.put("/budgets/{budget_id}", response_model=Budget, tags=["budgets"])
async def update_budget(
    budget_id: str = Path(..., description="Budget ID"),
    update_request: UpdateBudgetRequest = Body(...),
    monitor: BudgetMonitor = Depends(get_budget_monitor),
    current_user: dict = Depends(get_current_user)
):
    """
    Update an existing budget
    """
    try:
        # Get existing budget to check permissions
        existing_budget = await monitor.get_budget(budget_id)
        if not existing_budget:
            raise HTTPException(status_code=404, detail="Budget not found")
        
        # Validate permissions
        await require_permissions(current_user, ["finops:budget:update"])
        
        # Validate tenant access
        if existing_budget.tenant_id and not await verify_tenant_access(current_user, existing_budget.tenant_id):
            raise HTTPException(status_code=403, detail="Access denied to budget")
        
        # Update budget
        updated_budget = await monitor.update_budget(budget_id, update_request)
        
        logger.info(
            "Budget updated",
            budget_id=budget_id,
            updated_fields=list(update_request.dict(exclude_unset=True).keys())
        )
        
        return updated_budget
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error("Failed to update budget", budget_id=budget_id, error=str(e), exc_info=True)
        raise HTTPException(status_code=500, detail=f"Failed to update budget: {str(e)}")


@router.delete("/budgets/{budget_id}", tags=["budgets"])
async def delete_budget(
    budget_id: str = Path(..., description="Budget ID"),
    monitor: BudgetMonitor = Depends(get_budget_monitor),
    current_user: dict = Depends(get_current_user)
):
    """
    Delete a budget
    """
    try:
        # Get existing budget to check permissions
        existing_budget = await monitor.get_budget(budget_id)
        if not existing_budget:
            raise HTTPException(status_code=404, detail="Budget not found")
        
        # Validate permissions
        await require_permissions(current_user, ["finops:budget:delete"])
        
        # Validate tenant access
        if existing_budget.tenant_id and not await verify_tenant_access(current_user, existing_budget.tenant_id):
            raise HTTPException(status_code=403, detail="Access denied to budget")
        
        # Delete budget
        await monitor.delete_budget(budget_id)
        
        logger.info("Budget deleted", budget_id=budget_id)
        
        return {"message": "Budget deleted successfully"}
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error("Failed to delete budget", budget_id=budget_id, error=str(e), exc_info=True)
        raise HTTPException(status_code=500, detail=f"Failed to delete budget: {str(e)}")


@router.get("/budgets/{budget_id}/status", tags=["budgets"])
async def get_budget_status(
    budget_id: str = Path(..., description="Budget ID"),
    monitor: BudgetMonitor = Depends(get_budget_monitor),
    current_user: dict = Depends(get_current_user)
):
    """
    Get current budget status with spending and projections
    """
    try:
        budget = await monitor.get_budget(budget_id)
        if not budget:
            raise HTTPException(status_code=404, detail="Budget not found")
        
        # Validate tenant access
        if budget.tenant_id and not await verify_tenant_access(current_user, budget.tenant_id):
            raise HTTPException(status_code=403, detail="Access denied to budget")
        
        # Get detailed status
        status = await monitor.get_budget_status(budget_id)
        
        return status
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error("Failed to get budget status", budget_id=budget_id, error=str(e), exc_info=True)
        raise HTTPException(status_code=500, detail=f"Failed to get budget status: {str(e)}")


# === Budget Alerts ===

@router.get("/alerts", response_model=List[BudgetAlert], tags=["alerts"])
async def list_budget_alerts(
    severity: Optional[AlertSeverity] = Query(None, description="Filter by alert severity"),
    tenant_id: Optional[str] = Query(None, description="Filter by tenant"),
    is_acknowledged: Optional[bool] = Query(None, description="Filter by acknowledgment status"),
    limit: int = Query(50, ge=1, le=200, description="Maximum number of alerts to return"),
    offset: int = Query(0, ge=0, description="Number of alerts to skip"),
    monitor: BudgetMonitor = Depends(get_budget_monitor),
    current_user: dict = Depends(get_current_user)
):
    """
    List budget alerts with filtering and pagination
    """
    try:
        # Validate tenant access
        if tenant_id and not await verify_tenant_access(current_user, tenant_id):
            raise HTTPException(status_code=403, detail="Access denied to tenant")
        
        alerts = await monitor.list_alerts(
            severity=severity,
            tenant_id=tenant_id,
            is_acknowledged=is_acknowledged,
            limit=limit,
            offset=offset
        )
        
        return alerts
        
    except Exception as e:
        logger.error("Failed to list budget alerts", error=str(e), exc_info=True)
        raise HTTPException(status_code=500, detail=f"Failed to list budget alerts: {str(e)}")


@router.put("/alerts/{alert_id}/acknowledge", tags=["alerts"])
async def acknowledge_alert(
    alert_id: str = Path(..., description="Alert ID"),
    monitor: BudgetMonitor = Depends(get_budget_monitor),
    current_user: dict = Depends(get_current_user)
):
    """
    Acknowledge a budget alert
    """
    try:
        # Get alert to check permissions
        alert = await monitor.get_alert(alert_id)
        if not alert:
            raise HTTPException(status_code=404, detail="Alert not found")
        
        # Validate tenant access
        if alert.tenant_id and not await verify_tenant_access(current_user, alert.tenant_id):
            raise HTTPException(status_code=403, detail="Access denied to alert")
        
        # Acknowledge alert
        await monitor.acknowledge_alert(alert_id, current_user["user_id"])
        
        logger.info(
            "Alert acknowledged",
            alert_id=alert_id,
            acknowledged_by=current_user["user_id"]
        )
        
        return {"message": "Alert acknowledged successfully"}
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error("Failed to acknowledge alert", alert_id=alert_id, error=str(e), exc_info=True)
        raise HTTPException(status_code=500, detail=f"Failed to acknowledge alert: {str(e)}")


# === Provider Pricing Management ===

@router.get("/pricing", response_model=List[ProviderPricing], tags=["pricing"])
async def list_provider_pricing(
    provider: Optional[ProviderType] = Query(None, description="Filter by provider"),
    model_type: Optional[ModelType] = Query(None, description="Filter by model type"),
    is_active: Optional[bool] = Query(True, description="Filter by active status"),
    updater: PricingUpdater = Depends(get_pricing_updater),
    current_user: dict = Depends(get_current_user)
):
    """
    List current provider pricing information
    """
    try:
        pricing_data = await updater.get_pricing_data(
            provider=provider,
            model_type=model_type,
            is_active=is_active
        )
        
        return pricing_data
        
    except Exception as e:
        logger.error("Failed to list provider pricing", error=str(e), exc_info=True)
        raise HTTPException(status_code=500, detail=f"Failed to list provider pricing: {str(e)}")


@router.post("/pricing/refresh", tags=["pricing"])
async def refresh_pricing_data(
    provider: Optional[ProviderType] = Query(None, description="Refresh specific provider"),
    updater: PricingUpdater = Depends(get_pricing_updater),
    current_user: dict = Depends(get_current_user)
):
    """
    Manually refresh provider pricing data
    """
    try:
        # Validate permissions
        await require_permissions(current_user, ["finops:pricing:refresh"])
        
        # Refresh pricing
        updated_count = await updater.refresh_pricing(provider=provider)
        
        logger.info(
            "Pricing data refreshed",
            provider=provider,
            updated_count=updated_count,
            requested_by=current_user["user_id"]
        )
        
        return {
            "message": "Pricing data refreshed successfully",
            "updated_count": updated_count
        }
        
    except Exception as e:
        logger.error("Failed to refresh pricing data", error=str(e), exc_info=True)
        raise HTTPException(status_code=500, detail=f"Failed to refresh pricing data: {str(e)}")


# === Cost Forecasting ===

@router.get("/forecasts/{tenant_id}", response_model=List[CostForecast], tags=["forecasting"])
async def get_cost_forecasts(
    tenant_id: str = Path(..., description="Tenant ID"),
    forecast_days: int = Query(30, ge=1, le=365, description="Number of days to forecast"),
    calculator: CostCalculator = Depends(get_cost_calculator),
    current_user: dict = Depends(get_current_user)
):
    """
    Get cost forecasts for a tenant based on historical usage
    """
    try:
        # Validate tenant access
        if not await verify_tenant_access(current_user, tenant_id):
            raise HTTPException(status_code=403, detail="Access denied to tenant")
        
        forecasts = await calculator.generate_cost_forecasts(
            tenant_id=tenant_id,
            forecast_days=forecast_days
        )
        
        return forecasts
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error("Failed to get cost forecasts", tenant_id=tenant_id, error=str(e), exc_info=True)
        raise HTTPException(status_code=500, detail=f"Failed to get cost forecasts: {str(e)}")


# === Cost Optimization ===

@router.get("/optimizations", response_model=List[CostOptimization], tags=["optimization"])
async def get_cost_optimizations(
    tenant_id: Optional[str] = Query(None, description="Filter by tenant"),
    service_name: Optional[str] = Query(None, description="Filter by service"),
    status: Optional[str] = Query(None, description="Filter by status"),
    calculator: CostCalculator = Depends(get_cost_calculator),
    current_user: dict = Depends(get_current_user)
):
    """
    Get cost optimization recommendations
    """
    try:
        # Validate tenant access
        if tenant_id and not await verify_tenant_access(current_user, tenant_id):
            raise HTTPException(status_code=403, detail="Access denied to tenant")
        
        optimizations = await calculator.get_cost_optimizations(
            tenant_id=tenant_id,
            service_name=service_name,
            status=status
        )
        
        return optimizations
        
    except Exception as e:
        logger.error("Failed to get cost optimizations", error=str(e), exc_info=True)
        raise HTTPException(status_code=500, detail=f"Failed to get cost optimizations: {str(e)}")


# === Utility Functions ===

async def verify_tenant_access(current_user: dict, tenant_id: str) -> bool:
    """Verify user has access to the specified tenant"""
    try:
        # Check if user is admin or has access to tenant
        if "admin" in current_user.get("roles", []):
            return True
        
        # Check tenant-specific access
        user_tenants = current_user.get("tenant_ids", [])
        return tenant_id in user_tenants
        
    except Exception as e:
        logger.error("Failed to verify tenant access", error=str(e), exc_info=True)
        return False
