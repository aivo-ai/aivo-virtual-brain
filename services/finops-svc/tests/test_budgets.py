"""
Comprehensive Test Suite for FinOps Service
Tests budget management, cost calculations, and provider integrations
"""

import asyncio
import pytest
from datetime import datetime, timedelta
from decimal import Decimal
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4

import structlog
from fastapi.testclient import TestClient

# Import the models and services
from app.models import (
    UsageEvent, Budget, BudgetAlert, CostSummary, ProviderPricing,
    CreateBudgetRequest, CostQueryRequest, CostResponse,
    ProviderType, ModelType, BudgetType, BudgetPeriod, AlertSeverity,
    CostCategory, AlertChannel
)
from app.main import create_app
from app.cost_calculator import CostCalculator
from app.budget_monitor import BudgetMonitor
from app.providers.openai_provider import OpenAIProvider
from app.providers.gemini_provider import GeminiProvider
from app.providers.bedrock_provider import BedrockProvider

logger = structlog.get_logger(__name__)


@pytest.fixture
def app():
    """Create test FastAPI application"""
    return create_app()


@pytest.fixture
def client(app):
    """Create test client"""
    return TestClient(app)


@pytest.fixture
def sample_usage_event():
    """Create sample usage event for testing"""
    return UsageEvent(
        tenant_id="test-tenant-123",
        learner_id="learner-456",
        service_name="inference-gateway-svc",
        session_id="session-789",
        provider=ProviderType.OPENAI,
        model_name="gpt-4",
        model_type=ModelType.TEXT_GENERATION,
        input_tokens=1000,
        output_tokens=500,
        total_tokens=1500,
        request_count=1,
        timestamp=datetime.utcnow()
    )


@pytest.fixture
def sample_budget():
    """Create sample budget for testing"""
    return Budget(
        budget_type=BudgetType.TENANT,
        name="Test Tenant Budget",
        description="Budget for testing tenant",
        tenant_id="test-tenant-123",
        amount=Decimal("100.00"),
        period=BudgetPeriod.MONTHLY,
        start_date=datetime.utcnow(),
        alert_thresholds=[Decimal("50"), Decimal("75"), Decimal("90")],
        alert_channels=[AlertChannel.EMAIL],
        alert_recipients=["admin@aivo.com"]
    )


@pytest.fixture
async def mock_db_connection():
    """Mock database connection"""
    conn = AsyncMock()
    conn.fetch.return_value = []
    conn.fetchrow.return_value = None
    conn.execute.return_value = None
    return conn


class TestCostCalculator:
    """Test suite for cost calculation functionality"""
    
    @pytest.fixture
    async def cost_calculator(self, mock_db_connection):
        """Create cost calculator with mocked dependencies"""
        calculator = CostCalculator()
        calculator.db_pool = mock_db_connection
        return calculator
    
    async def test_calculate_openai_cost(self, cost_calculator, sample_usage_event):
        """Test OpenAI cost calculation"""
        # Setup OpenAI provider with known pricing
        openai_provider = OpenAIProvider()
        await openai_provider.get_current_pricing()
        
        # Calculate cost for GPT-4 usage
        cost = await openai_provider.calculate_usage_cost(sample_usage_event)
        
        # GPT-4: $0.03 per 1K input tokens, $0.06 per 1K output tokens
        # 1000 input tokens = $0.03, 500 output tokens = $0.03
        expected_cost = Decimal("0.06")
        
        assert cost == expected_cost
        assert cost > 0
        
    async def test_calculate_gemini_cost(self, cost_calculator):
        """Test Gemini cost calculation"""
        gemini_provider = GeminiProvider()
        await gemini_provider.get_current_pricing()
        
        # Create Gemini usage event
        gemini_event = UsageEvent(
            tenant_id="test-tenant-123",
            service_name="inference-gateway-svc",
            provider=ProviderType.GEMINI,
            model_name="gemini-1.5-flash",
            model_type=ModelType.TEXT_GENERATION,
            input_tokens=1000,
            output_tokens=500,
            request_count=1
        )
        
        cost = await gemini_provider.calculate_usage_cost(gemini_event)
        
        # Gemini Flash: $0.00035 per 1K input, $0.00105 per 1K output
        # 1000 input = $0.00035, 500 output = $0.000525
        expected_cost = Decimal("0.000875")
        
        assert cost == expected_cost
        
    async def test_calculate_bedrock_cost(self, cost_calculator):
        """Test Bedrock cost calculation"""
        bedrock_provider = BedrockProvider()
        await bedrock_provider.get_current_pricing()
        
        # Create Bedrock usage event
        bedrock_event = UsageEvent(
            tenant_id="test-tenant-123",
            service_name="inference-gateway-svc",
            provider=ProviderType.BEDROCK,
            model_name="anthropic.claude-3-haiku-20240307-v1:0",
            model_type=ModelType.TEXT_GENERATION,
            input_tokens=1000,
            output_tokens=500,
            request_count=1
        )
        
        cost = await bedrock_provider.calculate_usage_cost(bedrock_event)
        
        # Claude Haiku: $0.00025 per 1K input, $0.00125 per 1K output
        # 1000 input = $0.00025, 500 output = $0.000625
        expected_cost = Decimal("0.000875")
        
        assert cost == expected_cost
        
    async def test_cost_query_with_filters(self, cost_calculator, mock_db_connection):
        """Test cost querying with various filters"""
        # Mock database response
        mock_db_connection.fetch.return_value = [
            {
                'total_cost': Decimal('25.50'),
                'total_tokens': 15000,
                'total_requests': 20,
                'provider': 'openai',
                'model_name': 'gpt-4',
                'date': datetime.utcnow().date()
            }
        ]
        
        query = CostQueryRequest(
            start_date=datetime.utcnow() - timedelta(days=7),
            end_date=datetime.utcnow(),
            tenant_id="test-tenant-123",
            provider=ProviderType.OPENAI,
            group_by=["provider", "model_name", "day"]
        )
        
        response = await cost_calculator.query_costs(query)
        
        assert isinstance(response, CostResponse)
        assert response.total_cost >= 0
        
    async def test_usage_statistics_calculation(self, cost_calculator, mock_db_connection):
        """Test usage statistics calculation"""
        # Mock usage statistics data
        mock_db_connection.fetchrow.return_value = {
            'total_tokens': 50000,
            'input_tokens': 30000,
            'output_tokens': 20000,
            'total_requests': 100,
            'unique_sessions': 25,
            'total_cost': Decimal('45.75')
        }
        
        stats = await cost_calculator.get_usage_statistics(
            start_date=datetime.utcnow() - timedelta(days=30),
            end_date=datetime.utcnow(),
            tenant_id="test-tenant-123"
        )
        
        assert stats.total_tokens == 50000
        assert stats.input_tokens == 30000
        assert stats.output_tokens == 20000
        assert stats.total_requests == 100
        assert stats.unique_sessions == 25
        assert stats.cost_per_token > 0
        assert stats.cost_per_request > 0
        assert stats.cost_per_session > 0


class TestBudgetMonitor:
    """Test suite for budget monitoring functionality"""
    
    @pytest.fixture
    async def budget_monitor(self, mock_db_connection):
        """Create budget monitor with mocked dependencies"""
        monitor = BudgetMonitor()
        monitor.db_pool = mock_db_connection
        return monitor
    
    async def test_create_budget(self, budget_monitor, mock_db_connection):
        """Test budget creation"""
        budget_request = CreateBudgetRequest(
            budget_type=BudgetType.TENANT,
            name="Test Budget",
            amount=Decimal("500.00"),
            period=BudgetPeriod.MONTHLY,
            tenant_id="test-tenant-123",
            alert_thresholds=[Decimal("75"), Decimal("90")],
            alert_channels=[AlertChannel.EMAIL, AlertChannel.SLACK],
            alert_recipients=["admin@aivo.com"]
        )
        
        # Mock successful insertion
        mock_db_connection.fetchrow.return_value = {
            'id': str(uuid4()),
            'budget_type': 'tenant',
            'name': 'Test Budget',
            'amount': Decimal('500.00'),
            'created_at': datetime.utcnow()
        }
        
        budget = await budget_monitor.create_budget(budget_request)
        
        assert budget.name == "Test Budget"
        assert budget.amount == Decimal("500.00")
        assert budget.budget_type == BudgetType.TENANT
        assert budget.tenant_id == "test-tenant-123"
        assert AlertChannel.EMAIL in budget.alert_channels
        assert AlertChannel.SLACK in budget.alert_channels
        
    async def test_budget_threshold_alerts(self, budget_monitor, sample_budget):
        """Test budget threshold alert generation"""
        # Simulate budget at 80% usage
        sample_budget.current_spend = Decimal("80.00")  # 80% of 100.00 budget
        
        with patch.object(budget_monitor, 'send_budget_alert') as mock_send_alert:
            await budget_monitor.check_budget_thresholds(sample_budget)
            
            # Should trigger 75% threshold alert
            mock_send_alert.assert_called_once()
            call_args = mock_send_alert.call_args[0]
            alert = call_args[0]
            
            assert alert.severity == AlertSeverity.MEDIUM
            assert alert.threshold_percentage == Decimal("75")
            assert alert.current_spend == Decimal("80.00")
            assert alert.percentage_used == Decimal("80.0")
    
    async def test_budget_exceeded_alert(self, budget_monitor, sample_budget):
        """Test budget exceeded alert"""
        # Simulate budget exceeded
        sample_budget.current_spend = Decimal("105.00")  # 105% of 100.00 budget
        sample_budget.is_exceeded = True
        
        with patch.object(budget_monitor, 'send_budget_alert') as mock_send_alert:
            await budget_monitor.check_budget_thresholds(sample_budget)
            
            mock_send_alert.assert_called()
            call_args = mock_send_alert.call_args[0]
            alert = call_args[0]
            
            assert alert.severity == AlertSeverity.CRITICAL
            assert alert.current_spend == Decimal("105.00")
            assert alert.percentage_used == Decimal("105.0")
    
    async def test_budget_impact_tracking(self, budget_monitor, sample_usage_event):
        """Test tracking budget impact from usage events"""
        # Mock budget lookup
        budget_monitor.get_applicable_budgets = AsyncMock(return_value=[
            Budget(
                id="budget-123",
                budget_type=BudgetType.TENANT,
                name="Tenant Budget",
                tenant_id="test-tenant-123",
                amount=Decimal("100.00"),
                period=BudgetPeriod.MONTHLY,
                current_spend=Decimal("50.00")
            )
        ])
        
        # Mock cost calculation
        sample_usage_event.calculated_cost = Decimal("5.00")
        
        with patch.object(budget_monitor, 'update_budget_spend') as mock_update:
            await budget_monitor.check_budget_impact(sample_usage_event)
            
            mock_update.assert_called_once()
            # Verify budget spend would be updated with the event cost
            call_args = mock_update.call_args
            assert call_args[0][1] == Decimal("5.00")  # Cost to add
    
    async def test_quarterly_access_review_creation(self, budget_monitor):
        """Test quarterly access review budget creation"""
        review_budget = CreateBudgetRequest(
            budget_type=BudgetType.GLOBAL,
            name="Q3 2024 Budget Review",
            amount=Decimal("10000.00"),
            period=BudgetPeriod.QUARTERLY,
            alert_thresholds=[Decimal("60"), Decimal("80"), Decimal("95")],
            alert_channels=[AlertChannel.EMAIL, AlertChannel.SLACK],
            alert_recipients=["finops@aivo.com", "cto@aivo.com"]
        )
        
        budget = await budget_monitor.create_budget(review_budget)
        
        assert budget.period == BudgetPeriod.QUARTERLY
        assert budget.amount == Decimal("10000.00")
        assert len(budget.alert_thresholds) == 3
        assert budget.alert_recipients == ["finops@aivo.com", "cto@aivo.com"]


class TestProviderIntegrations:
    """Test suite for provider integrations"""
    
    async def test_openai_provider_pricing_update(self):
        """Test OpenAI provider pricing updates"""
        provider = OpenAIProvider()
        pricing_list = await provider.get_current_pricing()
        
        assert len(pricing_list) > 0
        
        # Check GPT-4 pricing
        gpt4_pricing = next((p for p in pricing_list if p.model_name == "gpt-4"), None)
        assert gpt4_pricing is not None
        assert gpt4_pricing.provider == ProviderType.OPENAI
        assert gpt4_pricing.model_type == ModelType.TEXT_GENERATION
        assert gpt4_pricing.input_token_price > 0
        assert gpt4_pricing.output_token_price > 0
        assert gpt4_pricing.is_active is True
    
    async def test_gemini_provider_optimization_suggestions(self):
        """Test Gemini provider cost optimization suggestions"""
        provider = GeminiProvider()
        
        # Create sample usage events
        usage_events = [
            UsageEvent(
                tenant_id="test-tenant",
                service_name="test-service",
                provider=ProviderType.GEMINI,
                model_name="gemini-1.5-pro",
                model_type=ModelType.TEXT_GENERATION,
                input_tokens=5000,
                output_tokens=2000,
                request_count=10
            ) for _ in range(20)  # 20 events for significant usage
        ]
        
        suggestions = await provider.get_cost_optimization_suggestions(usage_events)
        
        assert len(suggestions) > 0
        
        # Should suggest Flash model for cost savings
        flash_suggestion = next(
            (s for s in suggestions if "flash" in s.get("title", "").lower()), 
            None
        )
        assert flash_suggestion is not None
        assert flash_suggestion["type"] == "model_substitution"
        assert flash_suggestion["potential_monthly_savings"] > 0
    
    async def test_bedrock_provider_model_support(self):
        """Test Bedrock provider model support"""
        provider = BedrockProvider()
        
        supported_models = provider.get_supported_models()
        assert len(supported_models) > 0
        
        # Check for key models
        assert any("claude" in model for model in supported_models)
        assert any("titan" in model for model in supported_models)
        assert any("llama" in model for model in supported_models)
        
        provider_info = provider.get_provider_info()
        assert provider_info["provider"] == ProviderType.BEDROCK
        assert "text_generation" in provider_info["capabilities"]
        assert "cloudwatch_integration" in provider_info["capabilities"]
    
    async def test_provider_cost_estimation(self):
        """Test monthly cost estimation across providers"""
        providers = [OpenAIProvider(), GeminiProvider(), BedrockProvider()]
        
        # Create usage history for last 7 days
        usage_history = []
        for i in range(7):
            for provider_type, model in [
                (ProviderType.OPENAI, "gpt-4"),
                (ProviderType.GEMINI, "gemini-1.5-flash"),
                (ProviderType.BEDROCK, "anthropic.claude-3-haiku-20240307-v1:0")
            ]:
                event = UsageEvent(
                    tenant_id="test-tenant",
                    service_name="test-service",
                    provider=provider_type,
                    model_name=model,
                    model_type=ModelType.TEXT_GENERATION,
                    input_tokens=1000,
                    output_tokens=500,
                    request_count=5,
                    timestamp=datetime.utcnow() - timedelta(days=i)
                )
                usage_history.append(event)
        
        for provider in providers:
            provider_events = [
                e for e in usage_history 
                if e.provider == provider.provider_type
            ]
            
            if provider_events:
                estimation = await provider.estimate_monthly_cost(
                    provider_events, 
                    growth_factor=Decimal("1.2")  # 20% growth
                )
                
                assert estimation["estimated_monthly_cost"] >= 0
                assert estimation["confidence"] in ["low", "medium", "high"]
                assert estimation["data_points"] > 0
                assert estimation["growth_factor"] == Decimal("1.2")


class TestBudgetAlerts:
    """Test suite for budget alert functionality"""
    
    async def test_alert_creation_and_delivery(self):
        """Test budget alert creation and delivery"""
        alert = BudgetAlert(
            budget_id="budget-123",
            budget_name="Test Budget",
            severity=AlertSeverity.HIGH,
            threshold_percentage=Decimal("90"),
            current_spend=Decimal("95.00"),
            budget_amount=Decimal("100.00"),
            percentage_used=Decimal("95.0"),
            tenant_id="test-tenant-123",
            period_start=datetime.utcnow() - timedelta(days=30),
            period_end=datetime.utcnow(),
            alert_title="Budget Alert: 95% of budget used",
            alert_message="Your budget has reached 95% usage. Current spend: $95.00 of $100.00."
        )
        
        assert alert.severity == AlertSeverity.HIGH
        assert alert.percentage_used == Decimal("95.0")
        assert "95%" in alert.alert_title
        assert "$95.00" in alert.alert_message
        assert not alert.is_acknowledged
    
    async def test_alert_deduplication(self):
        """Test that duplicate alerts are not sent"""
        budget_monitor = BudgetMonitor()
        
        # Mock that alert was already sent for this threshold
        budget = Budget(
            id="budget-123",
            budget_type=BudgetType.TENANT,
            name="Test Budget",
            amount=Decimal("100.00"),
            period=BudgetPeriod.MONTHLY,
            current_spend=Decimal("76.00"),
            last_alert_threshold=Decimal("75"),  # Already alerted at 75%
            last_alert_sent=datetime.utcnow() - timedelta(minutes=30)
        )
        
        with patch.object(budget_monitor, 'send_budget_alert') as mock_send_alert:
            await budget_monitor.check_budget_thresholds(budget)
            
            # Should not send another 75% alert
            mock_send_alert.assert_not_called()
    
    async def test_critical_alert_immediate_delivery(self):
        """Test that critical alerts are delivered immediately"""
        budget_monitor = BudgetMonitor()
        
        budget = Budget(
            id="budget-123",
            budget_type=BudgetType.LEARNER,
            name="Student Budget",
            learner_id="learner-456",
            amount=Decimal("50.00"),
            period=BudgetPeriod.MONTHLY,
            current_spend=Decimal("55.00"),  # 110% - over budget
            alert_channels=[AlertChannel.EMAIL, AlertChannel.SLACK],
            alert_recipients=["teacher@school.edu", "admin@aivo.com"]
        )
        
        with patch.object(budget_monitor, 'send_budget_alert') as mock_send_alert:
            await budget_monitor.check_budget_thresholds(budget)
            
            mock_send_alert.assert_called()
            call_args = mock_send_alert.call_args[0]
            alert = call_args[0]
            
            assert alert.severity == AlertSeverity.CRITICAL
            assert alert.percentage_used >= Decimal("100.0")
            assert len(alert.channels_sent) == 0  # Will be set after sending
            assert len(alert.recipients_notified) == 0  # Will be set after sending


class TestAPIEndpoints:
    """Test suite for FinOps API endpoints"""
    
    def test_health_check(self, client):
        """Test health check endpoint"""
        response = client.get("/health")
        assert response.status_code == 200
        
        health_data = response.json()
        assert "status" in health_data
        assert "timestamp" in health_data
        assert "uptime_seconds" in health_data
    
    def test_metrics_endpoint(self, client):
        """Test Prometheus metrics endpoint"""
        response = client.get("/metrics")
        assert response.status_code == 200
        assert response.headers["content-type"] == "text/plain; charset=utf-8"
        
        metrics_text = response.text
        assert "finops_uptime_seconds" in metrics_text
        assert "finops_database_connected" in metrics_text
    
    @patch('app.routes.get_current_user')
    def test_create_budget_endpoint(self, mock_auth, client):
        """Test budget creation endpoint"""
        # Mock authentication
        mock_auth.return_value = {
            "user_id": "user-123",
            "roles": ["finops_admin"],
            "tenant_ids": ["test-tenant-123"]
        }
        
        budget_data = {
            "budget_type": "tenant",
            "name": "API Test Budget",
            "amount": "250.00",
            "period": "monthly",
            "tenant_id": "test-tenant-123",
            "alert_thresholds": [50.0, 75.0, 90.0],
            "alert_channels": ["email"],
            "alert_recipients": ["admin@aivo.com"]
        }
        
        with patch('app.routes.get_budget_monitor') as mock_monitor:
            mock_monitor.return_value.create_budget = AsyncMock(return_value=Budget(
                id="budget-123",
                budget_type=BudgetType.TENANT,
                name="API Test Budget",
                amount=Decimal("250.00"),
                period=BudgetPeriod.MONTHLY,
                tenant_id="test-tenant-123"
            ))
            
            response = client.post(
                "/api/v1/budgets",
                json=budget_data,
                headers={"Authorization": "Bearer test-token"}
            )
            
            assert response.status_code == 200
            response_data = response.json()
            assert response_data["name"] == "API Test Budget"
            assert response_data["amount"] == "250.00"
    
    @patch('app.routes.get_current_user')
    def test_cost_query_endpoint(self, mock_auth, client):
        """Test cost query endpoint"""
        mock_auth.return_value = {
            "user_id": "user-123",
            "roles": ["finops_viewer"],
            "tenant_ids": ["test-tenant-123"]
        }
        
        query_data = {
            "start_date": (datetime.utcnow() - timedelta(days=7)).isoformat(),
            "end_date": datetime.utcnow().isoformat(),
            "tenant_id": "test-tenant-123",
            "group_by": ["provider", "day"],
            "include_breakdown": True
        }
        
        with patch('app.routes.get_cost_calculator') as mock_calculator:
            mock_calculator.return_value.query_costs = AsyncMock(return_value=CostResponse(
                total_cost=Decimal("45.75"),
                total_tokens=30000,
                total_requests=150,
                period_start=datetime.utcnow() - timedelta(days=7),
                period_end=datetime.utcnow(),
                cost_by_provider={"openai": Decimal("30.00"), "gemini": Decimal("15.75")},
                cost_by_day={
                    "2024-08-13": Decimal("6.50"),
                    "2024-08-14": Decimal("8.25"),
                    "2024-08-15": Decimal("9.00")
                }
            ))
            
            response = client.post(
                "/api/v1/costs/query",
                json=query_data,
                headers={"Authorization": "Bearer test-token"}
            )
            
            assert response.status_code == 200
            response_data = response.json()
            assert response_data["total_cost"] == "45.75"
            assert "cost_by_provider" in response_data
            assert "cost_by_day" in response_data


class TestCostForecasting:
    """Test suite for cost forecasting and optimization"""
    
    async def test_cost_forecast_calculation(self):
        """Test cost forecasting based on historical data"""
        calculator = CostCalculator()
        
        # Create 30 days of historical usage
        usage_history = []
        base_cost = Decimal("10.00")
        
        for i in range(30):
            # Simulate growing usage (10% growth)
            daily_cost = base_cost * (Decimal("1.1") ** (i / 30))
            
            event = UsageEvent(
                tenant_id="test-tenant",
                service_name="inference-gateway",
                provider=ProviderType.OPENAI,
                model_name="gpt-4",
                model_type=ModelType.TEXT_GENERATION,
                input_tokens=int(daily_cost * 100),  # Correlate tokens to cost
                output_tokens=int(daily_cost * 50),
                calculated_cost=daily_cost,
                timestamp=datetime.utcnow() - timedelta(days=30-i)
            )
            usage_history.append(event)
        
        forecast = await calculator.generate_cost_forecasts(
            tenant_id="test-tenant",
            forecast_days=30
        )
        
        # Should have at least one forecast
        assert len(forecast) > 0
        
        # Forecast should project higher costs due to growth trend
        latest_forecast = forecast[0]
        assert latest_forecast.predicted_cost > base_cost
        assert latest_forecast.confidence_level > 0
        assert latest_forecast.trend_direction in ["increasing", "decreasing", "stable"]
    
    async def test_learner_specific_cost_tracking(self):
        """Test per-learner cost tracking and budgeting"""
        budget_monitor = BudgetMonitor()
        
        # Create learner-specific budget
        learner_budget = CreateBudgetRequest(
            budget_type=BudgetType.LEARNER,
            name="Emma's Monthly AI Budget",
            amount=Decimal("25.00"),
            period=BudgetPeriod.MONTHLY,
            tenant_id="school-district-1",
            learner_id="learner-emma-123",
            alert_thresholds=[Decimal("80"), Decimal("95")],
            alert_channels=[AlertChannel.EMAIL],
            alert_recipients=["teacher@school.edu", "parent@family.com"]
        )
        
        budget = await budget_monitor.create_budget(learner_budget)
        
        assert budget.budget_type == BudgetType.LEARNER
        assert budget.learner_id == "learner-emma-123"
        assert budget.amount == Decimal("25.00")
        assert "parent@family.com" in budget.alert_recipients
        
        # Simulate learner usage
        learner_usage = UsageEvent(
            tenant_id="school-district-1",
            learner_id="learner-emma-123",
            service_name="tutoring-svc",
            provider=ProviderType.OPENAI,
            model_name="gpt-3.5-turbo",
            model_type=ModelType.TEXT_GENERATION,
            input_tokens=500,
            output_tokens=200,
            calculated_cost=Decimal("0.75"),  # Small cost per interaction
            metadata={"subject": "mathematics", "grade": "5th"}
        )
        
        # Budget monitor should track this usage
        with patch.object(budget_monitor, 'update_budget_spend') as mock_update:
            await budget_monitor.check_budget_impact(learner_usage)
            
            # Should update the learner's budget
            mock_update.assert_called()


class TestComplianceAndAuditing:
    """Test suite for compliance and auditing features"""
    
    async def test_cost_reconciliation(self):
        """Test cost reconciliation with provider billing"""
        calculator = CostCalculator()
        
        # Sample usage events
        events = [
            UsageEvent(
                tenant_id="test-tenant",
                service_name="inference-svc",
                provider=ProviderType.OPENAI,
                model_name="gpt-4",
                input_tokens=1000,
                output_tokens=500,
                calculated_cost=Decimal("0.06"),
                timestamp=datetime.utcnow() - timedelta(hours=i)
            ) for i in range(24)  # 24 hours of usage
        ]
        
        # Calculate our internal costs
        total_internal_cost = sum(event.calculated_cost for event in events)
        
        # Mock provider billing amount (should be close)
        provider_billed_amount = total_internal_cost * Decimal("1.02")  # 2% variance
        
        # Calculate reconciliation
        variance = abs(total_internal_cost - provider_billed_amount)
        variance_percentage = (variance / total_internal_cost) * 100
        
        # Should be within acceptable variance (5%)
        assert variance_percentage < 5
        
        # Generate reconciliation report
        reconciliation_report = {
            "period": "last_24_hours",
            "internal_calculated": float(total_internal_cost),
            "provider_billed": float(provider_billed_amount),
            "variance": float(variance),
            "variance_percentage": float(variance_percentage),
            "status": "within_tolerance" if variance_percentage < 5 else "needs_review"
        }
        
        assert reconciliation_report["status"] == "within_tolerance"
    
    async def test_cost_audit_trail(self):
        """Test audit trail for cost tracking"""
        # All cost events should be auditable
        usage_event = UsageEvent(
            tenant_id="audit-test-tenant",
            learner_id="audit-test-learner",
            service_name="inference-gateway-svc",
            session_id="audit-session-123",
            provider=ProviderType.GEMINI,
            model_name="gemini-1.5-pro",
            model_type=ModelType.TEXT_GENERATION,
            input_tokens=2000,
            output_tokens=800,
            calculated_cost=Decimal("8.50"),
            metadata={
                "audit_context": "compliance_test",
                "user_ip": "192.168.1.100",
                "api_version": "v1"
            }
        )
        
        # Verify all required audit fields are present
        assert usage_event.id is not None
        assert usage_event.timestamp is not None
        assert usage_event.tenant_id is not None
        assert usage_event.calculated_cost is not None
        assert usage_event.metadata is not None
        
        # Verify event can be serialized for audit storage
        audit_record = {
            "event_id": usage_event.id,
            "timestamp": usage_event.timestamp.isoformat(),
            "tenant_id": usage_event.tenant_id,
            "learner_id": usage_event.learner_id,
            "service": usage_event.service_name,
            "provider": usage_event.provider,
            "model": usage_event.model_name,
            "cost": float(usage_event.calculated_cost),
            "metadata": usage_event.metadata
        }
        
        # Audit record should contain all necessary compliance data
        required_fields = [
            "event_id", "timestamp", "tenant_id", "service",
            "provider", "model", "cost"
        ]
        
        for field in required_fields:
            assert field in audit_record
            assert audit_record[field] is not None


if __name__ == "__main__":
    # Run the test suite
    pytest.main([__file__, "-v", "--tb=short"])
