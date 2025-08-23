"""
SCIM 2.0 Users Endpoint Implementation

Complete SCIM 2.0 Users resource with GET, POST, PUT, PATCH, DELETE
operations including filtering, pagination, and version control.
"""

from datetime import datetime
from typing import Optional, Dict, Any
from uuid import UUID, uuid4
from fastapi import APIRouter, Depends, HTTPException, Query, Request, Response
from fastapi.responses import JSONResponse
from sqlalchemy.orm import Session
from sqlalchemy.exc import IntegrityError

from ...database import get_db
from ...models import User, Tenant, SCIMOperation, increment_version
from ...schemas import SCIMUser, SCIMUserCreate, SCIMUserPatch, SCIMError, SCIMListResponse
from ...scim.mapping import SCIMMapper, SCIMPatchProcessor
from ...scim.pagination import SCIMQueryBuilder
from ...scim.filters import SCIMFilterValidator
from ..auth import get_current_tenant, require_scim_permission
from ..events import emit_user_provisioned, emit_user_deprovisioned, emit_seat_allocated

router = APIRouter(prefix="/scim/v2", tags=["SCIM Users"])


def log_scim_operation(
    db: Session,
    tenant_id: str,
    operation_type: str,
    resource_id: Optional[str] = None,
    external_id: Optional[str] = None,
    request: Optional[Request] = None,
    response_status: int = 200,
    response_body: Optional[Dict] = None,
    error_message: Optional[str] = None
):
    """Log SCIM operation for audit purposes."""
    
    operation = SCIMOperation(
        tenant_id=tenant_id,
        operation_type=operation_type,
        resource_type="User",
        resource_id=UUID(resource_id) if resource_id else None,
        external_id=external_id,
        http_method=request.method if request else None,
        endpoint=str(request.url) if request else None,
        request_body=dict(request.query_params) if request else None,
        response_status=response_status,
        response_body=response_body,
        client_ip=request.client.host if request else None,
        user_agent=request.headers.get("user-agent") if request else None,
        error_message=error_message,
        completed_at=datetime.utcnow()
    )
    
    db.add(operation)
    db.commit()


@router.get("/Users", response_model=SCIMListResponse)
async def list_users(
    request: Request,
    response: Response,
    filter: Optional[str] = Query(None, description="SCIM filter expression"),
    startIndex: Optional[str] = Query("1", description="1-based start index"),
    count: Optional[str] = Query("20", description="Number of results per page"),
    sortBy: Optional[str] = Query(None, description="Attribute to sort by"),
    sortOrder: Optional[str] = Query("ascending", description="Sort order"),
    attributes: Optional[str] = Query(None, description="Comma-separated list of attributes to return"),
    excludedAttributes: Optional[str] = Query(None, description="Comma-separated list of attributes to exclude"),
    db: Session = Depends(get_db),
    tenant: Tenant = Depends(get_current_tenant),
    _: bool = Depends(require_scim_permission("users:read"))
):
    """List users with SCIM 2.0 filtering, pagination, and sorting."""
    
    try:
        # Validate filter if provided
        if filter and not SCIMFilterValidator.validate(filter, "User"):
            error = SCIMError(
                status="400",
                scimType="invalidFilter",
                detail="Invalid filter expression"
            )
            log_scim_operation(db, str(tenant.id), "LIST", request=request, 
                             response_status=400, error_message="Invalid filter")
            return JSONResponse(status_code=400, content=error.dict(by_alias=True))
        
        # Build query with filtering, sorting, and pagination
        query_builder = SCIMQueryBuilder.from_params(
            db, User, filter, startIndex, count, sortBy, sortOrder, str(tenant.id)
        )
        
        users, metadata = query_builder.execute(db)
        
        # Convert to SCIM format
        base_url = f"{request.url.scheme}://{request.url.netloc}/scim/v2"
        scim_users = []
        
        for user in users:
            scim_user = SCIMMapper.user_to_scim(user, base_url)
            scim_users.append(scim_user.dict(by_alias=True))
        
        # Create list response
        list_response = SCIMListResponse(
            totalResults=metadata['totalResults'],
            startIndex=metadata['startIndex'],
            itemsPerPage=metadata['itemsPerPage'],
            Resources=scim_users
        )
        
        # Log operation
        log_scim_operation(db, str(tenant.id), "LIST", request=request, 
                         response_status=200, response_body={"count": len(scim_users)})
        
        return list_response
        
    except Exception as e:
        error = SCIMError(
            status="500",
            detail=f"Internal server error: {str(e)}"
        )
        log_scim_operation(db, str(tenant.id), "LIST", request=request,
                         response_status=500, error_message=str(e))
        return JSONResponse(status_code=500, content=error.dict(by_alias=True))


@router.get("/Users/{user_id}", response_model=SCIMUser)
async def get_user(
    user_id: str,
    request: Request,
    response: Response,
    attributes: Optional[str] = Query(None, description="Comma-separated list of attributes to return"),
    excludedAttributes: Optional[str] = Query(None, description="Comma-separated list of attributes to exclude"),
    db: Session = Depends(get_db),
    tenant: Tenant = Depends(get_current_tenant),
    _: bool = Depends(require_scim_permission("users:read"))
):
    """Get user by ID."""
    
    try:
        # Find user
        user = db.query(User).filter(
            User.id == UUID(user_id),
            User.tenant_id == tenant.id
        ).first()
        
        if not user:
            error = SCIMError(
                status="404",
                detail=f"User {user_id} not found"
            )
            log_scim_operation(db, str(tenant.id), "GET", resource_id=user_id,
                             request=request, response_status=404, error_message="User not found")
            return JSONResponse(status_code=404, content=error.dict(by_alias=True))
        
        # Convert to SCIM format
        base_url = f"{request.url.scheme}://{request.url.netloc}/scim/v2"
        scim_user = SCIMMapper.user_to_scim(user, base_url)
        
        # Set ETag header for version control
        from ...models import get_version_etag
        etag = get_version_etag(user)
        response.headers["ETag"] = f'"{etag}"'
        
        # Log operation
        log_scim_operation(db, str(tenant.id), "GET", resource_id=user_id,
                         external_id=user.external_id, request=request, response_status=200)
        
        return scim_user
        
    except ValueError:
        error = SCIMError(
            status="400",
            detail="Invalid user ID format"
        )
        return JSONResponse(status_code=400, content=error.dict(by_alias=True))
    except Exception as e:
        error = SCIMError(
            status="500",
            detail=f"Internal server error: {str(e)}"
        )
        log_scim_operation(db, str(tenant.id), "GET", resource_id=user_id,
                         request=request, response_status=500, error_message=str(e))
        return JSONResponse(status_code=500, content=error.dict(by_alias=True))


@router.post("/Users", response_model=SCIMUser, status_code=201)
async def create_user(
    user_data: SCIMUserCreate,
    request: Request,
    response: Response,
    db: Session = Depends(get_db),
    tenant: Tenant = Depends(get_current_tenant),
    _: bool = Depends(require_scim_permission("users:write"))
):
    """Create a new user."""
    
    try:
        # Check seat limits
        if tenant.seat_limit and tenant.seat_allocated >= tenant.seat_limit:
            error = SCIMError(
                status="409",
                scimType="tooMany",
                detail="Tenant seat limit exceeded"
            )
            log_scim_operation(db, str(tenant.id), "CREATE", 
                             external_id=user_data.external_id,
                             request=request, response_status=409, 
                             error_message="Seat limit exceeded")
            return JSONResponse(status_code=409, content=error.dict(by_alias=True))
        
        # Convert SCIM data to User model
        user = SCIMMapper.scim_to_user(user_data, str(tenant.id))
        user.id = uuid4()
        
        # Allocate seat
        user.seat_allocated = True
        user.seat_allocated_at = datetime.utcnow()
        user.seat_type = user_data.user_type or "user"
        
        # Add to database
        db.add(user)
        
        # Update tenant seat count
        tenant.seat_allocated += 1
        
        db.commit()
        db.refresh(user)
        
        # Convert back to SCIM format
        base_url = f"{request.url.scheme}://{request.url.netloc}/scim/v2"
        scim_user = SCIMMapper.user_to_scim(user, base_url)
        
        # Set Location header
        response.headers["Location"] = f"{base_url}/Users/{user.id}"
        
        # Set ETag header
        from ...models import get_version_etag
        etag = get_version_etag(user)
        response.headers["ETag"] = f'"{etag}"'
        
        # Emit events
        await emit_user_provisioned(str(tenant.id), str(user.id), user_data.dict())
        await emit_seat_allocated(str(tenant.id), str(user.id), user.seat_type)
        
        # Log operation
        log_scim_operation(db, str(tenant.id), "CREATE", resource_id=str(user.id),
                         external_id=user.external_id, request=request, response_status=201)
        
        return scim_user
        
    except IntegrityError as e:
        db.rollback()
        error = SCIMError(
            status="409",
            scimType="uniqueness",
            detail="User already exists with this userName or externalId"
        )
        log_scim_operation(db, str(tenant.id), "CREATE",
                         external_id=user_data.external_id,
                         request=request, response_status=409, 
                         error_message="Uniqueness constraint violation")
        return JSONResponse(status_code=409, content=error.dict(by_alias=True))
    except Exception as e:
        db.rollback()
        error = SCIMError(
            status="500",
            detail=f"Internal server error: {str(e)}"
        )
        log_scim_operation(db, str(tenant.id), "CREATE",
                         external_id=user_data.external_id,
                         request=request, response_status=500, error_message=str(e))
        return JSONResponse(status_code=500, content=error.dict(by_alias=True))


@router.put("/Users/{user_id}", response_model=SCIMUser)
async def replace_user(
    user_id: str,
    user_data: SCIMUserCreate,
    request: Request,
    response: Response,
    db: Session = Depends(get_db),
    tenant: Tenant = Depends(get_current_tenant),
    _: bool = Depends(require_scim_permission("users:write"))
):
    """Replace user (full update)."""
    
    try:
        # Find existing user
        user = db.query(User).filter(
            User.id == UUID(user_id),
            User.tenant_id == tenant.id
        ).first()
        
        if not user:
            error = SCIMError(
                status="404",
                detail=f"User {user_id} not found"
            )
            log_scim_operation(db, str(tenant.id), "REPLACE", resource_id=user_id,
                             request=request, response_status=404, error_message="User not found")
            return JSONResponse(status_code=404, content=error.dict(by_alias=True))
        
        # Check ETag for optimistic concurrency control
        if_match = request.headers.get("If-Match")
        if if_match:
            from ...models import get_version_etag
            current_etag = get_version_etag(user)
            if if_match.strip('"') != current_etag:
                error = SCIMError(
                    status="409",
                    scimType="mutability",
                    detail="Resource version conflict"
                )
                return JSONResponse(status_code=409, content=error.dict(by_alias=True))
        
        # Store original state for events
        was_active = user.active
        
        # Update user attributes
        user = SCIMMapper.update_user_from_scim(user, user_data.dict(by_alias=True))
        
        # Handle seat allocation changes
        if user_data.active and not user.seat_allocated:
            # Activating user - allocate seat
            if tenant.seat_limit and tenant.seat_allocated >= tenant.seat_limit:
                error = SCIMError(
                    status="409",
                    scimType="tooMany",
                    detail="Tenant seat limit exceeded"
                )
                return JSONResponse(status_code=409, content=error.dict(by_alias=True))
            
            user.seat_allocated = True
            user.seat_allocated_at = datetime.utcnow()
            tenant.seat_allocated += 1
            
        elif not user_data.active and user.seat_allocated:
            # Deactivating user - deallocate seat
            user.seat_allocated = False
            user.seat_allocated_at = None
            tenant.seat_allocated -= 1
        
        # Update version and timestamp
        increment_version(user)
        
        db.commit()
        db.refresh(user)
        
        # Convert back to SCIM format
        base_url = f"{request.url.scheme}://{request.url.netloc}/scim/v2"
        scim_user = SCIMMapper.user_to_scim(user, base_url)
        
        # Set ETag header
        from ...models import get_version_etag
        etag = get_version_etag(user)
        response.headers["ETag"] = f'"{etag}"'
        
        # Emit events based on state changes
        if was_active and not user.active:
            await emit_user_deprovisioned(str(tenant.id), str(user.id))
        elif not was_active and user.active:
            await emit_user_provisioned(str(tenant.id), str(user.id), user_data.dict())
        
        # Log operation
        log_scim_operation(db, str(tenant.id), "REPLACE", resource_id=user_id,
                         external_id=user.external_id, request=request, response_status=200)
        
        return scim_user
        
    except ValueError:
        error = SCIMError(
            status="400",
            detail="Invalid user ID format"
        )
        return JSONResponse(status_code=400, content=error.dict(by_alias=True))
    except Exception as e:
        db.rollback()
        error = SCIMError(
            status="500",
            detail=f"Internal server error: {str(e)}"
        )
        log_scim_operation(db, str(tenant.id), "REPLACE", resource_id=user_id,
                         request=request, response_status=500, error_message=str(e))
        return JSONResponse(status_code=500, content=error.dict(by_alias=True))


@router.patch("/Users/{user_id}", response_model=SCIMUser)
async def patch_user(
    user_id: str,
    patch_data: SCIMUserPatch,
    request: Request,
    response: Response,
    db: Session = Depends(get_db),
    tenant: Tenant = Depends(get_current_tenant),
    _: bool = Depends(require_scim_permission("users:write"))
):
    """Patch user (partial update)."""
    
    try:
        # Find existing user
        user = db.query(User).filter(
            User.id == UUID(user_id),
            User.tenant_id == tenant.id
        ).first()
        
        if not user:
            error = SCIMError(
                status="404",
                detail=f"User {user_id} not found"
            )
            log_scim_operation(db, str(tenant.id), "PATCH", resource_id=user_id,
                             request=request, response_status=404, error_message="User not found")
            return JSONResponse(status_code=404, content=error.dict(by_alias=True))
        
        # Apply patch operations
        SCIMPatchProcessor.apply_patch_operations(user, patch_data.operations)
        
        # Update version and timestamp
        increment_version(user)
        
        db.commit()
        db.refresh(user)
        
        # Convert back to SCIM format
        base_url = f"{request.url.scheme}://{request.url.netloc}/scim/v2"
        scim_user = SCIMMapper.user_to_scim(user, base_url)
        
        # Set ETag header
        from ...models import get_version_etag
        etag = get_version_etag(user)
        response.headers["ETag"] = f'"{etag}"'
        
        # Log operation
        log_scim_operation(db, str(tenant.id), "PATCH", resource_id=user_id,
                         external_id=user.external_id, request=request, response_status=200)
        
        return scim_user
        
    except ValueError as e:
        error = SCIMError(
            status="400",
            detail=f"Invalid patch operation: {str(e)}"
        )
        return JSONResponse(status_code=400, content=error.dict(by_alias=True))
    except Exception as e:
        db.rollback()
        error = SCIMError(
            status="500",
            detail=f"Internal server error: {str(e)}"
        )
        log_scim_operation(db, str(tenant.id), "PATCH", resource_id=user_id,
                         request=request, response_status=500, error_message=str(e))
        return JSONResponse(status_code=500, content=error.dict(by_alias=True))


@router.delete("/Users/{user_id}", status_code=204)
async def delete_user(
    user_id: str,
    request: Request,
    response: Response,
    db: Session = Depends(get_db),
    tenant: Tenant = Depends(get_current_tenant),
    _: bool = Depends(require_scim_permission("users:write"))
):
    """Delete user (soft delete with seat deallocation)."""
    
    try:
        # Find existing user
        user = db.query(User).filter(
            User.id == UUID(user_id),
            User.tenant_id == tenant.id
        ).first()
        
        if not user:
            error = SCIMError(
                status="404",
                detail=f"User {user_id} not found"
            )
            log_scim_operation(db, str(tenant.id), "DELETE", resource_id=user_id,
                             request=request, response_status=404, error_message="User not found")
            return JSONResponse(status_code=404, content=error.dict(by_alias=True))
        
        # Soft delete and deallocate seat
        user.active = False
        user.account_disabled = True
        
        if user.seat_allocated:
            user.seat_allocated = False
            user.seat_allocated_at = None
            tenant.seat_allocated -= 1
        
        # Update version
        increment_version(user)
        
        db.commit()
        
        # Emit events
        await emit_user_deprovisioned(str(tenant.id), str(user.id))
        
        # Log operation
        log_scim_operation(db, str(tenant.id), "DELETE", resource_id=user_id,
                         external_id=user.external_id, request=request, response_status=204)
        
        return Response(status_code=204)
        
    except ValueError:
        error = SCIMError(
            status="400",
            detail="Invalid user ID format"
        )
        return JSONResponse(status_code=400, content=error.dict(by_alias=True))
    except Exception as e:
        db.rollback()
        error = SCIMError(
            status="500",
            detail=f"Internal server error: {str(e)}"
        )
        log_scim_operation(db, str(tenant.id), "DELETE", resource_id=user_id,
                         request=request, response_status=500, error_message=str(e))
        return JSONResponse(status_code=500, content=error.dict(by_alias=True))
