"""
Schemas for coursework-lesson linkback operations.

Supports S5-10 implementation of coursework → lesson progress hooks
with proper RBAC validation and analytics integration.
"""

from datetime import datetime
from typing import Optional, Dict, Any, List
from uuid import UUID
from pydantic import BaseModel, Field, validator


class CourseworkLinkRequest(BaseModel):
    """Request schema for creating coursework-lesson links."""
    coursework_id: UUID = Field(..., description="UUID of the coursework item")
    lesson_id: UUID = Field(..., description="UUID of the lesson to link")
    learner_id: Optional[UUID] = Field(None, description="Optional learner scope restriction")
    mastery_weight: int = Field(100, ge=0, le=100, description="Weight in mastery calculation")
    difficulty_adjustment: int = Field(0, ge=-100, le=100, description="Difficulty modifier")
    link_context: Optional[Dict[str, Any]] = Field(None, description="Additional context for analytics")
    
    @validator('link_context')
    def validate_context(cls, v):
        if v is not None and len(str(v)) > 5000:
            raise ValueError("Link context too large (max 5000 chars)")
        return v


class CourseworkLinkResponse(BaseModel):
    """Response schema for coursework-lesson link operations."""
    id: UUID = Field(..., description="Unique link identifier")
    coursework_id: UUID = Field(..., description="UUID of the coursework item")
    lesson_id: UUID = Field(..., description="UUID of the linked lesson")
    learner_id: Optional[UUID] = Field(None, description="Learner scope if specified")
    
    # Link metadata
    created_by: UUID = Field(..., description="UUID of the user who created the link")
    created_at: datetime = Field(..., description="Link creation timestamp")
    updated_at: datetime = Field(..., description="Last update timestamp")
    
    # Progress tracking
    mastery_weight: int = Field(..., description="Weight in mastery calculation")
    difficulty_adjustment: int = Field(..., description="Difficulty modifier")
    link_context: Optional[Dict[str, Any]] = Field(None, description="Analytics context")
    
    # Status
    is_active: bool = Field(..., description="Whether the link is active")
    
    class Config:
        from_attributes = True


class LinkbackStatus(BaseModel):
    """Status response for linkback operations."""
    success: bool = Field(..., description="Whether the operation succeeded")
    message: str = Field(..., description="Status message")
    link_id: Optional[UUID] = Field(None, description="Created/affected link ID")
    event_emitted: bool = Field(False, description="Whether orchestrator event was emitted")


class CourseworkLinksQuery(BaseModel):
    """Query parameters for retrieving coursework links."""
    coursework_id: Optional[UUID] = Field(None, description="Filter by coursework ID")
    lesson_id: Optional[UUID] = Field(None, description="Filter by lesson ID")
    learner_id: Optional[UUID] = Field(None, description="Filter by learner ID")
    created_by: Optional[UUID] = Field(None, description="Filter by creator")
    is_active: bool = Field(True, description="Include only active links")
    limit: int = Field(50, ge=1, le=500, description="Maximum results to return")
    offset: int = Field(0, ge=0, description="Pagination offset")


class CourseworkLinksResponse(BaseModel):
    """Response for bulk link queries."""
    links: List[CourseworkLinkResponse] = Field(..., description="List of matching links")
    total_count: int = Field(..., description="Total matching links")
    has_more: bool = Field(..., description="Whether more results are available")


class LinkbackMetrics(BaseModel):
    """Analytics metrics for linkback performance."""
    total_links: int = Field(..., description="Total active links")
    links_by_subject: Dict[str, int] = Field(..., description="Links grouped by lesson subject")
    avg_mastery_weight: float = Field(..., description="Average mastery weight")
    recent_activity: Dict[str, int] = Field(..., description="Recent linkback activity")
    
    class Config:
        from_attributes = True


class ProgressHookEvent(BaseModel):
    """Event schema for orchestrator progress hooks."""
    event_type: str = Field("COURSEWORK_LINKED", description="Event type identifier")
    coursework_id: UUID = Field(..., description="UUID of the coursework item")
    lesson_id: UUID = Field(..., description="UUID of the linked lesson")
    learner_id: Optional[UUID] = Field(None, description="Learner scope if specified")
    link_id: UUID = Field(..., description="Link identifier")
    
    # Progress context
    mastery_weight: int = Field(..., description="Weight in mastery calculation")
    difficulty_adjustment: int = Field(..., description="Difficulty modifier")
    link_context: Optional[Dict[str, Any]] = Field(None, description="Analytics context")
    
    # Metadata
    created_by: UUID = Field(..., description="UUID of the user who created the link")
    timestamp: datetime = Field(..., description="Event timestamp")
    tenant_id: Optional[UUID] = Field(None, description="Tenant context")
    
    class Config:
        from_attributes = True


class LinkbackValidation(BaseModel):
    """Validation result for linkback operations."""
    is_valid: bool = Field(..., description="Whether the linkback is valid")
    errors: List[str] = Field(default_factory=list, description="Validation errors")
    warnings: List[str] = Field(default_factory=list, description="Validation warnings")
    
    # Context checks
    lesson_exists: bool = Field(..., description="Whether the lesson exists")
    coursework_accessible: bool = Field(..., description="Whether coursework is accessible")
    rbac_valid: bool = Field(..., description="Whether RBAC permissions are valid")
    learner_scope_valid: bool = Field(..., description="Whether learner scope is valid")
