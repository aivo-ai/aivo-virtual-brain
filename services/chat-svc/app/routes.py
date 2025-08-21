"""
Chat Service API Routes
RESTful endpoints for threaded chat functionality
"""

from typing import List, Optional, Dict, Any
import uuid
from datetime import datetime
from fastapi import APIRouter, Depends, HTTPException, Request, Query, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_, or_, desc, func
from sqlalchemy.orm import selectinload

from .database import get_db_session, filter_by_tenant
from .models import Thread, Message, ChatExportLog, ChatDeletionLog
from .schemas import (
    ThreadCreate, ThreadResponse, ThreadUpdate,
    MessageCreate, MessageResponse, MessageUpdate,
    ThreadListResponse, MessageListResponse,
    PrivacyExportRequest, PrivacyExportResponse,
    PrivacyDeletionRequest, PrivacyDeletionResponse
)
from .middleware import (
    get_current_user, get_tenant_id, validate_learner_access,
    get_request_context, require_permission
)
from .events import EventPublisher

# Create router
router = APIRouter(prefix="/api/v1", tags=["chat"])

# Event publisher
event_publisher = EventPublisher()


@router.post("/threads", response_model=ThreadResponse)
async def create_thread(
    thread_data: ThreadCreate,
    request: Request,
    db: AsyncSession = Depends(get_db_session)
):
    """
    Create a new chat thread for a learner
    """
    user = get_current_user(request)
    tenant_id = get_tenant_id(request)
    
    # Validate learner access
    validate_learner_access(request, thread_data.learner_id)
    
    # Create thread
    thread = Thread(
        id=str(uuid.uuid4()),
        tenant_id=tenant_id,
        learner_id=thread_data.learner_id,
        title=thread_data.title,
        description=thread_data.description,
        metadata=thread_data.metadata or {},
        created_by=user["user_id"],
        created_at=datetime.utcnow(),
        updated_at=datetime.utcnow()
    )
    
    db.add(thread)
    await db.commit()
    await db.refresh(thread)
    
    # Publish event
    await event_publisher.publish_thread_created(
        thread_id=thread.id,
        tenant_id=tenant_id,
        learner_id=thread.learner_id,
        created_by=user["user_id"],
        metadata=thread.metadata
    )
    
    return ThreadResponse.from_orm(thread)


@router.get("/threads", response_model=ThreadListResponse)
async def list_threads(
    request: Request,
    learner_id: Optional[str] = Query(None, description="Filter by learner ID"),
    limit: int = Query(20, ge=1, le=100, description="Number of threads to return"),
    offset: int = Query(0, ge=0, description="Number of threads to skip"),
    db: AsyncSession = Depends(get_db_session)
):
    """
    List chat threads with optional learner filtering
    """
    user = get_current_user(request)
    tenant_id = get_tenant_id(request)
    
    # Build query
    query = select(Thread).where(Thread.tenant_id == tenant_id)
    
    # Apply learner filtering based on permissions
    learner_scope = user.get("learner_scope", [])
    role = user.get("role", "")
    
    if role not in ["admin", "super_admin"]:
        if "*" not in learner_scope:
            # Restrict to specific learners in scope
            query = query.where(Thread.learner_id.in_(learner_scope))
    
    # Apply learner_id filter if provided
    if learner_id:
        validate_learner_access(request, learner_id)
        query = query.where(Thread.learner_id == learner_id)
    
    # Add ordering and pagination
    query = query.order_by(desc(Thread.updated_at)).offset(offset).limit(limit)
    
    # Execute query
    result = await db.execute(query)
    threads = result.scalars().all()
    
    # Get total count
    count_query = select(func.count(Thread.id)).where(Thread.tenant_id == tenant_id)
    if role not in ["admin", "super_admin"] and "*" not in learner_scope:
        count_query = count_query.where(Thread.learner_id.in_(learner_scope))
    if learner_id:
        count_query = count_query.where(Thread.learner_id == learner_id)
    
    total_result = await db.execute(count_query)
    total = total_result.scalar()
    
    return ThreadListResponse(
        threads=[ThreadResponse.from_orm(thread) for thread in threads],
        total=total,
        limit=limit,
        offset=offset
    )


@router.get("/threads/{thread_id}", response_model=ThreadResponse)
async def get_thread(
    thread_id: str,
    request: Request,
    db: AsyncSession = Depends(get_db_session)
):
    """
    Get a specific thread by ID
    """
    tenant_id = get_tenant_id(request)
    
    # Query thread
    query = select(Thread).where(
        and_(
            Thread.id == thread_id,
            Thread.tenant_id == tenant_id
        )
    )
    
    result = await db.execute(query)
    thread = result.scalar_one_or_none()
    
    if not thread:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Thread not found"
        )
    
    # Validate learner access
    validate_learner_access(request, thread.learner_id)
    
    return ThreadResponse.from_orm(thread)


@router.put("/threads/{thread_id}", response_model=ThreadResponse)
async def update_thread(
    thread_id: str,
    thread_data: ThreadUpdate,
    request: Request,
    db: AsyncSession = Depends(get_db_session)
):
    """
    Update a thread
    """
    user = get_current_user(request)
    tenant_id = get_tenant_id(request)
    
    # Get existing thread
    query = select(Thread).where(
        and_(
            Thread.id == thread_id,
            Thread.tenant_id == tenant_id
        )
    )
    
    result = await db.execute(query)
    thread = result.scalar_one_or_none()
    
    if not thread:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Thread not found"
        )
    
    # Validate learner access
    validate_learner_access(request, thread.learner_id)
    
    # Update fields
    if thread_data.title is not None:
        thread.title = thread_data.title
    if thread_data.description is not None:
        thread.description = thread_data.description
    if thread_data.metadata is not None:
        thread.metadata = thread_data.metadata
    
    thread.updated_at = datetime.utcnow()
    
    await db.commit()
    await db.refresh(thread)
    
    return ThreadResponse.from_orm(thread)


@router.delete("/threads/{thread_id}")
async def delete_thread(
    thread_id: str,
    request: Request,
    db: AsyncSession = Depends(get_db_session)
):
    """
    Delete a thread and all its messages
    """
    user = get_current_user(request)
    tenant_id = get_tenant_id(request)
    
    # Get existing thread
    query = select(Thread).where(
        and_(
            Thread.id == thread_id,
            Thread.tenant_id == tenant_id
        )
    )
    
    result = await db.execute(query)
    thread = result.scalar_one_or_none()
    
    if not thread:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Thread not found"
        )
    
    # Validate learner access
    validate_learner_access(request, thread.learner_id)
    
    # Delete all messages in thread
    messages_query = select(Message).where(Message.thread_id == thread_id)
    messages_result = await db.execute(messages_query)
    messages = messages_result.scalars().all()
    
    for message in messages:
        await db.delete(message)
    
    # Delete thread
    await db.delete(thread)
    await db.commit()
    
    # Publish deletion event
    await event_publisher.publish_thread_deleted(
        thread_id=thread_id,
        tenant_id=tenant_id,
        learner_id=thread.learner_id,
        deleted_by=user["user_id"]
    )
    
    return {"message": "Thread deleted successfully"}


@router.post("/threads/{thread_id}/messages", response_model=MessageResponse)
async def create_message(
    thread_id: str,
    message_data: MessageCreate,
    request: Request,
    db: AsyncSession = Depends(get_db_session)
):
    """
    Create a new message in a thread
    """
    user = get_current_user(request)
    tenant_id = get_tenant_id(request)
    
    # Verify thread exists and get learner_id
    thread_query = select(Thread).where(
        and_(
            Thread.id == thread_id,
            Thread.tenant_id == tenant_id
        )
    )
    
    thread_result = await db.execute(thread_query)
    thread = thread_result.scalar_one_or_none()
    
    if not thread:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Thread not found"
        )
    
    # Validate learner access
    validate_learner_access(request, thread.learner_id)
    
    # Create message
    message = Message(
        id=str(uuid.uuid4()),
        thread_id=thread_id,
        content=message_data.content,
        sender_id=user["user_id"],
        sender_type=message_data.sender_type,
        message_type=message_data.message_type,
        metadata=message_data.metadata or {},
        created_at=datetime.utcnow()
    )
    
    db.add(message)
    
    # Update thread's updated_at
    thread.updated_at = datetime.utcnow()
    
    await db.commit()
    await db.refresh(message)
    
    # Publish event
    await event_publisher.publish_message_created(
        message_id=message.id,
        thread_id=thread_id,
        tenant_id=tenant_id,
        learner_id=thread.learner_id,
        sender_id=user["user_id"],
        content=message.content,
        message_type=message.message_type,
        metadata=message.metadata
    )
    
    return MessageResponse.from_orm(message)


@router.get("/threads/{thread_id}/messages", response_model=MessageListResponse)
async def list_messages(
    thread_id: str,
    request: Request,
    limit: int = Query(50, ge=1, le=200, description="Number of messages to return"),
    offset: int = Query(0, ge=0, description="Number of messages to skip"),
    before: Optional[datetime] = Query(None, description="Get messages before this timestamp"),
    after: Optional[datetime] = Query(None, description="Get messages after this timestamp"),
    db: AsyncSession = Depends(get_db_session)
):
    """
    List messages in a thread with pagination
    """
    tenant_id = get_tenant_id(request)
    
    # Verify thread exists and get learner_id
    thread_query = select(Thread).where(
        and_(
            Thread.id == thread_id,
            Thread.tenant_id == tenant_id
        )
    )
    
    thread_result = await db.execute(thread_query)
    thread = thread_result.scalar_one_or_none()
    
    if not thread:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Thread not found"
        )
    
    # Validate learner access
    validate_learner_access(request, thread.learner_id)
    
    # Build query
    query = select(Message).where(Message.thread_id == thread_id)
    
    # Apply time filters
    if before:
        query = query.where(Message.created_at < before)
    if after:
        query = query.where(Message.created_at > after)
    
    # Add ordering and pagination
    query = query.order_by(desc(Message.created_at)).offset(offset).limit(limit)
    
    # Execute query
    result = await db.execute(query)
    messages = result.scalars().all()
    
    # Get total count
    count_query = select(func.count(Message.id)).where(Message.thread_id == thread_id)
    if before:
        count_query = count_query.where(Message.created_at < before)
    if after:
        count_query = count_query.where(Message.created_at > after)
    
    total_result = await db.execute(count_query)
    total = total_result.scalar()
    
    return MessageListResponse(
        messages=[MessageResponse.from_orm(message) for message in messages],
        total=total,
        limit=limit,
        offset=offset
    )


@router.get("/threads/{thread_id}/messages/{message_id}", response_model=MessageResponse)
async def get_message(
    thread_id: str,
    message_id: str,
    request: Request,
    db: AsyncSession = Depends(get_db_session)
):
    """
    Get a specific message by ID
    """
    tenant_id = get_tenant_id(request)
    
    # Verify thread exists and get learner_id
    thread_query = select(Thread).where(
        and_(
            Thread.id == thread_id,
            Thread.tenant_id == tenant_id
        )
    )
    
    thread_result = await db.execute(thread_query)
    thread = thread_result.scalar_one_or_none()
    
    if not thread:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Thread not found"
        )
    
    # Validate learner access
    validate_learner_access(request, thread.learner_id)
    
    # Get message
    query = select(Message).where(
        and_(
            Message.id == message_id,
            Message.thread_id == thread_id
        )
    )
    
    result = await db.execute(query)
    message = result.scalar_one_or_none()
    
    if not message:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Message not found"
        )
    
    return MessageResponse.from_orm(message)


@router.put("/threads/{thread_id}/messages/{message_id}", response_model=MessageResponse)
async def update_message(
    thread_id: str,
    message_id: str,
    message_data: MessageUpdate,
    request: Request,
    db: AsyncSession = Depends(get_db_session)
):
    """
    Update a message (content only)
    """
    user = get_current_user(request)
    tenant_id = get_tenant_id(request)
    
    # Verify thread exists and get learner_id
    thread_query = select(Thread).where(
        and_(
            Thread.id == thread_id,
            Thread.tenant_id == tenant_id
        )
    )
    
    thread_result = await db.execute(thread_query)
    thread = thread_result.scalar_one_or_none()
    
    if not thread:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Thread not found"
        )
    
    # Validate learner access
    validate_learner_access(request, thread.learner_id)
    
    # Get message
    query = select(Message).where(
        and_(
            Message.id == message_id,
            Message.thread_id == thread_id
        )
    )
    
    result = await db.execute(query)
    message = result.scalar_one_or_none()
    
    if not message:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Message not found"
        )
    
    # Check if user can edit this message
    if message.sender_id != user["user_id"] and user.get("role") not in ["admin", "super_admin"]:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Can only edit your own messages"
        )
    
    # Update message
    if message_data.content is not None:
        message.content = message_data.content
    if message_data.metadata is not None:
        message.metadata = message_data.metadata
    
    message.updated_at = datetime.utcnow()
    
    await db.commit()
    await db.refresh(message)
    
    return MessageResponse.from_orm(message)


@router.delete("/threads/{thread_id}/messages/{message_id}")
async def delete_message(
    thread_id: str,
    message_id: str,
    request: Request,
    db: AsyncSession = Depends(get_db_session)
):
    """
    Delete a message
    """
    user = get_current_user(request)
    tenant_id = get_tenant_id(request)
    
    # Verify thread exists and get learner_id
    thread_query = select(Thread).where(
        and_(
            Thread.id == thread_id,
            Thread.tenant_id == tenant_id
        )
    )
    
    thread_result = await db.execute(thread_query)
    thread = thread_result.scalar_one_or_none()
    
    if not thread:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Thread not found"
        )
    
    # Validate learner access
    validate_learner_access(request, thread.learner_id)
    
    # Get message
    query = select(Message).where(
        and_(
            Message.id == message_id,
            Message.thread_id == thread_id
        )
    )
    
    result = await db.execute(query)
    message = result.scalar_one_or_none()
    
    if not message:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Message not found"
        )
    
    # Check if user can delete this message
    if message.sender_id != user["user_id"] and user.get("role") not in ["admin", "super_admin"]:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Can only delete your own messages"
        )
    
    # Delete message
    await db.delete(message)
    await db.commit()
    
    return {"message": "Message deleted successfully"}


# Privacy and compliance endpoints
@router.post("/privacy/export", response_model=PrivacyExportResponse)
async def export_chat_data(
    export_request: PrivacyExportRequest,
    request: Request,
    db: AsyncSession = Depends(get_db_session)
):
    """
    Export all chat data for a learner (GDPR compliance)
    """
    user = get_current_user(request)
    tenant_id = get_tenant_id(request)
    
    # Validate learner access
    validate_learner_access(request, export_request.learner_id)
    
    # Create export log
    export_log = ChatExportLog(
        id=str(uuid.uuid4()),
        tenant_id=tenant_id,
        learner_id=export_request.learner_id,
        requested_by=user["user_id"],
        export_type=export_request.export_type,
        status="pending",
        created_at=datetime.utcnow()
    )
    
    db.add(export_log)
    await db.commit()
    await db.refresh(export_log)
    
    # TODO: Implement actual data export processing
    # This would typically be handled by a background job
    
    # Publish privacy export event
    await event_publisher.publish_privacy_export_requested(
        export_id=export_log.id,
        tenant_id=tenant_id,
        learner_id=export_request.learner_id,
        requested_by=user["user_id"],
        export_type=export_request.export_type
    )
    
    return PrivacyExportResponse(
        export_id=export_log.id,
        status=export_log.status,
        requested_at=export_log.created_at
    )


@router.post("/privacy/delete", response_model=PrivacyDeletionResponse)
async def delete_chat_data(
    deletion_request: PrivacyDeletionRequest,
    request: Request,
    db: AsyncSession = Depends(get_db_session)
):
    """
    Delete all chat data for a learner (GDPR right to be forgotten)
    """
    user = get_current_user(request)
    tenant_id = get_tenant_id(request)
    
    # Validate learner access
    validate_learner_access(request, deletion_request.learner_id)
    
    # Create deletion log
    deletion_log = ChatDeletionLog(
        id=str(uuid.uuid4()),
        tenant_id=tenant_id,
        learner_id=deletion_request.learner_id,
        requested_by=user["user_id"],
        deletion_type=deletion_request.deletion_type,
        status="pending",
        created_at=datetime.utcnow()
    )
    
    db.add(deletion_log)
    await db.commit()
    await db.refresh(deletion_log)
    
    # TODO: Implement actual data deletion processing
    # This would typically be handled by a background job
    
    # Publish privacy deletion event
    await event_publisher.publish_privacy_deletion_requested(
        deletion_id=deletion_log.id,
        tenant_id=tenant_id,
        learner_id=deletion_request.learner_id,
        requested_by=user["user_id"],
        deletion_type=deletion_request.deletion_type
    )
    
    return PrivacyDeletionResponse(
        deletion_id=deletion_log.id,
        status=deletion_log.status,
        requested_at=deletion_log.created_at
    )


@router.get("/health")
async def health_check():
    """
    Health check endpoint
    """
    return {"status": "healthy", "service": "chat-service"}
