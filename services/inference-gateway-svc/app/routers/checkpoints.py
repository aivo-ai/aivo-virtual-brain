"""
AIVO Inference Gateway - Checkpoints Router
S2-06 Implementation: Edge delivery of personalized checkpoints with signed URLs
"""

import asyncio
import hashlib
import hmac
import json
import time
from datetime import datetime, timedelta
from typing import Dict, Any, Optional
from urllib.parse import quote
from uuid import UUID

from fastapi import APIRouter, HTTPException, Depends, Request, BackgroundTasks
from pydantic import BaseModel, Field
from opentelemetry import trace

tracer = trace.get_tracer(__name__)

router = APIRouter(prefix="/v1/checkpoints", tags=["checkpoints"])


class CheckpointMetadata(BaseModel):
    """Checkpoint metadata response model"""
    learner_id: str = Field(..., description="Learner identifier")
    subject: str = Field(..., description="Subject area")
    version: int = Field(..., description="Checkpoint version")
    checkpoint_hash: str = Field(..., description="Unique checkpoint hash")
    signed_url: Optional[str] = Field(None, description="Pre-signed download URL")
    expires_at: str = Field(..., description="URL expiration timestamp")
    size_bytes: int = Field(..., description="Checkpoint size in bytes")
    quantization: str = Field(default="fp16", description="Quantization format")
    model_type: str = Field(default="personalized-llama", description="Base model type")
    created_at: str = Field(..., description="Checkpoint creation timestamp")


class CheckpointService:
    """Service for managing personalized checkpoints"""
    
    def __init__(self):
        self.cache: Dict[str, Dict] = {}  # In-memory cache for dev
        self.minio_config = {
            "endpoint": "localhost:9000",
            "access_key": "minioadmin", 
            "secret_key": "minioadmin",
            "bucket": "checkpoints",
            "region": "us-east-1"
        }
        # Pre-populate with some test checkpoints
        self._initialize_test_data()
    
    def _initialize_test_data(self):
        """Initialize test checkpoint data"""
        test_checkpoints = [
            {
                "learner_id": "550e8400-e29b-41d4-a716-446655440001",
                "subject": "mathematics",
                "version": 3,
                "checkpoint_hash": "ckpt_math_v3_a1b2c3d4",
                "size_bytes": 4294967296,  # 4GB
                "quantization": "int8",
                "model_type": "personalized-llama-7b",
                "created_at": "2024-08-14T10:30:00Z"
            },
            {
                "learner_id": "550e8400-e29b-41d4-a716-446655440001", 
                "subject": "science",
                "version": 5,
                "checkpoint_hash": "ckpt_science_v5_e5f6g7h8",
                "size_bytes": 2147483648,  # 2GB
                "quantization": "fp16",
                "model_type": "personalized-llama-7b",
                "created_at": "2024-08-14T11:15:00Z"
            },
            {
                "learner_id": "550e8400-e29b-41d4-a716-446655440002",
                "subject": "literature",
                "version": 2,
                "checkpoint_hash": "ckpt_lit_v2_i9j0k1l2",
                "size_bytes": 8589934592,  # 8GB
                "quantization": "fp16",
                "model_type": "personalized-llama-13b",
                "created_at": "2024-08-14T09:45:00Z"
            }
        ]
        
        for checkpoint in test_checkpoints:
            cache_key = f"{checkpoint['learner_id']}:{checkpoint['subject']}"
            self.cache[cache_key] = checkpoint
    
    async def get_checkpoint_metadata(self, learner_id: str, subject: str) -> Optional[Dict]:
        """Get checkpoint metadata for learner and subject"""
        with tracer.start_as_current_span("get_checkpoint_metadata") as span:
            span.set_attribute("learner_id", learner_id)
            span.set_attribute("subject", subject)
            
            cache_key = f"{learner_id}:{subject}"
            
            # Check cache first
            if cache_key in self.cache:
                checkpoint = self.cache[cache_key].copy()
                span.set_attribute("cache_hit", True)
                span.set_attribute("checkpoint_version", checkpoint["version"])
                return checkpoint
            
            span.set_attribute("cache_hit", False)
            
            # Simulate database/registry lookup
            await asyncio.sleep(0.1)  # Simulate network delay
            
            # For demo purposes, return None for unknown combinations
            return None
    
    def generate_signed_url(self, checkpoint_hash: str, expires_in_minutes: int = 10) -> str:
        """Generate a pre-signed URL for checkpoint download"""
        with tracer.start_as_current_span("generate_signed_url") as span:
            span.set_attribute("checkpoint_hash", checkpoint_hash)
            span.set_attribute("expires_in_minutes", expires_in_minutes)
            
            # Calculate expiration
            expires_at = datetime.utcnow() + timedelta(minutes=expires_in_minutes)
            expires_timestamp = int(expires_at.timestamp())
            
            # Build object path
            object_path = f"personalized/{checkpoint_hash}.safetensors"
            
            # Create string to sign (AWS S3-style)
            string_to_sign = f"GET\n\n\n{expires_timestamp}\n/{self.minio_config['bucket']}/{object_path}"
            
            # Generate signature
            signature = hmac.new(
                self.minio_config['secret_key'].encode(),
                string_to_sign.encode(),
                hashlib.sha1
            ).hexdigest()
            
            # Build signed URL
            base_url = f"http://{self.minio_config['endpoint']}/{self.minio_config['bucket']}"
            signed_url = (
                f"{base_url}/{object_path}"
                f"?AWSAccessKeyId={self.minio_config['access_key']}"
                f"&Expires={expires_timestamp}"
                f"&Signature={quote(signature)}"
            )
            
            span.set_attribute("signed_url_expires", expires_at.isoformat())
            
            return signed_url
    
    def invalidate_cache(self, learner_id: str, subject: str = None):
        """Invalidate cache entries for learner"""
        with tracer.start_as_current_span("invalidate_cache") as span:
            span.set_attribute("learner_id", learner_id)
            
            if subject:
                # Invalidate specific subject
                cache_key = f"{learner_id}:{subject}"
                if cache_key in self.cache:
                    del self.cache[cache_key]
                    span.set_attribute("invalidated_key", cache_key)
            else:
                # Invalidate all subjects for learner
                keys_to_remove = [k for k in self.cache.keys() if k.startswith(f"{learner_id}:")]
                for key in keys_to_remove:
                    del self.cache[key]
                span.set_attribute("invalidated_count", len(keys_to_remove))
    
    async def simulate_quantization(self, checkpoint_hash: str, target_format: str = "int8") -> Dict[str, Any]:
        """Simulate checkpoint quantization process"""
        with tracer.start_as_current_span("simulate_quantization") as span:
            span.set_attribute("checkpoint_hash", checkpoint_hash)
            span.set_attribute("target_format", target_format)
            
            # Simulate quantization time based on format
            quantization_times = {
                "fp32": 0.5,  # No quantization needed
                "fp16": 1.0,  # Light quantization  
                "int8": 2.5,  # Medium quantization
                "int4": 5.0   # Heavy quantization
            }
            
            processing_time = quantization_times.get(target_format, 2.0)
            await asyncio.sleep(processing_time)
            
            # Calculate size reduction
            size_reductions = {
                "fp32": 1.0,
                "fp16": 0.5,
                "int8": 0.25,
                "int4": 0.125
            }
            
            reduction_factor = size_reductions.get(target_format, 0.5)
            
            result = {
                "quantized_hash": f"{checkpoint_hash}_q{target_format}",
                "original_format": "fp32",
                "target_format": target_format,
                "size_reduction_factor": reduction_factor,
                "processing_time_seconds": processing_time,
                "status": "completed"
            }
            
            span.set_attribute("quantization_completed", True)
            span.set_attribute("size_reduction", reduction_factor)
            
            return result


# Global service instance
checkpoint_service = CheckpointService()


async def verify_learner_access(request: Request, learner_id: str) -> bool:
    """Verify that the requesting user has access to the learner's checkpoints"""
    # In production, this would validate JWT tokens, check user permissions, etc.
    # For demo purposes, we'll do basic validation
    
    try:
        # Validate UUID format
        UUID(learner_id)
    except ValueError:
        return False
    
    # Check if request has proper authorization header
    auth_header = request.headers.get("authorization")
    if not auth_header or not auth_header.startswith("Bearer "):
        return False
    
    # For demo, any valid bearer token works
    # In production: decode JWT, verify claims, check permissions
    token = auth_header[7:]  # Remove "Bearer "
    
    return len(token) > 0


@router.get("/{learner_id}/{subject}", response_model=CheckpointMetadata)
async def get_personalized_checkpoint(
    learner_id: str,
    subject: str,
    request: Request,
    background_tasks: BackgroundTasks,
    quantization: Optional[str] = "fp16",
    include_url: bool = True,
    url_expires_minutes: int = 10
):
    """
    Fetch personalized checkpoint metadata and signed URL for a specific learner and subject.
    
    - **learner_id**: Unique identifier for the learner
    - **subject**: Subject area (e.g., mathematics, science, literature)  
    - **quantization**: Quantization format (fp32, fp16, int8, int4)
    - **include_url**: Whether to include pre-signed download URL
    - **url_expires_minutes**: URL expiration time in minutes (1-60)
    """
    with tracer.start_as_current_span("get_personalized_checkpoint") as span:
        span.set_attribute("learner_id", learner_id)
        span.set_attribute("subject", subject)
        span.set_attribute("quantization", quantization)
        
        # Verify learner access
        has_access = await verify_learner_access(request, learner_id)
        if not has_access:
            span.set_attribute("access_denied", True)
            raise HTTPException(
                status_code=403,
                detail="Access denied: Invalid authentication or insufficient permissions for learner scope"
            )
        
        # Get checkpoint metadata
        checkpoint_data = await checkpoint_service.get_checkpoint_metadata(learner_id, subject)
        if not checkpoint_data:
            span.set_attribute("checkpoint_found", False)
            raise HTTPException(
                status_code=404,
                detail=f"No personalized checkpoint found for learner {learner_id} and subject {subject}"
            )
        
        span.set_attribute("checkpoint_found", True)
        span.set_attribute("checkpoint_version", checkpoint_data["version"])
        
        # Validate quantization format
        valid_formats = ["fp32", "fp16", "int8", "int4"]
        if quantization not in valid_formats:
            raise HTTPException(
                status_code=400,
                detail=f"Invalid quantization format. Supported: {valid_formats}"
            )
        
        # Validate URL expiration
        if url_expires_minutes < 1 or url_expires_minutes > 60:
            raise HTTPException(
                status_code=400,
                detail="URL expiration must be between 1 and 60 minutes"
            )
        
        # Simulate quantization if needed
        if quantization != checkpoint_data.get("quantization", "fp16"):
            span.set_attribute("quantization_required", True)
            # Run quantization in background for this demo
            background_tasks.add_task(
                checkpoint_service.simulate_quantization,
                checkpoint_data["checkpoint_hash"],
                quantization
            )
        
        # Generate signed URL if requested
        signed_url = None
        if include_url:
            signed_url = checkpoint_service.generate_signed_url(
                checkpoint_data["checkpoint_hash"],
                url_expires_minutes
            )
            span.set_attribute("signed_url_generated", True)
        
        # Calculate expiration time
        expires_at = datetime.utcnow() + timedelta(minutes=url_expires_minutes)
        
        # Build response
        response = CheckpointMetadata(
            learner_id=learner_id,
            subject=subject,
            version=checkpoint_data["version"],
            checkpoint_hash=checkpoint_data["checkpoint_hash"],
            signed_url=signed_url,
            expires_at=expires_at.isoformat() + "Z",
            size_bytes=checkpoint_data["size_bytes"],
            quantization=quantization,
            model_type=checkpoint_data["model_type"],
            created_at=checkpoint_data["created_at"]
        )
        
        span.set_attribute("response_generated", True)
        
        return response


@router.post("/{learner_id}/invalidate-cache")
async def invalidate_checkpoint_cache(
    learner_id: str,
    request: Request,
    subject: Optional[str] = None
):
    """
    Invalidate checkpoint cache for a learner.
    Called when new checkpoint_hash is available.
    
    - **learner_id**: Learner to invalidate cache for
    - **subject**: Optional specific subject to invalidate
    """
    with tracer.start_as_current_span("invalidate_checkpoint_cache") as span:
        span.set_attribute("learner_id", learner_id)
        
        # Verify learner access
        has_access = await verify_learner_access(request, learner_id)
        if not has_access:
            raise HTTPException(
                status_code=403,
                detail="Access denied: Invalid authentication or insufficient permissions"
            )
        
        # Invalidate cache
        checkpoint_service.invalidate_cache(learner_id, subject)
        
        return {
            "status": "success",
            "message": f"Cache invalidated for learner {learner_id}" + (f" subject {subject}" if subject else ""),
            "timestamp": datetime.utcnow().isoformat() + "Z"
        }


@router.get("/{learner_id}/{subject}/quantize/{format}")
async def quantize_checkpoint(
    learner_id: str,
    subject: str,
    format: str,
    request: Request
):
    """
    Request checkpoint quantization to a specific format.
    This is an async operation that returns a job ID.
    
    - **learner_id**: Learner identifier
    - **subject**: Subject area
    - **format**: Target quantization format (fp16, int8, int4)
    """
    with tracer.start_as_current_span("quantize_checkpoint") as span:
        span.set_attribute("learner_id", learner_id)
        span.set_attribute("subject", subject)
        span.set_attribute("target_format", format)
        
        # Verify learner access
        has_access = await verify_learner_access(request, learner_id)
        if not has_access:
            raise HTTPException(
                status_code=403,
                detail="Access denied: Invalid authentication or insufficient permissions"
            )
        
        # Get checkpoint metadata
        checkpoint_data = await checkpoint_service.get_checkpoint_metadata(learner_id, subject)
        if not checkpoint_data:
            raise HTTPException(
                status_code=404,
                detail=f"No checkpoint found for learner {learner_id} and subject {subject}"
            )
        
        # Validate format
        valid_formats = ["fp16", "int8", "int4"]
        if format not in valid_formats:
            raise HTTPException(
                status_code=400,
                detail=f"Invalid quantization format. Supported: {valid_formats}"
            )
        
        # Simulate quantization
        result = await checkpoint_service.simulate_quantization(
            checkpoint_data["checkpoint_hash"],
            format
        )
        
        return {
            "job_id": f"quant_{int(time.time())}_{learner_id[:8]}",
            "status": "processing",
            "checkpoint_hash": checkpoint_data["checkpoint_hash"],
            "target_format": format,
            "estimated_completion": (datetime.utcnow() + timedelta(minutes=5)).isoformat() + "Z",
            "quantization_result": result
        }


@router.get("/health")
async def checkpoint_service_health():
    """Health check for checkpoint service"""
    return {
        "service": "checkpoint-service",
        "status": "healthy",
        "cache_size": len(checkpoint_service.cache),
        "minio_configured": True,
        "timestamp": datetime.utcnow().isoformat() + "Z"
    }


# For integration testing
def get_checkpoint_service() -> CheckpointService:
    """Dependency injection for testing"""
    return checkpoint_service
