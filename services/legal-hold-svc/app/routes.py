"""
Legal Hold & eDiscovery API Routes

RESTful endpoints for managing legal preservation requirements,
eDiscovery exports, and compliance auditing.
"""

import asyncio
import json
import logging
from datetime import datetime, timezone, timedelta
from typing import List, Optional, Dict, Any
from uuid import UUID, uuid4
from pathlib import Path

from fastapi import (
    APIRouter, Depends, HTTPException, Query, BackgroundTasks, 
    UploadFile, File, Form, Response
)
from fastapi.responses import StreamingResponse, FileResponse
from sqlalchemy.orm import Session, selectinload
from sqlalchemy import and_, or_, desc, func, text
from pydantic import BaseModel, Field, validator

from .models import (
    LegalHold, HoldCustodian, HoldAffectedEntity, eDiscoveryExport,
    ExportItem, HoldAuditLog, ExportAccessLog, DataRetentionOverride,
    HoldStatus, ExportStatus
)

logger = logging.getLogger(__name__)

# Pydantic schemas for request/response
class LegalHoldCreate(BaseModel):
    """Schema for creating a legal hold"""
    title: str = Field(..., min_length=1, max_length=200)
    description: Optional[str] = None
    case_number: Optional[str] = None
    court_jurisdiction: Optional[str] = None
    legal_basis: str = Field(..., description="litigation, investigation, regulatory, compliance")
    custodian_attorney: Optional[str] = None
    
    scope_type: str = Field(..., description="tenant, learner, teacher, classroom, timerange, custom")
    scope_parameters: Dict[str, Any] = Field(..., description="Flexible scope definition")
    
    data_start_date: Optional[datetime] = None
    data_end_date: Optional[datetime] = None
    expiration_date: Optional[datetime] = None
    
    preserve_deleted_data: bool = True
    preserve_system_logs: bool = True
    preserve_communications: bool = True
    preserve_file_metadata: bool = True
    
    custodian_user_ids: List[UUID] = []
    notify_custodians: bool = True

    @validator('legal_basis')
    def validate_legal_basis(cls, v):
        allowed = ['litigation', 'investigation', 'regulatory', 'compliance']
        if v not in allowed:
            raise ValueError(f'Legal basis must be one of: {", ".join(allowed)}')
        return v

    @validator('scope_type')
    def validate_scope_type(cls, v):
        allowed = ['tenant', 'learner', 'teacher', 'classroom', 'timerange', 'custom']
        if v not in allowed:
            raise ValueError(f'Scope type must be one of: {", ".join(allowed)}')
        return v


class LegalHoldUpdate(BaseModel):
    """Schema for updating a legal hold"""
    title: Optional[str] = None
    description: Optional[str] = None
    expiration_date: Optional[datetime] = None
    status: Optional[str] = None
    
    @validator('status')
    def validate_status(cls, v):
        if v and v not in ['active', 'released', 'expired', 'suspended']:
            raise ValueError('Status must be active, released, expired, or suspended')
        return v


class LegalHoldResponse(BaseModel):
    """Schema for legal hold responses"""
    id: UUID
    hold_number: str
    title: str
    description: Optional[str]
    case_number: Optional[str]
    legal_basis: str
    status: str
    scope_type: str
    scope_parameters: Dict[str, Any]
    effective_date: datetime
    expiration_date: Optional[datetime]
    created_at: datetime
    affected_entities_count: int = 0
    custodians_count: int = 0

    class Config:
        from_attributes = True


class eDiscoveryExportCreate(BaseModel):
    """Schema for creating an eDiscovery export"""
    title: str = Field(..., min_length=1, max_length=200)
    description: Optional[str] = None
    
    export_format: str = Field(default="structured_json", description="structured_json, pst, pdf, native")
    include_metadata: bool = True
    include_system_logs: bool = True
    include_deleted_data: bool = False
    
    date_range_start: Optional[datetime] = None
    date_range_end: Optional[datetime] = None
    data_types: List[str] = ["chat", "audit", "files", "assessments"]
    entity_filters: Dict[str, Any] = {}
    
    requesting_attorney: Optional[str] = None
    urgency: str = Field(default="normal", description="low, normal, high, urgent")

    @validator('export_format')
    def validate_export_format(cls, v):
        allowed = ['structured_json', 'pst', 'pdf', 'native']
        if v not in allowed:
            raise ValueError(f'Export format must be one of: {", ".join(allowed)}')
        return v


class eDiscoveryExportResponse(BaseModel):
    """Schema for eDiscovery export responses"""
    id: UUID
    export_number: str
    title: str
    status: str
    progress_percentage: int
    total_records: int
    exported_records: int
    file_count: int
    total_size_bytes: int
    requested_date: datetime
    completed_date: Optional[datetime]
    archive_location: Optional[str]

    class Config:
        from_attributes = True


class HoldAuditLogResponse(BaseModel):
    """Schema for hold audit log responses"""
    id: UUID
    hold_id: UUID
    event_type: str
    event_description: str
    user_name: Optional[str]
    event_timestamp: datetime
    risk_level: str
    affected_entity_type: Optional[str]
    affected_entity_id: Optional[str]

    class Config:
        from_attributes = True


# Dependency injection functions (these would be implemented in separate files)
def get_db():
    """Database session dependency - placeholder"""
    pass

def get_current_user():
    """Current user dependency - placeholder"""
    pass

def require_compliance_role():
    """Compliance role requirement - placeholder"""
    pass


# Router setup
legal_holds_router = APIRouter()
ediscovery_router = APIRouter()
compliance_router = APIRouter()
audit_router = APIRouter()


# Legal Holds Endpoints

@legal_holds_router.post("", response_model=LegalHoldResponse)
async def create_legal_hold(
    hold_data: LegalHoldCreate,
    background_tasks: BackgroundTasks,
    current_user = Depends(require_compliance_role),
    db: Session = Depends(get_db)
):
    """Create a new legal hold"""
    
    # Generate unique hold number
    hold_number = f"LH-{datetime.now().strftime('%Y%m%d')}-{str(uuid4())[:8].upper()}"
    
    # Create hold record
    hold = LegalHold(
        hold_number=hold_number,
        title=hold_data.title,
        description=hold_data.description,
        case_number=hold_data.case_number,
        court_jurisdiction=hold_data.court_jurisdiction,
        legal_basis=hold_data.legal_basis,
        custodian_attorney=hold_data.custodian_attorney,
        scope_type=hold_data.scope_type,
        scope_parameters=hold_data.scope_parameters,
        data_start_date=hold_data.data_start_date,
        data_end_date=hold_data.data_end_date,
        expiration_date=hold_data.expiration_date,
        preserve_deleted_data=hold_data.preserve_deleted_data,
        preserve_system_logs=hold_data.preserve_system_logs,
        preserve_communications=hold_data.preserve_communications,
        preserve_file_metadata=hold_data.preserve_file_metadata,
        created_by=current_user.id,
        status=HoldStatus.ACTIVE.value
    )
    
    db.add(hold)
    db.flush()  # Get the hold ID
    
    # Add custodians
    for user_id in hold_data.custodian_user_ids:
        custodian = HoldCustodian(
            hold_id=hold.id,
            user_id=user_id,
            tenant_id=current_user.tenant_id,
            name="",  # Would be populated from user service
            email="",  # Would be populated from user service
        )
        db.add(custodian)
    
    # Apply hold to affected entities
    background_tasks.add_task(apply_hold_to_entities, hold.id, hold_data.scope_parameters)
    
    # Send notifications to custodians
    if hold_data.notify_custodians:
        background_tasks.add_task(notify_custodians, hold.id)
    
    # Create audit log entry
    audit_log = HoldAuditLog(
        hold_id=hold.id,
        event_type="hold_created",
        event_description=f"Legal hold '{hold.title}' created for case {hold.case_number}",
        event_category="administrative",
        user_id=current_user.id,
        user_name=current_user.name,
        user_role=current_user.role,
        tenant_id=current_user.tenant_id,
        risk_level="medium",
        event_metadata={"scope_type": hold.scope_type, "legal_basis": hold.legal_basis}
    )
    db.add(audit_log)
    
    db.commit()
    db.refresh(hold)
    
    logger.info(f"Legal hold {hold.hold_number} created by {current_user.name}")
    
    return LegalHoldResponse(
        id=hold.id,
        hold_number=hold.hold_number,
        title=hold.title,
        description=hold.description,
        case_number=hold.case_number,
        legal_basis=hold.legal_basis,
        status=hold.status,
        scope_type=hold.scope_type,
        scope_parameters=hold.scope_parameters,
        effective_date=hold.effective_date,
        expiration_date=hold.expiration_date,
        created_at=hold.created_at,
        affected_entities_count=0,
        custodians_count=len(hold_data.custodian_user_ids)
    )


@legal_holds_router.get("", response_model=List[LegalHoldResponse])
async def list_legal_holds(
    status: Optional[str] = Query(None),
    case_number: Optional[str] = Query(None),
    limit: int = Query(50, le=500),
    offset: int = Query(0, ge=0),
    current_user = Depends(require_compliance_role),
    db: Session = Depends(get_db)
):
    """List legal holds with filtering"""
    
    query = db.query(LegalHold)
    
    if status:
        query = query.filter(LegalHold.status == status)
    
    if case_number:
        query = query.filter(LegalHold.case_number.ilike(f"%{case_number}%"))
    
    # Apply tenant filtering for non-admin users
    if current_user.role not in ["admin", "super_admin"]:
        query = query.filter(LegalHold.created_by == current_user.id)
    
    holds = query.order_by(desc(LegalHold.created_at)).offset(offset).limit(limit).all()
    
    # Build response with counts
    response_holds = []
    for hold in holds:
        entities_count = db.query(HoldAffectedEntity).filter(
            HoldAffectedEntity.hold_id == hold.id
        ).count()
        
        custodians_count = db.query(HoldCustodian).filter(
            HoldCustodian.hold_id == hold.id
        ).count()
        
        response_holds.append(LegalHoldResponse(
            id=hold.id,
            hold_number=hold.hold_number,
            title=hold.title,
            description=hold.description,
            case_number=hold.case_number,
            legal_basis=hold.legal_basis,
            status=hold.status,
            scope_type=hold.scope_type,
            scope_parameters=hold.scope_parameters,
            effective_date=hold.effective_date,
            expiration_date=hold.expiration_date,
            created_at=hold.created_at,
            affected_entities_count=entities_count,
            custodians_count=custodians_count
        ))
    
    return response_holds


@legal_holds_router.get("/{hold_id}", response_model=LegalHoldResponse)
async def get_legal_hold(
    hold_id: UUID,
    current_user = Depends(require_compliance_role),
    db: Session = Depends(get_db)
):
    """Get specific legal hold details"""
    
    hold = db.query(LegalHold).options(
        selectinload(LegalHold.hold_custodians),
        selectinload(LegalHold.affected_entities)
    ).filter(LegalHold.id == hold_id).first()
    
    if not hold:
        raise HTTPException(status_code=404, detail="Legal hold not found")
    
    # Check permissions
    if current_user.role not in ["admin", "super_admin"] and hold.created_by != current_user.id:
        raise HTTPException(status_code=403, detail="Access denied")
    
    # Log access
    audit_log = HoldAuditLog(
        hold_id=hold.id,
        event_type="hold_accessed",
        event_description=f"Legal hold {hold.hold_number} accessed",
        event_category="access",
        user_id=current_user.id,
        user_name=current_user.name,
        user_role=current_user.role,
        tenant_id=current_user.tenant_id,
        risk_level="low"
    )
    db.add(audit_log)
    db.commit()
    
    return LegalHoldResponse(
        id=hold.id,
        hold_number=hold.hold_number,
        title=hold.title,
        description=hold.description,
        case_number=hold.case_number,
        legal_basis=hold.legal_basis,
        status=hold.status,
        scope_type=hold.scope_type,
        scope_parameters=hold.scope_parameters,
        effective_date=hold.effective_date,
        expiration_date=hold.expiration_date,
        created_at=hold.created_at,
        affected_entities_count=len(hold.affected_entities),
        custodians_count=len(hold.hold_custodians)
    )


@legal_holds_router.put("/{hold_id}", response_model=LegalHoldResponse)
async def update_legal_hold(
    hold_id: UUID,
    hold_update: LegalHoldUpdate,
    current_user = Depends(require_compliance_role),
    db: Session = Depends(get_db)
):
    """Update legal hold"""
    
    hold = db.query(LegalHold).filter(LegalHold.id == hold_id).first()
    
    if not hold:
        raise HTTPException(status_code=404, detail="Legal hold not found")
    
    # Check permissions
    if current_user.role not in ["admin", "super_admin"] and hold.created_by != current_user.id:
        raise HTTPException(status_code=403, detail="Access denied")
    
    # Store original values for audit
    original_values = {
        "title": hold.title,
        "description": hold.description,
        "status": hold.status,
        "expiration_date": hold.expiration_date.isoformat() if hold.expiration_date else None
    }
    
    # Update fields
    if hold_update.title is not None:
        hold.title = hold_update.title
    if hold_update.description is not None:
        hold.description = hold_update.description
    if hold_update.expiration_date is not None:
        hold.expiration_date = hold_update.expiration_date
    if hold_update.status is not None:
        if hold_update.status == "released":
            hold.released_by = current_user.id
            hold.released_date = datetime.now(timezone.utc)
        hold.status = hold_update.status
    
    # Create audit log entry
    new_values = {
        "title": hold.title,
        "description": hold.description,
        "status": hold.status,
        "expiration_date": hold.expiration_date.isoformat() if hold.expiration_date else None
    }
    
    audit_log = HoldAuditLog(
        hold_id=hold.id,
        event_type="hold_modified",
        event_description=f"Legal hold {hold.hold_number} updated",
        event_category="administrative",
        user_id=current_user.id,
        user_name=current_user.name,
        user_role=current_user.role,
        tenant_id=current_user.tenant_id,
        before_values=original_values,
        after_values=new_values,
        risk_level="medium"
    )
    db.add(audit_log)
    
    db.commit()
    db.refresh(hold)
    
    logger.info(f"Legal hold {hold.hold_number} updated by {current_user.name}")
    
    return LegalHoldResponse(
        id=hold.id,
        hold_number=hold.hold_number,
        title=hold.title,
        description=hold.description,
        case_number=hold.case_number,
        legal_basis=hold.legal_basis,
        status=hold.status,
        scope_type=hold.scope_type,
        scope_parameters=hold.scope_parameters,
        effective_date=hold.effective_date,
        expiration_date=hold.expiration_date,
        created_at=hold.created_at,
        affected_entities_count=0,
        custodians_count=0
    )


# eDiscovery Export Endpoints

@ediscovery_router.post("/{hold_id}/exports", response_model=eDiscoveryExportResponse)
async def create_export(
    hold_id: UUID,
    export_data: eDiscoveryExportCreate,
    background_tasks: BackgroundTasks,
    current_user = Depends(require_compliance_role),
    db: Session = Depends(get_db)
):
    """Create eDiscovery export for legal hold"""
    
    # Verify hold exists and is accessible
    hold = db.query(LegalHold).filter(LegalHold.id == hold_id).first()
    if not hold:
        raise HTTPException(status_code=404, detail="Legal hold not found")
    
    if current_user.role not in ["admin", "super_admin"] and hold.created_by != current_user.id:
        raise HTTPException(status_code=403, detail="Access denied")
    
    # Generate export number
    export_number = f"ED-{datetime.now().strftime('%Y%m%d')}-{str(uuid4())[:8].upper()}"
    
    # Create export record
    export = eDiscoveryExport(
        hold_id=hold_id,
        export_number=export_number,
        title=export_data.title,
        description=export_data.description,
        export_format=export_data.export_format,
        include_metadata=export_data.include_metadata,
        include_system_logs=export_data.include_system_logs,
        include_deleted_data=export_data.include_deleted_data,
        date_range_start=export_data.date_range_start,
        date_range_end=export_data.date_range_end,
        data_types=export_data.data_types,
        entity_filters=export_data.entity_filters,
        requesting_attorney=export_data.requesting_attorney,
        requested_by=current_user.id,
        status=ExportStatus.PENDING.value
    )
    
    db.add(export)
    db.commit()
    db.refresh(export)
    
    # Start export processing in background
    background_tasks.add_task(process_ediscovery_export, export.id)
    
    # Create audit log
    audit_log = HoldAuditLog(
        hold_id=hold_id,
        event_type="export_requested",
        event_description=f"eDiscovery export {export.export_number} requested",
        event_category="compliance",
        user_id=current_user.id,
        user_name=current_user.name,
        user_role=current_user.role,
        tenant_id=current_user.tenant_id,
        risk_level="high",
        event_metadata={"export_format": export.export_format, "data_types": export.data_types}
    )
    db.add(audit_log)
    db.commit()
    
    logger.info(f"eDiscovery export {export.export_number} requested by {current_user.name}")
    
    return eDiscoveryExportResponse(
        id=export.id,
        export_number=export.export_number,
        title=export.title,
        status=export.status,
        progress_percentage=export.progress_percentage,
        total_records=export.total_records,
        exported_records=export.exported_records,
        file_count=export.file_count,
        total_size_bytes=export.total_size_bytes,
        requested_date=export.requested_date,
        completed_date=export.completed_date,
        archive_location=export.archive_location
    )


@ediscovery_router.get("/{hold_id}/exports", response_model=List[eDiscoveryExportResponse])
async def list_exports(
    hold_id: UUID,
    current_user = Depends(require_compliance_role),
    db: Session = Depends(get_db)
):
    """List eDiscovery exports for a legal hold"""
    
    # Verify access to hold
    hold = db.query(LegalHold).filter(LegalHold.id == hold_id).first()
    if not hold:
        raise HTTPException(status_code=404, detail="Legal hold not found")
    
    if current_user.role not in ["admin", "super_admin"] and hold.created_by != current_user.id:
        raise HTTPException(status_code=403, detail="Access denied")
    
    exports = db.query(eDiscoveryExport).filter(
        eDiscoveryExport.hold_id == hold_id
    ).order_by(desc(eDiscoveryExport.requested_date)).all()
    
    return [
        eDiscoveryExportResponse(
            id=export.id,
            export_number=export.export_number,
            title=export.title,
            status=export.status,
            progress_percentage=export.progress_percentage,
            total_records=export.total_records,
            exported_records=export.exported_records,
            file_count=export.file_count,
            total_size_bytes=export.total_size_bytes,
            requested_date=export.requested_date,
            completed_date=export.completed_date,
            archive_location=export.archive_location
        )
        for export in exports
    ]


# Background processing functions

async def apply_hold_to_entities(hold_id: UUID, scope_parameters: Dict[str, Any]):
    """Apply legal hold to entities based on scope"""
    # Implementation would:
    # 1. Query relevant entities based on scope
    # 2. Create HoldAffectedEntity records
    # 3. Apply retention overrides
    # 4. Notify other services
    pass


async def notify_custodians(hold_id: UUID):
    """Send notifications to hold custodians"""
    # Implementation would:
    # 1. Get custodian information
    # 2. Send notification emails
    # 3. Update notification status
    pass


async def process_ediscovery_export(export_id: UUID):
    """Process eDiscovery export in background"""
    # Implementation would:
    # 1. Collect data from various services
    # 2. Create export archive with manifest
    # 3. Generate checksums and signatures
    # 4. Update export status and location
    pass


# Audit endpoints

@audit_router.get("/holds/{hold_id}/logs", response_model=List[HoldAuditLogResponse])
async def get_hold_audit_logs(
    hold_id: UUID,
    limit: int = Query(100, le=1000),
    offset: int = Query(0, ge=0),
    current_user = Depends(require_compliance_role),
    db: Session = Depends(get_db)
):
    """Get audit logs for a specific legal hold"""
    
    # Verify access to hold
    hold = db.query(LegalHold).filter(LegalHold.id == hold_id).first()
    if not hold:
        raise HTTPException(status_code=404, detail="Legal hold not found")
    
    if current_user.role not in ["admin", "super_admin"] and hold.created_by != current_user.id:
        raise HTTPException(status_code=403, detail="Access denied")
    
    logs = db.query(HoldAuditLog).filter(
        HoldAuditLog.hold_id == hold_id
    ).order_by(desc(HoldAuditLog.event_timestamp)).offset(offset).limit(limit).all()
    
    return [
        HoldAuditLogResponse(
            id=log.id,
            hold_id=log.hold_id,
            event_type=log.event_type,
            event_description=log.event_description,
            user_name=log.user_name,
            event_timestamp=log.event_timestamp,
            risk_level=log.risk_level,
            affected_entity_type=log.affected_entity_type,
            affected_entity_id=log.affected_entity_id
        )
        for log in logs
    ]


# Compliance endpoints

@compliance_router.post("/check-retention-override")
async def check_retention_override(
    entity_type: str,
    entity_id: str,
    tenant_id: UUID,
    current_user = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Check if entity has active retention override due to legal hold"""
    
    # Check for active retention overrides
    override = db.query(DataRetentionOverride).filter(
        and_(
            DataRetentionOverride.entity_type == entity_type,
            DataRetentionOverride.entity_id == entity_id,
            DataRetentionOverride.tenant_id == tenant_id,
            DataRetentionOverride.is_active == True
        )
    ).first()
    
    if override:
        return {
            "has_override": True,
            "override_reason": override.override_reason,
            "override_reference": override.override_reference,
            "override_start_date": override.override_start_date,
            "override_end_date": override.override_end_date
        }
    
    return {"has_override": False}


@compliance_router.post("/block-deletion")
async def block_deletion_attempt(
    entity_type: str,
    entity_id: str,
    tenant_id: UUID,
    attempted_by: UUID,
    current_user = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Record blocked deletion attempt due to legal hold"""
    
    # Find affected entity record
    affected_entity = db.query(HoldAffectedEntity).filter(
        and_(
            HoldAffectedEntity.entity_type == entity_type,
            HoldAffectedEntity.entity_id == entity_id,
            HoldAffectedEntity.tenant_id == tenant_id
        )
    ).first()
    
    if affected_entity:
        # Increment blocked attempts counter
        affected_entity.deletion_attempts_blocked += 1
        affected_entity.last_access_attempt = datetime.now(timezone.utc)
        
        # Create audit log
        audit_log = HoldAuditLog(
            hold_id=affected_entity.hold_id,
            event_type="deletion_blocked",
            event_description=f"Deletion attempt blocked for {entity_type} {entity_id}",
            event_category="compliance",
            user_id=attempted_by,
            tenant_id=tenant_id,
            affected_entity_type=entity_type,
            affected_entity_id=entity_id,
            risk_level="high",
            event_metadata={"blocked_at": datetime.now(timezone.utc).isoformat()}
        )
        db.add(audit_log)
        
        db.commit()
        
        logger.warning(f"Deletion blocked for {entity_type} {entity_id} due to legal hold")
        
        return {
            "deletion_blocked": True,
            "hold_id": affected_entity.hold_id,
            "message": "Deletion blocked due to active legal hold"
        }
    
    return {"deletion_blocked": False}
