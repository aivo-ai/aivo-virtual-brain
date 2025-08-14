# AIVO SEL Service - Package Initialization
# S2-12 Implementation - Social-Emotional Learning Service

"""
AIVO SEL Service

A comprehensive social-emotional learning service providing:
- Student emotional check-ins and assessment
- Personalized SEL strategy generation  
- Consent-aware alert system
- Privacy-compliant reporting and analytics

This service implements FERPA-compliant consent management
and integrates with the AIVO orchestrator for coordinated
student support workflows.
"""

__version__ = "2.12.0"
__author__ = "AIVO Development Team"
__description__ = "Social-Emotional Learning service with check-ins, strategies, and consent-aware alerts"

from .main import app

__all__ = ["app"]
