"""
API Routes for Feature Flag Service
"""

from fastapi import APIRouter, HTTPException, Depends, Request
from typing import Dict, List, Optional, Any
import logging
from datetime import datetime, timezone

from app.models import (
    FlagEvaluationRequest,
    FlagEvaluationResponse,
    FlagDefinitionResponse,
    EvaluationContext,
    ConfigCache,
    FlagEvaluator
)

logger = logging.getLogger(__name__)

router = APIRouter()


def get_cache(request: Request) -> ConfigCache:
    """Dependency to get config cache"""
    if not hasattr(request.app.state, 'config_cache'):
        raise HTTPException(status_code=503, detail="Config cache not initialized")
    return request.app.state.config_cache


def get_evaluator(request: Request) -> FlagEvaluator:
    """Dependency to get flag evaluator"""
    if not hasattr(request.app.state, 'flag_evaluator'):
        raise HTTPException(status_code=503, detail="Flag evaluator not initialized")
    return request.app.state.flag_evaluator


def get_request_context(request: Request) -> Dict[str, Any]:
    """Extract context from request headers and query params"""
    context = {}
    
    # Extract from headers
    headers_map = {
        'x-user-id': 'user_id',
        'x-session-id': 'session_id',
        'x-tenant-id': 'tenant_id',
        'x-user-role': 'role',
        'x-grade-band': 'grade_band',
        'x-tenant-tier': 'tenant_tier',
        'x-variation': 'variation'
    }
    
    for header_key, context_key in headers_map.items():
        value = request.headers.get(header_key)
        if value:
            context[context_key] = value
    
    # Extract from query parameters
    query_params = dict(request.query_params)
    for key, value in query_params.items():
        if key.startswith('ctx_'):
            context[key[4:]] = value  # Remove 'ctx_' prefix
    
    # Add request metadata
    context['ip_address'] = request.client.host if request.client else None
    context['user_agent'] = request.headers.get('user-agent')
    context['request_time'] = datetime.now(timezone.utc).isoformat()
    
    return context


@router.get("/health")
async def health_check(request: Request):
    """Health check endpoint"""
    try:
        cache = get_cache(request)
        is_healthy = await cache.health_check()
        if is_healthy:
            return {"status": "healthy", "timestamp": datetime.now(timezone.utc)}
        else:
            raise HTTPException(status_code=503, detail="Cache unhealthy")
    except Exception as e:
        logger.error(f"Health check failed: {e}")
        raise HTTPException(status_code=503, detail="Service unavailable")


@router.get("/readiness")
async def readiness_check(request: Request):
    """Readiness check endpoint"""
    try:
        cache = get_cache(request)
        flags = await cache.get_all_flags()
        flag_count = len(flags)
        
        return {
            "status": "ready",
            "flag_count": flag_count,
            "timestamp": datetime.now(timezone.utc)
        }
    except Exception as e:
        logger.error(f"Readiness check failed: {e}")
        raise HTTPException(status_code=503, detail="Service not ready")


@router.post("/flags/evaluate", response_model=FlagEvaluationResponse)
async def evaluate_flags(
    request_data: FlagEvaluationRequest,
    request: Request
):
    """Evaluate multiple feature flags"""
    try:
        evaluator = get_evaluator(request)
        
        # Merge request context with provided context
        request_context = get_request_context(request)
        evaluation_context = request_data.context.dict()
        
        # Request context takes precedence
        merged_context = {**evaluation_context, **request_context}
        
        # Add custom attributes
        if evaluation_context.get('custom_attributes'):
            merged_context.update(evaluation_context['custom_attributes'])
        
        logger.info(f"Evaluating flags {request_data.flags} with context: {merged_context}")
        
        # Evaluate flags
        results = await evaluator.evaluate_flags(request_data.flags, merged_context)
        
        return FlagEvaluationResponse(
            flags=results,
            evaluated_at=datetime.now(timezone.utc),
            cache_hit=True
        )
        
    except Exception as e:
        logger.error(f"Error evaluating flags: {e}")
        raise HTTPException(status_code=500, detail="Flag evaluation failed")


@router.get("/flags/{flag_key}/evaluate")
async def evaluate_single_flag(
    flag_key: str,
    request: Request
):
    """Evaluate a single feature flag"""
    try:
        evaluator = get_evaluator(request)
        
        # Get context from request
        context = get_request_context(request)
        
        logger.info(f"Evaluating flag {flag_key} with context: {context}")
        
        # Evaluate flag
        value = await evaluator.evaluate_flag(flag_key, context)
        
        if value is None:
            raise HTTPException(status_code=404, detail=f"Flag '{flag_key}' not found")
        
        return {
            "flag": flag_key,
            "value": value,
            "evaluated_at": datetime.now(timezone.utc),
            "context": context
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error evaluating flag {flag_key}: {e}")
        raise HTTPException(status_code=500, detail="Flag evaluation failed")


@router.get("/flags/user", response_model=FlagEvaluationResponse)
async def get_user_flags(request: Request):
    """Get all applicable flags for current user context"""
    try:
        evaluator = get_evaluator(request)
        
        # Get context from request
        context = get_request_context(request)
        
        logger.info(f"Getting user flags with context: {context}")
        
        # Get all user flags
        results = await evaluator.get_user_flags(context)
        
        return FlagEvaluationResponse(
            flags=results,
            evaluated_at=datetime.now(timezone.utc),
            cache_hit=True
        )
        
    except Exception as e:
        logger.error(f"Error getting user flags: {e}")
        raise HTTPException(status_code=500, detail="Failed to get user flags")


@router.get("/flags", response_model=List[FlagDefinitionResponse])
async def list_flags(
    request: Request,
    tags: Optional[str] = None,
    enabled: Optional[bool] = None
):
    """List all feature flags with optional filtering"""
    try:
        cache = get_cache(request)
        flags = await cache.get_all_flags()
        results = []
        
        tag_filter = tags.split(',') if tags else None
        
        for flag in flags.values():
            # Apply filters
            if enabled is not None and flag.enabled != enabled:
                continue
            
            if tag_filter and not any(tag in flag.tags for tag in tag_filter):
                continue
            
            results.append(FlagDefinitionResponse(
                key=flag.key,
                name=flag.name,
                description=flag.description,
                flag_type=flag.flag_type,
                enabled=flag.enabled,
                default_value=flag.default_value,
                tags=flag.tags,
                created_at=flag.created_at,
                updated_at=flag.updated_at
            ))
        
        return results
        
    except Exception as e:
        logger.error(f"Error listing flags: {e}")
        raise HTTPException(status_code=500, detail="Failed to list flags")


@router.get("/flags/{flag_key}", response_model=FlagDefinitionResponse)
async def get_flag_definition(flag_key: str, request: Request):
    """Get detailed information about a specific flag"""
    try:
        cache = get_cache(request)
        flag = await cache.get_flag(flag_key)
        
        if not flag:
            raise HTTPException(status_code=404, detail=f"Flag '{flag_key}' not found")
        
        return FlagDefinitionResponse(
            key=flag.key,
            name=flag.name,
            description=flag.description,
            flag_type=flag.flag_type,
            enabled=flag.enabled,
            default_value=flag.default_value,
            tags=flag.tags,
            created_at=flag.created_at,
            updated_at=flag.updated_at
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting flag {flag_key}: {e}")
        raise HTTPException(status_code=500, detail="Failed to get flag")


@router.post("/flags/refresh")
async def refresh_flags_cache(request: Request):
    """Manually refresh the flags cache"""
    try:
        cache = get_cache(request)
        await cache.refresh_flags()
        flag_count = len(await cache.get_all_flags())
        
        return {
            "status": "refreshed",
            "flag_count": flag_count,
            "timestamp": datetime.now(timezone.utc)
        }
        
    except Exception as e:
        logger.error(f"Error refreshing cache: {e}")
        raise HTTPException(status_code=500, detail="Failed to refresh cache")


# Feature flag specific endpoints
@router.get("/config/chat")
async def get_chat_config(request: Request):
    """Get chat-related configuration"""
    try:
        evaluator = get_evaluator(request)
        context = get_request_context(request)
        
        chat_flags = [
            'chat.streaming',
            'provider.order'
        ]
        
        results = await evaluator.evaluate_flags(chat_flags, context)
        
        return {
            "streaming_enabled": results.get('chat.streaming', False),
            "provider_order": results.get('provider.order', ['openai', 'anthropic']),
            "context": context
        }
        
    except Exception as e:
        logger.error(f"Error getting chat config: {e}")
        raise HTTPException(status_code=500, detail="Failed to get chat config")


@router.get("/config/games")
async def get_games_config(request: Request):
    """Get games-related configuration"""
    try:
        evaluator = get_evaluator(request)
        context = get_request_context(request)
        
        game_flags = [
            'game.enabled'
        ]
        
        results = await evaluator.evaluate_flags(game_flags, context)
        
        return {
            "games_enabled": results.get('game.enabled', False),
            "context": context
        }
        
    except Exception as e:
        logger.error(f"Error getting games config: {e}")
        raise HTTPException(status_code=500, detail="Failed to get games config")


@router.get("/config/slp")
async def get_slp_config(request: Request):
    """Get Speech-Language Pathology configuration"""
    try:
        evaluator = get_evaluator(request)
        context = get_request_context(request)
        
        slp_flags = [
            'slp.asrProvider'
        ]
        
        results = await evaluator.evaluate_flags(slp_flags, context)
        
        return {
            "asr_provider": results.get('slp.asrProvider', 'whisper'),
            "context": context
        }
        
    except Exception as e:
        logger.error(f"Error getting SLP config: {e}")
        raise HTTPException(status_code=500, detail="Failed to get SLP config")


@router.get("/config/sel")
async def get_sel_config(request: Request):
    """Get Social-Emotional Learning configuration"""
    try:
        evaluator = get_evaluator(request)
        context = get_request_context(request)
        
        sel_flags = [
            'sel.enabled'
        ]
        
        results = await evaluator.evaluate_flags(sel_flags, context)
        
        return {
            "sel_enabled": results.get('sel.enabled', False),
            "context": context
        }
        
    except Exception as e:
        logger.error(f"Error getting SEL config: {e}")
        raise HTTPException(status_code=500, detail="Failed to get SEL config")


# Debug endpoints (only in development)
@router.get("/debug/context")
async def debug_context(request: Request):
    """Debug endpoint to see request context"""
    context = get_request_context(request)
    return {
        "context": context,
        "headers": dict(request.headers),
        "query_params": dict(request.query_params)
    }


@router.get("/debug/flags")
async def debug_flags(request: Request):
    """Debug endpoint to see all flags"""
    try:
        cache = get_cache(request)
        flags = await cache.get_all_flags()
        return {
            "flag_count": len(flags),
            "flags": {
                key: {
                    "name": flag.name,
                    "enabled": flag.enabled,
                    "type": flag.flag_type,
                    "targeting_rules": len(flag.targeting_rules),
                    "has_rollout": flag.rollout_strategy is not None
                }
                for key, flag in flags.items()
            }
        }
    except Exception as e:
        logger.error(f"Error in debug flags: {e}")
        raise HTTPException(status_code=500, detail="Debug failed")
