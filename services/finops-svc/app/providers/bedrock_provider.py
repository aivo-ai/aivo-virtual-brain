"""
AWS Bedrock Provider for FinOps Cost Tracking
Handles AWS Bedrock API pricing, usage tracking, and cost calculation
"""

import asyncio
from datetime import datetime, timedelta
from decimal import Decimal
from typing import Dict, List, Optional, Any
import json

import boto3
import structlog
from botocore.exceptions import ClientError, NoCredentialsError

from ..models import ProviderPricing, UsageEvent, ProviderType, ModelType

logger = structlog.get_logger(__name__)


class BedrockProvider:
    """AWS Bedrock provider for cost tracking and pricing management"""
    
    def __init__(self):
        self.provider_type = ProviderType.BEDROCK
        self.pricing_cache = {}
        self.last_pricing_update = None
        
        # Current Bedrock pricing (as of August 2024)
        # Prices vary by region, these are us-east-1 prices
        self.default_pricing = {
            # Anthropic models
            "anthropic.claude-3-5-sonnet-20240620-v1:0": {
                "input_tokens": Decimal("0.003") / 1000,    # $0.003 per 1K tokens
                "output_tokens": Decimal("0.015") / 1000,   # $0.015 per 1K tokens
                "model_type": ModelType.TEXT_GENERATION
            },
            "anthropic.claude-3-haiku-20240307-v1:0": {
                "input_tokens": Decimal("0.00025") / 1000,  # $0.00025 per 1K tokens
                "output_tokens": Decimal("0.00125") / 1000, # $0.00125 per 1K tokens
                "model_type": ModelType.TEXT_GENERATION
            },
            "anthropic.claude-3-opus-20240229-v1:0": {
                "input_tokens": Decimal("0.015") / 1000,    # $0.015 per 1K tokens
                "output_tokens": Decimal("0.075") / 1000,   # $0.075 per 1K tokens
                "model_type": ModelType.TEXT_GENERATION
            },
            
            # Amazon models
            "amazon.titan-text-premier-v1:0": {
                "input_tokens": Decimal("0.0005") / 1000,   # $0.0005 per 1K tokens
                "output_tokens": Decimal("0.0015") / 1000,  # $0.0015 per 1K tokens
                "model_type": ModelType.TEXT_GENERATION
            },
            "amazon.titan-text-express-v1": {
                "input_tokens": Decimal("0.0002") / 1000,   # $0.0002 per 1K tokens
                "output_tokens": Decimal("0.0006") / 1000,  # $0.0006 per 1K tokens
                "model_type": ModelType.TEXT_GENERATION
            },
            "amazon.titan-embed-text-v1": {
                "input_tokens": Decimal("0.0001") / 1000,   # $0.0001 per 1K tokens
                "output_tokens": Decimal("0"),              # No output cost for embeddings
                "model_type": ModelType.TEXT_EMBEDDING
            },
            "amazon.titan-embed-text-v2:0": {
                "input_tokens": Decimal("0.00002") / 1000,  # $0.00002 per 1K tokens
                "output_tokens": Decimal("0"),              # No output cost for embeddings
                "model_type": ModelType.TEXT_EMBEDDING
            },
            
            # Cohere models
            "cohere.command-text-v14": {
                "input_tokens": Decimal("0.0015") / 1000,   # $0.0015 per 1K tokens
                "output_tokens": Decimal("0.002") / 1000,   # $0.002 per 1K tokens
                "model_type": ModelType.TEXT_GENERATION
            },
            "cohere.command-light-text-v14": {
                "input_tokens": Decimal("0.0003") / 1000,   # $0.0003 per 1K tokens
                "output_tokens": Decimal("0.0006") / 1000,  # $0.0006 per 1K tokens
                "model_type": ModelType.TEXT_GENERATION
            },
            "cohere.embed-english-v3": {
                "input_tokens": Decimal("0.0001") / 1000,   # $0.0001 per 1K tokens
                "output_tokens": Decimal("0"),              # No output cost for embeddings
                "model_type": ModelType.TEXT_EMBEDDING
            },
            
            # AI21 models
            "ai21.j2-ultra-v1": {
                "input_tokens": Decimal("0.0188") / 1000,   # $0.0188 per 1K tokens
                "output_tokens": Decimal("0.0188") / 1000,  # $0.0188 per 1K tokens
                "model_type": ModelType.TEXT_GENERATION
            },
            "ai21.j2-mid-v1": {
                "input_tokens": Decimal("0.0125") / 1000,   # $0.0125 per 1K tokens
                "output_tokens": Decimal("0.0125") / 1000,  # $0.0125 per 1K tokens
                "model_type": ModelType.TEXT_GENERATION
            },
            
            # Meta models
            "meta.llama2-70b-chat-v1": {
                "input_tokens": Decimal("0.00195") / 1000,  # $0.00195 per 1K tokens
                "output_tokens": Decimal("0.00256") / 1000, # $0.00256 per 1K tokens
                "model_type": ModelType.TEXT_GENERATION
            },
            "meta.llama2-13b-chat-v1": {
                "input_tokens": Decimal("0.00075") / 1000,  # $0.00075 per 1K tokens
                "output_tokens": Decimal("0.001") / 1000,   # $0.001 per 1K tokens
                "model_type": ModelType.TEXT_GENERATION
            },
            
            # Stability AI models
            "stability.stable-diffusion-xl-v1": {
                "input_tokens": Decimal("0"),               # No token cost for image generation
                "output_tokens": Decimal("0"),
                "image_price": Decimal("0.04"),             # $0.04 per image
                "model_type": ModelType.IMAGE_GENERATION
            }
        }
    
    async def get_current_pricing(self) -> List[ProviderPricing]:
        """Get current Bedrock pricing information"""
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
                    request_price=Decimal("0"),  # Bedrock doesn't charge per request
                    currency="USD",
                    effective_date=datetime.utcnow(),
                    is_active=True
                )
                pricing_list.append(pricing)
            
            # Cache the pricing
            self.pricing_cache = {p.model_name: p for p in pricing_list}
            self.last_pricing_update = datetime.utcnow()
            
            logger.info(
                "Bedrock pricing updated",
                model_count=len(pricing_list),
                provider=self.provider_type
            )
            
            return pricing_list
            
        except Exception as e:
            logger.error("Failed to get Bedrock pricing", error=str(e), exc_info=True)
            raise
    
    async def calculate_usage_cost(self, usage_event: UsageEvent) -> Decimal:
        """Calculate cost for a Bedrock usage event"""
        try:
            # Get pricing for the model
            if usage_event.model_name not in self.pricing_cache:
                await self.get_current_pricing()
            
            pricing = self.pricing_cache.get(usage_event.model_name)
            if not pricing:
                logger.warning(
                    "No pricing found for Bedrock model",
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
            
            # Calculate image costs (for Stability AI models)
            if usage_event.images_processed > 0 and pricing.image_price:
                image_cost = Decimal(usage_event.images_processed) * pricing.image_price
                total_cost += image_cost
            
            logger.debug(
                "Bedrock usage cost calculated",
                model=usage_event.model_name,
                input_tokens=usage_event.input_tokens,
                output_tokens=usage_event.output_tokens,
                images=usage_event.images_processed,
                calculated_cost=float(total_cost)
            )
            
            return total_cost
            
        except Exception as e:
            logger.error(
                "Failed to calculate Bedrock usage cost",
                model=usage_event.model_name,
                error=str(e),
                exc_info=True
            )
            return Decimal("0")
    
    async def get_usage_from_cloudwatch(
        self,
        region: str,
        start_date: datetime,
        end_date: datetime,
        aws_access_key_id: Optional[str] = None,
        aws_secret_access_key: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """
        Fetch Bedrock usage data from CloudWatch metrics
        """
        try:
            # Create CloudWatch client
            if aws_access_key_id and aws_secret_access_key:
                session = boto3.Session(
                    aws_access_key_id=aws_access_key_id,
                    aws_secret_access_key=aws_secret_access_key,
                    region_name=region
                )
            else:
                session = boto3.Session(region_name=region)
            
            cloudwatch = session.client('cloudwatch')
            
            # Get Bedrock usage metrics
            usage_data = []
            
            # Query for InvocationCount and TokenUsage metrics
            metrics_to_query = [
                {
                    'metric_name': 'InvocationCount',
                    'namespace': 'AWS/Bedrock',
                    'stat': 'Sum'
                },
                {
                    'metric_name': 'InputTokenCount',
                    'namespace': 'AWS/Bedrock', 
                    'stat': 'Sum'
                },
                {
                    'metric_name': 'OutputTokenCount',
                    'namespace': 'AWS/Bedrock',
                    'stat': 'Sum'
                }
            ]
            
            for metric in metrics_to_query:
                try:
                    response = cloudwatch.get_metric_statistics(
                        Namespace=metric['namespace'],
                        MetricName=metric['metric_name'],
                        Dimensions=[],  # Get all models
                        StartTime=start_date,
                        EndTime=end_date,
                        Period=3600,  # 1 hour periods
                        Statistics=[metric['stat']]
                    )
                    
                    for datapoint in response['Datapoints']:
                        usage_data.append({
                            'timestamp': datapoint['Timestamp'],
                            'metric_name': metric['metric_name'],
                            'value': datapoint[metric['stat']],
                            'unit': datapoint['Unit']
                        })
                        
                except ClientError as e:
                    logger.warning(
                        "Failed to get CloudWatch metric",
                        metric=metric['metric_name'],
                        error=str(e)
                    )
            
            logger.info(
                "Retrieved Bedrock usage from CloudWatch",
                region=region,
                data_points=len(usage_data),
                start_date=start_date.isoformat(),
                end_date=end_date.isoformat()
            )
            
            return usage_data
            
        except (NoCredentialsError, ClientError) as e:
            logger.error("AWS credentials or permissions error", error=str(e), exc_info=True)
            return []
        except Exception as e:
            logger.error("Failed to fetch Bedrock usage from CloudWatch", error=str(e), exc_info=True)
            return []
    
    async def validate_aws_credentials(
        self,
        region: str,
        aws_access_key_id: Optional[str] = None,
        aws_secret_access_key: Optional[str] = None
    ) -> bool:
        """Validate AWS credentials for Bedrock access"""
        try:
            if aws_access_key_id and aws_secret_access_key:
                session = boto3.Session(
                    aws_access_key_id=aws_access_key_id,
                    aws_secret_access_key=aws_secret_access_key,
                    region_name=region
                )
            else:
                session = boto3.Session(region_name=region)
            
            # Test with Bedrock client
            bedrock = session.client('bedrock')
            bedrock.list_foundation_models()
            
            return True
            
        except Exception as e:
            logger.error("Failed to validate AWS credentials", error=str(e), exc_info=True)
            return False
    
    async def get_rate_limits(self, region: str) -> Dict[str, Any]:
        """Get Bedrock service quotas and rate limits"""
        try:
            # Bedrock rate limits vary by model and region
            # These are typical default quotas
            return {
                "claude-3-5-sonnet": {
                    "tokens_per_minute": 200000,
                    "requests_per_minute": 1000
                },
                "claude-3-haiku": {
                    "tokens_per_minute": 300000,
                    "requests_per_minute": 1000
                },
                "claude-3-opus": {
                    "tokens_per_minute": 80000,
                    "requests_per_minute": 400
                },
                "titan-text-express": {
                    "tokens_per_minute": 400000,
                    "requests_per_minute": 2000
                },
                "llama2-70b": {
                    "tokens_per_minute": 40000,
                    "requests_per_minute": 200
                },
                "stable-diffusion-xl": {
                    "images_per_minute": 10,
                    "requests_per_minute": 10
                }
            }
            
        except Exception as e:
            logger.error("Failed to get Bedrock rate limits", error=str(e), exc_info=True)
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
            logger.error("Failed to estimate Bedrock monthly cost", error=str(e), exc_info=True)
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
        """Generate cost optimization suggestions for Bedrock usage"""
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
            
            # Suggest Claude Opus -> Sonnet for cost savings
            if "anthropic.claude-3-opus-20240229-v1:0" in model_usage:
                opus_cost = model_usage["anthropic.claude-3-opus-20240229-v1:0"]["cost"]
                if opus_cost > Decimal("10"):
                    potential_savings = opus_cost * Decimal("0.8")  # Sonnet is ~5x cheaper
                    suggestions.append({
                        "type": "model_substitution",
                        "title": "Consider Claude 3.5 Sonnet for cost savings",
                        "description": "Sonnet provides similar quality at significantly lower cost than Opus",
                        "current_model": "anthropic.claude-3-opus-20240229-v1:0",
                        "suggested_model": "anthropic.claude-3-5-sonnet-20240620-v1:0",
                        "potential_monthly_savings": potential_savings,
                        "implementation_effort": "low"
                    })
            
            # Suggest Haiku for simple tasks
            expensive_models = [
                "anthropic.claude-3-opus-20240229-v1:0",
                "anthropic.claude-3-5-sonnet-20240620-v1:0"
            ]
            
            for model in expensive_models:
                if model in model_usage and model_usage[model]["cost"] > Decimal("5"):
                    avg_tokens = (
                        model_usage[model]["input_tokens"] + model_usage[model]["output_tokens"]
                    ) / max(model_usage[model]["requests"], 1)
                    
                    if avg_tokens < 500:  # Simple requests
                        potential_savings = model_usage[model]["cost"] * Decimal("0.9")  # Haiku is much cheaper
                        suggestions.append({
                            "type": "model_substitution",
                            "title": "Use Claude 3 Haiku for simple tasks",
                            "description": "Haiku is much cheaper for short, simple requests",
                            "current_model": model,
                            "suggested_model": "anthropic.claude-3-haiku-20240307-v1:0",
                            "potential_monthly_savings": potential_savings,
                            "avg_tokens_per_request": float(avg_tokens),
                            "implementation_effort": "medium"
                        })
            
            # Suggest Titan models for cost-sensitive use cases
            if total_cost > Decimal("20"):
                suggestions.append({
                    "type": "model_substitution",
                    "title": "Consider Amazon Titan models for cost optimization",
                    "description": "Titan models offer competitive performance at lower costs",
                    "suggested_models": [
                        "amazon.titan-text-premier-v1:0",
                        "amazon.titan-text-express-v1"
                    ],
                    "potential_monthly_savings": total_cost * Decimal("0.3"),  # 30% savings estimate
                    "implementation_effort": "medium"
                })
            
            # Suggest regional optimization
            suggestions.append({
                "type": "regional_optimization",
                "title": "Optimize regional deployment",
                "description": "Consider deploying in regions with lower Bedrock pricing",
                "recommended_regions": ["us-east-1", "us-west-2"],
                "potential_monthly_savings": total_cost * Decimal("0.1"),  # 10% savings estimate
                "implementation_effort": "high"
            })
            
            # Suggest provisioned throughput for high volume
            high_volume_models = [
                model for model, usage in model_usage.items()
                if usage["requests"] > 10000  # High request volume
            ]
            
            if high_volume_models:
                for model in high_volume_models:
                    suggestions.append({
                        "type": "provisioned_throughput",
                        "title": f"Consider provisioned throughput for {model}",
                        "description": "Provisioned throughput can reduce costs for predictable high volume",
                        "current_requests": model_usage[model]["requests"],
                        "potential_monthly_savings": model_usage[model]["cost"] * Decimal("0.2"),
                        "implementation_effort": "high"
                    })
            
            logger.info(
                "Generated Bedrock cost optimization suggestions",
                suggestion_count=len(suggestions),
                total_cost=float(total_cost),
                models_analyzed=list(model_usage.keys())
            )
            
            return suggestions
            
        except Exception as e:
            logger.error("Failed to generate Bedrock optimization suggestions", error=str(e), exc_info=True)
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
            "name": "AWS Bedrock",
            "supported_models": self.get_supported_models(),
            "pricing_last_updated": self.last_pricing_update.isoformat() if self.last_pricing_update else None,
            "capabilities": [
                "text_generation",
                "text_embedding",
                "image_generation",
                "cloudwatch_integration"
            ],
            "strengths": [
                "Multiple model providers",
                "AWS integration",
                "Enterprise features",
                "Regional deployment"
            ],
            "model_providers": [
                "Anthropic",
                "Amazon",
                "Cohere", 
                "AI21",
                "Meta",
                "Stability AI"
            ]
        }
