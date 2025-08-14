"""
Custom middleware for the Lesson Registry service.
"""
import time
import uuid
import logging
from typing import Callable
from fastapi import Request, Response
from fastapi.responses import JSONResponse

logger = logging.getLogger(__name__)


async def request_id_middleware(request: Request, call_next: Callable) -> Response:
    """Add unique request ID to all requests."""
    request_id = str(uuid.uuid4())
    request.state.request_id = request_id
    
    # Add request ID to response headers
    response = await call_next(request)
    response.headers["X-Request-ID"] = request_id
    
    return response


async def error_handling_middleware(request: Request, call_next: Callable) -> Response:
    """Global error handling and logging middleware."""
    start_time = time.time()
    request_id = getattr(request.state, 'request_id', str(uuid.uuid4()))
    
    try:
        response = await call_next(request)
        process_time = time.time() - start_time
        
        # Log successful requests
        logger.info(
            f"Request {request_id}: {request.method} {request.url.path} "
            f"completed in {process_time:.4f}s with status {response.status_code}"
        )
        
        return response
        
    except Exception as exc:
        process_time = time.time() - start_time
        
        # Log error
        logger.error(
            f"Request {request_id}: {request.method} {request.url.path} "
            f"failed after {process_time:.4f}s with error: {exc}",
            exc_info=True
        )
        
        # Return standardized error response
        return JSONResponse(
            status_code=500,
            content={
                "error": "InternalServerError",
                "message": "An unexpected error occurred",
                "request_id": request_id,
                "path": str(request.url.path)
            }
        )
