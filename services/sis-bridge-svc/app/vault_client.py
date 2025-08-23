"""
Vault Client for secure credential management.
"""

import aiohttp
import json
from typing import Dict, Any, Optional
from .config import get_settings

settings = get_settings()


class VaultClient:
    """HashiCorp Vault client for SIS credentials."""
    
    def __init__(self):
        self.base_url = settings.vault_url
        self.token = settings.vault_token
        self.session: Optional[aiohttp.ClientSession] = None
    
    async def _get_session(self) -> aiohttp.ClientSession:
        """Get or create HTTP session."""
        if self.session is None or self.session.closed:
            headers = {
                'X-Vault-Token': self.token,
                'Content-Type': 'application/json'
            }
            self.session = aiohttp.ClientSession(
                timeout=aiohttp.ClientTimeout(total=30),
                headers=headers
            )
        return self.session
    
    async def get_secret(self, path: str) -> Dict[str, Any]:
        """
        Get secret from Vault.
        
        Args:
            path: Secret path (e.g., "secret/data/sis/clever/tenant123")
        
        Returns:
            Secret data
        """
        if not self.base_url or not self.token:
            raise Exception("Vault not configured")
        
        session = await self._get_session()
        url = f"{self.base_url}/v1/{path}"
        
        async with session.get(url) as response:
            if response.status == 200:
                data = await response.json()
                # Handle KV v2 format
                if 'data' in data and 'data' in data['data']:
                    return data['data']['data']
                elif 'data' in data:
                    return data['data']
                return data
            else:
                error_text = await response.text()
                raise Exception(f"Failed to get secret: {response.status} - {error_text}")
    
    async def put_secret(self, path: str, data: Dict[str, Any]) -> bool:
        """
        Store secret in Vault.
        
        Args:
            path: Secret path
            data: Secret data to store
        
        Returns:
            True if successful
        """
        if not self.base_url or not self.token:
            raise Exception("Vault not configured")
        
        session = await self._get_session()
        url = f"{self.base_url}/v1/{path}"
        
        # Handle KV v2 format
        payload = {"data": data}
        
        async with session.post(url, json=payload) as response:
            if response.status in [200, 204]:
                return True
            else:
                error_text = await response.text()
                raise Exception(f"Failed to store secret: {response.status} - {error_text}")
    
    async def delete_secret(self, path: str) -> bool:
        """
        Delete secret from Vault.
        
        Args:
            path: Secret path
        
        Returns:
            True if successful
        """
        if not self.base_url or not self.token:
            raise Exception("Vault not configured")
        
        session = await self._get_session()
        url = f"{self.base_url}/v1/{path}"
        
        async with session.delete(url) as response:
            if response.status in [200, 204]:
                return True
            else:
                error_text = await response.text()
                raise Exception(f"Failed to delete secret: {response.status} - {error_text}")
    
    async def cleanup(self):
        """Cleanup HTTP session."""
        if self.session and not self.session.closed:
            await self.session.close()
