"""
Chat Service Pydantic Schemas
Request and response models for the chat API
"""

from pydantic import BaseModel, Field, ConfigDict
from typing import Optional, List, Dict, Any, Literal
from datetime import datetime
from uuid import UUID


# Thread Schemas

class ThreadCreate(BaseModel):
    """Schema for creating a new thread"""
    learner_id: str = Field(..., min_length=1, max_length=255)
    subject: Optional[str] = Field(None, max_length=500)
    created_by: str = Field(..., min_length=1, max_length=255)


class ThreadUpdate(BaseModel):
    """Schema for updating a thread"""
    subject: Optional[str] = Field(None, max_length=500)
    is_archived: Optional[bool] = None


class ThreadResponse(BaseModel):
    """Schema for thread response"""
    model_config = ConfigDict(from_attributes=True)
    
    id: UUID
    learner_id: str
    subject: Optional[str]
    created_by: str
    tenant_id: str
    created_at: datetime
    updated_at: datetime
    is_archived: bool
    tenant_isolated: bool
    message_count: Optional[int] = None  # Added by query
    last_message_at: Optional[datetime] = None  # Added by query


class ThreadList(BaseModel):
    """Schema for thread list response"""
    threads: List[ThreadResponse]
    total: int
    page: int
    per_page: int
    has_more: bool


# Message Schemas

class MessageCreate(BaseModel):
    """Schema for creating a new message"""
    thread_id: UUID
    role: Literal["user", "assistant", "system"] = Field(..., description="Message role")
    content: Dict[str, Any] = Field(..., description="Structured message content")
    message_type: str = Field(default="text", max_length=100)
    parent_message_id: Optional[UUID] = None


class MessageUpdate(BaseModel):
    """Schema for updating a message"""
    content: Optional[Dict[str, Any]] = None


class MessageResponse(BaseModel):
    """Schema for message response"""
    model_config = ConfigDict(from_attributes=True)
    
    id: UUID
    thread_id: UUID
    role: str
    content: Dict[str, Any]
    message_type: str
    parent_message_id: Optional[UUID]
    tenant_id: str
    created_at: datetime
    edited_at: Optional[datetime]
    tenant_isolated: bool


class MessageList(BaseModel):
    """Schema for message list response"""
    messages: List[MessageResponse]
    total: int
    page: int
    per_page: int
    has_more: bool
    thread_id: UUID


# Thread with Messages Schema

class ThreadWithMessages(BaseModel):
    """Schema for thread with its messages"""
    model_config = ConfigDict(from_attributes=True)
    
    id: UUID
    learner_id: str
    subject: Optional[str]
    created_by: str
    tenant_id: str
    created_at: datetime
    updated_at: datetime
    is_archived: bool
    messages: List[MessageResponse]


# Privacy and Export Schemas

class ExportRequest(BaseModel):
    """Schema for privacy export request"""
    learner_id: str = Field(..., min_length=1, max_length=255)
    export_format: Literal["json", "csv"] = Field(default="json")
    include_metadata: bool = Field(default=True)
    thread_ids: Optional[List[UUID]] = None  # Export specific threads only


class ExportResponse(BaseModel):
    """Schema for export response"""
    export_id: UUID
    learner_id: str
    export_format: str
    thread_count: int
    message_count: int
    exported_at: datetime
    download_url: Optional[str] = None
    expires_at: Optional[datetime] = None


class DeletionRequest(BaseModel):
    """Schema for privacy deletion request"""
    learner_id: str = Field(..., min_length=1, max_length=255)
    reason: Optional[str] = Field(None, max_length=255)
    thread_ids: Optional[List[UUID]] = None  # Delete specific threads only


class DeletionResponse(BaseModel):
    """Schema for deletion response"""
    deletion_id: UUID
    learner_id: str
    deletion_type: str
    thread_count: int
    message_count: int
    deleted_at: datetime


# Event Schemas

class ChatMessageEvent(BaseModel):
    """Schema for chat message events"""
    event_type: Literal["CHAT_MESSAGE_CREATED", "CHAT_MESSAGE_UPDATED", "CHAT_MESSAGE_DELETED"]
    message_id: UUID
    thread_id: UUID
    learner_id: str
    tenant_id: str
    role: str
    message_type: str
    created_at: datetime
    created_by: str


class ChatThreadEvent(BaseModel):
    """Schema for chat thread events"""
    event_type: Literal["CHAT_THREAD_CREATED", "CHAT_THREAD_UPDATED", "CHAT_THREAD_ARCHIVED"]
    thread_id: UUID
    learner_id: str
    tenant_id: str
    subject: Optional[str]
    created_by: str
    created_at: datetime


# Query Parameters

class ThreadQueryParams(BaseModel):
    """Schema for thread query parameters"""
    learner_id: Optional[str] = None
    created_by: Optional[str] = None
    is_archived: Optional[bool] = None
    page: int = Field(default=1, ge=1)
    per_page: int = Field(default=20, ge=1, le=100)
    sort_by: Literal["created_at", "updated_at", "subject"] = Field(default="updated_at")
    sort_order: Literal["asc", "desc"] = Field(default="desc")


class MessageQueryParams(BaseModel):
    """Schema for message query parameters"""
    thread_id: UUID
    role: Optional[Literal["user", "assistant", "system"]] = None
    message_type: Optional[str] = None
    since: Optional[datetime] = None
    until: Optional[datetime] = None
    page: int = Field(default=1, ge=1)
    per_page: int = Field(default=50, ge=1, le=200)
    sort_order: Literal["asc", "desc"] = Field(default="asc")


# Health and Status Schemas

class HealthResponse(BaseModel):
    """Schema for health check response"""
    status: str
    service: str
    instance: str
    tenant_isolated: bool
    privacy_compliant: bool
    database_status: Optional[str] = None
    kafka_status: Optional[str] = None


class ServiceInfo(BaseModel):
    """Schema for service information"""
    service: str
    version: str
    description: str
    docs: str
    health: str
    tenant_isolated: bool = True


# Aliases for compatibility with routes.py
ThreadListResponse = ThreadList
MessageListResponse = MessageList
PrivacyExportRequest = ExportRequest
PrivacyExportResponse = ExportResponse
PrivacyDeletionRequest = DeletionRequest
PrivacyDeletionResponse = DeletionResponse
