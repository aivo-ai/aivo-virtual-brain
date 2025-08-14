"""
AIVO Inference Gateway - Routers Package
S2-01 Implementation: Router package initialization
"""

from .generate import router as generate_router
from .embed import router as embed_router
from .moderate import router as moderate_router

__all__ = [
    "generate_router",
    "embed_router", 
    "moderate_router"
]
