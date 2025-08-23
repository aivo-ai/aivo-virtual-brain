"""
OIDC SSO Implementation for Enterprise Authentication

Handles OpenID Connect authentication flows including authorization code flow,
token validation, and integration with JIT provisioning.
"""

import base64
import hashlib
import json
import secrets
from datetime import datetime, timedelta
from typing import Dict, Any, Optional, List
from urllib.parse import urlencode, parse_qs

import aiohttp
import jwt
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric import rsa

from ..config import get_settings


class OIDCError(Exception):
    """OIDC-specific errors."""
    def __init__(self, message: str, error_code: str = "OIDC_ERROR"):
        self.message = message
        self.error_code = error_code
        super().__init__(message)


class OIDCProvider:
    """OpenID Connect Provider implementation."""
    
    def __init__(self, provider_config: Dict[str, Any]):
        """Initialize OIDC provider with configuration."""
        self.settings = get_settings()
        self.config = provider_config
        
        # Required OIDC configuration
        self.issuer = provider_config.get("oidc_issuer")
        self.client_id = provider_config.get("oidc_client_id") or self.settings.oidc_client_id
        self.client_secret = provider_config.get("oidc_client_secret") or self.settings.oidc_client_secret
        
        # Endpoints - can be discovered or configured manually
        self.authorization_endpoint = provider_config.get("oidc_authorization_endpoint")
        self.token_endpoint = provider_config.get("oidc_token_endpoint")
        self.userinfo_endpoint = provider_config.get("oidc_userinfo_endpoint")
        self.jwks_uri = provider_config.get("oidc_jwks_uri")
        
        # Configuration
        self.redirect_uri = self.settings.oidc_redirect_uri
        self.scopes = self.settings.oidc_scopes
        
        # Cache for JWKS and discovery
        self._jwks_cache = None
        self._jwks_cache_expiry = None
        self._discovery_cache = None
        self._discovery_cache_expiry = None
    
    
    async def discover_configuration(self) -> Dict[str, Any]:
        """Discover OIDC configuration from well-known endpoint."""
        if not self.issuer:
            raise OIDCError("OIDC issuer not configured", "NO_ISSUER")
        
        # Check cache
        now = datetime.utcnow()
        if (self._discovery_cache and self._discovery_cache_expiry and 
            now < self._discovery_cache_expiry):
            return self._discovery_cache
        
        try:
            discovery_url = f"{self.issuer.rstrip('/')}/.well-known/openid-configuration"
            
            async with aiohttp.ClientSession() as session:
                async with session.get(discovery_url) as response:
                    if response.status != 200:
                        raise OIDCError(f"Discovery failed: {response.status}", "DISCOVERY_FAILED")
                    
                    discovery_data = await response.json()
                    
                    # Cache for 1 hour
                    self._discovery_cache = discovery_data
                    self._discovery_cache_expiry = now + timedelta(hours=1)
                    
                    # Update endpoints if not manually configured
                    if not self.authorization_endpoint:
                        self.authorization_endpoint = discovery_data.get("authorization_endpoint")
                    if not self.token_endpoint:
                        self.token_endpoint = discovery_data.get("token_endpoint")
                    if not self.userinfo_endpoint:
                        self.userinfo_endpoint = discovery_data.get("userinfo_endpoint")
                    if not self.jwks_uri:
                        self.jwks_uri = discovery_data.get("jwks_uri")
                    
                    return discovery_data
                    
        except aiohttp.ClientError as e:
            raise OIDCError(f"Discovery request failed: {str(e)}", "DISCOVERY_REQUEST_FAILED")
        except Exception as e:
            raise OIDCError(f"Discovery error: {str(e)}", "DISCOVERY_ERROR")
    
    
    def generate_authorization_url(self, state: Optional[str] = None, nonce: Optional[str] = None) -> Dict[str, str]:
        """
        Generate authorization URL for OIDC flow.
        
        Returns:
            Dictionary with authorization_url, state, and nonce
        """
        if not self.authorization_endpoint:
            raise OIDCError("Authorization endpoint not configured", "NO_AUTH_ENDPOINT")
        
        # Generate state and nonce if not provided
        if not state:
            state = secrets.token_urlsafe(32)
        if not nonce:
            nonce = secrets.token_urlsafe(32)
        
        # Build authorization parameters
        params = {
            "response_type": "code",
            "client_id": self.client_id,
            "redirect_uri": self.redirect_uri,
            "scope": " ".join(self.scopes),
            "state": state,
            "nonce": nonce
        }
        
        authorization_url = f"{self.authorization_endpoint}?{urlencode(params)}"
        
        return {
            "authorization_url": authorization_url,
            "state": state,
            "nonce": nonce
        }
    
    
    async def exchange_code_for_tokens(self, code: str, state: str, expected_state: str) -> Dict[str, Any]:
        """
        Exchange authorization code for tokens.
        
        Args:
            code: Authorization code from callback
            state: State parameter from callback
            expected_state: Expected state value
            
        Returns:
            Dictionary with tokens and user information
        """
        # Validate state
        if state != expected_state:
            raise OIDCError("Invalid state parameter", "INVALID_STATE")
        
        if not self.token_endpoint:
            raise OIDCError("Token endpoint not configured", "NO_TOKEN_ENDPOINT")
        
        try:
            # Prepare token request
            token_data = {
                "grant_type": "authorization_code",
                "code": code,
                "redirect_uri": self.redirect_uri,
                "client_id": self.client_id,
                "client_secret": self.client_secret
            }
            
            headers = {
                "Content-Type": "application/x-www-form-urlencoded",
                "Accept": "application/json"
            }
            
            async with aiohttp.ClientSession() as session:
                async with session.post(
                    self.token_endpoint,
                    data=token_data,
                    headers=headers
                ) as response:
                    if response.status != 200:
                        error_data = await response.text()
                        raise OIDCError(f"Token exchange failed: {error_data}", "TOKEN_EXCHANGE_FAILED")
                    
                    tokens = await response.json()
                    
                    # Validate required tokens
                    if "access_token" not in tokens:
                        raise OIDCError("No access token in response", "NO_ACCESS_TOKEN")
                    
                    # Validate ID token if present
                    id_token_claims = None
                    if "id_token" in tokens:
                        id_token_claims = await self.validate_id_token(tokens["id_token"])
                    
                    # Get user info
                    user_info = await self.get_user_info(tokens["access_token"])
                    
                    return {
                        "tokens": tokens,
                        "id_token_claims": id_token_claims,
                        "user_info": user_info
                    }
                    
        except aiohttp.ClientError as e:
            raise OIDCError(f"Token request failed: {str(e)}", "TOKEN_REQUEST_FAILED")
        except Exception as e:
            raise OIDCError(f"Token exchange error: {str(e)}", "TOKEN_EXCHANGE_ERROR")
    
    
    async def validate_id_token(self, id_token: str, nonce: Optional[str] = None) -> Dict[str, Any]:
        """
        Validate ID token signature and claims.
        
        Args:
            id_token: JWT ID token
            nonce: Expected nonce value
            
        Returns:
            Dictionary with validated claims
        """
        try:
            # Get JWKS for signature validation
            jwks = await self.get_jwks()
            
            # Decode header to get key ID
            header = jwt.get_unverified_header(id_token)
            kid = header.get("kid")
            
            # Find matching key
            public_key = None
            for key in jwks.get("keys", []):
                if key.get("kid") == kid:
                    # Convert JWK to public key
                    public_key = self._jwk_to_public_key(key)
                    break
            
            if not public_key:
                raise OIDCError("No matching key found for ID token", "NO_MATCHING_KEY")
            
            # Validate and decode token
            claims = jwt.decode(
                id_token,
                public_key,
                algorithms=["RS256", "HS256"],
                audience=self.client_id,
                issuer=self.issuer,
                options={"verify_exp": True, "verify_iat": True}
            )
            
            # Validate nonce if provided
            if nonce and claims.get("nonce") != nonce:
                raise OIDCError("Invalid nonce in ID token", "INVALID_NONCE")
            
            # Validate required claims
            if "sub" not in claims:
                raise OIDCError("Missing subject in ID token", "MISSING_SUBJECT")
            
            return claims
            
        except jwt.InvalidTokenError as e:
            raise OIDCError(f"Invalid ID token: {str(e)}", "INVALID_ID_TOKEN")
        except Exception as e:
            raise OIDCError(f"ID token validation error: {str(e)}", "ID_TOKEN_ERROR")
    
    
    async def get_user_info(self, access_token: str) -> Dict[str, Any]:
        """Get user information from userinfo endpoint."""
        if not self.userinfo_endpoint:
            raise OIDCError("Userinfo endpoint not configured", "NO_USERINFO_ENDPOINT")
        
        try:
            headers = {
                "Authorization": f"Bearer {access_token}",
                "Accept": "application/json"
            }
            
            async with aiohttp.ClientSession() as session:
                async with session.get(
                    self.userinfo_endpoint,
                    headers=headers
                ) as response:
                    if response.status != 200:
                        error_data = await response.text()
                        raise OIDCError(f"Userinfo request failed: {error_data}", "USERINFO_FAILED")
                    
                    user_info = await response.json()
                    return user_info
                    
        except aiohttp.ClientError as e:
            raise OIDCError(f"Userinfo request failed: {str(e)}", "USERINFO_REQUEST_FAILED")
        except Exception as e:
            raise OIDCError(f"Userinfo error: {str(e)}", "USERINFO_ERROR")
    
    
    async def get_jwks(self) -> Dict[str, Any]:
        """Get JSON Web Key Set for signature validation."""
        if not self.jwks_uri:
            raise OIDCError("JWKS URI not configured", "NO_JWKS_URI")
        
        # Check cache
        now = datetime.utcnow()
        if (self._jwks_cache and self._jwks_cache_expiry and 
            now < self._jwks_cache_expiry):
            return self._jwks_cache
        
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(self.jwks_uri) as response:
                    if response.status != 200:
                        raise OIDCError(f"JWKS request failed: {response.status}", "JWKS_REQUEST_FAILED")
                    
                    jwks = await response.json()
                    
                    # Cache for 1 hour
                    self._jwks_cache = jwks
                    self._jwks_cache_expiry = now + timedelta(hours=1)
                    
                    return jwks
                    
        except aiohttp.ClientError as e:
            raise OIDCError(f"JWKS request failed: {str(e)}", "JWKS_REQUEST_FAILED")
        except Exception as e:
            raise OIDCError(f"JWKS error: {str(e)}", "JWKS_ERROR")
    
    
    def _jwk_to_public_key(self, jwk: Dict[str, Any]) -> Any:
        """Convert JWK to cryptography public key."""
        try:
            if jwk.get("kty") == "RSA":
                # RSA key
                n = self._base64url_decode(jwk["n"])
                e = self._base64url_decode(jwk["e"])
                
                # Convert to integers
                n_int = int.from_bytes(n, byteorder='big')
                e_int = int.from_bytes(e, byteorder='big')
                
                # Create RSA public key
                public_numbers = rsa.RSAPublicNumbers(e_int, n_int)
                return public_numbers.public_key()
            
            else:
                raise OIDCError(f"Unsupported key type: {jwk.get('kty')}", "UNSUPPORTED_KEY_TYPE")
                
        except Exception as e:
            raise OIDCError(f"JWK conversion failed: {str(e)}", "JWK_CONVERSION_FAILED")
    
    
    def _base64url_decode(self, data: str) -> bytes:
        """Base64url decode with padding."""
        # Add padding if needed
        padding = 4 - (len(data) % 4)
        if padding != 4:
            data += '=' * padding
        
        return base64.urlsafe_b64decode(data)
    
    
    def extract_user_data(self, user_info: Dict[str, Any], id_token_claims: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """
        Extract and normalize user data from OIDC response.
        
        Args:
            user_info: User info from userinfo endpoint
            id_token_claims: Claims from ID token
            
        Returns:
            Normalized user data dictionary
        """
        # Combine user info and ID token claims
        combined_data = {**(id_token_claims or {}), **user_info}
        
        # Extract standard claims
        user_data = {
            'subject': combined_data.get('sub'),
            'email': combined_data.get('email'),
            'email_verified': combined_data.get('email_verified', False),
            'display_name': (combined_data.get('name') or 
                           f"{combined_data.get('given_name', '')} {combined_data.get('family_name', '')}".strip()),
            'first_name': combined_data.get('given_name'),
            'last_name': combined_data.get('family_name'),
            'picture': combined_data.get('picture'),
            'locale': combined_data.get('locale'),
            'groups': self._extract_groups_from_oidc(combined_data),
            'attributes': combined_data
        }
        
        # Remove empty values
        return {k: v for k, v in user_data.items() if v is not None}
    
    
    def _extract_groups_from_oidc(self, claims: Dict[str, Any]) -> List[str]:
        """Extract group information from OIDC claims."""
        groups = []
        
        # Common group claim names
        group_claims = ['groups', 'roles', 'authorities', 'memberOf']
        
        for claim_name in group_claims:
            if claim_name in claims:
                claim_value = claims[claim_name]
                if isinstance(claim_value, list):
                    groups.extend([str(g) for g in claim_value])
                elif isinstance(claim_value, str):
                    # Handle comma-separated groups
                    groups.extend([g.strip() for g in claim_value.split(',') if g.strip()])
                break
        
        return list(set(groups))  # Remove duplicates
    
    
    async def refresh_access_token(self, refresh_token: str) -> Dict[str, Any]:
        """Refresh access token using refresh token."""
        if not self.token_endpoint:
            raise OIDCError("Token endpoint not configured", "NO_TOKEN_ENDPOINT")
        
        try:
            token_data = {
                "grant_type": "refresh_token",
                "refresh_token": refresh_token,
                "client_id": self.client_id,
                "client_secret": self.client_secret
            }
            
            headers = {
                "Content-Type": "application/x-www-form-urlencoded",
                "Accept": "application/json"
            }
            
            async with aiohttp.ClientSession() as session:
                async with session.post(
                    self.token_endpoint,
                    data=token_data,
                    headers=headers
                ) as response:
                    if response.status != 200:
                        error_data = await response.text()
                        raise OIDCError(f"Token refresh failed: {error_data}", "TOKEN_REFRESH_FAILED")
                    
                    tokens = await response.json()
                    return tokens
                    
        except aiohttp.ClientError as e:
            raise OIDCError(f"Token refresh request failed: {str(e)}", "TOKEN_REFRESH_REQUEST_FAILED")
        except Exception as e:
            raise OIDCError(f"Token refresh error: {str(e)}", "TOKEN_REFRESH_ERROR")
    
    
    def generate_logout_url(self, id_token_hint: Optional[str] = None, 
                          post_logout_redirect_uri: Optional[str] = None) -> Optional[str]:
        """Generate logout URL if supported by provider."""
        try:
            # This would typically be discovered from the OIDC configuration
            end_session_endpoint = self._discovery_cache.get("end_session_endpoint") if self._discovery_cache else None
            
            if not end_session_endpoint:
                return None
            
            params = {}
            if id_token_hint:
                params["id_token_hint"] = id_token_hint
            if post_logout_redirect_uri:
                params["post_logout_redirect_uri"] = post_logout_redirect_uri
            
            if params:
                return f"{end_session_endpoint}?{urlencode(params)}"
            else:
                return end_session_endpoint
                
        except Exception:
            return None
