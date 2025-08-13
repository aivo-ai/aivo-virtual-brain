# AIVO IEP Service - GraphQL Resolvers
# S1-11 Implementation - Strawberry GraphQL Resolvers with CRDT Support

import strawberry
from typing import List, Optional, Dict, Any, AsyncGenerator
from datetime import datetime, timezone
from sqlalchemy.orm import Session
from sqlalchemy import and_, or_, desc
import uuid
import json
import logging

from .models import IEP as IEPModel, IEPSection as IEPSectionModel, ESignature as ESignatureModel
from .models import EvidenceAttachment as EvidenceAttachmentModel, CRDTOperationLog
from .schema import (
    IEP, IEPSection, ESignature, EvidenceAttachment, CRDTOperation,
    IEPCreateInput, IEPSectionUpsertInput, CRDTOperationInput,
    EvidenceAttachmentInput, ESignatureInviteInput,
    IEPMutationResponse, IEPSectionMutationResponse, EvidenceAttachmentResponse,
    ESignatureResponse, IEPUpdateEvent, IEPFilterInput, PaginationInput, IEPConnection,
    IEPStatus, SectionType, SignatureRole
)
from .database import get_db
from .crdt_engine import CRDTEngine
from .signature_service import ESignatureService

logger = logging.getLogger(__name__)

# Helper function to convert SQLAlchemy models to GraphQL types
def convert_iep_model_to_graphql(iep_model: IEPModel) -> IEP:
    """Convert SQLAlchemy IEP model to GraphQL IEP type."""
    return IEP(
        id=str(iep_model.id),
        student_id=iep_model.student_id,
        tenant_id=iep_model.tenant_id,
        school_district=iep_model.school_district,
        school_name=iep_model.school_name,
        title=iep_model.title,
        academic_year=iep_model.academic_year,
        grade_level=iep_model.grade_level,
        status=IEPStatus(iep_model.status.value),
        version=iep_model.version,
        is_current=iep_model.is_current,
        effective_date=iep_model.effective_date,
        expiration_date=iep_model.expiration_date,
        next_review_date=iep_model.next_review_date,
        crdt_state=iep_model.crdt_state,
        last_operation_id=iep_model.last_operation_id,
        signature_required_roles=iep_model.signature_required_roles,
        signature_deadline=iep_model.signature_deadline,
        content_hash=iep_model.content_hash,
        created_by=iep_model.created_by,
        created_at=iep_model.created_at,
        updated_by=iep_model.updated_by,
        updated_at=iep_model.updated_at,
        sections=[convert_section_model_to_graphql(section) for section in iep_model.sections],
        signatures=[convert_signature_model_to_graphql(sig) for sig in iep_model.signatures],
        evidence_attachments=[convert_evidence_model_to_graphql(ev) for ev in iep_model.evidence_attachments]
    )

def convert_section_model_to_graphql(section_model: IEPSectionModel) -> IEPSection:
    """Convert SQLAlchemy IEPSection model to GraphQL IEPSection type."""
    return IEPSection(
        id=str(section_model.id),
        section_type=SectionType(section_model.section_type.value),
        title=section_model.title,
        order_index=section_model.order_index,
        content=section_model.content,
        operation_counter=section_model.operation_counter,
        last_editor_id=section_model.last_editor_id,
        last_edited_at=section_model.last_edited_at,
        is_required=section_model.is_required,
        is_locked=section_model.is_locked,
        validation_rules=section_model.validation_rules,
        created_at=section_model.created_at,
        updated_at=section_model.updated_at
    )

def convert_signature_model_to_graphql(signature_model: ESignatureModel) -> ESignature:
    """Convert SQLAlchemy ESignature model to GraphQL ESignature type."""
    return ESignature(
        id=str(signature_model.id),
        signer_id=signature_model.signer_id,
        signer_name=signature_model.signer_name,
        signer_email=signature_model.signer_email,
        signer_role=SignatureRole(signature_model.signer_role.value),
        is_signed=signature_model.is_signed,
        signed_at=signature_model.signed_at,
        signature_method=signature_model.signature_method,
        auth_method=signature_model.auth_method,
        invitation_sent_at=signature_model.invitation_sent_at,
        expires_at=signature_model.expires_at,
        created_at=signature_model.created_at
    )

def convert_evidence_model_to_graphql(evidence_model: EvidenceAttachmentModel) -> EvidenceAttachment:
    """Convert SQLAlchemy EvidenceAttachment model to GraphQL EvidenceAttachment type."""
    return EvidenceAttachment(
        id=str(evidence_model.id),
        filename=evidence_model.filename,
        original_filename=evidence_model.original_filename,
        content_type=evidence_model.content_type,
        file_size=evidence_model.file_size,
        evidence_type=evidence_model.evidence_type,
        description=evidence_model.description,
        tags=evidence_model.tags or [],
        is_confidential=evidence_model.is_confidential,
        access_level=evidence_model.access_level,
        uploaded_by=evidence_model.uploaded_by,
        uploaded_at=evidence_model.uploaded_at
    )

@strawberry.type
class Query:
    """GraphQL Query root with IEP operations."""
    
    @strawberry.field
    async def iep(self, id: str) -> Optional[IEP]:
        """Get a single IEP by ID."""
        try:
            db = next(get_db())
            iep_model = db.query(IEPModel).filter(IEPModel.id == uuid.UUID(id)).first()
            
            if not iep_model:
                return None
                
            return convert_iep_model_to_graphql(iep_model)
            
        except Exception as e:
            logger.error(f"Error fetching IEP {id}: {str(e)}")
            return None
        finally:
            db.close()
    
    @strawberry.field
    async def ieps(
        self,
        filters: Optional[IEPFilterInput] = None,
        pagination: Optional[PaginationInput] = None
    ) -> IEPConnection:
        """Get filtered and paginated IEPs."""
        try:
            db = next(get_db())
            
            # Build base query
            query = db.query(IEPModel)
            
            # Apply filters
            if filters:
                if filters.student_id:
                    query = query.filter(IEPModel.student_id == filters.student_id)
                if filters.tenant_id:
                    query = query.filter(IEPModel.tenant_id == filters.tenant_id)
                if filters.status:
                    query = query.filter(IEPModel.status == filters.status.value)
                if filters.academic_year:
                    query = query.filter(IEPModel.academic_year == filters.academic_year)
                if filters.is_current is not None:
                    query = query.filter(IEPModel.is_current == filters.is_current)
                if filters.created_after:
                    query = query.filter(IEPModel.created_at >= filters.created_after)
                if filters.created_before:
                    query = query.filter(IEPModel.created_at <= filters.created_before)
            
            # Get total count
            total_count = query.count()
            
            # Apply pagination and ordering
            if pagination:
                if pagination.order_by:
                    if pagination.order_direction == "DESC":
                        query = query.order_by(desc(getattr(IEPModel, pagination.order_by, IEPModel.created_at)))
                    else:
                        query = query.order_by(getattr(IEPModel, pagination.order_by, IEPModel.created_at))
                else:
                    query = query.order_by(desc(IEPModel.created_at))
                
                query = query.offset(pagination.offset).limit(pagination.limit)
            else:
                query = query.order_by(desc(IEPModel.created_at)).limit(50)
            
            iep_models = query.all()
            
            return IEPConnection(
                items=[convert_iep_model_to_graphql(iep) for iep in iep_models],
                total_count=total_count,
                has_next_page=len(iep_models) == (pagination.limit if pagination else 50),
                has_previous_page=(pagination.offset if pagination else 0) > 0
            )
            
        except Exception as e:
            logger.error(f"Error fetching IEPs: {str(e)}")
            return IEPConnection(items=[], total_count=0, has_next_page=False, has_previous_page=False)
        finally:
            db.close()
    
    @strawberry.field
    async def iep_versions(self, student_id: str, tenant_id: str) -> List[IEP]:
        """Get all versions of IEPs for a student."""
        try:
            db = next(get_db())
            iep_models = db.query(IEPModel).filter(
                and_(
                    IEPModel.student_id == student_id,
                    IEPModel.tenant_id == tenant_id
                )
            ).order_by(desc(IEPModel.version)).all()
            
            return [convert_iep_model_to_graphql(iep) for iep in iep_models]
            
        except Exception as e:
            logger.error(f"Error fetching IEP versions for student {student_id}: {str(e)}")
            return []
        finally:
            db.close()

@strawberry.type
class Mutation:
    """GraphQL Mutation root with IEP operations."""
    
    @strawberry.mutation
    async def create_iep(self, input: IEPCreateInput) -> IEPMutationResponse:
        """Create a new IEP document."""
        try:
            db = next(get_db())
            
            # Create new IEP
            new_iep = IEPModel(
                student_id=input.student_id,
                tenant_id=input.tenant_id,
                school_district=input.school_district,
                school_name=input.school_name,
                title=input.title,
                academic_year=input.academic_year,
                grade_level=input.grade_level,
                effective_date=input.effective_date,
                expiration_date=input.expiration_date,
                signature_required_roles=input.signature_required_roles,
                created_by="system",  # TODO: Get from context
                updated_by="system"   # TODO: Get from context
            )
            
            db.add(new_iep)
            db.commit()
            db.refresh(new_iep)
            
            logger.info(f"Created new IEP {new_iep.id} for student {input.student_id}")
            
            return IEPMutationResponse(
                success=True,
                message="IEP created successfully",
                iep=convert_iep_model_to_graphql(new_iep)
            )
            
        except Exception as e:
            db.rollback()
            logger.error(f"Error creating IEP: {str(e)}")
            return IEPMutationResponse(
                success=False,
                message="Failed to create IEP",
                errors=[str(e)]
            )
        finally:
            db.close()
    
    @strawberry.mutation
    async def upsert_section(self, input: IEPSectionUpsertInput) -> IEPSectionMutationResponse:
        """Create or update an IEP section with CRDT support."""
        try:
            db = next(get_db())
            
            # Find existing section or create new one
            section = db.query(IEPSectionModel).filter(
                and_(
                    IEPSectionModel.iep_id == uuid.UUID(input.iep_id),
                    IEPSectionModel.section_type == input.section_type.value
                )
            ).first()
            
            if section:
                # Update existing section
                section.title = input.title
                section.content = input.content
                section.updated_by = "system"  # TODO: Get from context
                section.updated_at = datetime.now(timezone.utc)
                if input.order_index is not None:
                    section.order_index = input.order_index
                if input.validation_rules:
                    section.validation_rules = input.validation_rules
            else:
                # Create new section
                section = IEPSectionModel(
                    iep_id=uuid.UUID(input.iep_id),
                    section_type=input.section_type.value,
                    title=input.title,
                    content=input.content,
                    order_index=input.order_index or 0,
                    validation_rules=input.validation_rules or {},
                    created_by="system",  # TODO: Get from context
                    updated_by="system"   # TODO: Get from context
                )
                db.add(section)
            
            db.commit()
            db.refresh(section)
            
            logger.info(f"Upserted section {section.id} for IEP {input.iep_id}")
            
            return IEPSectionMutationResponse(
                success=True,
                message="Section updated successfully",
                section=convert_section_model_to_graphql(section)
            )
            
        except Exception as e:
            db.rollback()
            logger.error(f"Error upserting section: {str(e)}")
            return IEPSectionMutationResponse(
                success=False,
                message="Failed to update section",
                errors=[str(e)]
            )
        finally:
            db.close()
    
    @strawberry.mutation
    async def set_iep_status(self, iep_id: str, status: IEPStatus) -> IEPMutationResponse:
        """Update IEP status with workflow validation."""
        try:
            db = next(get_db())
            
            iep = db.query(IEPModel).filter(IEPModel.id == uuid.UUID(iep_id)).first()
            if not iep:
                return IEPMutationResponse(
                    success=False,
                    message="IEP not found",
                    errors=["IEP not found"]
                )
            
            # TODO: Add status transition validation logic
            iep.status = status.value
            iep.updated_by = "system"  # TODO: Get from context
            iep.updated_at = datetime.now(timezone.utc)
            
            db.commit()
            db.refresh(iep)
            
            logger.info(f"Updated IEP {iep_id} status to {status}")
            
            return IEPMutationResponse(
                success=True,
                message=f"IEP status updated to {status}",
                iep=convert_iep_model_to_graphql(iep)
            )
            
        except Exception as e:
            db.rollback()
            logger.error(f"Error updating IEP status: {str(e)}")
            return IEPMutationResponse(
                success=False,
                message="Failed to update IEP status",
                errors=[str(e)]
            )
        finally:
            db.close()
    
    @strawberry.mutation
    async def attach_evidence(self, input: EvidenceAttachmentInput) -> EvidenceAttachmentResponse:
        """Attach evidence document to an IEP."""
        try:
            db = next(get_db())
            
            # Create evidence attachment record
            attachment = EvidenceAttachmentModel(
                iep_id=uuid.UUID(input.iep_id),
                filename=f"{uuid.uuid4()}_{input.filename}",  # Unique filename
                original_filename=input.filename,
                content_type=input.content_type,
                file_size=input.file_size,
                evidence_type=input.evidence_type,
                description=input.description,
                tags=input.tags,
                is_confidential=input.is_confidential,
                storage_path=f"iep-evidence/{input.iep_id}/{uuid.uuid4()}",
                checksum="pending",  # TODO: Generate checksum
                uploaded_by="system"  # TODO: Get from context
            )
            
            db.add(attachment)
            db.commit()
            db.refresh(attachment)
            
            # TODO: Generate pre-signed upload URL
            upload_url = f"https://upload.example.com/evidence/{attachment.id}"
            
            logger.info(f"Created evidence attachment {attachment.id} for IEP {input.iep_id}")
            
            return EvidenceAttachmentResponse(
                success=True,
                message="Evidence attachment created successfully",
                attachment=convert_evidence_model_to_graphql(attachment),
                upload_url=upload_url
            )
            
        except Exception as e:
            db.rollback()
            logger.error(f"Error attaching evidence: {str(e)}")
            return EvidenceAttachmentResponse(
                success=False,
                message="Failed to attach evidence",
                errors=[str(e)]
            )
        finally:
            db.close()

@strawberry.type
class Subscription:
    """GraphQL Subscription root for real-time IEP updates."""
    
    @strawberry.subscription
    async def iep_updated(self, iep_id: str) -> AsyncGenerator[IEPUpdateEvent, None]:
        """Subscribe to real-time IEP updates."""
        # TODO: Implement WebSocket-based subscription with Redis/PostgreSQL NOTIFY
        # This is a placeholder implementation
        
        logger.info(f"Client subscribed to IEP updates for {iep_id}")
        
        # Placeholder: yield a test event
        yield IEPUpdateEvent(
            iep_id=iep_id,
            event_type="subscription_started",
            updated_by="system",
            timestamp=datetime.now(timezone.utc),
            metadata={"message": "Subscription active"}
        )
