"""
Lesson Registry - CDN URL Signing

CloudFront and MinIO URL signing for secure, time-limited access to lesson assets.
Supports different storage backends with configurable expiration times and permissions.
"""
import hmac
import hashlib
import base64
import json
from datetime import datetime, timedelta
from typing import Optional, Dict, Any, List
from urllib.parse import quote, urlencode
import logging

# CDN/Storage imports (will be available in production environment)
try:
    import boto3
    from botocore.exceptions import ClientError
except ImportError:
    boto3 = None
    ClientError = Exception

logger = logging.getLogger(__name__)


class CDNSigner:
    """
    Base class for CDN URL signing implementations.
    
    Provides interface for generating time-limited, signed URLs
    for asset access with role-based permissions.
    """
    
    def __init__(self, expires_seconds: int = 600):
        self.expires_seconds = expires_seconds
        
    def sign_url(
        self, 
        asset_path: str, 
        user_role: str, 
        expires_seconds: Optional[int] = None
    ) -> Dict[str, Any]:
        """
        Generate signed URL for asset access.
        
        Args:
            asset_path: S3 key or path to the asset
            user_role: User role for permission validation
            expires_seconds: Custom expiration time (overrides default)
            
        Returns:
            Dict containing signed_url and expires_at timestamp
        """
        raise NotImplementedError("Subclasses must implement sign_url method")
    
    def validate_role_permissions(self, user_role: str, operation: str = "read") -> bool:
        """
        Validate user role permissions for asset operations.
        
        Args:
            user_role: User role (subject_brain, teacher, parent, student)
            operation: Operation type (read, create, update, delete)
            
        Returns:
            True if role has permission for operation
        """
        role_permissions = {
            "subject_brain": ["create", "read", "update", "delete"],
            "teacher": ["read", "update"],  # Can patch metadata
            "parent": ["read"],
            "student": ["read"],
            "admin": ["create", "read", "update", "delete"]
        }
        
        allowed_ops = role_permissions.get(user_role, [])
        return operation in allowed_ops


class CloudFrontSigner(CDNSigner):
    """
    AWS CloudFront URL signing for global CDN delivery.
    
    Generates signed URLs using CloudFront private keys for secure,
    time-limited access to lesson assets distributed globally.
    """
    
    def __init__(
        self, 
        distribution_domain: str,
        key_pair_id: str,
        private_key: str,
        expires_seconds: int = 600
    ):
        super().__init__(expires_seconds)
        self.distribution_domain = distribution_domain.rstrip('/')
        self.key_pair_id = key_pair_id
        self.private_key = private_key
        
        # Parse private key for signing
        self._setup_private_key()
    
    def _setup_private_key(self):
        """Setup private key for CloudFront signing."""
        try:
            from cryptography.hazmat.primitives import serialization
            from cryptography.hazmat.primitives.asymmetric import rsa
            
            # Load private key
            self.signing_key = serialization.load_pem_private_key(
                self.private_key.encode('utf-8'),
                password=None
            )
        except ImportError:
            logger.error("cryptography package required for CloudFront signing")
            raise
        except Exception as e:
            logger.error(f"Failed to load CloudFront private key: {e}")
            raise
    
    def sign_url(
        self, 
        asset_path: str, 
        user_role: str, 
        expires_seconds: Optional[int] = None
    ) -> Dict[str, Any]:
        """
        Generate CloudFront signed URL.
        
        Creates a signed URL using AWS CloudFront private key signing
        with time-based expiration and role validation.
        """
        if not self.validate_role_permissions(user_role, "read"):
            raise PermissionError(f"Role '{user_role}' not authorized for asset access")
        
        expires_seconds = expires_seconds or self.expires_seconds
        expires_at = datetime.utcnow() + timedelta(seconds=expires_seconds)
        expires_timestamp = int(expires_at.timestamp())
        
        # Build CloudFront URL
        base_url = f"{self.distribution_domain}/{asset_path.lstrip('/')}"
        
        # Create policy for signed URL
        policy = {
            "Statement": [
                {
                    "Resource": base_url,
                    "Condition": {
                        "DateLessThan": {
                            "AWS:EpochTime": expires_timestamp
                        }
                    }
                }
            ]
        }
        
        # Generate signature
        policy_json = json.dumps(policy, separators=(',', ':'))
        signature = self._sign_policy(policy_json)
        
        # Build signed URL with query parameters
        params = {
            'Expires': str(expires_timestamp),
            'Signature': signature,
            'Key-Pair-Id': self.key_pair_id
        }
        
        signed_url = f"{base_url}?{urlencode(params)}"
        
        logger.info(f"Generated CloudFront signed URL for {asset_path}, expires at {expires_at}")
        
        return {
            "signed_url": signed_url,
            "expires_at": expires_at,
            "cdn_type": "cloudfront"
        }
    
    def _sign_policy(self, policy_json: str) -> str:
        """Generate CloudFront signature for policy."""
        from cryptography.hazmat.primitives import hashes
        from cryptography.hazmat.primitives.asymmetric import padding
        
        # Sign the policy
        signature = self.signing_key.sign(
            policy_json.encode('utf-8'),
            padding.PKCS1v15(),
            hashes.SHA1()
        )
        
        # Base64 encode and make URL-safe
        encoded = base64.b64encode(signature).decode('utf-8')
        url_safe = encoded.replace('+', '-').replace('=', '_').replace('/', '~')
        
        return url_safe


class MinIOSigner(CDNSigner):
    """
    MinIO/S3 presigned URL generator for self-hosted storage.
    
    Creates presigned URLs for direct access to assets stored in
    MinIO or S3-compatible storage with role-based permissions.
    """
    
    def __init__(
        self,
        endpoint_url: str,
        access_key: str,
        secret_key: str,
        bucket_name: str,
        expires_seconds: int = 600,
        region_name: str = "us-east-1"
    ):
        super().__init__(expires_seconds)
        self.bucket_name = bucket_name
        
        # Initialize S3 client for MinIO
        if boto3 is None:
            raise ImportError("boto3 package required for MinIO/S3 operations")
            
        self.s3_client = boto3.client(
            's3',
            endpoint_url=endpoint_url,
            aws_access_key_id=access_key,
            aws_secret_access_key=secret_key,
            region_name=region_name
        )
    
    def sign_url(
        self, 
        asset_path: str, 
        user_role: str, 
        expires_seconds: Optional[int] = None
    ) -> Dict[str, Any]:
        """
        Generate MinIO/S3 presigned URL.
        
        Creates a presigned URL for direct access to assets with
        time-based expiration and role validation.
        """
        if not self.validate_role_permissions(user_role, "read"):
            raise PermissionError(f"Role '{user_role}' not authorized for asset access")
        
        expires_seconds = expires_seconds or self.expires_seconds
        expires_at = datetime.utcnow() + timedelta(seconds=expires_seconds)
        
        try:
            # Generate presigned URL
            signed_url = self.s3_client.generate_presigned_url(
                'get_object',
                Params={
                    'Bucket': self.bucket_name,
                    'Key': asset_path.lstrip('/')
                },
                ExpiresIn=expires_seconds
            )
            
            logger.info(f"Generated MinIO presigned URL for {asset_path}, expires at {expires_at}")
            
            return {
                "signed_url": signed_url,
                "expires_at": expires_at,
                "cdn_type": "minio"
            }
            
        except ClientError as e:
            logger.error(f"Failed to generate MinIO presigned URL: {e}")
            raise


class MultiCDNSigner:
    """
    Multi-CDN signing coordinator for hybrid cloud deployments.
    
    Routes signing requests to appropriate CDN based on configuration,
    asset type, or geographic requirements.
    """
    
    def __init__(self, primary_signer: CDNSigner, fallback_signer: Optional[CDNSigner] = None):
        self.primary_signer = primary_signer
        self.fallback_signer = fallback_signer
    
    def sign_url(
        self, 
        asset_path: str, 
        user_role: str, 
        prefer_cdn: Optional[str] = None,
        expires_seconds: Optional[int] = None
    ) -> Dict[str, Any]:
        """
        Generate signed URL using preferred or primary CDN.
        
        Args:
            asset_path: Path to the asset
            user_role: User role for permissions
            prefer_cdn: Preferred CDN type ('cloudfront', 'minio')
            expires_seconds: Custom expiration time
        """
        try:
            # Use preferred CDN if specified and available
            if prefer_cdn == "minio" and isinstance(self.fallback_signer, MinIOSigner):
                return self.fallback_signer.sign_url(asset_path, user_role, expires_seconds)
            elif prefer_cdn == "cloudfront" and isinstance(self.primary_signer, CloudFrontSigner):
                return self.primary_signer.sign_url(asset_path, user_role, expires_seconds)
            
            # Default to primary signer
            return self.primary_signer.sign_url(asset_path, user_role, expires_seconds)
            
        except Exception as e:
            logger.warning(f"Primary CDN signing failed: {e}")
            
            # Fallback to secondary signer if available
            if self.fallback_signer:
                try:
                    result = self.fallback_signer.sign_url(asset_path, user_role, expires_seconds)
                    result["fallback_used"] = True
                    return result
                except Exception as fallback_error:
                    logger.error(f"Fallback CDN signing also failed: {fallback_error}")
            
            # Re-raise original error if no fallback
            raise


def create_signer_from_config(config: Dict[str, Any]) -> CDNSigner:
    """
    Factory function to create CDN signer from configuration.
    
    Args:
        config: Configuration dictionary with CDN settings
        
    Returns:
        Configured CDN signer instance
    """
    cdn_type = config.get('type', 'minio').lower()
    expires_seconds = config.get('expires_seconds', 600)
    
    if cdn_type == 'cloudfront':
        return CloudFrontSigner(
            distribution_domain=config['distribution_domain'],
            key_pair_id=config['key_pair_id'],
            private_key=config['private_key'],
            expires_seconds=expires_seconds
        )
    elif cdn_type == 'minio':
        return MinIOSigner(
            endpoint_url=config['endpoint_url'],
            access_key=config['access_key'],
            secret_key=config['secret_key'],
            bucket_name=config['bucket_name'],
            expires_seconds=expires_seconds,
            region_name=config.get('region_name', 'us-east-1')
        )
    else:
        raise ValueError(f"Unsupported CDN type: {cdn_type}")


def batch_sign_assets(
    signer: CDNSigner,
    asset_paths: List[str],
    user_role: str,
    expires_seconds: Optional[int] = None
) -> Dict[str, Dict[str, Any]]:
    """
    Sign multiple asset URLs in batch for efficiency.
    
    Args:
        signer: CDN signer instance
        asset_paths: List of asset paths to sign
        user_role: User role for permissions
        expires_seconds: Custom expiration time
        
    Returns:
        Dictionary mapping asset paths to signed URL data
    """
    signed_assets = {}
    
    for asset_path in asset_paths:
        try:
            signed_data = signer.sign_url(asset_path, user_role, expires_seconds)
            signed_assets[asset_path] = signed_data
        except Exception as e:
            logger.error(f"Failed to sign URL for {asset_path}: {e}")
            signed_assets[asset_path] = {"error": str(e)}
    
    return signed_assets
