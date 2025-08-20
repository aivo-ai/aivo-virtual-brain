"""
Cost calculation engine for AI inference services.

This module provides comprehensive cost calculation for various AI providers including
OpenAI, Google Gemini, AWS Bedrock, and others. It handles token-based pricing,
image processing, audio processing, and custom pricing models.
"""

import asyncio
import logging
from datetime import datetime, timezone
from decimal import Decimal, ROUND_HALF_UP
from typing import Dict, List, Optional, Tuple, Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from .models import UsageEvent, ProviderPricing, ProviderType, ModelType
from .database import get_db_session
from .providers.openai_provider import OpenAIProvider
from .providers.gemini_provider import GeminiProvider
from .providers.bedrock_provider import BedrockProvider

logger = logging.getLogger(__name__)


class CostCalculator:
    """Main cost calculation engine for all AI providers."""
    
    def __init__(self):
        self.providers = {
            ProviderType.OPENAI: OpenAIProvider(),
            ProviderType.GEMINI: GeminiProvider(),
            ProviderType.BEDROCK: BedrockProvider(),
        }
        self._pricing_cache = {}
        self._cache_expiry = {}
    
    async def calculate_usage_cost(
        self, 
        usage_event: UsageEvent,
        session: Optional[AsyncSession] = None
    ) -> Tuple[Decimal, Dict[str, Any]]:
        """
        Calculate cost for a usage event with detailed breakdown.
        
        Args:
            usage_event: The usage event to calculate cost for
            session: Optional database session
            
        Returns:
            Tuple of (calculated_cost, cost_breakdown)
        """
        try:
            # Use provided session or create new one
            if session:
                return await self._calculate_with_session(usage_event, session)
            else:
                async with get_db_session() as db_session:
                    return await self._calculate_with_session(usage_event, db_session)
                    
        except Exception as e:
            logger.error(f"Cost calculation failed for usage event: {e}")
            # Return fallback cost estimation
            fallback_cost = await self._get_fallback_cost(usage_event)
            return fallback_cost, {"error": str(e), "fallback": True}
    
    async def _calculate_with_session(
        self, 
        usage_event: UsageEvent, 
        session: AsyncSession
    ) -> Tuple[Decimal, Dict[str, Any]]:
        """Calculate cost with database session."""
        # Get provider-specific calculator
        provider_calculator = self.providers.get(usage_event.provider)
        if not provider_calculator:
            logger.warning(f"No provider calculator for {usage_event.provider}")
            return await self._calculate_generic_cost(usage_event, session)
        
        # Use provider-specific calculation
        cost, breakdown = await provider_calculator.calculate_usage_cost(
            usage_event, session
        )
        
        # Add general cost information
        breakdown.update({
            "calculation_time": datetime.now(timezone.utc).isoformat(),
            "provider": usage_event.provider.value,
            "model": usage_event.model_name,
            "calculation_method": "provider_specific"
        })
        
        return cost, breakdown
    
    async def _calculate_generic_cost(
        self, 
        usage_event: UsageEvent, 
        session: AsyncSession
    ) -> Tuple[Decimal, Dict[str, Any]]:
        """Calculate cost using generic pricing lookup."""
        # Get pricing information from database
        pricing = await self._get_pricing_info(
            usage_event.provider,
            usage_event.model_name,
            usage_event.model_type,
            session
        )
        
        if not pricing:
            logger.warning(f"No pricing data for {usage_event.provider}/{usage_event.model_name}")
            fallback_cost = await self._get_fallback_cost(usage_event)
            return fallback_cost, {"fallback": True, "reason": "no_pricing_data"}
        
        # Calculate token costs
        input_cost = Decimal(str(usage_event.input_tokens or 0)) * pricing.input_token_price
        output_cost = Decimal(str(usage_event.output_tokens or 0)) * pricing.output_token_price
        
        # Calculate other costs
        request_cost = Decimal(str(usage_event.request_count)) * (pricing.request_price or Decimal('0'))
        image_cost = Decimal(str(usage_event.images_processed or 0)) * (pricing.image_price or Decimal('0'))
        audio_cost = Decimal(str(usage_event.audio_minutes or 0)) * (pricing.audio_price or Decimal('0'))
        storage_cost = Decimal(str(usage_event.storage_gb or 0)) * (pricing.storage_price or Decimal('0'))
        
        # Total cost
        total_cost = input_cost + output_cost + request_cost + image_cost + audio_cost + storage_cost
        
        # Round to 6 decimal places
        total_cost = total_cost.quantize(Decimal('0.000001'), rounding=ROUND_HALF_UP)
        
        breakdown = {
            "input_token_cost": float(input_cost),
            "output_token_cost": float(output_cost),
            "request_cost": float(request_cost),
            "image_cost": float(image_cost),
            "audio_cost": float(audio_cost),
            "storage_cost": float(storage_cost),
            "total_cost": float(total_cost),
            "pricing_effective_date": pricing.effective_date.isoformat(),
            "calculation_method": "generic"
        }
        
        return total_cost, breakdown
    
    async def _get_pricing_info(
        self,
        provider: ProviderType,
        model_name: str,
        model_type: ModelType,
        session: AsyncSession
    ) -> Optional[ProviderPricing]:
        """Get current pricing information for a provider/model."""
        # Check cache first
        cache_key = f"{provider.value}:{model_name}"
        if cache_key in self._pricing_cache:
            cached_pricing, cached_time = self._pricing_cache[cache_key]
            # Cache valid for 1 hour
            if (datetime.now(timezone.utc) - cached_time).seconds < 3600:
                return cached_pricing
        
        # Query database for current pricing
        query = select(ProviderPricing).where(
            ProviderPricing.provider == provider,
            ProviderPricing.model_name == model_name,
            ProviderPricing.is_active == True,
            ProviderPricing.effective_date <= datetime.now(timezone.utc)
        ).order_by(ProviderPricing.effective_date.desc()).limit(1)
        
        result = await session.execute(query)
        pricing = result.scalar_one_or_none()
        
        # Cache the result
        if pricing:
            self._pricing_cache[cache_key] = (pricing, datetime.now(timezone.utc))
        
        return pricing
    
    async def _get_fallback_cost(self, usage_event: UsageEvent) -> Decimal:
        """Get fallback cost estimation when pricing data is unavailable."""
        # Use conservative estimates based on typical market rates
        fallback_rates = {
            ProviderType.OPENAI: {
                ModelType.TEXT_GENERATION: Decimal('0.00005'),  # $0.05/1K tokens
                ModelType.TEXT_EMBEDDING: Decimal('0.0000001'),  # $0.0001/1K tokens
                ModelType.IMAGE_GENERATION: Decimal('0.02'),     # $0.02/image
                ModelType.IMAGE_ANALYSIS: Decimal('0.01'),       # $0.01/image
                ModelType.SPEECH_TO_TEXT: Decimal('0.006'),      # $0.006/minute
                ModelType.TEXT_TO_SPEECH: Decimal('0.015'),      # $0.015/1K chars
            },
            ProviderType.GEMINI: {
                ModelType.TEXT_GENERATION: Decimal('0.000001'),  # $0.001/1K tokens
                ModelType.TEXT_EMBEDDING: Decimal('0.0000001'),  # $0.0001/1K tokens
                ModelType.IMAGE_ANALYSIS: Decimal('0.0025'),     # $0.0025/image
            },
            ProviderType.BEDROCK: {
                ModelType.TEXT_GENERATION: Decimal('0.00008'),   # $0.08/1K tokens
                ModelType.TEXT_EMBEDDING: Decimal('0.0000001'),  # $0.0001/1K tokens
                ModelType.IMAGE_GENERATION: Decimal('0.04'),     # $0.04/image
            }
        }
        
        provider_rates = fallback_rates.get(usage_event.provider, {})
        rate = provider_rates.get(usage_event.model_type, Decimal('0.00005'))
        
        # Calculate based on total tokens or requests
        if usage_event.input_tokens or usage_event.output_tokens:
            total_tokens = (usage_event.input_tokens or 0) + (usage_event.output_tokens or 0)
            cost = Decimal(str(total_tokens)) * rate
        else:
            cost = Decimal(str(usage_event.request_count)) * rate * Decimal('100')  # Assume 100 tokens per request
        
        return cost.quantize(Decimal('0.000001'), rounding=ROUND_HALF_UP)
    
    async def calculate_batch_costs(
        self, 
        usage_events: List[UsageEvent],
        session: Optional[AsyncSession] = None
    ) -> List[Tuple[UsageEvent, Decimal, Dict[str, Any]]]:
        """Calculate costs for multiple usage events efficiently."""
        if session:
            return await self._calculate_batch_with_session(usage_events, session)
        else:
            async with get_db_session() as db_session:
                return await self._calculate_batch_with_session(usage_events, db_session)
    
    async def _calculate_batch_with_session(
        self,
        usage_events: List[UsageEvent],
        session: AsyncSession
    ) -> List[Tuple[UsageEvent, Decimal, Dict[str, Any]]]:
        """Calculate batch costs with database session."""
        results = []
        
        # Group events by provider for efficient processing
        provider_groups = {}
        for event in usage_events:
            if event.provider not in provider_groups:
                provider_groups[event.provider] = []
            provider_groups[event.provider].append(event)
        
        # Process each provider group
        for provider, events in provider_groups.items():
            provider_calculator = self.providers.get(provider)
            
            if provider_calculator and hasattr(provider_calculator, 'calculate_batch_costs'):
                # Use provider-specific batch calculation
                batch_results = await provider_calculator.calculate_batch_costs(events, session)
                results.extend(batch_results)
            else:
                # Calculate individually
                for event in events:
                    cost, breakdown = await self._calculate_with_session(event, session)
                    results.append((event, cost, breakdown))
        
        return results
    
    async def get_cost_optimization_suggestions(
        self,
        usage_events: List[UsageEvent],
        tenant_id: str,
        session: Optional[AsyncSession] = None
    ) -> List[Dict[str, Any]]:
        """Get cost optimization suggestions based on usage patterns."""
        suggestions = []
        
        if session:
            return await self._get_optimization_suggestions_with_session(
                usage_events, tenant_id, session
            )
        else:
            async with get_db_session() as db_session:
                return await self._get_optimization_suggestions_with_session(
                    usage_events, tenant_id, db_session
                )
    
    async def _get_optimization_suggestions_with_session(
        self,
        usage_events: List[UsageEvent],
        tenant_id: str,
        session: AsyncSession
    ) -> List[Dict[str, Any]]:
        """Get optimization suggestions with database session."""
        suggestions = []
        
        # Analyze usage patterns
        usage_analysis = await self._analyze_usage_patterns(usage_events)
        
        # Get provider-specific suggestions
        for provider, events in usage_analysis["by_provider"].items():
            provider_calculator = self.providers.get(provider)
            if provider_calculator and hasattr(provider_calculator, 'get_cost_optimization_suggestions'):
                provider_suggestions = await provider_calculator.get_cost_optimization_suggestions(
                    events, tenant_id, session
                )
                suggestions.extend(provider_suggestions)
        
        # Add general optimization suggestions
        general_suggestions = await self._get_general_optimization_suggestions(usage_analysis, tenant_id)
        suggestions.extend(general_suggestions)
        
        return suggestions
    
    async def _analyze_usage_patterns(self, usage_events: List[UsageEvent]) -> Dict[str, Any]:
        """Analyze usage patterns for optimization insights."""
        analysis = {
            "total_events": len(usage_events),
            "total_cost": Decimal('0'),
            "by_provider": {},
            "by_model": {},
            "by_service": {},
            "token_stats": {
                "total_input": 0,
                "total_output": 0,
                "avg_input": 0,
                "avg_output": 0
            }
        }
        
        total_input_tokens = 0
        total_output_tokens = 0
        
        for event in usage_events:
            # Group by provider
            if event.provider not in analysis["by_provider"]:
                analysis["by_provider"][event.provider] = []
            analysis["by_provider"][event.provider].append(event)
            
            # Group by model
            if event.model_name not in analysis["by_model"]:
                analysis["by_model"][event.model_name] = []
            analysis["by_model"][event.model_name].append(event)
            
            # Group by service
            if event.service_name not in analysis["by_service"]:
                analysis["by_service"][event.service_name] = []
            analysis["by_service"][event.service_name].append(event)
            
            # Aggregate tokens and cost
            total_input_tokens += event.input_tokens or 0
            total_output_tokens += event.output_tokens or 0
            analysis["total_cost"] += event.calculated_cost or Decimal('0')
        
        # Calculate averages
        if usage_events:
            analysis["token_stats"].update({
                "total_input": total_input_tokens,
                "total_output": total_output_tokens,
                "avg_input": total_input_tokens / len(usage_events),
                "avg_output": total_output_tokens / len(usage_events)
            })
        
        return analysis
    
    async def _get_general_optimization_suggestions(
        self, 
        usage_analysis: Dict[str, Any],
        tenant_id: str
    ) -> List[Dict[str, Any]]:
        """Get general cost optimization suggestions."""
        suggestions = []
        
        # High token usage suggestion
        if usage_analysis["token_stats"]["avg_input"] > 2000:
            suggestions.append({
                "type": "token_optimization",
                "title": "Optimize input token usage",
                "description": "Consider implementing input token limits or prompt optimization to reduce costs",
                "potential_savings_percentage": 15.0,
                "implementation_effort": "medium",
                "risk_level": "low"
            })
        
        # Multiple model usage suggestion
        if len(usage_analysis["by_model"]) > 3:
            suggestions.append({
                "type": "model_consolidation",
                "title": "Consider model consolidation",
                "description": "Multiple models in use. Consider standardizing on fewer models for better rate negotiations",
                "potential_savings_percentage": 10.0,
                "implementation_effort": "high",
                "risk_level": "medium"
            })
        
        # High cost per request suggestion
        avg_cost_per_request = float(usage_analysis["total_cost"]) / max(usage_analysis["total_events"], 1)
        if avg_cost_per_request > 0.10:
            suggestions.append({
                "type": "cost_per_request",
                "title": "High cost per request detected",
                "description": f"Average cost per request is ${avg_cost_per_request:.4f}. Consider optimizing request patterns",
                "potential_savings_percentage": 20.0,
                "implementation_effort": "medium",
                "risk_level": "low"
            })
        
        return suggestions
    
    async def estimate_monthly_cost(
        self,
        tenant_id: str,
        provider: Optional[ProviderType] = None,
        model_name: Optional[str] = None,
        session: Optional[AsyncSession] = None
    ) -> Dict[str, Any]:
        """Estimate monthly cost based on recent usage patterns."""
        if session:
            return await self._estimate_monthly_cost_with_session(
                tenant_id, provider, model_name, session
            )
        else:
            async with get_db_session() as db_session:
                return await self._estimate_monthly_cost_with_session(
                    tenant_id, provider, model_name, db_session
                )
    
    async def _estimate_monthly_cost_with_session(
        self,
        tenant_id: str,
        provider: Optional[ProviderType],
        model_name: Optional[str],
        session: AsyncSession
    ) -> Dict[str, Any]:
        """Estimate monthly cost with database session."""
        # Get usage from last 7 days
        from datetime import timedelta
        
        end_date = datetime.now(timezone.utc)
        start_date = end_date - timedelta(days=7)
        
        # Build query
        query = select(UsageEvent).where(
            UsageEvent.tenant_id == tenant_id,
            UsageEvent.timestamp >= start_date,
            UsageEvent.timestamp <= end_date
        )
        
        if provider:
            query = query.where(UsageEvent.provider == provider)
        if model_name:
            query = query.where(UsageEvent.model_name == model_name)
        
        result = await session.execute(query)
        recent_events = result.scalars().all()
        
        if not recent_events:
            return {
                "estimated_monthly_cost": 0,
                "confidence": "low",
                "basis": "no_recent_usage"
            }
        
        # Calculate weekly cost and project to monthly
        weekly_cost = sum(event.calculated_cost or Decimal('0') for event in recent_events)
        monthly_cost = weekly_cost * Decimal('4.33')  # Average weeks per month
        
        # Calculate confidence based on usage consistency
        daily_costs = {}
        for event in recent_events:
            day = event.timestamp.date()
            if day not in daily_costs:
                daily_costs[day] = Decimal('0')
            daily_costs[day] += event.calculated_cost or Decimal('0')
        
        # Standard deviation of daily costs
        if len(daily_costs) > 1:
            daily_values = list(daily_costs.values())
            mean_daily = sum(daily_values) / len(daily_values)
            variance = sum((x - mean_daily) ** 2 for x in daily_values) / len(daily_values)
            std_dev = variance ** Decimal('0.5')
            coefficient_of_variation = std_dev / mean_daily if mean_daily > 0 else Decimal('1')
            
            if coefficient_of_variation < Decimal('0.3'):
                confidence = "high"
            elif coefficient_of_variation < Decimal('0.6'):
                confidence = "medium"
            else:
                confidence = "low"
        else:
            confidence = "low"
        
        return {
            "estimated_monthly_cost": float(monthly_cost),
            "weekly_cost": float(weekly_cost),
            "daily_average": float(weekly_cost / 7),
            "confidence": confidence,
            "basis": f"{len(recent_events)} events over 7 days",
            "usage_days": len(daily_costs)
        }
