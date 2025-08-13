# AIVO Notification Service - Push Notification Service
# S1-12 Implementation - Web Push Notifications

import json
import logging
from typing import Dict, Any, List, Optional
from datetime import datetime, timezone
import asyncio
import aiohttp
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.asymmetric import ec
from cryptography.hazmat.primitives.ciphers import Cipher, algorithms, modes
from cryptography.hazmat.primitives.kdf.hkdf import HKDF
from cryptography.hazmat.backends import default_backend
import base64
import os
from sqlalchemy.orm import Session

from .models import PushSubscription, Notification

logger = logging.getLogger(__name__)

class PushNotificationService:
    """Service for sending web push notifications."""
    
    def __init__(self):
        # VAPID keys for web push (would be loaded from environment in production)
        self.vapid_public_key = os.getenv("VAPID_PUBLIC_KEY", "")
        self.vapid_private_key = os.getenv("VAPID_PRIVATE_KEY", "")
        self.vapid_email = os.getenv("VAPID_EMAIL", "admin@aivo.ai")
        
        # For now, use mock implementation since we don't have real VAPID keys
        self.mock_mode = not (self.vapid_public_key and self.vapid_private_key)
        
        if self.mock_mode:
            logger.warning("Push service running in mock mode - no real notifications sent")
    
    async def send_to_user(
        self, 
        user_id: str, 
        notification_data: Dict[str, Any], 
        db: Session
    ) -> Dict[str, Any]:
        """Send push notification to all user's subscribed devices."""
        try:
            # Get user's active push subscriptions
            subscriptions = db.query(PushSubscription).filter(
                PushSubscription.user_id == user_id,
                PushSubscription.is_active == True
            ).all()
            
            if not subscriptions:
                return {"status": "no_subscriptions", "sent": 0, "failed": 0}
            
            # Prepare notification payload
            payload = {
                "title": notification_data.get("title", "New Notification"),
                "body": notification_data.get("message", ""),
                "icon": "/icons/notification-icon.png",
                "badge": "/icons/notification-badge.png",
                "tag": f"notification-{notification_data.get('id', '')}",
                "timestamp": int(datetime.now(timezone.utc).timestamp() * 1000),
                "data": {
                    "notification_id": notification_data.get("id"),
                    "type": notification_data.get("notification_type"),
                    "action_url": notification_data.get("action_url"),
                    "metadata": notification_data.get("metadata", {})
                },
                "actions": []
            }
            
            # Add action buttons based on notification type
            if notification_data.get("action_url"):
                payload["actions"].append({
                    "action": "view",
                    "title": "View",
                    "icon": "/icons/view-action.png"
                })
            
            payload["actions"].append({
                "action": "dismiss",
                "title": "Dismiss",
                "icon": "/icons/dismiss-action.png"
            })
            
            # Send to each subscription
            sent_count = 0
            failed_count = 0
            
            for subscription in subscriptions:
                try:
                    result = await self._send_to_subscription(subscription, payload)
                    if result["success"]:
                        sent_count += 1
                        # Update last used timestamp
                        subscription.last_used_at = datetime.now(timezone.utc)
                    else:
                        failed_count += 1
                        # Check if subscription is invalid
                        if result.get("invalid_subscription"):
                            subscription.is_active = False
                            
                except Exception as e:
                    logger.error(f"Error sending push to subscription {subscription.id}: {e}")
                    failed_count += 1
            
            db.commit()
            
            return {
                "status": "completed",
                "sent": sent_count,
                "failed": failed_count,
                "total_subscriptions": len(subscriptions)
            }
            
        except Exception as e:
            logger.error(f"Error sending push notifications to user {user_id}: {e}")
            return {"status": "error", "error": str(e), "sent": 0, "failed": 0}
    
    async def _send_to_subscription(
        self, 
        subscription: PushSubscription, 
        payload: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Send push notification to a specific subscription."""
        if self.mock_mode:
            # Mock implementation for development
            logger.info(f"MOCK PUSH: Sending to {subscription.endpoint[:50]}...")
            logger.info(f"MOCK PUSH: Payload: {payload['title']} - {payload['body']}")
            return {"success": True, "mock": True}
        
        try:
            # Encrypt the payload
            encrypted_payload = self._encrypt_payload(
                json.dumps(payload).encode('utf-8'),
                subscription.p256dh_key,
                subscription.auth_key
            )
            
            # Generate VAPID headers
            vapid_headers = self._generate_vapid_headers(subscription.endpoint)
            
            # Send HTTP request to push service
            headers = {
                "Content-Type": "application/octet-stream",
                "Content-Encoding": "aes128gcm",
                "TTL": str(24 * 60 * 60),  # 24 hours
                **vapid_headers
            }
            
            async with aiohttp.ClientSession() as session:
                async with session.post(
                    subscription.endpoint,
                    data=encrypted_payload,
                    headers=headers,
                    timeout=aiohttp.ClientTimeout(total=10)
                ) as response:
                    
                    if response.status == 200 or response.status == 201:
                        return {"success": True}
                    elif response.status == 410:  # Gone - subscription invalid
                        return {"success": False, "invalid_subscription": True}
                    else:
                        logger.error(f"Push notification failed: HTTP {response.status}")
                        return {"success": False, "http_status": response.status}
                        
        except asyncio.TimeoutError:
            logger.error("Push notification timeout")
            return {"success": False, "error": "timeout"}
        except Exception as e:
            logger.error(f"Error sending push notification: {e}")
            return {"success": False, "error": str(e)}
    
    def _encrypt_payload(self, payload: bytes, p256dh_key: str, auth_key: str) -> bytes:
        """Encrypt payload using Web Push encryption standard."""
        try:
            # This is a simplified implementation
            # In production, use a proper Web Push encryption library
            # like pywebpush or implement the full RFC 8291 standard
            
            # For now, return the payload as-is (would need proper implementation)
            # Real implementation would involve:
            # 1. ECDH key exchange
            # 2. HKDF key derivation
            # 3. AES-GCM encryption
            
            return payload  # Placeholder - needs proper encryption
            
        except Exception as e:
            logger.error(f"Error encrypting push payload: {e}")
            raise
    
    def _generate_vapid_headers(self, endpoint: str) -> Dict[str, str]:
        """Generate VAPID headers for authentication."""
        if self.mock_mode:
            return {"Authorization": "vapid t=mock_token", "Crypto-Key": "p256ecdsa=mock_key"}
        
        try:
            # This would generate proper VAPID JWT token
            # Implementation needs proper JWT signing with ES256
            
            # Mock headers for now
            return {
                "Authorization": f"vapid t=mock_jwt_token",
                "Crypto-Key": f"p256ecdsa={self.vapid_public_key}"
            }
            
        except Exception as e:
            logger.error(f"Error generating VAPID headers: {e}")
            raise
    
    async def send_test_notification(self, user_id: str, db: Session) -> Dict[str, Any]:
        """Send a test push notification to user."""
        test_notification = {
            "id": "test-notification",
            "title": "🔔 Test Notification",
            "message": "This is a test push notification from AIVO Notification Service.",
            "notification_type": "system",
            "priority": "normal",
            "metadata": {"test": True},
            "action_url": "/notifications"
        }
        
        return await self.send_to_user(user_id, test_notification, db)
    
    def validate_subscription_data(self, subscription_data: Dict[str, Any]) -> bool:
        """Validate push subscription data."""
        required_fields = ["endpoint", "p256dh_key", "auth_key"]
        
        for field in required_fields:
            if not subscription_data.get(field):
                return False
        
        # Additional validation
        endpoint = subscription_data["endpoint"]
        
        # Check if endpoint is from a known push service
        valid_endpoints = [
            "https://fcm.googleapis.com/",
            "https://updates.push.services.mozilla.com/",
            "https://wns2-bn1p.notify.windows.com/",
            "https://notify.bugsnag.com/"
        ]
        
        if not any(endpoint.startswith(valid) for valid in valid_endpoints):
            logger.warning(f"Unknown push endpoint: {endpoint}")
        
        return True
