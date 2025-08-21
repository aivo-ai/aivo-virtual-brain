"""
System health and statistics endpoints
Provides real-time monitoring data for admin dashboard
"""

from fastapi import APIRouter, Depends, HTTPException
from typing import Dict, List, Any, Optional
from datetime import datetime, timedelta
import httpx
import asyncio
import logging

from app.auth import AdminUser, verify_admin_token
from app.audit import log_admin_action
from app.config import settings
from app.models import SystemStats, ServiceHealth, SystemAlert

logger = logging.getLogger(__name__)
router = APIRouter()


@router.get("/stats", response_model=SystemStats)
async def get_system_stats(admin: AdminUser = Depends(verify_admin_token)):
    """
    Get comprehensive system statistics
    Available to all staff roles
    """
    await log_admin_action(
        admin.user_id,
        "system_stats_accessed",
        details={"roles": admin.roles}
    )
    
    try:
        # Collect stats from various sources
        stats = await _collect_system_stats()
        return stats
    except Exception as e:
        logger.error(f"Error collecting system stats: {e}")
        raise HTTPException(status_code=500, detail="Failed to collect system statistics")


@router.get("/health", response_model=Dict[str, ServiceHealth])
async def get_service_health(admin: AdminUser = Depends(verify_admin_token)):
    """
    Get health status of all services
    Available to all staff roles
    """
    await log_admin_action(
        admin.user_id,
        "service_health_checked",
        details={"requested_by": admin.email}
    )
    
    try:
        health_data = await _check_all_services_health()
        return health_data
    except Exception as e:
        logger.error(f"Error checking service health: {e}")
        raise HTTPException(status_code=500, detail="Failed to check service health")


@router.get("/alerts", response_model=List[SystemAlert])
async def get_system_alerts(
    severity: Optional[str] = None,
    limit: int = 50,
    admin: AdminUser = Depends(verify_admin_token)
):
    """
    Get active system alerts
    Available to all staff roles
    """
    await log_admin_action(
        admin.user_id,
        "alerts_accessed",
        details={
            "severity_filter": severity,
            "limit": limit
        }
    )
    
    try:
        alerts = await _get_active_alerts(severity, limit)
        return alerts
    except Exception as e:
        logger.error(f"Error retrieving alerts: {e}")
        raise HTTPException(status_code=500, detail="Failed to retrieve alerts")


@router.get("/metrics")
async def get_system_metrics(
    timeframe: str = "1h",
    admin: AdminUser = Depends(verify_admin_token)
):
    """
    Get system performance metrics
    Available to all staff roles
    """
    await log_admin_action(
        admin.user_id,
        "metrics_accessed",
        details={"timeframe": timeframe}
    )
    
    try:
        metrics = await _get_performance_metrics(timeframe)
        return metrics
    except Exception as e:
        logger.error(f"Error retrieving metrics: {e}")
        raise HTTPException(status_code=500, detail="Failed to retrieve metrics")


@router.get("/flags")
async def get_feature_flags(admin: AdminUser = Depends(verify_admin_token)):
    """
    Get current feature flag status
    Available to all staff roles (read-only)
    """
    await log_admin_action(
        admin.user_id,
        "feature_flags_viewed",
        details={"access_level": "read_only"}
    )
    
    return {
        "emergency_access": settings.ENABLE_EMERGENCY_ACCESS,
        "queue_management": settings.ENABLE_QUEUE_MANAGEMENT,
        "learner_inspection": settings.ENABLE_LEARNER_INSPECTION,
        "audit_export": settings.ENABLE_AUDIT_EXPORT,
        "environment": settings.ENVIRONMENT
    }


@router.put("/flags/{flag_name}")
async def toggle_feature_flag(
    flag_name: str,
    enabled: bool,
    admin: AdminUser = Depends(verify_admin_token)
):
    """
    Toggle feature flag
    Only available to system admins
    """
    if not admin.is_system_admin():
        raise HTTPException(
            status_code=403,
            detail="System admin role required for feature flag management"
        )
    
    await log_admin_action(
        admin.user_id,
        "feature_flag_toggled",
        details={
            "flag_name": flag_name,
            "enabled": enabled,
            "previous_state": getattr(settings, f"ENABLE_{flag_name.upper()}", None)
        }
    )
    
    # Update feature flag (in production, this would update a configuration service)
    if settings.ENVIRONMENT == "development":
        setattr(settings, f"ENABLE_{flag_name.upper()}", enabled)
        return {
            "flag_name": flag_name,
            "enabled": enabled,
            "updated_by": admin.email,
            "timestamp": datetime.utcnow()
        }
    else:
        raise HTTPException(
            status_code=501,
            detail="Feature flag updates require configuration service integration"
        )


async def _collect_system_stats() -> SystemStats:
    """Collect comprehensive system statistics"""
    
    # Mock data for development
    if settings.ENVIRONMENT == "development":
        return SystemStats(
            total_learners=12450,
            active_sessions=234,
            pending_approvals=8,
            failed_jobs=3,
            system_uptime="7d 14h 23m",
            avg_response_time=145.7,
            error_rate=0.02,
            queue_health="healthy",
            last_updated=datetime.utcnow()
        )
    
    # Production stats collection
    stats_tasks = [
        _get_learner_count(),
        _get_active_sessions(),
        _get_approval_queue_stats(),
        _get_job_failure_stats(),
        _get_system_uptime(),
        _get_performance_stats()
    ]
    
    results = await asyncio.gather(*stats_tasks, return_exceptions=True)
    
    return SystemStats(
        total_learners=results[0] if not isinstance(results[0], Exception) else 0,
        active_sessions=results[1] if not isinstance(results[1], Exception) else 0,
        pending_approvals=results[2] if not isinstance(results[2], Exception) else 0,
        failed_jobs=results[3] if not isinstance(results[3], Exception) else 0,
        system_uptime=results[4] if not isinstance(results[4], Exception) else "unknown",
        avg_response_time=results[5].get("avg_response_time", 0) if not isinstance(results[5], Exception) else 0,
        error_rate=results[5].get("error_rate", 0) if not isinstance(results[5], Exception) else 0,
        queue_health="unknown",
        last_updated=datetime.utcnow()
    )


async def _check_all_services_health() -> Dict[str, ServiceHealth]:
    """Check health of all services"""
    
    services = {
        "approval-svc": settings.APPROVAL_SERVICE_URL,
        "orchestrator-svc": settings.ORCHESTRATOR_SERVICE_URL,
        "ingest-svc": settings.INGEST_SERVICE_URL,
        "learner-svc": settings.LEARNER_SERVICE_URL,
        "user-svc": settings.USER_SERVICE_URL,
        "audit-svc": settings.AUDIT_SERVICE_URL
    }
    
    health_results = {}
    
    async with httpx.AsyncClient(timeout=5.0) as client:
        for service_name, service_url in services.items():
            try:
                response = await client.get(f"{service_url}/health")
                
                if response.status_code == 200:
                    health_results[service_name] = ServiceHealth(
                        status="healthy",
                        response_time=response.elapsed.total_seconds() * 1000,
                        last_check=datetime.utcnow(),
                        details=response.json() if response.content else {}
                    )
                else:
                    health_results[service_name] = ServiceHealth(
                        status="unhealthy",
                        response_time=response.elapsed.total_seconds() * 1000 if response.elapsed else 0,
                        last_check=datetime.utcnow(),
                        details={"status_code": response.status_code}
                    )
                    
            except Exception as e:
                health_results[service_name] = ServiceHealth(
                    status="error",
                    response_time=0,
                    last_check=datetime.utcnow(),
                    details={"error": str(e)}
                )
    
    return health_results


async def _get_active_alerts(severity: Optional[str] = None, limit: int = 50) -> List[SystemAlert]:
    """Get active system alerts"""
    
    # Mock alerts for development
    if settings.ENVIRONMENT == "development":
        alerts = [
            SystemAlert(
                id="alert_001",
                type="performance",
                severity="warning",
                message="High response time detected in orchestrator service",
                timestamp=datetime.utcnow() - timedelta(minutes=15),
                source="orchestrator-svc",
                resolved=False
            ),
            SystemAlert(
                id="alert_002", 
                type="queue",
                severity="info",
                message="Job queue backlog increasing",
                timestamp=datetime.utcnow() - timedelta(hours=1),
                source="ingest-svc",
                resolved=False
            ),
            SystemAlert(
                id="alert_003",
                type="security",
                severity="critical",
                message="Multiple failed authentication attempts detected",
                timestamp=datetime.utcnow() - timedelta(minutes=5),
                source="auth-svc",
                resolved=False
            )
        ]
        
        if severity:
            alerts = [a for a in alerts if a.severity == severity]
        
        return alerts[:limit]
    
    # Production alert fetching
    try:
        async with httpx.AsyncClient() as client:
            params = {"limit": limit}
            if severity:
                params["severity"] = severity
                
            response = await client.get(
                f"{settings.AUDIT_SERVICE_URL}/alerts",
                params=params
            )
            
            if response.status_code == 200:
                return [SystemAlert(**alert) for alert in response.json()]
            else:
                logger.warning(f"Failed to fetch alerts: {response.status_code}")
                return []
                
    except Exception as e:
        logger.error(f"Error fetching alerts: {e}")
        return []


async def _get_performance_metrics(timeframe: str) -> Dict[str, Any]:
    """Get system performance metrics"""
    
    # Mock metrics for development
    if settings.ENVIRONMENT == "development":
        return {
            "timeframe": timeframe,
            "cpu_usage": 45.2,
            "memory_usage": 67.8,
            "disk_usage": 34.1,
            "network_io": {
                "bytes_in": 1234567,
                "bytes_out": 987654
            },
            "request_rate": 234.5,
            "error_rate": 0.02,
            "avg_response_time": 145.7,
            "p95_response_time": 298.4,
            "active_connections": 42
        }
    
    # Production metrics would come from monitoring service
    return {"error": "Metrics service not configured"}


# Helper functions for production stats
async def _get_learner_count() -> int:
    """Get total learner count from learner service"""
    try:
        async with httpx.AsyncClient() as client:
            response = await client.get(f"{settings.LEARNER_SERVICE_URL}/admin/count")
            return response.json().get("count", 0)
    except:
        return 0


async def _get_active_sessions() -> int:
    """Get active session count"""
    try:
        async with httpx.AsyncClient() as client:
            response = await client.get(f"{settings.USER_SERVICE_URL}/admin/sessions/active")
            return response.json().get("count", 0)
    except:
        return 0


async def _get_approval_queue_stats() -> int:
    """Get pending approval count"""
    try:
        async with httpx.AsyncClient() as client:
            response = await client.get(f"{settings.APPROVAL_SERVICE_URL}/admin/pending/count")
            return response.json().get("count", 0)
    except:
        return 0


async def _get_job_failure_stats() -> int:
    """Get failed job count"""
    try:
        async with httpx.AsyncClient() as client:
            response = await client.get(f"{settings.ORCHESTRATOR_SERVICE_URL}/admin/jobs/failed/count")
            return response.json().get("count", 0)
    except:
        return 0


async def _get_system_uptime() -> str:
    """Get system uptime"""
    # Mock uptime calculation
    return "7d 14h 23m"


async def _get_performance_stats() -> Dict[str, float]:
    """Get system performance statistics"""
    return {
        "avg_response_time": 145.7,
        "error_rate": 0.02
    }
