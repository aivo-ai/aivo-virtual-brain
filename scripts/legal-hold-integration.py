#!/usr/bin/env python3
"""
Legal Hold and eDiscovery Integration Script

This script demonstrates how other services can integrate with the Legal Hold service
to check for retention overrides and handle data preservation requirements.
"""

import asyncio
import httpx
import logging
from typing import Dict, List, Optional, Any
from datetime import datetime
import json

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class LegalHoldIntegration:
    """Integration client for Legal Hold service."""
    
    def __init__(self, legal_hold_service_url: str, auth_token: str):
        self.base_url = legal_hold_service_url.rstrip('/')
        self.auth_token = auth_token
        self.headers = {
            'Authorization': f'Bearer {auth_token}',
            'Content-Type': 'application/json'
        }
    
    async def check_retention_override(
        self, 
        entity_type: str, 
        entity_id: str
    ) -> Dict[str, Any]:
        """
        Check if an entity has active retention overrides due to legal holds.
        
        Args:
            entity_type: Type of entity (e.g., 'chat', 'file', 'user_data')
            entity_id: Unique identifier for the entity
            
        Returns:
            Dict containing override status and details
        """
        async with httpx.AsyncClient() as client:
            try:
                response = await client.get(
                    f"{self.base_url}/api/v1/legal-holds/retention-override",
                    params={
                        'entity_type': entity_type,
                        'entity_id': entity_id
                    },
                    headers=self.headers
                )
                response.raise_for_status()
                return response.json()
            except httpx.HTTPError as e:
                logger.error(f"Failed to check retention override: {e}")
                return {'has_override': False, 'error': str(e)}
    
    async def notify_data_access(
        self, 
        entity_type: str, 
        entity_id: str, 
        access_type: str,
        user_id: Optional[str] = None
    ) -> bool:
        """
        Notify the legal hold service of data access for audit purposes.
        
        Args:
            entity_type: Type of entity accessed
            entity_id: Unique identifier for the entity
            access_type: Type of access ('read', 'modify', 'delete_attempt')
            user_id: User performing the access
            
        Returns:
            True if notification was successful
        """
        async with httpx.AsyncClient() as client:
            try:
                payload = {
                    'entity_type': entity_type,
                    'entity_id': entity_id,
                    'access_type': access_type,
                    'user_id': user_id,
                    'timestamp': datetime.utcnow().isoformat()
                }
                
                response = await client.post(
                    f"{self.base_url}/api/v1/audit/data-access",
                    json=payload,
                    headers=self.headers
                )
                response.raise_for_status()
                return True
            except httpx.HTTPError as e:
                logger.error(f"Failed to notify data access: {e}")
                return False
    
    async def get_active_holds_for_scope(
        self, 
        scope_type: str, 
        scope_id: str
    ) -> List[Dict[str, Any]]:
        """
        Get all active legal holds that affect a specific scope.
        
        Args:
            scope_type: Type of scope (e.g., 'tenant', 'learner', 'teacher')
            scope_id: Identifier for the scope
            
        Returns:
            List of active legal holds affecting the scope
        """
        async with httpx.AsyncClient() as client:
            try:
                response = await client.get(
                    f"{self.base_url}/api/v1/legal-holds/by-scope",
                    params={
                        'scope_type': scope_type,
                        'scope_id': scope_id,
                        'status': 'active'
                    },
                    headers=self.headers
                )
                response.raise_for_status()
                return response.json()
            except httpx.HTTPError as e:
                logger.error(f"Failed to get active holds: {e}")
                return []


class ChatServiceIntegration:
    """Example integration for Chat Service with Legal Hold checks."""
    
    def __init__(self, legal_hold_client: LegalHoldIntegration):
        self.legal_hold = legal_hold_client
    
    async def delete_message(self, message_id: str, user_id: str) -> Dict[str, Any]:
        """
        Delete a chat message with legal hold verification.
        
        Args:
            message_id: ID of the message to delete
            user_id: User requesting deletion
            
        Returns:
            Result of deletion attempt
        """
        # Check if message is under legal hold
        override_check = await self.legal_hold.check_retention_override(
            entity_type='chat_message',
            entity_id=message_id
        )
        
        if override_check.get('has_override'):
            # Log the deletion attempt
            await self.legal_hold.notify_data_access(
                entity_type='chat_message',
                entity_id=message_id,
                access_type='delete_attempt',
                user_id=user_id
            )
            
            hold_details = override_check.get('holds', [])
            return {
                'success': False,
                'reason': 'legal_hold',
                'message': 'Cannot delete message under legal hold',
                'holds': hold_details
            }
        
        # Proceed with deletion (simulated)
        logger.info(f"Deleting message {message_id}")
        
        # Log successful access
        await self.legal_hold.notify_data_access(
            entity_type='chat_message',
            entity_id=message_id,
            access_type='delete',
            user_id=user_id
        )
        
        return {
            'success': True,
            'message': 'Message deleted successfully'
        }
    
    async def export_conversation(
        self, 
        conversation_id: str, 
        export_format: str = 'json'
    ) -> Dict[str, Any]:
        """
        Export conversation data with legal hold awareness.
        
        Args:
            conversation_id: ID of conversation to export
            export_format: Format for export
            
        Returns:
            Export result with legal hold information
        """
        # Check if conversation is under legal hold
        override_check = await self.legal_hold.check_retention_override(
            entity_type='conversation',
            entity_id=conversation_id
        )
        
        export_data = {
            'conversation_id': conversation_id,
            'export_timestamp': datetime.utcnow().isoformat(),
            'format': export_format,
            'legal_hold_status': override_check.get('has_override', False)
        }
        
        if override_check.get('has_override'):
            export_data['legal_holds'] = override_check.get('holds', [])
            export_data['preservation_required'] = True
            
            # Include additional metadata for legal exports
            export_data['chain_of_custody'] = {
                'export_id': f"CHAT_EXPORT_{datetime.utcnow().strftime('%Y%m%d_%H%M%S')}",
                'legal_basis': [hold.get('legal_basis') for hold in override_check.get('holds', [])],
                'custodians': [hold.get('custodians', []) for hold in override_check.get('holds', [])]
            }
        
        # Log the export
        await self.legal_hold.notify_data_access(
            entity_type='conversation',
            entity_id=conversation_id,
            access_type='export',
            user_id='system'
        )
        
        return export_data


class PrivacyServiceIntegration:
    """Example integration for Privacy Service with Legal Hold checks."""
    
    def __init__(self, legal_hold_client: LegalHoldIntegration):
        self.legal_hold = legal_hold_client
    
    async def process_deletion_request(
        self, 
        user_id: str, 
        data_types: List[str]
    ) -> Dict[str, Any]:
        """
        Process user data deletion request with legal hold verification.
        
        Args:
            user_id: User requesting data deletion
            data_types: Types of data to delete
            
        Returns:
            Result of deletion processing
        """
        results = []
        
        for data_type in data_types:
            # Check for legal holds on user data
            override_check = await self.legal_hold.check_retention_override(
                entity_type=data_type,
                entity_id=user_id
            )
            
            if override_check.get('has_override'):
                # Cannot delete data under legal hold
                await self.legal_hold.notify_data_access(
                    entity_type=data_type,
                    entity_id=user_id,
                    access_type='delete_attempt',
                    user_id=user_id
                )
                
                results.append({
                    'data_type': data_type,
                    'status': 'blocked',
                    'reason': 'legal_hold',
                    'holds': override_check.get('holds', [])
                })
            else:
                # Proceed with deletion
                await self.legal_hold.notify_data_access(
                    entity_type=data_type,
                    entity_id=user_id,
                    access_type='delete',
                    user_id=user_id
                )
                
                results.append({
                    'data_type': data_type,
                    'status': 'deleted',
                    'deletion_date': datetime.utcnow().isoformat()
                })
        
        return {
            'user_id': user_id,
            'request_date': datetime.utcnow().isoformat(),
            'results': results,
            'partial_completion': any(r['status'] == 'blocked' for r in results)
        }
    
    async def check_tenant_retention_policies(self, tenant_id: str) -> Dict[str, Any]:
        """
        Check retention policies for a tenant considering legal holds.
        
        Args:
            tenant_id: Tenant to check policies for
            
        Returns:
            Retention policy status with legal hold impacts
        """
        # Get active holds affecting this tenant
        active_holds = await self.legal_hold.get_active_holds_for_scope(
            scope_type='tenant',
            scope_id=tenant_id
        )
        
        policy_status = {
            'tenant_id': tenant_id,
            'has_active_holds': len(active_holds) > 0,
            'active_holds_count': len(active_holds),
            'retention_suspended': len(active_holds) > 0,
            'policy_override_reason': 'legal_preservation' if active_holds else None
        }
        
        if active_holds:
            policy_status['affected_holds'] = [
                {
                    'hold_id': hold['id'],
                    'title': hold['title'],
                    'legal_basis': hold['legal_basis'],
                    'effective_date': hold['effective_date']
                }
                for hold in active_holds
            ]
        
        return policy_status


async def demonstrate_integrations():
    """Demonstrate legal hold integrations with various services."""
    
    # Initialize legal hold client
    legal_hold_client = LegalHoldIntegration(
        legal_hold_service_url="http://localhost:8000",
        auth_token="your-auth-token-here"
    )
    
    # Initialize service integrations
    chat_service = ChatServiceIntegration(legal_hold_client)
    privacy_service = PrivacyServiceIntegration(legal_hold_client)
    
    print("=== Legal Hold Integration Demonstrations ===\n")
    
    # Demo 1: Chat message deletion with legal hold check
    print("1. Chat Message Deletion:")
    result = await chat_service.delete_message(
        message_id="msg_12345",
        user_id="user_67890"
    )
    print(f"   Result: {json.dumps(result, indent=2)}\n")
    
    # Demo 2: Conversation export with legal hold awareness
    print("2. Conversation Export:")
    export_result = await chat_service.export_conversation(
        conversation_id="conv_54321",
        export_format="json"
    )
    print(f"   Export: {json.dumps(export_result, indent=2)}\n")
    
    # Demo 3: Privacy deletion request with legal hold verification
    print("3. Privacy Deletion Request:")
    deletion_result = await privacy_service.process_deletion_request(
        user_id="user_12345",
        data_types=["chat_history", "files", "analytics"]
    )
    print(f"   Deletion: {json.dumps(deletion_result, indent=2)}\n")
    
    # Demo 4: Tenant retention policy check
    print("4. Tenant Retention Policy Check:")
    policy_status = await privacy_service.check_tenant_retention_policies(
        tenant_id="tenant_abcdef"
    )
    print(f"   Policy: {json.dumps(policy_status, indent=2)}\n")
    
    # Demo 5: Direct retention override check
    print("5. Direct Retention Override Check:")
    override_check = await legal_hold_client.check_retention_override(
        entity_type="user_profile",
        entity_id="user_99999"
    )
    print(f"   Override: {json.dumps(override_check, indent=2)}\n")


if __name__ == "__main__":
    # Run the demonstration
    asyncio.run(demonstrate_integrations())
