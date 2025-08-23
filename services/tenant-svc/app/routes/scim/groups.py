"""
SCIM 2.0 Groups Endpoint Implementation

Complete SCIM 2.0 Groups resource with GET, POST, PUT, PATCH, DELETE
operations including filtering, pagination, and membership management.
"""

from datetime import datetime
from typing import Optional, Dict, Any, List
from uuid import UUID, uuid4
from fastapi import APIRouter, Depends, HTTPException, Query, Request, Response
from fastapi.responses import JSONResponse
from sqlalchemy.orm import Session
from sqlalchemy.exc import IntegrityError

from ...database import get_db
from ...models import Group, GroupMembership, User, Tenant, SCIMOperation, increment_version
from ...schemas import SCIMGroup, SCIMGroupCreate, SCIMGroupPatch, SCIMError, SCIMListResponse
from ...scim.mapping import SCIMMapper, SCIMPatchProcessor
from ...scim.pagination import SCIMQueryBuilder
from ...scim.filters import SCIMFilterValidator
from ..auth import get_current_tenant, require_scim_permission
from ..events import emit_group_created, emit_group_deleted, emit_user_added_to_group, emit_user_removed_from_group

router = APIRouter(prefix="/scim/v2", tags=["SCIM Groups"])


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
        resource_type="Group",
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


@router.get("/Groups", response_model=SCIMListResponse)
async def list_groups(
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
    _: bool = Depends(require_scim_permission("groups:read"))
):
    """List groups with SCIM 2.0 filtering, pagination, and sorting."""
    
    try:
        # Validate filter if provided
        if filter and not SCIMFilterValidator.validate(filter, "Group"):
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
            db, Group, filter, startIndex, count, sortBy, sortOrder, str(tenant.id)
        )
        
        groups, metadata = query_builder.execute(db)
        
        # Convert to SCIM format
        base_url = f"{request.url.scheme}://{request.url.netloc}/scim/v2"
        scim_groups = []
        
        for group in groups:
            scim_group = SCIMMapper.group_to_scim(group, base_url, db)
            scim_groups.append(scim_group.dict(by_alias=True))
        
        # Create list response
        list_response = SCIMListResponse(
            totalResults=metadata['totalResults'],
            startIndex=metadata['startIndex'],
            itemsPerPage=metadata['itemsPerPage'],
            Resources=scim_groups
        )
        
        # Log operation
        log_scim_operation(db, str(tenant.id), "LIST", request=request, 
                         response_status=200, response_body={"count": len(scim_groups)})
        
        return list_response
        
    except Exception as e:
        error = SCIMError(
            status="500",
            detail=f"Internal server error: {str(e)}"
        )
        log_scim_operation(db, str(tenant.id), "LIST", request=request,
                         response_status=500, error_message=str(e))
        return JSONResponse(status_code=500, content=error.dict(by_alias=True))


@router.get("/Groups/{group_id}", response_model=SCIMGroup)
async def get_group(
    group_id: str,
    request: Request,
    response: Response,
    attributes: Optional[str] = Query(None, description="Comma-separated list of attributes to return"),
    excludedAttributes: Optional[str] = Query(None, description="Comma-separated list of attributes to exclude"),
    db: Session = Depends(get_db),
    tenant: Tenant = Depends(get_current_tenant),
    _: bool = Depends(require_scim_permission("groups:read"))
):
    """Get group by ID."""
    
    try:
        # Find group
        group = db.query(Group).filter(
            Group.id == UUID(group_id),
            Group.tenant_id == tenant.id
        ).first()
        
        if not group:
            error = SCIMError(
                status="404",
                detail=f"Group {group_id} not found"
            )
            log_scim_operation(db, str(tenant.id), "GET", resource_id=group_id,
                             request=request, response_status=404, error_message="Group not found")
            return JSONResponse(status_code=404, content=error.dict(by_alias=True))
        
        # Convert to SCIM format
        base_url = f"{request.url.scheme}://{request.url.netloc}/scim/v2"
        scim_group = SCIMMapper.group_to_scim(group, base_url, db)
        
        # Set ETag header for version control
        from ...models import get_version_etag
        etag = get_version_etag(group)
        response.headers["ETag"] = f'"{etag}"'
        
        # Log operation
        log_scim_operation(db, str(tenant.id), "GET", resource_id=group_id,
                         external_id=group.external_id, request=request, response_status=200)
        
        return scim_group
        
    except ValueError:
        error = SCIMError(
            status="400",
            detail="Invalid group ID format"
        )
        return JSONResponse(status_code=400, content=error.dict(by_alias=True))
    except Exception as e:
        error = SCIMError(
            status="500",
            detail=f"Internal server error: {str(e)}"
        )
        log_scim_operation(db, str(tenant.id), "GET", resource_id=group_id,
                         request=request, response_status=500, error_message=str(e))
        return JSONResponse(status_code=500, content=error.dict(by_alias=True))


@router.post("/Groups", response_model=SCIMGroup, status_code=201)
async def create_group(
    group_data: SCIMGroupCreate,
    request: Request,
    response: Response,
    db: Session = Depends(get_db),
    tenant: Tenant = Depends(get_current_tenant),
    _: bool = Depends(require_scim_permission("groups:write"))
):
    """Create a new group."""
    
    try:
        # Convert SCIM data to Group model
        group = SCIMMapper.scim_to_group(group_data, str(tenant.id))
        group.id = uuid4()
        
        # Add to database
        db.add(group)
        db.commit()
        db.refresh(group)
        
        # Handle member assignments if provided
        if group_data.members:
            for member_ref in group_data.members:
                # Validate member exists
                user = db.query(User).filter(
                    User.id == UUID(member_ref.value),
                    User.tenant_id == tenant.id
                ).first()
                
                if user:
                    membership = GroupMembership(
                        id=uuid4(),
                        group_id=group.id,
                        user_id=user.id,
                        tenant_id=tenant.id,
                        added_at=datetime.utcnow(),
                        sis_source_id=getattr(member_ref, 'sis_source_id', None)
                    )
                    db.add(membership)
                    
                    # Emit event
                    await emit_user_added_to_group(str(tenant.id), str(user.id), str(group.id))
        
        if group_data.members:
            db.commit()
        
        # Convert back to SCIM format
        base_url = f"{request.url.scheme}://{request.url.netloc}/scim/v2"
        scim_group = SCIMMapper.group_to_scim(group, base_url, db)
        
        # Set Location header
        response.headers["Location"] = f"{base_url}/Groups/{group.id}"
        
        # Set ETag header
        from ...models import get_version_etag
        etag = get_version_etag(group)
        response.headers["ETag"] = f'"{etag}"'
        
        # Emit events
        await emit_group_created(str(tenant.id), str(group.id), group_data.dict())
        
        # Log operation
        log_scim_operation(db, str(tenant.id), "CREATE", resource_id=str(group.id),
                         external_id=group.external_id, request=request, response_status=201)
        
        return scim_group
        
    except IntegrityError as e:
        db.rollback()
        error = SCIMError(
            status="409",
            scimType="uniqueness",
            detail="Group already exists with this displayName or externalId"
        )
        log_scim_operation(db, str(tenant.id), "CREATE",
                         external_id=group_data.external_id,
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
                         external_id=group_data.external_id,
                         request=request, response_status=500, error_message=str(e))
        return JSONResponse(status_code=500, content=error.dict(by_alias=True))


@router.put("/Groups/{group_id}", response_model=SCIMGroup)
async def replace_group(
    group_id: str,
    group_data: SCIMGroupCreate,
    request: Request,
    response: Response,
    db: Session = Depends(get_db),
    tenant: Tenant = Depends(get_current_tenant),
    _: bool = Depends(require_scim_permission("groups:write"))
):
    """Replace group (full update)."""
    
    try:
        # Find existing group
        group = db.query(Group).filter(
            Group.id == UUID(group_id),
            Group.tenant_id == tenant.id
        ).first()
        
        if not group:
            error = SCIMError(
                status="404",
                detail=f"Group {group_id} not found"
            )
            log_scim_operation(db, str(tenant.id), "REPLACE", resource_id=group_id,
                             request=request, response_status=404, error_message="Group not found")
            return JSONResponse(status_code=404, content=error.dict(by_alias=True))
        
        # Check ETag for optimistic concurrency control
        if_match = request.headers.get("If-Match")
        if if_match:
            from ...models import get_version_etag
            current_etag = get_version_etag(group)
            if if_match.strip('"') != current_etag:
                error = SCIMError(
                    status="409",
                    scimType="mutability",
                    detail="Resource version conflict"
                )
                return JSONResponse(status_code=409, content=error.dict(by_alias=True))
        
        # Update group attributes
        group = SCIMMapper.update_group_from_scim(group, group_data.dict(by_alias=True))
        
        # Handle membership changes - replace all memberships
        # Remove existing memberships
        existing_memberships = db.query(GroupMembership).filter(
            GroupMembership.group_id == group.id
        ).all()
        
        for membership in existing_memberships:
            db.delete(membership)
            await emit_user_removed_from_group(str(tenant.id), str(membership.user_id), str(group.id))
        
        # Add new memberships
        if group_data.members:
            for member_ref in group_data.members:
                # Validate member exists
                user = db.query(User).filter(
                    User.id == UUID(member_ref.value),
                    User.tenant_id == tenant.id
                ).first()
                
                if user:
                    membership = GroupMembership(
                        id=uuid4(),
                        group_id=group.id,
                        user_id=user.id,
                        tenant_id=tenant.id,
                        added_at=datetime.utcnow(),
                        sis_source_id=getattr(member_ref, 'sis_source_id', None)
                    )
                    db.add(membership)
                    
                    # Emit event
                    await emit_user_added_to_group(str(tenant.id), str(user.id), str(group.id))
        
        # Update version and timestamp
        increment_version(group)
        
        db.commit()
        db.refresh(group)
        
        # Convert back to SCIM format
        base_url = f"{request.url.scheme}://{request.url.netloc}/scim/v2"
        scim_group = SCIMMapper.group_to_scim(group, base_url, db)
        
        # Set ETag header
        from ...models import get_version_etag
        etag = get_version_etag(group)
        response.headers["ETag"] = f'"{etag}"'
        
        # Log operation
        log_scim_operation(db, str(tenant.id), "REPLACE", resource_id=group_id,
                         external_id=group.external_id, request=request, response_status=200)
        
        return scim_group
        
    except ValueError:
        error = SCIMError(
            status="400",
            detail="Invalid group ID format"
        )
        return JSONResponse(status_code=400, content=error.dict(by_alias=True))
    except Exception as e:
        db.rollback()
        error = SCIMError(
            status="500",
            detail=f"Internal server error: {str(e)}"
        )
        log_scim_operation(db, str(tenant.id), "REPLACE", resource_id=group_id,
                         request=request, response_status=500, error_message=str(e))
        return JSONResponse(status_code=500, content=error.dict(by_alias=True))


@router.patch("/Groups/{group_id}", response_model=SCIMGroup)
async def patch_group(
    group_id: str,
    patch_data: SCIMGroupPatch,
    request: Request,
    response: Response,
    db: Session = Depends(get_db),
    tenant: Tenant = Depends(get_current_tenant),
    _: bool = Depends(require_scim_permission("groups:write"))
):
    """Patch group (partial update)."""
    
    try:
        # Find existing group
        group = db.query(Group).filter(
            Group.id == UUID(group_id),
            Group.tenant_id == tenant.id
        ).first()
        
        if not group:
            error = SCIMError(
                status="404",
                detail=f"Group {group_id} not found"
            )
            log_scim_operation(db, str(tenant.id), "PATCH", resource_id=group_id,
                             request=request, response_status=404, error_message="Group not found")
            return JSONResponse(status_code=404, content=error.dict(by_alias=True))
        
        # Apply patch operations
        await SCIMPatchProcessor.apply_group_patch_operations(group, patch_data.operations, db, tenant.id)
        
        # Update version and timestamp
        increment_version(group)
        
        db.commit()
        db.refresh(group)
        
        # Convert back to SCIM format
        base_url = f"{request.url.scheme}://{request.url.netloc}/scim/v2"
        scim_group = SCIMMapper.group_to_scim(group, base_url, db)
        
        # Set ETag header
        from ...models import get_version_etag
        etag = get_version_etag(group)
        response.headers["ETag"] = f'"{etag}"'
        
        # Log operation
        log_scim_operation(db, str(tenant.id), "PATCH", resource_id=group_id,
                         external_id=group.external_id, request=request, response_status=200)
        
        return scim_group
        
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
        log_scim_operation(db, str(tenant.id), "PATCH", resource_id=group_id,
                         request=request, response_status=500, error_message=str(e))
        return JSONResponse(status_code=500, content=error.dict(by_alias=True))


@router.delete("/Groups/{group_id}", status_code=204)
async def delete_group(
    group_id: str,
    request: Request,
    response: Response,
    db: Session = Depends(get_db),
    tenant: Tenant = Depends(get_current_tenant),
    _: bool = Depends(require_scim_permission("groups:write"))
):
    """Delete group."""
    
    try:
        # Find existing group
        group = db.query(Group).filter(
            Group.id == UUID(group_id),
            Group.tenant_id == tenant.id
        ).first()
        
        if not group:
            error = SCIMError(
                status="404",
                detail=f"Group {group_id} not found"
            )
            log_scim_operation(db, str(tenant.id), "DELETE", resource_id=group_id,
                             request=request, response_status=404, error_message="Group not found")
            return JSONResponse(status_code=404, content=error.dict(by_alias=True))
        
        # Remove all group memberships first
        memberships = db.query(GroupMembership).filter(
            GroupMembership.group_id == group.id
        ).all()
        
        for membership in memberships:
            db.delete(membership)
            await emit_user_removed_from_group(str(tenant.id), str(membership.user_id), str(group.id))
        
        # Delete the group
        db.delete(group)
        db.commit()
        
        # Emit events
        await emit_group_deleted(str(tenant.id), str(group.id))
        
        # Log operation
        log_scim_operation(db, str(tenant.id), "DELETE", resource_id=group_id,
                         external_id=group.external_id, request=request, response_status=204)
        
        return Response(status_code=204)
        
    except ValueError:
        error = SCIMError(
            status="400",
            detail="Invalid group ID format"
        )
        return JSONResponse(status_code=400, content=error.dict(by_alias=True))
    except Exception as e:
        db.rollback()
        error = SCIMError(
            status="500",
            detail=f"Internal server error: {str(e)}"
        )
        log_scim_operation(db, str(tenant.id), "DELETE", resource_id=group_id,
                         request=request, response_status=500, error_message=str(e))
        return JSONResponse(status_code=500, content=error.dict(by_alias=True))
