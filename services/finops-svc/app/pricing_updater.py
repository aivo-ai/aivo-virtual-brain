"""
Provider pricing update system for the FinOps service.

This module automatically updates provider pricing information from official APIs
and sources to ensure accurate cost calculations.
"""

import asyncio
import logging
from datetime import datetime, timezone, timedelta
from decimal import Decimal
from typing import Dict, List, Optional, Any, Tuple

import aiohttp
from sqlalchemy import select, and_
from sqlalchemy.ext.asyncio import AsyncSession

from .models import ProviderPricing, ProviderType, ModelType
from .database import get_db_session
from .config import config

logger = logging.getLogger(__name__)


class PricingUpdater:
    """Manages automatic pricing updates from provider APIs."""
    
    def __init__(self):
        self.update_interval_hours = 24
        self.last_update = {}
        self._api_timeouts = 30
        self._rate_limits = {
            ProviderType.OPENAI: 60,  # 1 request per minute
            ProviderType.GEMINI: 60,  # 1 request per minute
            ProviderType.BEDROCK: 300  # 1 request per 5 minutes
        }
        self._last_api_call = {}
    
    async def update_all_pricing(self, force: bool = False) -> Dict[str, Any]:
        """Update pricing for all providers."""
        results = {
            "updated_providers": [],
            "failed_providers": [],
            "total_updates": 0,
            "errors": []
        }
        
        try:
            # Update each provider
            for provider in ProviderType:
                try:
                    if await self._should_update_provider(provider, force):
                        provider_result = await self._update_provider_pricing(provider)
                        
                        if provider_result["success"]:
                            results["updated_providers"].append(provider.value)
                            results["total_updates"] += provider_result["count"]
                            self.last_update[provider] = datetime.now(timezone.utc)
                        else:
                            results["failed_providers"].append(provider.value)
                            results["errors"].extend(provider_result["errors"])
                    
                except Exception as e:
                    logger.error(f"Error updating pricing for {provider.value}: {e}")
                    results["failed_providers"].append(provider.value)
                    results["errors"].append(f"{provider.value}: {str(e)}")
            
            logger.info(f"Pricing update completed: {results['total_updates']} updates across {len(results['updated_providers'])} providers")
            
        except Exception as e:
            logger.error(f"Pricing update failed: {e}")
            results["errors"].append(f"General error: {str(e)}")
        
        return results
    
    async def _should_update_provider(self, provider: ProviderType, force: bool) -> bool:
        """Check if provider pricing should be updated."""
        if force:
            return True
        
        last_update = self.last_update.get(provider)
        if not last_update:
            return True
        
        time_since_update = datetime.now(timezone.utc) - last_update
        return time_since_update.total_seconds() > (self.update_interval_hours * 3600)
    
    async def _update_provider_pricing(self, provider: ProviderType) -> Dict[str, Any]:
        """Update pricing for a specific provider."""
        result = {
            "success": False,
            "count": 0,
            "errors": []
        }
        
        try:
            if provider == ProviderType.OPENAI:
                pricing_data = await self._fetch_openai_pricing()
            elif provider == ProviderType.GEMINI:
                pricing_data = await self._fetch_gemini_pricing()
            elif provider == ProviderType.BEDROCK:
                pricing_data = await self._fetch_bedrock_pricing()
            else:
                # Use manual pricing for other providers
                pricing_data = await self._get_manual_pricing(provider)
            
            if pricing_data:
                async with get_db_session() as session:
                    count = await self._save_pricing_data(provider, pricing_data, session)
                    result["success"] = True
                    result["count"] = count
            else:
                result["errors"].append("No pricing data retrieved")
                
        except Exception as e:
            logger.error(f"Provider pricing update failed for {provider.value}: {e}")
            result["errors"].append(str(e))
        
        return result
    
    async def _fetch_openai_pricing(self) -> List[Dict[str, Any]]:
        """Fetch current OpenAI pricing from API or documented rates."""
        # OpenAI doesn't provide a direct pricing API, so we use documented rates
        # This should be updated manually when OpenAI changes their pricing
        
        pricing_data = [
            # GPT-4 Turbo
            {
                "model_name": "gpt-4-turbo",
                "model_type": ModelType.TEXT_GENERATION,
                "input_token_price": Decimal("0.00001"),   # $0.01/1K tokens
                "output_token_price": Decimal("0.00003"),  # $0.03/1K tokens
                "rate_limit_rpm": 10000,
                "rate_limit_tpm": 2000000
            },
            # GPT-4
            {
                "model_name": "gpt-4",
                "model_type": ModelType.TEXT_GENERATION,
                "input_token_price": Decimal("0.00003"),   # $0.03/1K tokens
                "output_token_price": Decimal("0.00006"),  # $0.06/1K tokens
                "rate_limit_rpm": 10000,
                "rate_limit_tpm": 300000
            },
            # GPT-3.5 Turbo
            {
                "model_name": "gpt-3.5-turbo",
                "model_type": ModelType.TEXT_GENERATION,
                "input_token_price": Decimal("0.0000005"),  # $0.0005/1K tokens
                "output_token_price": Decimal("0.0000015"), # $0.0015/1K tokens
                "rate_limit_rpm": 10000,
                "rate_limit_tpm": 2000000
            },
            # Text Embedding 3 Large
            {
                "model_name": "text-embedding-3-large",
                "model_type": ModelType.TEXT_EMBEDDING,
                "input_token_price": Decimal("0.00000013"), # $0.00013/1K tokens
                "output_token_price": Decimal("0"),
                "rate_limit_rpm": 5000,
                "rate_limit_tpm": 5000000
            },
            # Text Embedding 3 Small
            {
                "model_name": "text-embedding-3-small",
                "model_type": ModelType.TEXT_EMBEDDING,
                "input_token_price": Decimal("0.00000002"), # $0.00002/1K tokens
                "output_token_price": Decimal("0"),
                "rate_limit_rpm": 5000,
                "rate_limit_tpm": 5000000
            },
            # DALL-E 3
            {
                "model_name": "dall-e-3",
                "model_type": ModelType.IMAGE_GENERATION,
                "input_token_price": Decimal("0"),
                "output_token_price": Decimal("0"),
                "image_price": Decimal("0.04"),  # $0.04/image (1024x1024)
                "rate_limit_rpm": 200
            },
            # DALL-E 2
            {
                "model_name": "dall-e-2",
                "model_type": ModelType.IMAGE_GENERATION,
                "input_token_price": Decimal("0"),
                "output_token_price": Decimal("0"),
                "image_price": Decimal("0.02"),  # $0.02/image (1024x1024)
                "rate_limit_rpm": 200
            },
            # Whisper
            {
                "model_name": "whisper-1",
                "model_type": ModelType.SPEECH_TO_TEXT,
                "input_token_price": Decimal("0"),
                "output_token_price": Decimal("0"),
                "audio_price": Decimal("0.006"),  # $0.006/minute
                "rate_limit_rpm": 200
            },
            # TTS
            {
                "model_name": "tts-1",
                "model_type": ModelType.TEXT_TO_SPEECH,
                "input_token_price": Decimal("0.000015"),  # $0.015/1K characters
                "output_token_price": Decimal("0"),
                "rate_limit_rpm": 200
            },
            {
                "model_name": "tts-1-hd",
                "model_type": ModelType.TEXT_TO_SPEECH,
                "input_token_price": Decimal("0.00003"),   # $0.030/1K characters
                "output_token_price": Decimal("0"),
                "rate_limit_rpm": 200
            }
        ]
        
        logger.info(f"Retrieved {len(pricing_data)} OpenAI pricing records")
        return pricing_data
    
    async def _fetch_gemini_pricing(self) -> List[Dict[str, Any]]:
        """Fetch current Google Gemini pricing."""
        # Google doesn't provide a direct pricing API either
        # Using documented rates from Google AI Studio pricing page
        
        pricing_data = [
            # Gemini 1.5 Flash
            {
                "model_name": "gemini-1.5-flash",
                "model_type": ModelType.TEXT_GENERATION,
                "input_token_price": Decimal("0.00000035"),  # $0.35/1M tokens
                "output_token_price": Decimal("0.00000105"), # $1.05/1M tokens
                "rate_limit_rpm": 1000,
                "rate_limit_tpm": 1000000
            },
            # Gemini 1.5 Pro
            {
                "model_name": "gemini-1.5-pro",
                "model_type": ModelType.TEXT_GENERATION,
                "input_token_price": Decimal("0.0000035"),   # $3.50/1M tokens
                "output_token_price": Decimal("0.0000105"),  # $10.50/1M tokens
                "rate_limit_rpm": 360,
                "rate_limit_tpm": 120000
            },
            # Gemini Pro Vision (for image analysis)
            {
                "model_name": "gemini-pro-vision",
                "model_type": ModelType.IMAGE_ANALYSIS,
                "input_token_price": Decimal("0.00000025"),  # $0.25/1M tokens for text
                "output_token_price": Decimal("0.0000005"),  # $0.50/1M tokens
                "image_price": Decimal("0.0025"),            # $0.0025/image
                "rate_limit_rpm": 60,
                "rate_limit_tpm": 32000
            },
            # Text Embedding
            {
                "model_name": "text-embedding-004",
                "model_type": ModelType.TEXT_EMBEDDING,
                "input_token_price": Decimal("0.00000001"),  # $0.01/1M tokens
                "output_token_price": Decimal("0"),
                "rate_limit_rpm": 1500,
                "rate_limit_tpm": 1500000
            }
        ]
        
        logger.info(f"Retrieved {len(pricing_data)} Gemini pricing records")
        return pricing_data
    
    async def _fetch_bedrock_pricing(self) -> List[Dict[str, Any]]:
        """Fetch current AWS Bedrock pricing."""
        # AWS Bedrock pricing varies by region and provider
        # Using US East (N. Virginia) pricing as baseline
        
        pricing_data = [
            # Claude 3 Haiku
            {
                "model_name": "claude-3-haiku",
                "model_type": ModelType.TEXT_GENERATION,
                "input_token_price": Decimal("0.00000025"),  # $0.25/1M tokens
                "output_token_price": Decimal("0.00000125"), # $1.25/1M tokens
                "rate_limit_rpm": 10000,
                "rate_limit_tpm": 2000000
            },
            # Claude 3 Sonnet
            {
                "model_name": "claude-3-sonnet",
                "model_type": ModelType.TEXT_GENERATION,
                "input_token_price": Decimal("0.000003"),    # $3.00/1M tokens
                "output_token_price": Decimal("0.000015"),   # $15.00/1M tokens
                "rate_limit_rpm": 10000,
                "rate_limit_tpm": 200000
            },
            # Claude 3 Opus
            {
                "model_name": "claude-3-opus",
                "model_type": ModelType.TEXT_GENERATION,
                "input_token_price": Decimal("0.000015"),    # $15.00/1M tokens
                "output_token_price": Decimal("0.000075"),   # $75.00/1M tokens
                "rate_limit_rpm": 1000,
                "rate_limit_tpm": 80000
            },
            # Titan Text G1 - Express
            {
                "model_name": "amazon.titan-text-express-v1",
                "model_type": ModelType.TEXT_GENERATION,
                "input_token_price": Decimal("0.0000008"),   # $0.8/1M tokens
                "output_token_price": Decimal("0.0000016"),  # $1.6/1M tokens
                "rate_limit_rpm": 10000,
                "rate_limit_tpm": 2000000
            },
            # Titan Embeddings
            {
                "model_name": "amazon.titan-embed-text-v1",
                "model_type": ModelType.TEXT_EMBEDDING,
                "input_token_price": Decimal("0.0000001"),   # $0.1/1M tokens
                "output_token_price": Decimal("0"),
                "rate_limit_rpm": 2000,
                "rate_limit_tpm": 4000000
            },
            # Stable Diffusion XL
            {
                "model_name": "stability.stable-diffusion-xl-v1",
                "model_type": ModelType.IMAGE_GENERATION,
                "input_token_price": Decimal("0"),
                "output_token_price": Decimal("0"),
                "image_price": Decimal("0.04"),              # $0.04/image
                "rate_limit_rpm": 50
            },
            # Cohere Command
            {
                "model_name": "cohere.command-text-v14",
                "model_type": ModelType.TEXT_GENERATION,
                "input_token_price": Decimal("0.0000015"),   # $1.5/1M tokens
                "output_token_price": Decimal("0.000002"),   # $2.0/1M tokens
                "rate_limit_rpm": 10000,
                "rate_limit_tpm": 2000000
            },
            # AI21 Jurassic
            {
                "model_name": "ai21.j2-ultra-v1",
                "model_type": ModelType.TEXT_GENERATION,
                "input_token_price": Decimal("0.0000125"),   # $12.5/1M tokens
                "output_token_price": Decimal("0.0000125"),  # $12.5/1M tokens
                "rate_limit_rpm": 10000,
                "rate_limit_tpm": 300000
            }
        ]
        
        logger.info(f"Retrieved {len(pricing_data)} Bedrock pricing records")
        return pricing_data
    
    async def _get_manual_pricing(self, provider: ProviderType) -> List[Dict[str, Any]]:
        """Get manually configured pricing for providers without APIs."""
        # Placeholder for other providers like Azure OpenAI, Anthropic direct, etc.
        manual_pricing = {
            ProviderType.AZURE_OPENAI: [
                {
                    "model_name": "gpt-4",
                    "model_type": ModelType.TEXT_GENERATION,
                    "input_token_price": Decimal("0.00003"),
                    "output_token_price": Decimal("0.00006"),
                    "rate_limit_rpm": 10000,
                    "rate_limit_tpm": 300000
                }
            ],
            ProviderType.ANTHROPIC: [
                {
                    "model_name": "claude-3-opus",
                    "model_type": ModelType.TEXT_GENERATION,
                    "input_token_price": Decimal("0.000015"),
                    "output_token_price": Decimal("0.000075"),
                    "rate_limit_rpm": 1000,
                    "rate_limit_tpm": 80000
                }
            ],
            ProviderType.LOCAL: []  # No pricing for local models
        }
        
        return manual_pricing.get(provider, [])
    
    async def _save_pricing_data(
        self, 
        provider: ProviderType, 
        pricing_data: List[Dict[str, Any]], 
        session: AsyncSession
    ) -> int:
        """Save pricing data to database."""
        count = 0
        effective_date = datetime.now(timezone.utc)
        
        try:
            # Deactivate old pricing records
            await session.execute(
                text("""
                    UPDATE provider_pricing 
                    SET is_active = false, expires_date = :expires_date
                    WHERE provider = :provider AND is_active = true
                """),
                {
                    "provider": provider.value,
                    "expires_date": effective_date
                }
            )
            
            # Insert new pricing records
            for pricing in pricing_data:
                new_pricing = ProviderPricing(
                    provider=provider,
                    model_name=pricing["model_name"],
                    model_type=pricing["model_type"],
                    input_token_price=pricing["input_token_price"],
                    output_token_price=pricing["output_token_price"],
                    image_price=pricing.get("image_price"),
                    audio_price=pricing.get("audio_price"),
                    request_price=pricing.get("request_price", Decimal("0")),
                    storage_price=pricing.get("storage_price"),
                    currency="USD",
                    effective_date=effective_date,
                    is_active=True,
                    rate_limit_rpm=pricing.get("rate_limit_rpm"),
                    rate_limit_tpm=pricing.get("rate_limit_tpm")
                )
                
                session.add(new_pricing)
                count += 1
            
            await session.commit()
            logger.info(f"Saved {count} pricing records for {provider.value}")
            
        except Exception as e:
            logger.error(f"Error saving pricing data for {provider.value}: {e}")
            await session.rollback()
            raise
        
        return count
    
    async def get_current_pricing(
        self, 
        provider: Optional[ProviderType] = None,
        model_name: Optional[str] = None,
        session: Optional[AsyncSession] = None
    ) -> List[ProviderPricing]:
        """Get current active pricing records."""
        if session:
            return await self._get_pricing_with_session(provider, model_name, session)
        else:
            async with get_db_session() as db_session:
                return await self._get_pricing_with_session(provider, model_name, db_session)
    
    async def _get_pricing_with_session(
        self,
        provider: Optional[ProviderType],
        model_name: Optional[str],
        session: AsyncSession
    ) -> List[ProviderPricing]:
        """Get pricing with database session."""
        query = select(ProviderPricing).where(
            ProviderPricing.is_active == True,
            ProviderPricing.effective_date <= datetime.now(timezone.utc)
        )
        
        if provider:
            query = query.where(ProviderPricing.provider == provider)
        
        if model_name:
            query = query.where(ProviderPricing.model_name == model_name)
        
        query = query.order_by(
            ProviderPricing.provider,
            ProviderPricing.model_name,
            ProviderPricing.effective_date.desc()
        )
        
        result = await session.execute(query)
        return list(result.scalars().all())
    
    async def check_pricing_freshness(self) -> Dict[str, Any]:
        """Check how fresh the pricing data is for each provider."""
        freshness = {}
        
        async with get_db_session() as session:
            for provider in ProviderType:
                query = select(ProviderPricing.updated_at).where(
                    ProviderPricing.provider == provider,
                    ProviderPricing.is_active == True
                ).order_by(ProviderPricing.updated_at.desc()).limit(1)
                
                result = await session.execute(query)
                last_update = result.scalar()
                
                if last_update:
                    age_hours = (datetime.now(timezone.utc) - last_update).total_seconds() / 3600
                    freshness[provider.value] = {
                        "last_update": last_update.isoformat(),
                        "age_hours": round(age_hours, 2),
                        "is_stale": age_hours > self.update_interval_hours
                    }
                else:
                    freshness[provider.value] = {
                        "last_update": None,
                        "age_hours": None,
                        "is_stale": True
                    }
        
        return freshness
    
    async def force_pricing_refresh(self, provider: Optional[ProviderType] = None) -> Dict[str, Any]:
        """Force refresh pricing for specific provider or all providers."""
        if provider:
            result = await self._update_provider_pricing(provider)
            return {provider.value: result}
        else:
            return await self.update_all_pricing(force=True)
