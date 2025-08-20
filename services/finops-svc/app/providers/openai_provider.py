"""
OpenAI Provider for FinOps Cost Tracking
Handles OpenAI API pricing, usage tracking, and cost calculation
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


class OpenAIProvider:
    """OpenAI provider for cost tracking and pricing management"""
    
    def __init__(self):
        self.provider_type = ProviderType.OPENAI
        self.base_url = "https://api.openai.com/v1"
        self.pricing_cache = {}
        self.last_pricing_update = None
        
        # Current OpenAI pricing (as of August 2024)
        # These would be updated via API or manual updates
        self.default_pricing = {
            "gpt-4": {
                "input_tokens": Decimal("0.03") / 1000,    # $0.03 per 1K tokens
                "output_tokens": Decimal("0.06") / 1000,   # $0.06 per 1K tokens
                "model_type": ModelType.TEXT_GENERATION
            },
            "gpt-4-turbo": {
                "input_tokens": Decimal("0.01") / 1000,    # $0.01 per 1K tokens
                "output_tokens": Decimal("0.03") / 1000,   # $0.03 per 1K tokens
                "model_type": ModelType.TEXT_GENERATION
            },
            "gpt-3.5-turbo": {
                "input_tokens": Decimal("0.0015") / 1000,  # $0.0015 per 1K tokens
                "output_tokens": Decimal("0.002") / 1000,  # $0.002 per 1K tokens
                "model_type": ModelType.TEXT_GENERATION
            },
            "text-embedding-3-small": {
                "input_tokens": Decimal("0.00002") / 1000, # $0.00002 per 1K tokens
                "output_tokens": Decimal("0"),             # No output cost for embeddings
                "model_type": ModelType.TEXT_EMBEDDING
            },
            "text-embedding-3-large": {
                "input_tokens": Decimal("0.00013") / 1000, # $0.00013 per 1K tokens
                "output_tokens": Decimal("0"),             # No output cost for embeddings
                "model_type": ModelType.TEXT_EMBEDDING
            },
            "dall-e-3": {
                "input_tokens": Decimal("0"),              # No token cost for image generation
                "output_tokens": Decimal("0"),
                "image_price": Decimal("0.04"),            # $0.04 per image (1024x1024)
                "model_type": ModelType.IMAGE_GENERATION
            },
            "dall-e-2": {
                "input_tokens": Decimal("0"),
                "output_tokens": Decimal("0"),
                "image_price": Decimal("0.02"),            # $0.02 per image (1024x1024)
                "model_type": ModelType.IMAGE_GENERATION
            },
            "whisper-1": {
                "input_tokens": Decimal("0"),
                "output_tokens": Decimal("0"),
                "audio_price": Decimal("0.006"),           # $0.006 per minute
                "model_type": ModelType.SPEECH_TO_TEXT
            },
            "tts-1": {
                "input_tokens": Decimal("0.015") / 1000,   # $0.015 per 1K characters
                "output_tokens": Decimal("0"),
                "model_type": ModelType.TEXT_TO_SPEECH
            },
            "tts-1-hd": {
                "input_tokens": Decimal("0.03") / 1000,    # $0.03 per 1K characters
                "output_tokens": Decimal("0"),
                "model_type": ModelType.TEXT_TO_SPEECH
            }
        }
    
    async def get_current_pricing(self) -> List[ProviderPricing]:
        """Get current OpenAI pricing information"""
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
                    audio_price=pricing_info.get("audio_price"),
                    request_price=Decimal("0"),  # OpenAI doesn't charge per request
                    currency="USD",
                    effective_date=datetime.utcnow(),
                    is_active=True
                )
                pricing_list.append(pricing)
            
            # Cache the pricing
            self.pricing_cache = {p.model_name: p for p in pricing_list}
            self.last_pricing_update = datetime.utcnow()
            
            logger.info(
                "OpenAI pricing updated",
                model_count=len(pricing_list),
                provider=self.provider_type
            )
            
            return pricing_list
            
        except Exception as e:
            logger.error("Failed to get OpenAI pricing", error=str(e), exc_info=True)
            raise
    
    async def calculate_usage_cost(self, usage_event: UsageEvent) -> Decimal:
        """Calculate cost for a usage event"""
        try:
            # Get pricing for the model
            if usage_event.model_name not in self.pricing_cache:
                await self.get_current_pricing()
            
            pricing = self.pricing_cache.get(usage_event.model_name)
            if not pricing:
                logger.warning(
                    "No pricing found for model",
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
            
            # Calculate image costs
            if usage_event.images_processed > 0 and pricing.image_price:
                image_cost = Decimal(usage_event.images_processed) * pricing.image_price
                total_cost += image_cost
            
            # Calculate audio costs
            if usage_event.audio_minutes > 0 and pricing.audio_price:
                audio_cost = usage_event.audio_minutes * pricing.audio_price
                total_cost += audio_cost
            
            # Add request cost (if any)
            if pricing.request_price:
                request_cost = Decimal(usage_event.request_count) * pricing.request_price
                total_cost += request_cost
            
            logger.debug(
                "OpenAI usage cost calculated",
                model=usage_event.model_name,
                input_tokens=usage_event.input_tokens,
                output_tokens=usage_event.output_tokens,
                images=usage_event.images_processed,
                audio_minutes=float(usage_event.audio_minutes),
                calculated_cost=float(total_cost)
            )
            
            return total_cost
            
        except Exception as e:
            logger.error(
                "Failed to calculate OpenAI usage cost",
                model=usage_event.model_name,
                error=str(e),
                exc_info=True
            )
            return Decimal("0")
    
    async def get_usage_from_api(
        self,
        api_key: str,
        start_date: datetime,
        end_date: datetime
    ) -> List[Dict[str, Any]]:
        """
        Fetch usage data from OpenAI API (if available)
        Note: OpenAI doesn't provide detailed usage API, this is for future compatibility
        """
        try:
            # This would be implemented when OpenAI provides usage API
            logger.info(
                "OpenAI usage API not available, using local tracking",
                start_date=start_date.isoformat(),
                end_date=end_date.isoformat()
            )
            return []
            
        except Exception as e:
            logger.error("Failed to fetch OpenAI usage from API", error=str(e), exc_info=True)
            return []
    
    async def validate_api_key(self, api_key: str) -> bool:
        """Validate OpenAI API key"""
        try:
            async with aiohttp.ClientSession() as session:
                headers = {
                    "Authorization": f"Bearer {api_key}",
                    "Content-Type": "application/json"
                }
                
                # Make a simple API call to validate the key
                async with session.get(
                    f"{self.base_url}/models",
                    headers=headers,
                    timeout=aiohttp.ClientTimeout(total=10)
                ) as response:
                    return response.status == 200
                    
        except Exception as e:
            logger.error("Failed to validate OpenAI API key", error=str(e), exc_info=True)
            return False
    
    async def get_rate_limits(self, api_key: str) -> Dict[str, Any]:
        """Get current rate limits for the API key"""
        try:
            # OpenAI rate limits are returned in response headers
            # This would make a test request to get current limits
            async with aiohttp.ClientSession() as session:
                headers = {
                    "Authorization": f"Bearer {api_key}",
                    "Content-Type": "application/json"
                }
                
                async with session.get(
                    f"{self.base_url}/models",
                    headers=headers,
                    timeout=aiohttp.ClientTimeout(total=10)
                ) as response:
                    if response.status == 200:
                        return {
                            "requests_per_minute": response.headers.get("x-ratelimit-limit-requests"),
                            "tokens_per_minute": response.headers.get("x-ratelimit-limit-tokens"),
                            "remaining_requests": response.headers.get("x-ratelimit-remaining-requests"),
                            "remaining_tokens": response.headers.get("x-ratelimit-remaining-tokens"),
                            "reset_requests": response.headers.get("x-ratelimit-reset-requests"),
                            "reset_tokens": response.headers.get("x-ratelimit-reset-tokens")
                        }
            
            return {}
            
        except Exception as e:
            logger.error("Failed to get OpenAI rate limits", error=str(e), exc_info=True)
            return {}
    
    async def estimate_monthly_cost(
        self,
        usage_history: List[UsageEvent],
        growth_factor: Decimal = Decimal("1.0")
    ) -> Dict[str, Any]:
        """Estimate monthly costs based on usage history"""
        try:
            # Calculate current daily average
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
            logger.error("Failed to estimate OpenAI monthly cost", error=str(e), exc_info=True)
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
        """Generate cost optimization suggestions for OpenAI usage"""
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
            
            # Suggest GPT-4 -> GPT-3.5-turbo for appropriate use cases
            if "gpt-4" in model_usage and "gpt-3.5-turbo" not in model_usage:
                gpt4_cost = model_usage["gpt-4"]["cost"]
                if gpt4_cost > Decimal("10"):  # If spending more than $10 on GPT-4
                    potential_savings = gpt4_cost * Decimal("0.8")  # Assume 80% could be GPT-3.5
                    suggestions.append({
                        "type": "model_substitution",
                        "title": "Consider GPT-3.5-turbo for simpler tasks",
                        "description": "GPT-3.5-turbo costs significantly less and may be suitable for many use cases",
                        "current_model": "gpt-4",
                        "suggested_model": "gpt-3.5-turbo",
                        "potential_monthly_savings": potential_savings,
                        "implementation_effort": "medium"
                    })
            
            # Suggest embedding model optimization
            if "text-embedding-3-large" in model_usage:
                large_embedding_cost = model_usage["text-embedding-3-large"]["cost"]
                if large_embedding_cost > Decimal("5"):
                    potential_savings = large_embedding_cost * Decimal("0.85")  # 85% savings with small model
                    suggestions.append({
                        "type": "model_substitution",
                        "title": "Consider text-embedding-3-small for embeddings",
                        "description": "Small embedding model costs much less with minimal performance impact for many use cases",
                        "current_model": "text-embedding-3-large",
                        "suggested_model": "text-embedding-3-small",
                        "potential_monthly_savings": potential_savings,
                        "implementation_effort": "low"
                    })
            
            # Suggest request batching for high-frequency usage
            total_requests = sum(usage["requests"] for usage in model_usage.values())
            avg_tokens_per_request = sum(
                usage["input_tokens"] + usage["output_tokens"] 
                for usage in model_usage.values()
            ) / max(total_requests, 1)
            
            if total_requests > 1000 and avg_tokens_per_request < 100:
                suggestions.append({
                    "type": "request_optimization",
                    "title": "Consider batching small requests",
                    "description": "Many small requests can be batched together to reduce overhead",
                    "current_requests": total_requests,
                    "avg_tokens_per_request": float(avg_tokens_per_request),
                    "potential_monthly_savings": total_cost * Decimal("0.1"),  # 10% savings estimate
                    "implementation_effort": "high"
                })
            
            # Suggest caching for repeated requests
            if total_requests > 500:
                suggestions.append({
                    "type": "caching",
                    "title": "Implement response caching",
                    "description": "Cache responses for repeated queries to reduce API calls",
                    "potential_monthly_savings": total_cost * Decimal("0.15"),  # 15% savings estimate
                    "implementation_effort": "medium"
                })
            
            logger.info(
                "Generated OpenAI cost optimization suggestions",
                suggestion_count=len(suggestions),
                total_cost=float(total_cost),
                models_analyzed=list(model_usage.keys())
            )
            
            return suggestions
            
        except Exception as e:
            logger.error("Failed to generate OpenAI optimization suggestions", error=str(e), exc_info=True)
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
            "name": "OpenAI",
            "supported_models": self.get_supported_models(),
            "pricing_last_updated": self.last_pricing_update.isoformat() if self.last_pricing_update else None,
            "base_url": self.base_url,
            "capabilities": [
                "text_generation",
                "text_embedding", 
                "image_generation",
                "speech_to_text",
                "text_to_speech"
            ]
        }
