"""
Event System for SCIM Operations

Provides event emission for user provisioning, group management, and seat allocation.
"""

import asyncio
import json
from datetime import datetime
from typing import Dict, Any, Optional
from uuid import UUID

# In a real implementation, this would integrate with your event bus
# (e.g., Kafka, RabbitMQ, AWS EventBridge, etc.)


class SCIMEventEmitter:
    """Event emitter for SCIM operations."""
    
    def __init__(self):
        self.subscribers = {}
    
    async def emit(self, event_type: str, tenant_id: str, data: Dict[str, Any]):
        """
        Emit a SCIM event.
        
        Args:
            event_type: Type of event (e.g., "user.provisioned")
            tenant_id: Tenant ID
            data: Event data
        """
        
        event = {
            "event_type": event_type,
            "tenant_id": tenant_id,
            "timestamp": datetime.utcnow().isoformat(),
            "data": data
        }
        
        # In production, send to event bus
        print(f"SCIM Event: {json.dumps(event, indent=2)}")
        
        # Call any registered subscribers
        if event_type in self.subscribers:
            for callback in self.subscribers[event_type]:
                try:
                    await callback(event)
                except Exception as e:
                    print(f"Error in event subscriber: {e}")
    
    def subscribe(self, event_type: str, callback):
        """Subscribe to an event type."""
        if event_type not in self.subscribers:
            self.subscribers[event_type] = []
        self.subscribers[event_type].append(callback)


# Global event emitter
scim_events = SCIMEventEmitter()


# User Events
async def emit_user_provisioned(tenant_id: str, user_id: str, user_data: Dict[str, Any]):
    """Emit user provisioned event."""
    await scim_events.emit("user.provisioned", tenant_id, {
        "user_id": user_id,
        "user_data": user_data
    })


async def emit_user_deprovisioned(tenant_id: str, user_id: str):
    """Emit user deprovisioned event."""
    await scim_events.emit("user.deprovisioned", tenant_id, {
        "user_id": user_id
    })


async def emit_user_updated(tenant_id: str, user_id: str, changes: Dict[str, Any]):
    """Emit user updated event."""
    await scim_events.emit("user.updated", tenant_id, {
        "user_id": user_id,
        "changes": changes
    })


async def emit_user_activated(tenant_id: str, user_id: str):
    """Emit user activated event."""
    await scim_events.emit("user.activated", tenant_id, {
        "user_id": user_id
    })


async def emit_user_deactivated(tenant_id: str, user_id: str):
    """Emit user deactivated event."""
    await scim_events.emit("user.deactivated", tenant_id, {
        "user_id": user_id
    })


# Group Events
async def emit_group_created(tenant_id: str, group_id: str, group_data: Dict[str, Any]):
    """Emit group created event."""
    await scim_events.emit("group.created", tenant_id, {
        "group_id": group_id,
        "group_data": group_data
    })


async def emit_group_deleted(tenant_id: str, group_id: str):
    """Emit group deleted event."""
    await scim_events.emit("group.deleted", tenant_id, {
        "group_id": group_id
    })


async def emit_group_updated(tenant_id: str, group_id: str, changes: Dict[str, Any]):
    """Emit group updated event."""
    await scim_events.emit("group.updated", tenant_id, {
        "group_id": group_id,
        "changes": changes
    })


async def emit_user_added_to_group(tenant_id: str, user_id: str, group_id: str):
    """Emit user added to group event."""
    await scim_events.emit("group.member.added", tenant_id, {
        "user_id": user_id,
        "group_id": group_id
    })


async def emit_user_removed_from_group(tenant_id: str, user_id: str, group_id: str):
    """Emit user removed from group event."""
    await scim_events.emit("group.member.removed", tenant_id, {
        "user_id": user_id,
        "group_id": group_id
    })


# Seat Management Events
async def emit_seat_allocated(tenant_id: str, user_id: str, seat_type: str):
    """Emit seat allocated event."""
    await scim_events.emit("seat.allocated", tenant_id, {
        "user_id": user_id,
        "seat_type": seat_type
    })


async def emit_seat_deallocated(tenant_id: str, user_id: str, seat_type: str):
    """Emit seat deallocated event."""
    await scim_events.emit("seat.deallocated", tenant_id, {
        "user_id": user_id,
        "seat_type": seat_type
    })


async def emit_seat_limit_reached(tenant_id: str, limit: int):
    """Emit seat limit reached event."""
    await scim_events.emit("seat.limit.reached", tenant_id, {
        "limit": limit
    })


# Audit Events
async def emit_scim_operation_audit(
    tenant_id: str,
    operation_type: str,
    resource_type: str,
    resource_id: Optional[str] = None,
    actor: Optional[str] = None,
    client_ip: Optional[str] = None,
    success: bool = True,
    error_message: Optional[str] = None
):
    """Emit SCIM operation audit event."""
    await scim_events.emit("scim.operation.audit", tenant_id, {
        "operation_type": operation_type,
        "resource_type": resource_type,
        "resource_id": resource_id,
        "actor": actor,
        "client_ip": client_ip,
        "success": success,
        "error_message": error_message
    })


# Error Events
async def emit_scim_error(
    tenant_id: str,
    error_type: str,
    error_message: str,
    context: Optional[Dict[str, Any]] = None
):
    """Emit SCIM error event."""
    await scim_events.emit("scim.error", tenant_id, {
        "error_type": error_type,
        "error_message": error_message,
        "context": context or {}
    })


# SIS Integration Events (for later SIS bridge service)
async def emit_sis_sync_started(tenant_id: str, provider: str, sync_type: str):
    """Emit SIS sync started event."""
    await scim_events.emit("sis.sync.started", tenant_id, {
        "provider": provider,
        "sync_type": sync_type
    })


async def emit_sis_sync_completed(tenant_id: str, provider: str, sync_type: str, stats: Dict[str, Any]):
    """Emit SIS sync completed event."""
    await scim_events.emit("sis.sync.completed", tenant_id, {
        "provider": provider,
        "sync_type": sync_type,
        "stats": stats
    })


async def emit_sis_sync_failed(tenant_id: str, provider: str, sync_type: str, error: str):
    """Emit SIS sync failed event."""
    await scim_events.emit("sis.sync.failed", tenant_id, {
        "provider": provider,
        "sync_type": sync_type,
        "error": error
    })


async def emit_sis_user_mapped(tenant_id: str, user_id: str, sis_user_id: str, provider: str):
    """Emit SIS user mapped event."""
    await scim_events.emit("sis.user.mapped", tenant_id, {
        "user_id": user_id,
        "sis_user_id": sis_user_id,
        "provider": provider
    })


async def emit_sis_enrollment_created(tenant_id: str, user_id: str, course_id: str, provider: str):
    """Emit SIS enrollment created event."""
    await scim_events.emit("sis.enrollment.created", tenant_id, {
        "user_id": user_id,
        "course_id": course_id,
        "provider": provider
    })


# Event Subscribers for Business Logic
async def handle_user_provisioned(event: Dict[str, Any]):
    """Handle user provisioned event."""
    # Example: Create user profile, send welcome email, etc.
    tenant_id = event["tenant_id"]
    user_data = event["data"]["user_data"]
    print(f"Creating user profile for tenant {tenant_id}: {user_data.get('userName')}")


async def handle_seat_allocated(event: Dict[str, Any]):
    """Handle seat allocated event."""
    # Example: Update billing, track usage, etc.
    tenant_id = event["tenant_id"]
    seat_type = event["data"]["seat_type"]
    print(f"Seat allocated for tenant {tenant_id}: {seat_type}")


async def handle_group_member_added(event: Dict[str, Any]):
    """Handle user added to group event."""
    # Example: Update permissions, sync to external systems, etc.
    tenant_id = event["tenant_id"]
    user_id = event["data"]["user_id"]
    group_id = event["data"]["group_id"]
    print(f"User {user_id} added to group {group_id} in tenant {tenant_id}")


# Register default subscribers
scim_events.subscribe("user.provisioned", handle_user_provisioned)
scim_events.subscribe("seat.allocated", handle_seat_allocated)
scim_events.subscribe("group.member.added", handle_group_member_added)
