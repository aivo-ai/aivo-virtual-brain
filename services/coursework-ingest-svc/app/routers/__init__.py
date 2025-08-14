"""
Routers package for coursework ingest service.
"""

from .upload import router as upload_router

__all__ = ["upload_router"]
