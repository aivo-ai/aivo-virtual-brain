"""
API routes for Compliance Service (S5-09)

Evidence aggregation endpoints for isolation tests, consent history,
data protection analytics, and audit logs.
"""

import asyncio
from datetime import datetime, timezone, timedelta
from typing import Dict, Any, List, Optional
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy import select, func, and_, desc, asc
from sqlalchemy.ext.asyncio import AsyncSession
import structlog

from .models import (
    IsolationTestResult,
    ConsentRecord,
    DataProtectionRequest,
    AuditEvent,
    IsolationTestStatus,
    ConsentStatus,
    DataProtectionStatus,
    AuditEventType,
    TenantEvidenceResponse,
    LearnerEvidenceResponse,
    EvidenceMetrics,
    ComplianceChartData,
    SparklineData,
    IsolationTestSummary,
    ConsentSummary,
    DataProtectionSummary,
    AuditEventSummary
)

logger = structlog.get_logger()


def create_router() -> APIRouter:
    """Create and configure the API router."""
    router = APIRouter()
    
    @router.get("/evidence/tenant/{tenant_id}", response_model=TenantEvidenceResponse)
    async def get_tenant_evidence(
        tenant_id: UUID,
        days: int = Query(30, description="Number of days to look back", ge=1, le=365),
        db: AsyncSession = Depends()
    ) -> TenantEvidenceResponse:
        """
        Get compliance evidence for a tenant.
        
        Returns:
        - Isolation test pass rates and results
        - Chaos engineering check results
        - Retention job status and compliance
        - Aggregated compliance metrics
        """
        try:
            logger.info("Fetching tenant evidence", tenant_id=str(tenant_id), days=days)
            
            # Calculate date range
            end_date = datetime.now(timezone.utc)
            start_date = end_date - timedelta(days=days)
            
            # Get isolation test results
            isolation_query = select(IsolationTestResult).where(
                and_(
                    IsolationTestResult.tenant_id == tenant_id,
                    IsolationTestResult.started_at >= start_date
                )
            ).order_by(desc(IsolationTestResult.started_at))
            
            isolation_results = await db.execute(isolation_query)
            isolation_tests = isolation_results.scalars().all()
            
            # Aggregate isolation test data by type
            isolation_summaries = []
            test_types = {}
            
            for test in isolation_tests:
                if test.test_type not in test_types:
                    test_types[test.test_type] = {
                        'total': 0,
                        'passed': 0,
                        'failed': 0,
                        'durations': [],
                        'last_date': None
                    }
                
                test_types[test.test_type]['total'] += test.test_count or 0
                test_types[test.test_type]['passed'] += test.passed_count or 0
                test_types[test.test_type]['failed'] += test.failed_count or 0
                
                if test.duration_seconds:
                    test_types[test.test_type]['durations'].append(test.duration_seconds)
                
                if not test_types[test.test_type]['last_date'] or test.started_at > test_types[test.test_type]['last_date']:
                    test_types[test.test_type]['last_date'] = test.started_at
            
            for test_type, data in test_types.items():
                pass_rate = data['passed'] / data['total'] if data['total'] > 0 else 0.0
                avg_duration = sum(data['durations']) / len(data['durations']) if data['durations'] else 0.0
                
                isolation_summaries.append(IsolationTestSummary(
                    test_type=test_type,
                    total_tests=data['total'],
                    passed_tests=data['passed'],
                    failed_tests=data['failed'],
                    pass_rate=pass_rate,
                    last_test_date=data['last_date'] or start_date,
                    average_duration=avg_duration
                ))
            
            # Calculate overall metrics
            total_tests = sum(data['total'] for data in test_types.values())
            total_passed = sum(data['passed'] for data in test_types.values())
            total_failed = sum(data['failed'] for data in test_types.values())
            overall_pass_rate = total_passed / total_tests if total_tests > 0 else 1.0
            
            # Get chaos check results (simulated for now)
            chaos_checks = await _get_chaos_check_results(tenant_id, start_date, end_date)
            
            # Get retention job status
            retention_status = await _get_retention_job_status(tenant_id)
            
            # Calculate retention compliance score
            retention_compliance_score = await _calculate_retention_compliance(tenant_id)
            
            response = TenantEvidenceResponse(
                tenant_id=tenant_id,
                isolation_tests=isolation_summaries,
                chaos_checks=chaos_checks,
                retention_job_status=retention_status,
                last_updated=datetime.now(timezone.utc),
                overall_isolation_pass_rate=overall_pass_rate,
                total_isolation_tests=total_tests,
                failed_isolation_tests=total_failed,
                retention_compliance_score=retention_compliance_score
            )
            
            logger.info(
                "Tenant evidence retrieved",
                tenant_id=str(tenant_id),
                isolation_tests=len(isolation_summaries),
                overall_pass_rate=overall_pass_rate
            )
            
            return response
            
        except Exception as e:
            logger.error("Failed to get tenant evidence", tenant_id=str(tenant_id), error=str(e))
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to retrieve tenant evidence"
            )
    
    @router.get("/evidence/learner/{learner_id}", response_model=LearnerEvidenceResponse)
    async def get_learner_evidence(
        learner_id: UUID,
        days: int = Query(90, description="Number of days to look back", ge=1, le=365),
        include_audit_details: bool = Query(False, description="Include detailed audit event data"),
        db: AsyncSession = Depends()
    ) -> LearnerEvidenceResponse:
        """
        Get compliance evidence for a learner.
        
        Returns:
        - Consent history and versions
        - Data protection request status
        - Audit event logs
        - DP toggle states and preferences
        """
        try:
            logger.info("Fetching learner evidence", learner_id=str(learner_id), days=days)
            
            # Calculate date range
            end_date = datetime.now(timezone.utc)
            start_date = end_date - timedelta(days=days)
            
            # Get consent history
            consent_query = select(ConsentRecord).where(
                and_(
                    ConsentRecord.learner_id == learner_id,
                    ConsentRecord.created_at >= start_date
                )
            ).order_by(desc(ConsentRecord.created_at))
            
            consent_results = await db.execute(consent_query)
            consent_records = consent_results.scalars().all()
            
            consent_history = []
            for record in consent_records:
                consent_history.append(ConsentSummary(
                    consent_type=record.consent_type,
                    current_version=record.consent_version,
                    status=ConsentStatus(record.status),
                    granted_at=record.granted_at,
                    expires_at=record.expires_at,
                    withdrawn_at=record.withdrawn_at
                ))
            
            # Get data protection requests
            dp_query = select(DataProtectionRequest).where(
                and_(
                    DataProtectionRequest.learner_id == learner_id,
                    DataProtectionRequest.created_at >= start_date
                )
            ).order_by(desc(DataProtectionRequest.created_at))
            
            dp_results = await db.execute(dp_query)
            dp_requests = dp_results.scalars().all()
            
            dp_summaries = []
            for request in dp_requests:
                dp_summaries.append(DataProtectionSummary(
                    action=request.action,
                    status=DataProtectionStatus(request.status),
                    requested_at=request.requested_at,
                    completed_at=request.completed_at,
                    result_available=bool(request.result_url)
                ))
            
            # Get audit events
            audit_query = select(AuditEvent).where(
                and_(
                    AuditEvent.learner_id == learner_id,
                    AuditEvent.timestamp >= start_date
                )
            ).order_by(desc(AuditEvent.timestamp))
            
            if not include_audit_details:
                audit_query = audit_query.limit(100)  # Limit for performance
            
            audit_results = await db.execute(audit_query)
            audit_events = audit_results.scalars().all()
            
            audit_summaries = []
            for event in audit_events:
                audit_summaries.append(AuditEventSummary(
                    event_type=AuditEventType(event.event_type),
                    action=event.action,
                    timestamp=event.timestamp,
                    actor_id=event.actor_id,
                    resource_type=event.resource_type,
                    event_data=event.event_data if include_audit_details else None
                ))
            
            # Get DP toggle states
            dp_toggle_state = await _get_dp_toggle_state(learner_id)
            
            # Calculate metrics
            active_consents = sum(1 for c in consent_history if c.status == ConsentStatus.ACTIVE)
            pending_dp = sum(1 for dp in dp_summaries if dp.status == DataProtectionStatus.PENDING)
            last_activity = max(
                (e.timestamp for e in audit_summaries),
                default=start_date
            )
            
            response = LearnerEvidenceResponse(
                learner_id=learner_id,
                consent_history=consent_history,
                data_protection_requests=dp_summaries,
                audit_events=audit_summaries,
                dp_toggle_state=dp_toggle_state,
                last_updated=datetime.now(timezone.utc),
                total_consent_versions=len(set(c.current_version for c in consent_history)),
                active_consents=active_consents,
                pending_dp_requests=pending_dp,
                total_audit_events=len(audit_summaries),
                last_activity=last_activity
            )
            
            logger.info(
                "Learner evidence retrieved",
                learner_id=str(learner_id),
                consent_records=len(consent_history),
                dp_requests=len(dp_summaries),
                audit_events=len(audit_summaries)
            )
            
            return response
            
        except Exception as e:
            logger.error("Failed to get learner evidence", learner_id=str(learner_id), error=str(e))
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to retrieve learner evidence"
            )
    
    @router.get("/evidence/metrics", response_model=EvidenceMetrics)
    async def get_evidence_metrics(
        days: int = Query(7, description="Number of days for activity metrics", ge=1, le=30),
        db: AsyncSession = Depends()
    ) -> EvidenceMetrics:
        """
        Get overall compliance evidence metrics.
        
        Returns aggregated metrics across all tenants and learners.
        """
        try:
            logger.info("Fetching evidence metrics", days=days)
            
            # Calculate date range for activity metrics
            end_date = datetime.now(timezone.utc)
            start_date = end_date - timedelta(days=days)
            
            # Count unique tenants and learners
            tenant_count_query = select(func.count(func.distinct(IsolationTestResult.tenant_id)))
            tenant_result = await db.execute(tenant_count_query)
            total_tenants = tenant_result.scalar() or 0
            
            learner_count_query = select(func.count(func.distinct(ConsentRecord.learner_id)))
            learner_result = await db.execute(learner_count_query)
            total_learners = learner_result.scalar() or 0
            
            # Count recent activities
            isolation_count_query = select(func.count(IsolationTestResult.id)).where(
                IsolationTestResult.started_at >= start_date
            )
            isolation_result = await db.execute(isolation_count_query)
            isolation_tests_24h = isolation_result.scalar() or 0
            
            consent_count_query = select(func.count(ConsentRecord.id)).where(
                ConsentRecord.created_at >= start_date
            )
            consent_result = await db.execute(consent_count_query)
            consent_changes_24h = consent_result.scalar() or 0
            
            dp_count_query = select(func.count(DataProtectionRequest.id)).where(
                DataProtectionRequest.requested_at >= start_date
            )
            dp_result = await db.execute(dp_count_query)
            dp_requests_24h = dp_result.scalar() or 0
            
            audit_count_query = select(func.count(AuditEvent.id)).where(
                AuditEvent.timestamp >= start_date
            )
            audit_result = await db.execute(audit_count_query)
            audit_events_24h = audit_result.scalar() or 0
            
            # Calculate overall compliance score
            compliance_score = await _calculate_overall_compliance_score()
            
            response = EvidenceMetrics(
                total_tenants=total_tenants,
                total_learners=total_learners,
                isolation_tests_24h=isolation_tests_24h,
                consent_changes_24h=consent_changes_24h,
                dp_requests_24h=dp_requests_24h,
                audit_events_24h=audit_events_24h,
                compliance_score=compliance_score,
                last_calculated=datetime.now(timezone.utc)
            )
            
            logger.info(
                "Evidence metrics retrieved",
                total_tenants=total_tenants,
                total_learners=total_learners,
                compliance_score=compliance_score
            )
            
            return response
            
        except Exception as e:
            logger.error("Failed to get evidence metrics", error=str(e))
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to retrieve evidence metrics"
            )
    
    @router.get("/evidence/charts", response_model=ComplianceChartData)
    async def get_compliance_charts(
        days: int = Query(30, description="Number of days for chart data", ge=7, le=90),
        tenant_id: Optional[UUID] = Query(None, description="Filter by tenant ID"),
        db: AsyncSession = Depends()
    ) -> ComplianceChartData:
        """
        Get chart data for compliance dashboard.
        
        Returns sparkline data for various compliance metrics.
        """
        try:
            logger.info("Fetching compliance chart data", days=days, tenant_id=str(tenant_id) if tenant_id else None)
            
            # Calculate date range and intervals
            end_date = datetime.now(timezone.utc)
            start_date = end_date - timedelta(days=days)
            
            # Generate time intervals (daily)
            intervals = []
            current_date = start_date
            while current_date <= end_date:
                intervals.append(current_date)
                current_date += timedelta(days=1)
            
            # Get isolation pass rate data
            isolation_data = await _get_isolation_pass_rate_sparkline(
                start_date, end_date, intervals, tenant_id, db
            )
            
            # Get consent activity data
            consent_data = await _get_consent_activity_sparkline(
                start_date, end_date, intervals, tenant_id, db
            )
            
            # Get DP request volume data
            dp_data = await _get_dp_request_sparkline(
                start_date, end_date, intervals, tenant_id, db
            )
            
            # Get audit event frequency data
            audit_data = await _get_audit_frequency_sparkline(
                start_date, end_date, intervals, tenant_id, db
            )
            
            response = ComplianceChartData(
                isolation_pass_rate=isolation_data,
                consent_activity=consent_data,
                dp_request_volume=dp_data,
                audit_event_frequency=audit_data
            )
            
            logger.info("Compliance chart data retrieved", days=days, intervals=len(intervals))
            
            return response
            
        except Exception as e:
            logger.error("Failed to get compliance chart data", error=str(e))
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to retrieve compliance chart data"
            )
    
    return router


# Helper functions
async def _get_chaos_check_results(tenant_id: UUID, start_date: datetime, end_date: datetime) -> Dict[str, Any]:
    """Get chaos engineering check results (simulated for now)."""
    # In a real implementation, this would query chaos engineering test results
    return {
        "network_partition_tests": {
            "total": 24,
            "passed": 22,
            "failed": 2,
            "last_run": (datetime.now(timezone.utc) - timedelta(hours=2)).isoformat()
        },
        "service_failure_tests": {
            "total": 16,
            "passed": 15,
            "failed": 1,
            "last_run": (datetime.now(timezone.utc) - timedelta(hours=6)).isoformat()
        },
        "resource_exhaustion_tests": {
            "total": 8,
            "passed": 8,
            "failed": 0,
            "last_run": (datetime.now(timezone.utc) - timedelta(hours=12)).isoformat()
        }
    }


async def _get_retention_job_status(tenant_id: UUID) -> Dict[str, Any]:
    """Get retention job status for tenant."""
    # In a real implementation, this would query retention job status
    return {
        "last_retention_run": (datetime.now(timezone.utc) - timedelta(days=1)).isoformat(),
        "next_scheduled_run": (datetime.now(timezone.utc) + timedelta(days=6)).isoformat(),
        "items_processed": 1247,
        "items_deleted": 89,
        "items_archived": 158,
        "status": "completed",
        "compliance_policies": {
            "learner_data": "7_years",
            "audit_logs": "10_years",
            "system_logs": "1_year"
        }
    }


async def _calculate_retention_compliance(tenant_id: UUID) -> float:
    """Calculate retention compliance score."""
    # In a real implementation, this would analyze retention policy adherence
    return 0.95


async def _get_dp_toggle_state(learner_id: UUID) -> Dict[str, bool]:
    """Get data protection toggle states for learner."""
    # In a real implementation, this would query learner preferences
    return {
        "data_processing_consent": True,
        "ai_training_consent": True,
        "marketing_consent": False,
        "third_party_sharing": False,
        "analytics_tracking": True,
        "personalization": True
    }


async def _calculate_overall_compliance_score() -> float:
    """Calculate overall compliance score."""
    # In a real implementation, this would use various compliance metrics
    return 0.92


async def _get_isolation_pass_rate_sparkline(
    start_date: datetime,
    end_date: datetime,
    intervals: List[datetime],
    tenant_id: Optional[UUID],
    db: AsyncSession
) -> SparklineData:
    """Get isolation test pass rate sparkline data."""
    values = []
    
    for i in range(len(intervals) - 1):
        day_start = intervals[i]
        day_end = intervals[i + 1]
        
        # Query isolation tests for this day
        query = select(
            func.sum(IsolationTestResult.passed_count).label('passed'),
            func.sum(IsolationTestResult.test_count).label('total')
        ).where(
            and_(
                IsolationTestResult.started_at >= day_start,
                IsolationTestResult.started_at < day_end
            )
        )
        
        if tenant_id:
            query = query.where(IsolationTestResult.tenant_id == tenant_id)
        
        result = await db.execute(query)
        row = result.first()
        
        if row and row.total and row.total > 0:
            pass_rate = row.passed / row.total
        else:
            pass_rate = 1.0  # Default to 100% if no tests
        
        values.append(pass_rate)
    
    return SparklineData(
        timestamps=intervals[:-1],
        values=values,
        metric_name="isolation_pass_rate"
    )


async def _get_consent_activity_sparkline(
    start_date: datetime,
    end_date: datetime,
    intervals: List[datetime],
    tenant_id: Optional[UUID],
    db: AsyncSession
) -> SparklineData:
    """Get consent activity sparkline data."""
    values = []
    
    for i in range(len(intervals) - 1):
        day_start = intervals[i]
        day_end = intervals[i + 1]
        
        # Count consent records for this day
        query = select(func.count(ConsentRecord.id)).where(
            and_(
                ConsentRecord.created_at >= day_start,
                ConsentRecord.created_at < day_end
            )
        )
        
        result = await db.execute(query)
        count = result.scalar() or 0
        values.append(float(count))
    
    return SparklineData(
        timestamps=intervals[:-1],
        values=values,
        metric_name="consent_activity"
    )


async def _get_dp_request_sparkline(
    start_date: datetime,
    end_date: datetime,
    intervals: List[datetime],
    tenant_id: Optional[UUID],
    db: AsyncSession
) -> SparklineData:
    """Get data protection request volume sparkline data."""
    values = []
    
    for i in range(len(intervals) - 1):
        day_start = intervals[i]
        day_end = intervals[i + 1]
        
        # Count DP requests for this day
        query = select(func.count(DataProtectionRequest.id)).where(
            and_(
                DataProtectionRequest.requested_at >= day_start,
                DataProtectionRequest.requested_at < day_end
            )
        )
        
        result = await db.execute(query)
        count = result.scalar() or 0
        values.append(float(count))
    
    return SparklineData(
        timestamps=intervals[:-1],
        values=values,
        metric_name="dp_request_volume"
    )


async def _get_audit_frequency_sparkline(
    start_date: datetime,
    end_date: datetime,
    intervals: List[datetime],
    tenant_id: Optional[UUID],
    db: AsyncSession
) -> SparklineData:
    """Get audit event frequency sparkline data."""
    values = []
    
    for i in range(len(intervals) - 1):
        day_start = intervals[i]
        day_end = intervals[i + 1]
        
        # Count audit events for this day
        query = select(func.count(AuditEvent.id)).where(
            and_(
                AuditEvent.timestamp >= day_start,
                AuditEvent.timestamp < day_end
            )
        )
        
        if tenant_id:
            query = query.where(AuditEvent.tenant_id == tenant_id)
        
        result = await db.execute(query)
        count = result.scalar() or 0
        values.append(float(count))
    
    return SparklineData(
        timestamps=intervals[:-1],
        values=values,
        metric_name="audit_event_frequency"
    )
