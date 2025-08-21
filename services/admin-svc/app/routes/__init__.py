"""
Route package initialization
"""

# Import all route modules to make them available
from . import system, approvals, queues, support, audit

__all__ = ["system", "approvals", "queues", "support", "audit"]
