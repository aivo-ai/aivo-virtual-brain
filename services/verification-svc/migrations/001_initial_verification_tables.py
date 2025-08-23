"""
Initial migration for Guardian Identity Verification Service
Creates all tables for COPPA-compliant verification system

Revision ID: 001_initial_verification_tables
Revises: 
Create Date: 2025-08-23 00:00:00.000000
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers
revision = '001_initial_verification_tables'
down_revision = None
branch_labels = None
depends_on = None


def upgrade():
    """Create initial verification tables"""
    
    # Create verification_method enum
    verification_method_enum = postgresql.ENUM(
        'micro_charge', 'kba', 'hybrid',
        name='verificationmethod'
    )
    verification_method_enum.create(op.get_bind())
    
    # Create verification_status enum
    verification_status_enum = postgresql.ENUM(
        'pending', 'in_progress', 'verified', 'failed', 'expired', 'rate_limited',
        name='verificationstatus'
    )
    verification_status_enum.create(op.get_bind())
    
    # Create failure_reason enum
    failure_reason_enum = postgresql.ENUM(
        'insufficient_funds', 'card_declined', 'kba_failed', 'expired',
        'too_many_attempts', 'geo_restricted', 'provider_error', 'fraud_detected',
        name='failurereason'
    )
    failure_reason_enum.create(op.get_bind())
    
    # Create guardian_verifications table
    op.create_table(
        'guardian_verifications',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('guardian_user_id', sa.String(100), nullable=False, index=True),
        sa.Column('tenant_id', sa.String(100), nullable=False, index=True),
        sa.Column('verification_method', verification_method_enum, nullable=False),
        sa.Column('status', verification_status_enum, nullable=False, default='pending'),
        sa.Column('created_at', sa.DateTime, nullable=False, default=sa.func.now()),
        sa.Column('updated_at', sa.DateTime, nullable=False, default=sa.func.now()),
        sa.Column('verified_at', sa.DateTime, nullable=True),
        sa.Column('expires_at', sa.DateTime, nullable=False),
        sa.Column('attempt_count', sa.Integer, nullable=False, default=0),
        sa.Column('last_attempt_at', sa.DateTime, nullable=True),
        sa.Column('lockout_until', sa.DateTime, nullable=True),
        sa.Column('failure_reason', failure_reason_enum, nullable=True),
        sa.Column('failure_details', sa.Text, nullable=True),
        sa.Column('verification_country', sa.String(2), nullable=True),
        sa.Column('ip_country', sa.String(2), nullable=True),
        sa.Column('data_retention_until', sa.DateTime, nullable=False),
        sa.Column('consent_version', sa.String(20), nullable=False, default='2025-v1'),
    )
    
    # Create indexes for guardian_verifications
    op.create_index('idx_guardian_status', 'guardian_verifications', ['guardian_user_id', 'status'])
    op.create_index('idx_tenant_verification', 'guardian_verifications', ['tenant_id', 'created_at'])
    op.create_index('idx_expiry_cleanup', 'guardian_verifications', ['data_retention_until'])
    op.create_index('idx_lockout_check', 'guardian_verifications', ['guardian_user_id', 'lockout_until'])
    
    # Create unique constraint
    op.create_unique_constraint(
        'uq_guardian_tenant_verification',
        'guardian_verifications',
        ['guardian_user_id', 'tenant_id', 'created_at']
    )
    
    # Create charge_verifications table
    op.create_table(
        'charge_verifications',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('verification_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('stripe_payment_intent_id', sa.String(100), nullable=False, unique=True),
        sa.Column('stripe_customer_id', sa.String(100), nullable=True),
        sa.Column('charge_amount_cents', sa.Integer, nullable=False, default=10),
        sa.Column('currency', sa.String(3), nullable=False, default='USD'),
        sa.Column('payment_method_token', sa.String(100), nullable=True),
        sa.Column('card_fingerprint', sa.String(50), nullable=True),
        sa.Column('card_last_four', sa.String(4), nullable=True),
        sa.Column('charge_status', sa.String(50), nullable=False, default='pending'),
        sa.Column('refund_status', sa.String(50), nullable=True),
        sa.Column('refund_id', sa.String(100), nullable=True),
        sa.Column('created_at', sa.DateTime, nullable=False, default=sa.func.now()),
        sa.Column('charged_at', sa.DateTime, nullable=True),
        sa.Column('refunded_at', sa.DateTime, nullable=True),
        sa.Column('pii_scrubbed_at', sa.DateTime, nullable=True),
        sa.ForeignKeyConstraint(['verification_id'], ['guardian_verifications.id']),
    )
    
    # Create indexes for charge_verifications
    op.create_index('idx_stripe_payment_intent', 'charge_verifications', ['stripe_payment_intent_id'])
    op.create_index('idx_verification_charge', 'charge_verifications', ['verification_id', 'created_at'])
    op.create_index('idx_card_fingerprint', 'charge_verifications', ['card_fingerprint'])
    
    # Create kba_sessions table
    op.create_table(
        'kba_sessions',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('verification_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('provider_name', sa.String(50), nullable=False),
        sa.Column('provider_session_id', sa.String(100), nullable=False),
        sa.Column('questions_presented', sa.Integer, nullable=False, default=0),
        sa.Column('questions_answered', sa.Integer, nullable=False, default=0),
        sa.Column('correct_answers', sa.Integer, nullable=False, default=0),
        sa.Column('kba_score', sa.Integer, nullable=True),
        sa.Column('pass_threshold', sa.Integer, nullable=False, default=80),
        sa.Column('passed', sa.Boolean, nullable=True),
        sa.Column('verification_eligible', sa.Boolean, nullable=False, default=True),
        sa.Column('created_at', sa.DateTime, nullable=False, default=sa.func.now()),
        sa.Column('completed_at', sa.DateTime, nullable=True),
        sa.Column('expires_at', sa.DateTime, nullable=False),
        sa.Column('provider_data_deleted_at', sa.DateTime, nullable=True),
        sa.ForeignKeyConstraint(['verification_id'], ['guardian_verifications.id']),
    )
    
    # Create indexes for kba_sessions
    op.create_index('idx_provider_session', 'kba_sessions', ['provider_name', 'provider_session_id'])
    op.create_index('idx_verification_kba', 'kba_sessions', ['verification_id', 'created_at'])
    op.create_index('idx_kba_expiry', 'kba_sessions', ['expires_at'])
    
    # Create verification_audit_logs table
    op.create_table(
        'verification_audit_logs',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('verification_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('event_type', sa.String(50), nullable=False),
        sa.Column('event_description', sa.String(200), nullable=False),
        sa.Column('ip_address_hash', sa.String(64), nullable=True),
        sa.Column('user_agent_hash', sa.String(64), nullable=True),
        sa.Column('session_id', sa.String(100), nullable=True),
        sa.Column('success', sa.Boolean, nullable=False),
        sa.Column('error_code', sa.String(50), nullable=True),
        sa.Column('metadata', postgresql.JSON, nullable=True),
        sa.Column('created_at', sa.DateTime, nullable=False, default=sa.func.now()),
        sa.Column('auto_delete_at', sa.DateTime, nullable=False),
        sa.ForeignKeyConstraint(['verification_id'], ['guardian_verifications.id']),
    )
    
    # Create indexes for verification_audit_logs
    op.create_index('idx_verification_audit', 'verification_audit_logs', ['verification_id', 'created_at'])
    op.create_index('idx_event_type', 'verification_audit_logs', ['event_type', 'created_at'])
    op.create_index('idx_audit_deletion', 'verification_audit_logs', ['auto_delete_at'])
    
    # Create verification_rate_limits table
    op.create_table(
        'verification_rate_limits',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('guardian_user_id', sa.String(100), nullable=False, index=True),
        sa.Column('ip_address_hash', sa.String(64), nullable=True, index=True),
        sa.Column('rate_limit_type', sa.String(50), nullable=False),
        sa.Column('attempt_count', sa.Integer, nullable=False, default=1),
        sa.Column('window_start', sa.DateTime, nullable=False, default=sa.func.now()),
        sa.Column('window_end', sa.DateTime, nullable=False),
        sa.Column('locked_out', sa.Boolean, nullable=False, default=False),
        sa.Column('lockout_until', sa.DateTime, nullable=True),
        sa.Column('lockout_reason', sa.String(100), nullable=True),
        sa.Column('created_at', sa.DateTime, nullable=False, default=sa.func.now()),
        sa.Column('updated_at', sa.DateTime, nullable=False, default=sa.func.now()),
    )
    
    # Create indexes for verification_rate_limits
    op.create_index('idx_guardian_rate_limit', 'verification_rate_limits', ['guardian_user_id', 'rate_limit_type'])
    op.create_index('idx_ip_rate_limit', 'verification_rate_limits', ['ip_address_hash', 'rate_limit_type'])
    op.create_index('idx_rate_limit_window', 'verification_rate_limits', ['window_end'])
    
    # Create unique constraint for rate limits
    op.create_unique_constraint(
        'uq_guardian_rate_limit_window',
        'verification_rate_limits',
        ['guardian_user_id', 'rate_limit_type', 'window_start']
    )
    
    # Create geo_policy_rules table
    op.create_table(
        'geo_policy_rules',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('country_code', sa.String(2), nullable=False, index=True),
        sa.Column('region_code', sa.String(10), nullable=True),
        sa.Column('micro_charge_allowed', sa.Boolean, nullable=False, default=True),
        sa.Column('kba_allowed', sa.Boolean, nullable=False, default=True),
        sa.Column('minimum_age', sa.Integer, nullable=False, default=18),
        sa.Column('gdpr_applicable', sa.Boolean, nullable=False, default=False),
        sa.Column('coppa_applicable', sa.Boolean, nullable=False, default=False),
        sa.Column('additional_consent_required', sa.Boolean, nullable=False, default=False),
        sa.Column('policy_version', sa.String(20), nullable=False, default='2025-v1'),
        sa.Column('effective_date', sa.DateTime, nullable=False, default=sa.func.now()),
        sa.Column('notes', sa.Text, nullable=True),
        sa.Column('created_at', sa.DateTime, nullable=False, default=sa.func.now()),
        sa.Column('updated_at', sa.DateTime, nullable=False, default=sa.func.now()),
    )
    
    # Create indexes for geo_policy_rules
    op.create_index('idx_country_policy', 'geo_policy_rules', ['country_code', 'effective_date'])
    
    # Create unique constraint for geo policies
    op.create_unique_constraint(
        'uq_geo_policy_effective',
        'geo_policy_rules',
        ['country_code', 'region_code', 'effective_date']
    )


def downgrade():
    """Drop all verification tables"""
    
    # Drop tables in reverse order
    op.drop_table('geo_policy_rules')
    op.drop_table('verification_rate_limits')
    op.drop_table('verification_audit_logs')
    op.drop_table('kba_sessions')
    op.drop_table('charge_verifications')
    op.drop_table('guardian_verifications')
    
    # Drop enums
    op.execute('DROP TYPE IF EXISTS failurereason')
    op.execute('DROP TYPE IF EXISTS verificationstatus')
    op.execute('DROP TYPE IF EXISTS verificationmethod')
