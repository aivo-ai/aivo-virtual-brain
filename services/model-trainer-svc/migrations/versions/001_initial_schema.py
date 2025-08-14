"""Initial model trainer schema

Revision ID: 001
Revises: 
Create Date: 2025-08-14 00:00:00.000000

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = '001'
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Create job status enum
    job_status_enum = postgresql.ENUM(
        'PENDING', 'VALIDATING', 'TRAINING', 'EVALUATING', 
        'COMPLETED', 'FAILED', 'CANCELLED',
        name='jobstatus'
    )
    job_status_enum.create(op.get_bind())
    
    # Create evaluation status enum
    evaluation_status_enum = postgresql.ENUM(
        'PENDING', 'RUNNING', 'PASSED', 'FAILED', 'ERROR',
        name='evaluationstatus'
    )
    evaluation_status_enum.create(op.get_bind())
    
    # Create provider enum
    provider_enum = postgresql.ENUM(
        'OPENAI', 'VERTEX_AI', 'BEDROCK', 'ANTHROPIC',
        name='provider'
    )
    provider_enum.create(op.get_bind())
    
    # Create training_jobs table
    op.create_table('training_jobs',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('name', sa.String(length=255), nullable=False),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('status', job_status_enum, nullable=False),
        sa.Column('provider', provider_enum, nullable=False),
        sa.Column('base_model', sa.String(length=255), nullable=False),
        sa.Column('dataset_uri', sa.String(length=500), nullable=False),
        sa.Column('config', sa.JSON(), nullable=False),
        sa.Column('policy', sa.JSON(), nullable=False),
        sa.Column('datasheet', sa.JSON(), nullable=False),
        sa.Column('provider_job_id', sa.String(length=255), nullable=True),
        sa.Column('provider_model_id', sa.String(length=255), nullable=True),
        sa.Column('provider_metadata', sa.JSON(), nullable=True),
        sa.Column('training_tokens', sa.Integer(), nullable=True),
        sa.Column('training_cost', sa.Float(), nullable=True),
        sa.Column('training_duration', sa.Integer(), nullable=True),
        sa.Column('error_message', sa.Text(), nullable=True),
        sa.Column('retry_count', sa.Integer(), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('started_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('completed_at', sa.DateTime(timezone=True), nullable=True),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('name', name='uq_training_job_name'),
        sa.UniqueConstraint('provider_job_id')
    )
    
    # Create evaluations table
    op.create_table('evaluations',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('job_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('name', sa.String(length=255), nullable=False),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('status', evaluation_status_enum, nullable=False),
        sa.Column('harness_config', sa.JSON(), nullable=False),
        sa.Column('thresholds', sa.JSON(), nullable=False),
        sa.Column('pedagogy_score', sa.Float(), nullable=True),
        sa.Column('safety_score', sa.Float(), nullable=True),
        sa.Column('overall_score', sa.Float(), nullable=True),
        sa.Column('passed', sa.Boolean(), nullable=True),
        sa.Column('results', sa.JSON(), nullable=True),
        sa.Column('metrics', sa.JSON(), nullable=True),
        sa.Column('error_message', sa.Text(), nullable=True),
        sa.Column('retry_count', sa.Integer(), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('started_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('completed_at', sa.DateTime(timezone=True), nullable=True),
        sa.PrimaryKeyConstraint('id')
    )
    
    # Create model_promotions table
    op.create_table('model_promotions',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('job_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('evaluation_id', postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column('registry_model_id', postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column('registry_version_id', postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column('registry_binding_id', postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column('promoted', sa.Boolean(), nullable=False),
        sa.Column('promotion_reason', sa.Text(), nullable=True),
        sa.Column('promotion_metadata', sa.JSON(), nullable=True),
        sa.Column('error_message', sa.Text(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.PrimaryKeyConstraint('id')
    )
    
    # Create indexes for better performance
    op.create_index('ix_training_jobs_id', 'training_jobs', ['id'])
    op.create_index('ix_training_jobs_name', 'training_jobs', ['name'])
    op.create_index('ix_training_jobs_status', 'training_jobs', ['status'])
    op.create_index('ix_training_jobs_provider', 'training_jobs', ['provider'])
    
    op.create_index('ix_evaluations_id', 'evaluations', ['id'])
    op.create_index('ix_evaluations_job_id', 'evaluations', ['job_id'])
    op.create_index('ix_evaluations_status', 'evaluations', ['status'])
    
    op.create_index('ix_model_promotions_id', 'model_promotions', ['id'])
    op.create_index('ix_model_promotions_job_id', 'model_promotions', ['job_id'])
    op.create_index('ix_model_promotions_evaluation_id', 'model_promotions', ['evaluation_id'])


def downgrade() -> None:
    # Drop indexes
    op.drop_index('ix_model_promotions_evaluation_id', 'model_promotions')
    op.drop_index('ix_model_promotions_job_id', 'model_promotions')
    op.drop_index('ix_model_promotions_id', 'model_promotions')
    
    op.drop_index('ix_evaluations_status', 'evaluations')
    op.drop_index('ix_evaluations_job_id', 'evaluations')
    op.drop_index('ix_evaluations_id', 'evaluations')
    
    op.drop_index('ix_training_jobs_provider', 'training_jobs')
    op.drop_index('ix_training_jobs_status', 'training_jobs')
    op.drop_index('ix_training_jobs_name', 'training_jobs')
    op.drop_index('ix_training_jobs_id', 'training_jobs')
    
    # Drop tables
    op.drop_table('model_promotions')
    op.drop_table('evaluations')
    op.drop_table('training_jobs')
    
    # Drop enums
    op.execute('DROP TYPE provider')
    op.execute('DROP TYPE evaluationstatus')
    op.execute('DROP TYPE jobstatus')
