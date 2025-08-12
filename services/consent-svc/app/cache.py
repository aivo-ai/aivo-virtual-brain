"""
Consent Service Redis Cache
Redis caching layer for consent state with TTL and invalidation
"""

import json
import structlog
from typing import Dict, List, Optional, Union
from redis.asyncio import Redis, ConnectionPool
from redis.exceptions import RedisError

from app.config import settings
from app.schemas import ConsentStateResponse, ConsentKey

logger = structlog.get_logger(__name__)


class ConsentCacheService:
    """Redis cache service for consent state management"""
    
    def __init__(self):
        self.pool = ConnectionPool.from_url(
            settings.redis_url,
            max_connections=20,
            retry_on_timeout=True,
            retry_on_error=[ConnectionError, TimeoutError],
            health_check_interval=30
        )
        self.redis = Redis(connection_pool=self.pool)
        logger.info("Consent cache service initialized", redis_url=settings.redis_url)
    
    @property
    def consent_key(self) -> str:
        """Consent cache key prefix"""
        return "consent"
    
    @property
    def gate_key(self) -> str:
        """Gateway consent gate cache key prefix"""
        return "consent_gate"
    
    def _make_consent_key(self, learner_id: str) -> str:
        """Generate Redis key for consent state"""
        return f"{self.consent_key}:{learner_id}"
    
    def _make_gate_key(self, learner_id: str, consent_type: str) -> str:
        """Generate Redis key for gateway consent gate"""
        return f"{self.gate_key}:{learner_id}:{consent_type}"
    
    def _make_bulk_key(self, learner_ids: List[str]) -> str:
        """Generate Redis key for bulk consent lookup"""
        return f"{self.consent_key}:bulk:{':'.join(sorted(learner_ids))}"
    
    async def health_check(self) -> bool:
        """Check Redis connectivity"""
        try:
            await self.redis.ping()
            return True
        except Exception as e:
            logger.error("Redis health check failed", error=str(e))
            return False
    
    async def get_consent_state(self, learner_id: str) -> Optional[ConsentStateResponse]:
        """Get consent state from cache"""
        try:
            key = self._make_consent_key(learner_id)
            cached_data = await self.redis.get(key)
            
            if cached_data:
                data = json.loads(cached_data)
                consent_response = ConsentStateResponse(**data)
                
                logger.debug(
                    "Cache hit for consent state",
                    learner_id=learner_id,
                    key=key
                )
                
                return consent_response
            
            logger.debug(
                "Cache miss for consent state",
                learner_id=learner_id,
                key=key
            )
            
            return None
            
        except Exception as e:
            logger.error(
                "Failed to get consent state from cache",
                learner_id=learner_id,
                error=str(e)
            )
            return None
    
    async def set_consent_state(
        self, 
        learner_id: str, 
        consent_state: ConsentStateResponse,
        ttl: Optional[int] = None
    ) -> bool:
        """Set consent state in cache"""
        try:
            key = self._make_consent_key(learner_id)
            ttl = ttl or settings.cache_ttl_seconds
            
            # Store consent state
            data = consent_state.model_dump_json()
            await self.redis.setex(key, ttl, data)
            
            # Update gateway gate cache entries
            await self._update_gate_cache(learner_id, consent_state, ttl)
            
            logger.debug(
                "Cached consent state",
                learner_id=learner_id,
                key=key,
                ttl=ttl
            )
            
            return True
            
        except Exception as e:
            logger.error(
                "Failed to cache consent state",
                learner_id=learner_id,
                error=str(e)
            )
            return False
    
    async def _update_gate_cache(
        self, 
        learner_id: str, 
        consent_state: ConsentStateResponse,
        ttl: int
    ):
        """Update gateway consent gate cache entries"""
        try:
            # Cache individual consent flags for gateway
            gate_values = {
                "media": consent_state.media,
                "chat": consent_state.chat,
                "third_party": consent_state.third_party
            }
            
            pipeline = self.redis.pipeline()
            
            for consent_type, value in gate_values.items():
                gate_key = self._make_gate_key(learner_id, consent_type)
                pipeline.setex(gate_key, ttl, json.dumps(value))
            
            await pipeline.execute()
            
            logger.debug(
                "Updated gateway consent cache",
                learner_id=learner_id,
                consent_flags=gate_values
            )
            
        except Exception as e:
            logger.error(
                "Failed to update gateway consent cache",
                learner_id=learner_id,
                error=str(e)
            )
    
    async def get_consent_gate_value(
        self, 
        learner_id: str, 
        consent_type: str
    ) -> Optional[bool]:
        """Get consent gate value for gateway"""
        try:
            key = self._make_gate_key(learner_id, consent_type)
            cached_value = await self.redis.get(key)
            
            if cached_value:
                value = json.loads(cached_value)
                
                logger.debug(
                    "Gateway consent gate hit",
                    learner_id=learner_id,
                    consent_type=consent_type,
                    value=value
                )
                
                return value
            
            logger.debug(
                "Gateway consent gate miss",
                learner_id=learner_id,
                consent_type=consent_type
            )
            
            return None
            
        except Exception as e:
            logger.error(
                "Failed to get consent gate value",
                learner_id=learner_id,
                consent_type=consent_type,
                error=str(e)
            )
            return None
    
    async def get_bulk_consent_states(
        self, 
        learner_ids: List[str]
    ) -> Dict[str, ConsentStateResponse]:
        """Get multiple consent states from cache"""
        try:
            if not learner_ids:
                return {}
            
            # Use pipeline for bulk retrieval
            pipeline = self.redis.pipeline()
            keys = [self._make_consent_key(lid) for lid in learner_ids]
            
            for key in keys:
                pipeline.get(key)
            
            results = await pipeline.execute()
            
            consent_states = {}
            cache_hits = 0
            
            for i, (learner_id, cached_data) in enumerate(zip(learner_ids, results)):
                if cached_data:
                    try:
                        data = json.loads(cached_data)
                        consent_states[learner_id] = ConsentStateResponse(**data)
                        cache_hits += 1
                    except Exception as e:
                        logger.warning(
                            "Failed to parse cached consent state",
                            learner_id=learner_id,
                            error=str(e)
                        )
            
            logger.debug(
                "Bulk consent cache lookup",
                requested=len(learner_ids),
                cache_hits=cache_hits,
                hit_rate=f"{(cache_hits/len(learner_ids)*100):.1f}%"
            )
            
            return consent_states
            
        except Exception as e:
            logger.error(
                "Failed to get bulk consent states from cache",
                learner_count=len(learner_ids),
                error=str(e)
            )
            return {}
    
    async def invalidate_consent_state(self, learner_id: str) -> bool:
        """Invalidate consent state from cache"""
        try:
            # Remove consent state
            consent_key = self._make_consent_key(learner_id)
            
            # Remove gateway gate entries
            gate_keys = [
                self._make_gate_key(learner_id, "media"),
                self._make_gate_key(learner_id, "chat"),
                self._make_gate_key(learner_id, "third_party")
            ]
            
            all_keys = [consent_key] + gate_keys
            deleted = await self.redis.delete(*all_keys)
            
            logger.debug(
                "Invalidated consent cache",
                learner_id=learner_id,
                keys_deleted=deleted
            )
            
            return deleted > 0
            
        except Exception as e:
            logger.error(
                "Failed to invalidate consent cache",
                learner_id=learner_id,
                error=str(e)
            )
            return False
    
    async def invalidate_bulk_consent_states(self, learner_ids: List[str]) -> int:
        """Invalidate multiple consent states from cache"""
        try:
            if not learner_ids:
                return 0
            
            # Collect all keys to delete
            all_keys = []
            
            for learner_id in learner_ids:
                # Consent state key
                all_keys.append(self._make_consent_key(learner_id))
                
                # Gateway gate keys
                all_keys.extend([
                    self._make_gate_key(learner_id, "media"),
                    self._make_gate_key(learner_id, "chat"),
                    self._make_gate_key(learner_id, "third_party")
                ])
            
            deleted = await self.redis.delete(*all_keys)
            
            logger.debug(
                "Bulk invalidated consent cache",
                learner_ids=len(learner_ids),
                keys_deleted=deleted
            )
            
            return deleted
            
        except Exception as e:
            logger.error(
                "Failed to bulk invalidate consent cache",
                learner_count=len(learner_ids),
                error=str(e)
            )
            return 0
    
    async def set_cache_stats(self) -> Dict[str, Union[int, str]]:
        """Get cache statistics"""
        try:
            info = await self.redis.info()
            
            # Count consent-related keys
            consent_keys = await self.redis.keys(f"{self.consent_key}:*")
            gate_keys = await self.redis.keys(f"{self.gate_key}:*")
            
            stats = {
                "consent_keys": len(consent_keys),
                "gate_keys": len(gate_keys),
                "total_keys": len(consent_keys) + len(gate_keys),
                "memory_usage": info.get("used_memory_human", "unknown"),
                "connected_clients": info.get("connected_clients", 0),
                "cache_hits": info.get("keyspace_hits", 0),
                "cache_misses": info.get("keyspace_misses", 0)
            }
            
            if stats["cache_hits"] + stats["cache_misses"] > 0:
                hit_rate = stats["cache_hits"] / (stats["cache_hits"] + stats["cache_misses"])
                stats["hit_rate"] = f"{hit_rate:.2%}"
            else:
                stats["hit_rate"] = "0%"
            
            logger.info("Retrieved cache statistics", **stats)
            
            return stats
            
        except Exception as e:
            logger.error("Failed to get cache statistics", error=str(e))
            return {}
    
    async def clear_all_consent_cache(self) -> int:
        """Clear all consent-related cache entries"""
        try:
            # Get all consent and gate keys
            consent_keys = await self.redis.keys(f"{self.consent_key}:*")
            gate_keys = await self.redis.keys(f"{self.gate_key}:*")
            
            all_keys = consent_keys + gate_keys
            
            if all_keys:
                deleted = await self.redis.delete(*all_keys)
            else:
                deleted = 0
            
            logger.info(
                "Cleared all consent cache",
                consent_keys=len(consent_keys),
                gate_keys=len(gate_keys),
                total_deleted=deleted
            )
            
            return deleted
            
        except Exception as e:
            logger.error("Failed to clear consent cache", error=str(e))
            return 0
    
    async def close(self):
        """Close Redis connections"""
        try:
            await self.redis.close()
            logger.info("Redis connections closed")
        except Exception as e:
            logger.error("Failed to close Redis connections", error=str(e))


# Global cache service instance
cache_service = ConsentCacheService()
