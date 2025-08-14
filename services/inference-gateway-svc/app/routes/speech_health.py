"""
Health and status endpoints for speech services.
"""

from fastapi import APIRouter, HTTPException
from typing import Dict, Any, List
import logging

from ..speech.config import get_speech_config_manager, initialize_speech_matrix


logger = logging.getLogger(__name__)
router = APIRouter(prefix="/speech", tags=["speech"])


@router.get("/health")
async def get_speech_health() -> Dict[str, Any]:
    """Get health status of all speech providers."""
    try:
        config_manager = get_speech_config_manager()
        matrix = config_manager.matrix
        
        # Initialize matrix if not already done
        if not matrix.providers:
            matrix = initialize_speech_matrix()
        
        health_status = await matrix.get_health_status()
        return health_status
        
    except Exception as e:
        logger.error(f"Speech health check failed: {e}")
        raise HTTPException(status_code=500, detail=f"Health check failed: {str(e)}")


@router.get("/locales")
async def get_supported_locales() -> Dict[str, Any]:
    """Get all supported locales and their speech capabilities."""
    try:
        config_manager = get_speech_config_manager()
        
        # Get all locale information
        locales_info = {}
        for locale_code in config_manager.get_supported_locales():
            locale_info = config_manager.get_locale_info(locale_code)
            if locale_info:
                locales_info[locale_code] = {
                    "code": locale_info.get("code", locale_code),
                    "display_name": locale_info.get("display_name", locale_code),
                    "native_name": locale_info.get("native_name", locale_code),
                    "rtl": locale_info.get("rtl", False),
                    "region": locale_info.get("region", ""),
                    "status": locale_info.get("status", "unknown"),
                    "speech_support": locale_info.get("speech_support", {}),
                    "educational_subjects": locale_info.get("educational_subjects", [])
                }
        
        return {
            "supported_locales": locales_info,
            "rtl_locales": config_manager.get_rtl_locales(),
            "total_locales": len(locales_info),
            "locale_groups": {
                "tier_1": [code for code, info in locales_info.items() if info.get("status") == "active" and len(info.get("speech_support", {}).get("asr", [])) >= 2],
                "tier_2": [code for code, info in locales_info.items() if info.get("status") == "beta"],
                "experimental": [code for code, info in locales_info.items() if info.get("status") == "experimental"]
            }
        }
        
    except Exception as e:
        logger.error(f"Failed to get locales: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to get locales: {str(e)}")


@router.get("/providers")
async def get_speech_providers() -> Dict[str, Any]:
    """Get information about available speech providers."""
    try:
        config_manager = get_speech_config_manager()
        provider_matrix = config_manager.get_provider_matrix()
        
        providers_info = {}
        for provider_name, provider_config in provider_matrix.get("providers", {}).items():
            providers_info[provider_name] = {
                "name": provider_config.get("name", provider_name),
                "priority": provider_config.get("priority", 999),
                "capabilities": provider_config.get("capabilities", []),
                "supported_locales": provider_config.get("supported_locales", []),
                "quality_score": provider_config.get("quality_score", 0),
                "rate_limits": provider_config.get("rate_limits", {})
            }
        
        return {
            "providers": providers_info,
            "fallback_chains": provider_matrix.get("fallback_chains", {}),
            "total_providers": len(providers_info)
        }
        
    except Exception as e:
        logger.error(f"Failed to get providers: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to get providers: {str(e)}")


@router.get("/matrix")
async def get_speech_matrix() -> Dict[str, Any]:
    """Get the complete speech provider matrix with supported pairs."""
    try:
        config_manager = get_speech_config_manager()
        
        # Build speech pairs matrix
        speech_pairs = {}
        locales_info = config_manager.config_data.get("supported_locales", {})
        
        for locale_code, locale_info in locales_info.items():
            speech_support = locale_info.get("speech_support", {})
            asr_providers = speech_support.get("asr", [])
            tts_providers = speech_support.get("tts", [])
            
            speech_pairs[locale_code] = {
                "locale_info": {
                    "display_name": locale_info.get("display_name", locale_code),
                    "native_name": locale_info.get("native_name", locale_code),
                    "rtl": locale_info.get("rtl", False),
                    "status": locale_info.get("status", "unknown")
                },
                "asr_providers": asr_providers,
                "tts_providers": tts_providers,
                "full_speech_support": len(asr_providers) > 0 and len(tts_providers) > 0,
                "provider_count": len(set(asr_providers + tts_providers)),
                "primary_provider": asr_providers[0] if asr_providers else None,
                "fallback_available": len(asr_providers) > 1 or len(tts_providers) > 1
            }
        
        # Get fallback chains
        fallback_chains = config_manager.get_fallback_chains()
        
        return {
            "speech_pairs": speech_pairs,
            "fallback_chains": fallback_chains,
            "provider_matrix": config_manager.get_provider_matrix(),
            "summary": {
                "total_locales": len(speech_pairs),
                "full_support_locales": len([p for p in speech_pairs.values() if p["full_speech_support"]]),
                "asr_only_locales": len([p for p in speech_pairs.values() if len(p["asr_providers"]) > 0 and len(p["tts_providers"]) == 0]),
                "tts_only_locales": len([p for p in speech_pairs.values() if len(p["tts_providers"]) > 0 and len(p["asr_providers"]) == 0])
            }
        }
        
    except Exception as e:
        logger.error(f"Failed to get speech matrix: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to get speech matrix: {str(e)}")


@router.get("/locale/{locale_code}")
async def get_locale_details(locale_code: str) -> Dict[str, Any]:
    """Get detailed information about a specific locale."""
    try:
        config_manager = get_speech_config_manager()
        locale_info = config_manager.get_locale_info(locale_code)
        
        if not locale_info:
            raise HTTPException(status_code=404, detail=f"Locale '{locale_code}' not found")
        
        # Get providers for this locale
        speech_support = locale_info.get("speech_support", {})
        asr_providers = speech_support.get("asr", [])
        tts_providers = speech_support.get("tts", [])
        
        # Get fallback chains for this locale
        fallback_chains = config_manager.get_fallback_chains()
        asr_fallback = fallback_chains.get("asr", {}).get(locale_code, fallback_chains.get("asr", {}).get("default", []))
        tts_fallback = fallback_chains.get("tts", {}).get(locale_code, fallback_chains.get("tts", {}).get("default", []))
        
        return {
            "locale": locale_info,
            "speech_capabilities": {
                "asr": {
                    "supported": len(asr_providers) > 0,
                    "providers": asr_providers,
                    "fallback_chain": asr_fallback
                },
                "tts": {
                    "supported": len(tts_providers) > 0,
                    "providers": tts_providers,
                    "fallback_chain": tts_fallback
                }
            },
            "full_speech_support": len(asr_providers) > 0 and len(tts_providers) > 0,
            "recommended_provider": asr_providers[0] if asr_providers else tts_providers[0] if tts_providers else None
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get locale details: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to get locale details: {str(e)}")


@router.post("/initialize")
async def initialize_providers() -> Dict[str, Any]:
    """Initialize speech providers (for testing/admin purposes)."""
    try:
        matrix = initialize_speech_matrix()
        
        provider_status = {}
        for provider_name, provider in matrix.providers.items():
            try:
                health = await provider.health_check()
                provider_status[provider_name] = health
            except Exception as e:
                provider_status[provider_name] = {
                    "provider": provider_name,
                    "status": "error",
                    "error": str(e)
                }
        
        return {
            "message": "Speech providers initialized",
            "providers_initialized": len(matrix.providers),
            "provider_status": provider_status
        }
        
    except Exception as e:
        logger.error(f"Failed to initialize providers: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to initialize providers: {str(e)}")
