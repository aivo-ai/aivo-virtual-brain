"""
SCIM Routes Package

Provides SCIM 2.0 API endpoints for Users, Groups, and Schemas.
"""

from .users import router as users_router
from .groups import router as groups_router
from .schemas import router as schemas_router

__all__ = ["users_router", "groups_router", "schemas_router"]
