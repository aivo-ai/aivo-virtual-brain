"""
Provider Management Routes

Handles CRUD operations for SIS provider configurations.
"""

from datetime import datetime
from typing import List, Dict, Any
from uuid import UUID
from fastapi import APIRouter, HTTPException, Depends
from fastapi.responses import JSONResponse
from sqlalchemy.orm import Session
from pydantic import BaseModel, Field

from ..database import get_db, TenantSISProvider, SyncJob
from ..providers import get_provider, AVAILABLE_PROVIDERS
from ..vault_client import VaultClient
from ..config import get_settings

router = APIRouter()
settings = get_settings()


class ProviderConfigRequest(BaseModel):
    """Request model for provider configuration."""
    provider: str = Field(..., description="Provider type (clever, classlink)")
    config: Dict[str, Any] = Field(..., description="Provider configuration")
    enabled: bool = Field(default=True, description="Whether provider is enabled")
    webhook_enabled: bool = Field(default=False, description="Whether webhooks are enabled")
    webhook_secret: str = Field(default=None, description="Webhook verification secret")
    auto_sync: bool = Field(default=False, description="Auto sync on webhook events")
    sync_interval: int = Field(default=3600, description="Sync interval in seconds")
    use_vault: bool = Field(default=False, description="Store credentials in Vault")
    vault_path: str = Field(default=None, description="Vault path for credentials")


class ProviderConfigResponse(BaseModel):
    """Response model for provider configuration."""
    id: str
    tenant_id: str
    provider: str
    enabled: bool
    webhook_enabled: bool
    webhook_secret: str = None
    auto_sync: bool
    sync_interval: int
    vault_path: str = None
    created_at: str
    updated_at: str
    last_sync: str = None
    sync_status: str = None


@router.get("/{tenant_id}")
async def list_providers(
    tenant_id: UUID,
    db: Session = Depends(get_db)
) -> List[ProviderConfigResponse]:
    """List all SIS providers for a tenant."""
    
    try:
        providers = db.query(TenantSISProvider).filter(
            TenantSISProvider.tenant_id == tenant_id
        ).order_by(TenantSISProvider.created_at.desc()).all()
        
        provider_list = []
        for provider in providers:
            # Get last sync job
            last_sync_job = db.query(SyncJob).filter(
                SyncJob.provider_id == provider.id
            ).order_by(SyncJob.created_at.desc()).first()
            
            provider_info = ProviderConfigResponse(
                id=str(provider.id),
                tenant_id=str(provider.tenant_id),
                provider=provider.provider,
                enabled=provider.enabled,
                webhook_enabled=provider.webhook_enabled,
                webhook_secret=provider.webhook_secret,
                auto_sync=provider.auto_sync,
                sync_interval=provider.sync_interval,
                vault_path=provider.credentials_path,
                created_at=provider.created_at.isoformat(),
                updated_at=provider.updated_at.isoformat(),
                last_sync=last_sync_job.created_at.isoformat() if last_sync_job else None,
                sync_status=last_sync_job.status if last_sync_job else None
            )
            
            provider_list.append(provider_info)
        
        return provider_list
    
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/{tenant_id}")
async def create_provider(
    tenant_id: UUID,
    config: ProviderConfigRequest,
    db: Session = Depends(get_db)
) -> ProviderConfigResponse:
    """Create a new SIS provider configuration."""
    
    try:
        # Validate provider type
        if config.provider not in AVAILABLE_PROVIDERS:
            raise HTTPException(
                status_code=400,
                detail=f"Unsupported provider type: {config.provider}. "
                       f"Available providers: {', '.join(AVAILABLE_PROVIDERS.keys())}"
            )
        
        # Check for existing provider of same type
        existing = db.query(TenantSISProvider).filter(
            TenantSISProvider.tenant_id == tenant_id,
            TenantSISProvider.provider == config.provider
        ).first()
        
        if existing:
            raise HTTPException(
                status_code=400,
                detail=f"Provider {config.provider} already exists for this tenant"
            )
        
        # Validate provider configuration by creating test instance
        try:
            provider_instance = get_provider(config.provider, config.config)
            await provider_instance.validate_config()
            await provider_instance.cleanup()
        except Exception as e:
            raise HTTPException(
                status_code=400,
                detail=f"Invalid provider configuration: {str(e)}"
            )
        
        # Store credentials in Vault if requested
        credentials_path = None
        stored_config = config.config.copy()
        
        if config.use_vault and settings.vault_url:
            vault_client = VaultClient()
            try:
                # Extract sensitive credentials
                sensitive_keys = ['client_secret', 'api_key', 'password', 'token']
                credentials = {}
                
                for key in sensitive_keys:
                    if key in stored_config:
                        credentials[key] = stored_config.pop(key)
                
                if credentials:
                    credentials_path = f"sis-bridge/{tenant_id}/{config.provider}"
                    await vault_client.store_secret(credentials_path, credentials)
                
                await vault_client.cleanup()
            except Exception as e:
                raise HTTPException(
                    status_code=500,
                    detail=f"Failed to store credentials in Vault: {str(e)}"
                )
        
        # Create provider configuration
        provider_config = TenantSISProvider(
            tenant_id=tenant_id,
            provider=config.provider,
            config=stored_config,
            credentials_path=credentials_path,
            enabled=config.enabled,
            webhook_enabled=config.webhook_enabled,
            webhook_secret=config.webhook_secret,
            auto_sync=config.auto_sync,
            sync_interval=config.sync_interval,
            created_at=datetime.utcnow(),
            updated_at=datetime.utcnow()
        )
        
        db.add(provider_config)
        db.commit()
        db.refresh(provider_config)
        
        return ProviderConfigResponse(
            id=str(provider_config.id),
            tenant_id=str(provider_config.tenant_id),
            provider=provider_config.provider,
            enabled=provider_config.enabled,
            webhook_enabled=provider_config.webhook_enabled,
            webhook_secret=provider_config.webhook_secret,
            auto_sync=provider_config.auto_sync,
            sync_interval=provider_config.sync_interval,
            vault_path=provider_config.credentials_path,
            created_at=provider_config.created_at.isoformat(),
            updated_at=provider_config.updated_at.isoformat(),
            last_sync=None,
            sync_status=None
        )
    
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/{tenant_id}/{provider_id}")
async def get_provider(
    tenant_id: UUID,
    provider_id: UUID,
    db: Session = Depends(get_db)
) -> ProviderConfigResponse:
    """Get a specific SIS provider configuration."""
    
    try:
        provider_config = db.query(TenantSISProvider).filter(
            TenantSISProvider.id == provider_id,
            TenantSISProvider.tenant_id == tenant_id
        ).first()
        
        if not provider_config:
            raise HTTPException(status_code=404, detail="Provider not found")
        
        # Get last sync job
        last_sync_job = db.query(SyncJob).filter(
            SyncJob.provider_id == provider_id
        ).order_by(SyncJob.created_at.desc()).first()
        
        return ProviderConfigResponse(
            id=str(provider_config.id),
            tenant_id=str(provider_config.tenant_id),
            provider=provider_config.provider,
            enabled=provider_config.enabled,
            webhook_enabled=provider_config.webhook_enabled,
            webhook_secret=provider_config.webhook_secret,
            auto_sync=provider_config.auto_sync,
            sync_interval=provider_config.sync_interval,
            vault_path=provider_config.credentials_path,
            created_at=provider_config.created_at.isoformat(),
            updated_at=provider_config.updated_at.isoformat(),
            last_sync=last_sync_job.created_at.isoformat() if last_sync_job else None,
            sync_status=last_sync_job.status if last_sync_job else None
        )
    
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.put("/{tenant_id}/{provider_id}")
async def update_provider(
    tenant_id: UUID,
    provider_id: UUID,
    config: ProviderConfigRequest,
    db: Session = Depends(get_db)
) -> ProviderConfigResponse:
    """Update an existing SIS provider configuration."""
    
    try:
        provider_config = db.query(TenantSISProvider).filter(
            TenantSISProvider.id == provider_id,
            TenantSISProvider.tenant_id == tenant_id
        ).first()
        
        if not provider_config:
            raise HTTPException(status_code=404, detail="Provider not found")
        
        # Validate provider type matches
        if config.provider != provider_config.provider:
            raise HTTPException(
                status_code=400,
                detail="Provider type cannot be changed. Delete and recreate instead."
            )
        
        # Validate new configuration
        try:
            provider_instance = get_provider(config.provider, config.config)
            await provider_instance.validate_config()
            await provider_instance.cleanup()
        except Exception as e:
            raise HTTPException(
                status_code=400,
                detail=f"Invalid provider configuration: {str(e)}"
            )
        
        # Update credentials in Vault if using Vault
        credentials_path = provider_config.credentials_path
        stored_config = config.config.copy()
        
        if config.use_vault and settings.vault_url:
            vault_client = VaultClient()
            try:
                # Extract sensitive credentials
                sensitive_keys = ['client_secret', 'api_key', 'password', 'token']
                credentials = {}
                
                for key in sensitive_keys:
                    if key in stored_config:
                        credentials[key] = stored_config.pop(key)
                
                if credentials:
                    if not credentials_path:
                        credentials_path = f"sis-bridge/{tenant_id}/{config.provider}"
                    
                    await vault_client.store_secret(credentials_path, credentials)
                
                await vault_client.cleanup()
            except Exception as e:
                raise HTTPException(
                    status_code=500,
                    detail=f"Failed to update credentials in Vault: {str(e)}"
                )
        elif not config.use_vault and credentials_path:
            # Remove from Vault if no longer using it
            vault_client = VaultClient()
            try:
                await vault_client.delete_secret(credentials_path)
                await vault_client.cleanup()
                credentials_path = None
            except Exception:
                pass  # Ignore errors when deleting from Vault
        
        # Update provider configuration
        provider_config.config = stored_config
        provider_config.credentials_path = credentials_path
        provider_config.enabled = config.enabled
        provider_config.webhook_enabled = config.webhook_enabled
        provider_config.webhook_secret = config.webhook_secret
        provider_config.auto_sync = config.auto_sync
        provider_config.sync_interval = config.sync_interval
        provider_config.updated_at = datetime.utcnow()
        
        db.commit()
        db.refresh(provider_config)
        
        # Get last sync job
        last_sync_job = db.query(SyncJob).filter(
            SyncJob.provider_id == provider_id
        ).order_by(SyncJob.created_at.desc()).first()
        
        return ProviderConfigResponse(
            id=str(provider_config.id),
            tenant_id=str(provider_config.tenant_id),
            provider=provider_config.provider,
            enabled=provider_config.enabled,
            webhook_enabled=provider_config.webhook_enabled,
            webhook_secret=provider_config.webhook_secret,
            auto_sync=provider_config.auto_sync,
            sync_interval=provider_config.sync_interval,
            vault_path=provider_config.credentials_path,
            created_at=provider_config.created_at.isoformat(),
            updated_at=provider_config.updated_at.isoformat(),
            last_sync=last_sync_job.created_at.isoformat() if last_sync_job else None,
            sync_status=last_sync_job.status if last_sync_job else None
        )
    
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.delete("/{tenant_id}/{provider_id}")
async def delete_provider(
    tenant_id: UUID,
    provider_id: UUID,
    db: Session = Depends(get_db)
):
    """Delete an SIS provider configuration."""
    
    try:
        provider_config = db.query(TenantSISProvider).filter(
            TenantSISProvider.id == provider_id,
            TenantSISProvider.tenant_id == tenant_id
        ).first()
        
        if not provider_config:
            raise HTTPException(status_code=404, detail="Provider not found")
        
        # Remove credentials from Vault if stored there
        if provider_config.credentials_path and settings.vault_url:
            vault_client = VaultClient()
            try:
                await vault_client.delete_secret(provider_config.credentials_path)
                await vault_client.cleanup()
            except Exception:
                pass  # Ignore errors when deleting from Vault
        
        # Delete provider configuration (cascade will handle related records)
        db.delete(provider_config)
        db.commit()
        
        return {"message": "Provider deleted successfully"}
    
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/{tenant_id}/{provider_id}/test")
async def test_provider_connection(
    tenant_id: UUID,
    provider_id: UUID,
    db: Session = Depends(get_db)
):
    """Test connection to SIS provider."""
    
    try:
        provider_config = db.query(TenantSISProvider).filter(
            TenantSISProvider.id == provider_id,
            TenantSISProvider.tenant_id == tenant_id
        ).first()
        
        if not provider_config:
            raise HTTPException(status_code=404, detail="Provider not found")
        
        # Get provider credentials
        vault_client = VaultClient() if settings.vault_url else None
        
        if vault_client and provider_config.credentials_path:
            credentials = await vault_client.get_secret(provider_config.credentials_path)
            credentials = {**provider_config.config, **credentials}
        else:
            credentials = provider_config.config
        
        # Test provider connection
        sis_provider = get_provider(provider_config.provider, credentials)
        
        try:
            test_result = await sis_provider.test_connection()
            await sis_provider.cleanup()
            
            if vault_client:
                await vault_client.cleanup()
            
            return {
                "status": "success" if test_result else "failed",
                "message": "Connection test successful" if test_result else "Connection test failed",
                "provider": provider_config.provider
            }
        
        except Exception as e:
            await sis_provider.cleanup()
            if vault_client:
                await vault_client.cleanup()
            
            return {
                "status": "failed",
                "message": f"Connection test failed: {str(e)}",
                "provider": provider_config.provider
            }
    
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/available")
async def list_available_providers():
    """List all available SIS provider types."""
    
    provider_list = []
    for provider_name, provider_class in AVAILABLE_PROVIDERS.items():
        provider_info = {
            "name": provider_name,
            "description": getattr(provider_class, '__doc__', 'No description available'),
            "required_config": getattr(provider_class, 'REQUIRED_CONFIG', []),
            "optional_config": getattr(provider_class, 'OPTIONAL_CONFIG', []),
            "webhook_support": getattr(provider_class, 'WEBHOOK_SUPPORT', False)
        }
        provider_list.append(provider_info)
    
    return {"providers": provider_list}
