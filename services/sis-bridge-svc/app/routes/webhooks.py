"""
Webhook Handlers for SIS Providers

Handles real-time webhook notifications from Clever and ClassLink.
"""

import hashlib
import hmac
import json
from datetime import datetime
from typing import Dict, Any
from uuid import UUID
from fastapi import APIRouter, Request, HTTPException, Header, Depends
from fastapi.responses import JSONResponse
from sqlalchemy.orm import Session

from ..database import get_db, TenantSISProvider, WebhookEvent, SyncJob
from ..providers import get_provider
from ..scheduler import SyncScheduler
from ..vault_client import VaultClient
from ..config import get_settings

router = APIRouter()
settings = get_settings()


def verify_webhook_signature(payload: bytes, signature: str, secret: str) -> bool:
    """Verify webhook signature."""
    
    try:
        expected_signature = hmac.new(
            secret.encode('utf-8'),
            payload,
            hashlib.sha256
        ).hexdigest()
        
        # Remove 'sha256=' prefix if present
        if signature.startswith('sha256='):
            signature = signature[7:]
        
        return hmac.compare_digest(expected_signature, signature)
    except Exception:
        return False


async def get_provider_by_webhook_path(tenant_id: UUID, provider_name: str, db: Session) -> TenantSISProvider:
    """Get SIS provider configuration from webhook path."""
    
    provider_config = db.query(TenantSISProvider).filter(
        TenantSISProvider.tenant_id == tenant_id,
        TenantSISProvider.provider == provider_name,
        TenantSISProvider.enabled == True,
        TenantSISProvider.webhook_enabled == True
    ).first()
    
    if not provider_config:
        raise HTTPException(
            status_code=404,
            detail=f"No enabled {provider_name} provider found for tenant"
        )
    
    return provider_config


@router.post("/clever/{tenant_id}")
async def clever_webhook(
    tenant_id: UUID,
    request: Request,
    x_clever_signature: str = Header(None),
    db: Session = Depends(get_db)
):
    """Handle Clever webhook events."""
    
    try:
        # Get provider configuration
        provider_config = await get_provider_by_webhook_path(tenant_id, "clever", db)
        
        # Read raw payload
        payload = await request.body()
        
        # Verify webhook signature
        if x_clever_signature and provider_config.webhook_secret:
            if not verify_webhook_signature(payload, x_clever_signature, provider_config.webhook_secret):
                raise HTTPException(status_code=401, detail="Invalid webhook signature")
        
        # Parse webhook payload
        try:
            webhook_data = json.loads(payload)
        except json.JSONDecodeError:
            raise HTTPException(status_code=400, detail="Invalid JSON payload")
        
        # Extract event information
        event_type = webhook_data.get('type', 'unknown')
        event_data = webhook_data.get('data', {})
        
        # Store webhook event
        webhook_event = WebhookEvent(
            provider_id=provider_config.id,
            tenant_id=tenant_id,
            event_type=event_type,
            event_data=webhook_data,
            headers=dict(request.headers),
            created_at=datetime.utcnow()
        )
        
        db.add(webhook_event)
        db.commit()
        db.refresh(webhook_event)
        
        # Process webhook if auto-processing is enabled
        if provider_config.auto_sync:
            await process_webhook_event(webhook_event.id, db, request)
        
        return JSONResponse(
            content={"status": "received", "event_id": str(webhook_event.id)},
            status_code=200
        )
    
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Webhook processing failed: {str(e)}")


@router.post("/classlink/{tenant_id}")
async def classlink_webhook(
    tenant_id: UUID,
    request: Request,
    x_classlink_signature: str = Header(None),
    db: Session = Depends(get_db)
):
    """Handle ClassLink webhook events."""
    
    try:
        # Get provider configuration
        provider_config = await get_provider_by_webhook_path(tenant_id, "classlink", db)
        
        # Read raw payload
        payload = await request.body()
        
        # Verify webhook signature
        if x_classlink_signature and provider_config.webhook_secret:
            if not verify_webhook_signature(payload, x_classlink_signature, provider_config.webhook_secret):
                raise HTTPException(status_code=401, detail="Invalid webhook signature")
        
        # Parse webhook payload
        try:
            webhook_data = json.loads(payload)
        except json.JSONDecodeError:
            raise HTTPException(status_code=400, detail="Invalid JSON payload")
        
        # Extract event information
        event_type = webhook_data.get('eventType', 'unknown')
        
        # Store webhook event
        webhook_event = WebhookEvent(
            provider_id=provider_config.id,
            tenant_id=tenant_id,
            event_type=event_type,
            event_data=webhook_data,
            headers=dict(request.headers),
            created_at=datetime.utcnow()
        )
        
        db.add(webhook_event)
        db.commit()
        db.refresh(webhook_event)
        
        # Process webhook if auto-processing is enabled
        if provider_config.auto_sync:
            await process_webhook_event(webhook_event.id, db, request)
        
        return JSONResponse(
            content={"status": "received", "event_id": str(webhook_event.id)},
            status_code=200
        )
    
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Webhook processing failed: {str(e)}")


async def process_webhook_event(event_id: UUID, db: Session, request: Request):
    """Process a webhook event by triggering targeted sync."""
    
    try:
        # Get webhook event
        webhook_event = db.query(WebhookEvent).filter(WebhookEvent.id == event_id).first()
        if not webhook_event or webhook_event.processed:
            return
        
        # Get provider configuration
        provider_config = db.query(TenantSISProvider).filter(
            TenantSISProvider.id == webhook_event.provider_id
        ).first()
        
        if not provider_config:
            return
        
        # Get scheduler from app state
        scheduler = getattr(request.app.state, 'scheduler', None)
        if not scheduler:
            print("Sync scheduler not available for webhook processing")
            return
        
        # Get provider credentials and initialize SIS provider
        vault_client = VaultClient() if settings.vault_url else None
        
        if vault_client and provider_config.credentials_path:
            credentials = await vault_client.get_secret(provider_config.credentials_path)
            credentials = {**provider_config.config, **credentials}
        else:
            credentials = provider_config.config
        
        sis_provider = get_provider(provider_config.provider, credentials)
        
        # Get resource IDs that need to be synced from webhook
        resource_ids = await sis_provider.handle_webhook(
            webhook_event.event_type,
            webhook_event.event_data
        )
        
        if resource_ids:
            # Start targeted sync for affected resources
            # For simplicity, trigger a full incremental sync
            # In a full implementation, you could implement targeted resource sync
            job_id = await scheduler.schedule_immediate_sync(
                provider_id=provider_config.id,
                sync_type="webhook"
            )
            
            # Mark webhook as processed and link to sync job
            webhook_event.processed = True
            webhook_event.processed_at = datetime.utcnow()
            webhook_event.sync_job_id = job_id
            db.commit()
            
            print(f"Triggered sync job {job_id} for webhook event {event_id}")
        else:
            # Mark as processed even if no sync needed
            webhook_event.processed = True
            webhook_event.processed_at = datetime.utcnow()
            db.commit()
        
        # Cleanup
        await sis_provider.cleanup()
        if vault_client:
            await vault_client.cleanup()
    
    except Exception as e:
        # Mark webhook as failed
        webhook_event.error_message = str(e)
        webhook_event.retry_count = webhook_event.retry_count + 1
        db.commit()
        
        print(f"Error processing webhook event {event_id}: {e}")


@router.get("/events/{tenant_id}")
async def list_webhook_events(
    tenant_id: UUID,
    provider_id: UUID = None,
    limit: int = 50,
    db: Session = Depends(get_db)
):
    """List recent webhook events for tenant."""
    
    try:
        query = db.query(WebhookEvent).filter(WebhookEvent.tenant_id == tenant_id)
        
        if provider_id:
            query = query.filter(WebhookEvent.provider_id == provider_id)
        
        events = query.order_by(WebhookEvent.created_at.desc()).limit(limit).all()
        
        event_list = []
        for event in events:
            event_info = {
                "id": str(event.id),
                "provider_id": str(event.provider_id),
                "event_type": event.event_type,
                "processed": event.processed,
                "created_at": event.created_at.isoformat(),
                "processed_at": event.processed_at.isoformat() if event.processed_at else None,
                "sync_job_id": str(event.sync_job_id) if event.sync_job_id else None,
                "error_message": event.error_message,
                "retry_count": event.retry_count
            }
            event_list.append(event_info)
        
        return {"events": event_list}
    
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/events/{event_id}/retry")
async def retry_webhook_event(
    event_id: UUID,
    request: Request,
    db: Session = Depends(get_db)
):
    """Retry processing a failed webhook event."""
    
    try:
        webhook_event = db.query(WebhookEvent).filter(WebhookEvent.id == event_id).first()
        
        if not webhook_event:
            raise HTTPException(status_code=404, detail="Webhook event not found")
        
        if webhook_event.processed and not webhook_event.error_message:
            return {"message": "Event already processed successfully"}
        
        # Reset processing status
        webhook_event.processed = False
        webhook_event.error_message = None
        webhook_event.processed_at = None
        db.commit()
        
        # Process the event
        await process_webhook_event(event_id, db, request)
        
        return {"message": "Event reprocessing initiated"}
    
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
