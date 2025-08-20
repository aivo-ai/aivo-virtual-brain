"""
Google Gemini Provider for FinOps Cost Tracking
Handles Google Gemini API pricing, usage tracking, and cost calculation
"""

import asyncio
from datetime import datetime, timedelta
from decimal import Decimal
from typing import Dict, List, Optional, Any
import json

import aiohttp
import structlog

from ..models import ProviderPricing, UsageEvent, ProviderType, ModelType

logger = structlog.get_logger(__name__)


class GeminiProvider:
    """Google Gemini provider for cost tracking and pricing management"""
    
    def __init__(self):
        self.provider_type = ProviderType.GEMINI
        self.base_url = "https://generativelanguage.googleapis.com/v1beta"
        self.pricing_cache = {}
        self.last_pricing_update = None
        
        # Current Gemini pricing (as of August 2024)
        self.default_pricing = {
            "gemini-1.5-pro": {
                "input_tokens": Decimal("0.0035") / 1000,   # $0.0035 per 1K tokens
                "output_tokens": Decimal("0.0105") / 1000,  # $0.0105 per 1K tokens
                "model_type": ModelType.TEXT_GENERATION
            },
            "gemini-1.5-flash": {
                "input_tokens": Decimal("0.00035") / 1000,  # $0.00035 per 1K tokens
                "output_tokens": Decimal("0.00105") / 1000, # $0.00105 per 1K tokens
                "model_type": ModelType.TEXT_GENERATION
            },
            "gemini-1.0-pro": {
                "input_tokens": Decimal("0.0005") / 1000,   # $0.0005 per 1K tokens
                "output_tokens": Decimal("0.0015") / 1000,  # $0.0015 per 1K tokens
                "model_type": ModelType.TEXT_GENERATION
            },
            "text-embedding-004": {
                "input_tokens": Decimal("0.000025") / 1000, # $0.000025 per 1K tokens
                "output_tokens": Decimal("0"),              # No output cost for embeddings
                "model_type": ModelType.TEXT_EMBEDDING
            },
            "gemini-pro-vision": {
                "input_tokens": Decimal("0.0025") / 1000,   # $0.0025 per 1K tokens
                "output_tokens": Decimal("0.005") / 1000,   # $0.005 per 1K tokens
                "image_price": Decimal("0.0025"),           # $0.0025 per image
                "model_type": ModelType.IMAGE_ANALYSIS
            }
        }
    
    async def get_current_pricing(self) -> List[ProviderPricing]:
        """Get current Gemini pricing information"""
        try:
            pricing_list = []
            
            for model_name, pricing_info in self.default_pricing.items():
                pricing = ProviderPricing(
                    provider=self.provider_type,
                    model_name=model_name,
                    model_type=pricing_info["model_type"],
                    input_token_price=pricing_info["input_tokens"],
                    output_token_price=pricing_info["output_tokens"],
                    image_price=pricing_info.get("image_price"),
                    request_price=Decimal("0"),  # Gemini doesn't charge per request
                    currency="USD",
                    effective_date=datetime.utcnow(),
                    is_active=True,
                    # Gemini rate limits (approximate)
                    rate_limit_rpm=60 if "flash" in model_name else 30,
                    rate_limit_tpm=1000000 if "flash" in model_name else 500000
                )
                pricing_list.append(pricing)
            
            # Cache the pricing
            self.pricing_cache = {p.model_name: p for p in pricing_list}
            self.last_pricing_update = datetime.utcnow()
            
            logger.info(
                "Gemini pricing updated",
                model_count=len(pricing_list),
                provider=self.provider_type
            )
            
            return pricing_list
            
        except Exception as e:
            logger.error("Failed to get Gemini pricing", error=str(e), exc_info=True)
            raise
    
    async def calculate_usage_cost(self, usage_event: UsageEvent) -> Decimal:
        """Calculate cost for a Gemini usage event"""
        try:
            # Get pricing for the model
            if usage_event.model_name not in self.pricing_cache:
                await self.get_current_pricing()
            
            pricing = self.pricing_cache.get(usage_event.model_name)
            if not pricing:
                logger.warning(
                    "No pricing found for Gemini model",
                    model=usage_event.model_name,
                    provider=self.provider_type
                )
                return Decimal("0")
            
            total_cost = Decimal("0")
            
            # Calculate token costs
            if usage_event.input_tokens > 0 and pricing.input_token_price:
                input_cost = (Decimal(usage_event.input_tokens) / 1000) * pricing.input_token_price
                total_cost += input_cost
            
            if usage_event.output_tokens > 0 and pricing.output_token_price:
                output_cost = (Decimal(usage_event.output_tokens) / 1000) * pricing.output_token_price
                total_cost += output_cost
            
            # Calculate image costs (for vision models)
            if usage_event.images_processed > 0 and pricing.image_price:
                image_cost = Decimal(usage_event.images_processed) * pricing.image_price
                total_cost += image_cost
            
            logger.debug(
                "Gemini usage cost calculated",
                model=usage_event.model_name,
                input_tokens=usage_event.input_tokens,
                output_tokens=usage_event.output_tokens,
                images=usage_event.images_processed,
                calculated_cost=float(total_cost)
            )
            
            return total_cost
            
        except Exception as e:
            logger.error(
                "Failed to calculate Gemini usage cost",
                model=usage_event.model_name,
                error=str(e),
                exc_info=True
            )
            return Decimal("0")
    
    async def validate_api_key(self, api_key: str) -> bool:
        """Validate Gemini API key"""
        try:
            async with aiohttp.ClientSession() as session:
                # Test with a simple list models request
                async with session.get(
                    f"{self.base_url}/models",
                    params={"key": api_key},
                    timeout=aiohttp.ClientTimeout(total=10)
                ) as response:
                    return response.status == 200
                    
        except Exception as e:
            logger.error("Failed to validate Gemini API key", error=str(e), exc_info=True)
            return False
    
    async def get_rate_limits(self, api_key: str) -> Dict[str, Any]:
        """Get current rate limits for the Gemini API key"""
        try:
            # Gemini rate limits are per model and tier
            # These are typical limits, actual limits may vary
            return {
                "gemini-1.5-pro": {
                    "requests_per_minute": 30,
                    "tokens_per_minute": 500000,
                    "requests_per_day": 1000
                },
                "gemini-1.5-flash": {
                    "requests_per_minute": 60,
                    "tokens_per_minute": 1000000,
                    "requests_per_day": 2000
                },
                "gemini-1.0-pro": {
                    "requests_per_minute": 60,
                    "tokens_per_minute": 500000,
                    "requests_per_day": 1500
                }
            }
            
        except Exception as e:
            logger.error("Failed to get Gemini rate limits", error=str(e), exc_info=True)
            return {}
    
    async def estimate_monthly_cost(
        self,
        usage_history: List[UsageEvent],
        growth_factor: Decimal = Decimal("1.0")
    ) -> Dict[str, Any]:
        """Estimate monthly costs based on usage history"""
        try:
            if not usage_history:
                return {
                    "estimated_monthly_cost": Decimal("0"),
                    "breakdown_by_model": {},
                    "confidence": "low"
                }
            
            # Group by model and calculate costs
            model_costs = {}
            total_cost = Decimal("0")
            
            for event in usage_history:
                cost = await self.calculate_usage_cost(event)
                if event.model_name not in model_costs:
                    model_costs[event.model_name] = Decimal("0")
                model_costs[event.model_name] += cost
                total_cost += cost
            
            # Calculate daily average and project to monthly
            days_in_history = len(set(event.timestamp.date() for event in usage_history))
            if days_in_history == 0:
                days_in_history = 1
            
            daily_average = total_cost / days_in_history
            monthly_estimate = daily_average * 30 * growth_factor
            
            # Calculate confidence based on data points
            confidence = "high" if len(usage_history) > 100 else "medium" if len(usage_history) > 20 else "low"
            
            return {
                "estimated_monthly_cost": monthly_estimate,
                "daily_average": daily_average,
                "breakdown_by_model": {
                    model: (cost / days_in_history * 30 * growth_factor)
                    for model, cost in model_costs.items()
                },
                "confidence": confidence,
                "data_points": len(usage_history),
                "days_analyzed": days_in_history,
                "growth_factor": growth_factor
            }
            
        except Exception as e:
            logger.error("Failed to estimate Gemini monthly cost", error=str(e), exc_info=True)
            return {
                "estimated_monthly_cost": Decimal("0"),
                "breakdown_by_model": {},
                "confidence": "low",
                "error": str(e)
            }
    
    async def get_cost_optimization_suggestions(
        self,
        usage_events: List[UsageEvent]
    ) -> List[Dict[str, Any]]:
        """Generate cost optimization suggestions for Gemini usage"""
        try:
            suggestions = []
            
            if not usage_events:
                return suggestions
            
            # Analyze model usage patterns
            model_usage = {}
            total_cost = Decimal("0")
            
            for event in usage_events:
                if event.model_name not in model_usage:
                    model_usage[event.model_name] = {
                        "requests": 0,
                        "input_tokens": 0,
                        "output_tokens": 0,
                        "cost": Decimal("0")
                    }
                
                model_usage[event.model_name]["requests"] += event.request_count
                model_usage[event.model_name]["input_tokens"] += event.input_tokens
                model_usage[event.model_name]["output_tokens"] += event.output_tokens
                
                cost = await self.calculate_usage_cost(event)
                model_usage[event.model_name]["cost"] += cost
                total_cost += cost
            
            # Suggest Gemini 1.5 Pro -> Flash for appropriate use cases
            if "gemini-1.5-pro" in model_usage and model_usage["gemini-1.5-pro"]["cost"] > Decimal("5"):
                pro_cost = model_usage["gemini-1.5-pro"]["cost"]
                potential_savings = pro_cost * Decimal("0.7")  # Flash is about 10x cheaper
                suggestions.append({
                    "type": "model_substitution",
                    "title": "Consider Gemini 1.5 Flash for simpler tasks",
                    "description": "Flash model is significantly cheaper and faster for many use cases",
                    "current_model": "gemini-1.5-pro",
                    "suggested_model": "gemini-1.5-flash",
                    "potential_monthly_savings": potential_savings,
                    "implementation_effort": "low"
                })
            
            # Suggest upgrading from 1.0 Pro to 1.5 Flash for better value
            if "gemini-1.0-pro" in model_usage and model_usage["gemini-1.0-pro"]["cost"] > Decimal("3"):
                suggestions.append({
                    "type": "model_upgrade",
                    "title": "Upgrade to Gemini 1.5 Flash",
                    "description": "Better performance and similar cost to 1.0 Pro",
                    "current_model": "gemini-1.0-pro",
                    "suggested_model": "gemini-1.5-flash",
                    "potential_monthly_savings": Decimal("0"),
                    "performance_improvement": "Better quality responses",
                    "implementation_effort": "low"
                })
            
            # Suggest context window optimization
            avg_input_tokens = sum(
                usage["input_tokens"] for usage in model_usage.values()
            ) / max(sum(usage["requests"] for usage in model_usage.values()), 1)
            
            if avg_input_tokens > 10000:  # Large context usage
                suggestions.append({
                    "type": "context_optimization",
                    "title": "Optimize context window usage",
                    "description": "Consider truncating or summarizing long contexts to reduce token costs",
                    "avg_input_tokens": float(avg_input_tokens),
                    "potential_monthly_savings": total_cost * Decimal("0.2"),  # 20% savings estimate
                    "implementation_effort": "medium"
                })
            
            # Suggest request batching for vision models
            vision_models = [model for model in model_usage.keys() if "vision" in model.lower()]
            if vision_models:
                for model in vision_models:
                    if model_usage[model]["requests"] > 100:
                        suggestions.append({
                            "type": "batching",
                            "title": f"Batch image processing for {model}",
                            "description": "Process multiple images in single requests to reduce overhead",
                            "current_requests": model_usage[model]["requests"],
                            "potential_monthly_savings": model_usage[model]["cost"] * Decimal("0.15"),
                            "implementation_effort": "medium"
                        })
            
            logger.info(
                "Generated Gemini cost optimization suggestions",
                suggestion_count=len(suggestions),
                total_cost=float(total_cost),
                models_analyzed=list(model_usage.keys())
            )
            
            return suggestions
            
        except Exception as e:
            logger.error("Failed to generate Gemini optimization suggestions", error=str(e), exc_info=True)
            return []
    
    def is_pricing_current(self) -> bool:
        """Check if pricing data is current (updated within last 24 hours)"""
        if not self.last_pricing_update:
            return False
        
        return (datetime.utcnow() - self.last_pricing_update) < timedelta(hours=24)
    
    def get_supported_models(self) -> List[str]:
        """Get list of supported models for cost tracking"""
        return list(self.default_pricing.keys())
    
    def get_provider_info(self) -> Dict[str, Any]:
        """Get general provider information"""
        return {
            "provider": self.provider_type,
            "name": "Google Gemini",
            "supported_models": self.get_supported_models(),
            "pricing_last_updated": self.last_pricing_update.isoformat() if self.last_pricing_update else None,
            "base_url": self.base_url,
            "capabilities": [
                "text_generation",
                "text_embedding",
                "image_analysis",
                "multimodal"
            ],
            "strengths": [
                "Cost-effective Flash model",
                "Large context windows",
                "Multimodal capabilities",
                "Competitive pricing"
            ]
        }
