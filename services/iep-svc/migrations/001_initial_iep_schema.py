# AIVO IEP Service - Database Migration 001
# S1-11 Implementation - Initial IEP Schema with CRDT and E-Signature Support

"""
Initial migration for IEP service database schema.

Creates tables for IEP documents, sections, signatures, evidence attachments,
and CRDT operation logs to support collaborative editing and e-signature workflows.
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers
revision = '001_initial_iep_schema'
down_revision = None
branch_labels = None
depends_on = None

def upgrade():
    """Apply migration - create initial IEP schema."""
    
    # Create IEP status enum
    iep_status_enum = sa.Enum(
        'draft', 'in_review', 'approved', 'active', 'archived', 'expired',
        name='iepstatus'
    )
    iep_status_enum.create(op.get_bind())
    
    # Create section type enum
    section_type_enum = sa.Enum(
        'student_info', 'present_levels', 'annual_goals', 'services', 
        'placement', 'transition', 'assessments', 'accommodations',
        name='sectiontype'
    )
    section_type_enum.create(op.get_bind())
    
    # Create signature role enum
    signature_role_enum = sa.Enum(
        'student', 'parent_guardian', 'teacher', 'case_manager',
        'administrator', 'service_provider', 'advocate',
        name='signaturerole'
    )
    signature_role_enum.create(op.get_bind())
    
    # Create CRDT operation enum
    crdt_operation_enum = sa.Enum(
        'insert', 'delete', 'update', 'retain',
        name='crdtoperation'
    )
    crdt_operation_enum.create(op.get_bind())
    
    # Create IEPs table
    op.create_table(
        'ieps',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('student_id', sa.String(50), nullable=False, index=True),
        sa.Column('tenant_id', sa.String(50), nullable=False, index=True),
        sa.Column('school_district', sa.String(200), nullable=False),
        sa.Column('school_name', sa.String(200), nullable=False),
        sa.Column('title', sa.String(300), nullable=False),
        sa.Column('academic_year', sa.String(20), nullable=False),
        sa.Column('grade_level', sa.String(20), nullable=False),
        sa.Column('status', iep_status_enum, nullable=False, default='draft', index=True),
        sa.Column('version', sa.Integer, nullable=False, default=1),
        sa.Column('is_current', sa.Boolean, nullable=False, default=True, index=True),
        sa.Column('effective_date', sa.DateTime(timezone=True)),
        sa.Column('expiration_date', sa.DateTime(timezone=True)),
        sa.Column('next_review_date', sa.DateTime(timezone=True)),
        sa.Column('crdt_state', sa.JSON, nullable=False, default={}),
        sa.Column('operation_log', sa.JSON, nullable=False, default=[]),
        sa.Column('last_operation_id', sa.String(50)),
        sa.Column('signature_required_roles', sa.JSON, nullable=False, default=[]),
        sa.Column('signature_deadline', sa.DateTime(timezone=True)),
        sa.Column('content_hash', sa.String(64)),
        sa.Column('created_by', sa.String(50), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('updated_by', sa.String(50), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False)
    )
    
    # Create IEP sections table
    op.create_table(
        'iep_sections',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('iep_id', postgresql.UUID(as_uuid=True), nullable=False, index=True),
        sa.Column('section_type', section_type_enum, nullable=False, index=True),
        sa.Column('title', sa.String(200), nullable=False),
        sa.Column('order_index', sa.Integer, nullable=False, default=0),
        sa.Column('content', sa.Text, nullable=False, default=''),
        sa.Column('crdt_operations', sa.JSON, nullable=False, default=[]),
        sa.Column('operation_counter', sa.Integer, nullable=False, default=0),
        sa.Column('last_editor_id', sa.String(50)),
        sa.Column('last_edited_at', sa.DateTime(timezone=True)),
        sa.Column('edit_session_id', sa.String(50)),
        sa.Column('is_required', sa.Boolean, nullable=False, default=True),
        sa.Column('is_locked', sa.Boolean, nullable=False, default=False),
        sa.Column('validation_rules', sa.JSON, nullable=False, default={}),
        sa.Column('created_by', sa.String(50), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('updated_by', sa.String(50), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(['iep_id'], ['ieps.id'], ondelete='CASCADE')
    )
    
    # Create e-signatures table
    op.create_table(
        'e_signatures',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('iep_id', postgresql.UUID(as_uuid=True), nullable=False, index=True),
        sa.Column('signer_id', sa.String(50), nullable=False, index=True),
        sa.Column('signer_name', sa.String(200), nullable=False),
        sa.Column('signer_email', sa.String(200), nullable=False),
        sa.Column('signer_role', signature_role_enum, nullable=False, index=True),
        sa.Column('is_signed', sa.Boolean, nullable=False, default=False, index=True),
        sa.Column('signed_at', sa.DateTime(timezone=True)),
        sa.Column('signature_method', sa.String(50)),
        sa.Column('auth_method', sa.String(100)),
        sa.Column('ip_address', sa.String(45)),
        sa.Column('user_agent', sa.String(500)),
        sa.Column('signature_hash', sa.String(128)),
        sa.Column('certificate_fingerprint', sa.String(128)),
        sa.Column('consent_text', sa.Text),
        sa.Column('legal_notices', sa.JSON, nullable=False, default={}),
        sa.Column('invitation_sent_at', sa.DateTime(timezone=True)),
        sa.Column('reminder_count', sa.Integer, nullable=False, default=0),
        sa.Column('expires_at', sa.DateTime(timezone=True)),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(['iep_id'], ['ieps.id'], ondelete='CASCADE')
    )
    
    # Create evidence attachments table
    op.create_table(
        'evidence_attachments',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('iep_id', postgresql.UUID(as_uuid=True), nullable=False, index=True),
        sa.Column('filename', sa.String(500), nullable=False),
        sa.Column('original_filename', sa.String(500), nullable=False),
        sa.Column('content_type', sa.String(100), nullable=False),
        sa.Column('file_size', sa.Integer, nullable=False),
        sa.Column('storage_path', sa.String(1000), nullable=False),
        sa.Column('storage_provider', sa.String(50), nullable=False, default='local'),
        sa.Column('evidence_type', sa.String(100), nullable=False),
        sa.Column('description', sa.Text),
        sa.Column('tags', sa.JSON, nullable=False, default=[]),
        sa.Column('checksum', sa.String(64), nullable=False),
        sa.Column('virus_scan_status', sa.String(20), nullable=False, default='pending'),
        sa.Column('virus_scan_at', sa.DateTime(timezone=True)),
        sa.Column('is_confidential', sa.Boolean, nullable=False, default=False),
        sa.Column('access_level', sa.String(50), nullable=False, default='team'),
        sa.Column('uploaded_by', sa.String(50), nullable=False),
        sa.Column('uploaded_at', sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(['iep_id'], ['ieps.id'], ondelete='CASCADE')
    )
    
    # Create CRDT operation log table
    op.create_table(
        'crdt_operation_log',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('iep_id', postgresql.UUID(as_uuid=True), nullable=False, index=True),
        sa.Column('section_id', postgresql.UUID(as_uuid=True), index=True),
        sa.Column('operation_id', sa.String(50), nullable=False, unique=True, index=True),
        sa.Column('operation_type', crdt_operation_enum, nullable=False, index=True),
        sa.Column('operation_data', sa.JSON, nullable=False),
        sa.Column('position', sa.Integer, nullable=False),
        sa.Column('length', sa.Integer, nullable=False, default=0),
        sa.Column('content', sa.Text),
        sa.Column('author_id', sa.String(50), nullable=False, index=True),
        sa.Column('timestamp', sa.DateTime(timezone=True), nullable=False, index=True),
        sa.Column('client_timestamp', sa.DateTime(timezone=True)),
        sa.Column('parent_operation_id', sa.String(50)),
        sa.Column('vector_clock', sa.JSON, nullable=False, default={}),
        sa.ForeignKeyConstraint(['iep_id'], ['ieps.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['section_id'], ['iep_sections.id'], ondelete='CASCADE')
    )
    
    # Create indexes for performance
    op.create_index('idx_ieps_student_tenant', 'ieps', ['student_id', 'tenant_id'])
    op.create_index('idx_ieps_academic_year_status', 'ieps', ['academic_year', 'status'])
    op.create_index('idx_sections_iep_type', 'iep_sections', ['iep_id', 'section_type'])
    op.create_index('idx_signatures_iep_status', 'e_signatures', ['iep_id', 'is_signed'])
    op.create_index('idx_evidence_iep_type', 'evidence_attachments', ['iep_id', 'evidence_type'])
    op.create_index('idx_crdt_log_timestamp', 'crdt_operation_log', ['timestamp'])

def downgrade():
    """Rollback migration - drop all IEP tables."""
    
    # Drop tables in reverse order (respecting foreign keys)
    op.drop_table('crdt_operation_log')
    op.drop_table('evidence_attachments')
    op.drop_table('e_signatures')
    op.drop_table('iep_sections')
    op.drop_table('ieps')
    
    # Drop enums
    sa.Enum(name='crdtoperation').drop(op.get_bind())
    sa.Enum(name='signaturerole').drop(op.get_bind())
    sa.Enum(name='sectiontype').drop(op.get_bind())
    sa.Enum(name='iepstatus').drop(op.get_bind())
