-- Database initialization script for Data Residency Service
-- This script sets up the initial database structure and seed data

-- Create extensions
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";
CREATE EXTENSION IF NOT EXISTS "pgcrypto";

-- Create custom types
DO $$ BEGIN
    CREATE TYPE region_code_enum AS ENUM (
        'us-east', 'us-west', 'eu-west', 'eu-central', 
        'apac-south', 'apac-east', 'ca-central'
    );
EXCEPTION
    WHEN duplicate_object THEN null;
END $$;

DO $$ BEGIN
    CREATE TYPE compliance_framework_enum AS ENUM (
        'gdpr', 'ccpa', 'coppa', 'ferpa', 'pipeda', 'lgpd'
    );
EXCEPTION
    WHEN duplicate_object THEN null;
END $$;

-- Insert initial region infrastructure data
INSERT INTO region_infrastructure (
    region_id, region_code, region_name, s3_bucket_name, s3_region, 
    backup_bucket_name, opensearch_domain, opensearch_endpoint,
    inference_providers, model_endpoints, vpc_id, subnet_ids,
    security_group_ids, compliance_certifications, data_center_location,
    is_active, created_at, updated_at
) VALUES 
(
    uuid_generate_v4(),
    'us-east',
    'US East (Virginia)',
    'aivo-data-us-east',
    'us-east-1',
    'aivo-backup-us-east',
    'aivo-search-us-east',
    'https://search-aivo-us-east.us-east-1.es.amazonaws.com',
    '[
        {
            "provider": "aws-bedrock",
            "region": "us-east-1",
            "models": ["claude-3-haiku", "claude-3-sonnet", "titan-text"],
            "endpoint": "https://bedrock-runtime.us-east-1.amazonaws.com"
        },
        {
            "provider": "openai",
            "region": "us-east-1", 
            "models": ["gpt-4", "gpt-3.5-turbo"],
            "endpoint": "https://api.openai.com/v1"
        }
    ]'::json,
    '{
        "bedrock": "https://bedrock-runtime.us-east-1.amazonaws.com",
        "openai": "https://api.openai.com/v1"
    }'::json,
    'vpc-12345678',
    '["subnet-12345", "subnet-67890"]'::json,
    '["sg-abcdef", "sg-123456"]'::json,
    '["SOC2", "HIPAA", "FedRAMP"]'::json,
    'US East Coast - Virginia',
    true,
    NOW(),
    NOW()
),
(
    uuid_generate_v4(),
    'us-west',
    'US West (Oregon)',
    'aivo-data-us-west',
    'us-west-2',
    'aivo-backup-us-west',
    'aivo-search-us-west',
    'https://search-aivo-us-west.us-west-2.es.amazonaws.com',
    '[
        {
            "provider": "aws-bedrock",
            "region": "us-west-2",
            "models": ["claude-3-haiku", "claude-3-sonnet"],
            "endpoint": "https://bedrock-runtime.us-west-2.amazonaws.com"
        }
    ]'::json,
    '{
        "bedrock": "https://bedrock-runtime.us-west-2.amazonaws.com"
    }'::json,
    'vpc-87654321',
    '["subnet-98765", "subnet-54321"]'::json,
    '["sg-fedcba", "sg-654321"]'::json,
    '["SOC2", "CCPA"]'::json,
    'US West Coast - Oregon',
    true,
    NOW(),
    NOW()
),
(
    uuid_generate_v4(),
    'eu-west',
    'EU West (Ireland)',
    'aivo-data-eu-west',
    'eu-west-1',
    'aivo-backup-eu-west',
    'aivo-search-eu-west',
    'https://search-aivo-eu-west.eu-west-1.es.amazonaws.com',
    '[
        {
            "provider": "aws-bedrock",
            "region": "eu-west-1",
            "models": ["claude-3-haiku"],
            "endpoint": "https://bedrock-runtime.eu-west-1.amazonaws.com"
        },
        {
            "provider": "anthropic-eu",
            "region": "eu-west-1",
            "models": ["claude-3-sonnet"],
            "endpoint": "https://api.anthropic.com/v1"
        }
    ]'::json,
    '{
        "bedrock": "https://bedrock-runtime.eu-west-1.amazonaws.com",
        "anthropic": "https://api.anthropic.com/v1"
    }'::json,
    'vpc-eu123456',
    '["subnet-eu111", "subnet-eu222"]'::json,
    '["sg-eu123", "sg-eu456"]'::json,
    '["GDPR", "SOC2", "ISO27001"]'::json,
    'EU West - Ireland',
    true,
    NOW(),
    NOW()
),
(
    uuid_generate_v4(),
    'eu-central',
    'EU Central (Frankfurt)',
    'aivo-data-eu-central',
    'eu-central-1',
    'aivo-backup-eu-central',
    'aivo-search-eu-central',
    'https://search-aivo-eu-central.eu-central-1.es.amazonaws.com',
    '[
        {
            "provider": "aws-bedrock",
            "region": "eu-central-1",
            "models": ["claude-3-haiku"],
            "endpoint": "https://bedrock-runtime.eu-central-1.amazonaws.com"
        }
    ]'::json,
    '{
        "bedrock": "https://bedrock-runtime.eu-central-1.amazonaws.com"
    }'::json,
    'vpc-eu789012',
    '["subnet-eu333", "subnet-eu444"]'::json,
    '["sg-eu789", "sg-eu012"]'::json,
    '["GDPR", "SOC2", "ISO27001"]'::json,
    'EU Central - Frankfurt',
    true,
    NOW(),
    NOW()
),
(
    uuid_generate_v4(),
    'ca-central',
    'Canada Central (Central)',
    'aivo-data-ca-central',
    'ca-central-1',
    'aivo-backup-ca-central',
    'aivo-search-ca-central',
    'https://search-aivo-ca-central.ca-central-1.es.amazonaws.com',
    '[
        {
            "provider": "aws-bedrock",
            "region": "ca-central-1",
            "models": ["claude-3-haiku"],
            "endpoint": "https://bedrock-runtime.ca-central-1.amazonaws.com"
        }
    ]'::json,
    '{
        "bedrock": "https://bedrock-runtime.ca-central-1.amazonaws.com"
    }'::json,
    'vpc-ca123456',
    '["subnet-ca111", "subnet-ca222"]'::json,
    '["sg-ca123", "sg-ca456"]'::json,
    '["PIPEDA", "SOC2"]'::json,
    'Canada Central',
    true,
    NOW(),
    NOW()
) ON CONFLICT (region_code) DO NOTHING;

-- Create indexes for better performance
CREATE INDEX IF NOT EXISTS idx_residency_policies_tenant_active ON residency_policies(tenant_id, is_active);
CREATE INDEX IF NOT EXISTS idx_residency_policies_learner_active ON residency_policies(learner_id, is_active) WHERE learner_id IS NOT NULL;
CREATE INDEX IF NOT EXISTS idx_residency_policies_region ON residency_policies(primary_region);
CREATE INDEX IF NOT EXISTS idx_residency_policies_created ON residency_policies(created_at);

CREATE INDEX IF NOT EXISTS idx_data_access_logs_tenant_time ON data_access_logs(tenant_id, timestamp);
CREATE INDEX IF NOT EXISTS idx_data_access_logs_learner_time ON data_access_logs(learner_id, timestamp) WHERE learner_id IS NOT NULL;
CREATE INDEX IF NOT EXISTS idx_data_access_logs_user_time ON data_access_logs(user_id, timestamp);
CREATE INDEX IF NOT EXISTS idx_data_access_logs_cross_region ON data_access_logs(is_cross_region, timestamp);
CREATE INDEX IF NOT EXISTS idx_data_access_logs_compliance ON data_access_logs(compliance_check_result, timestamp);
CREATE INDEX IF NOT EXISTS idx_data_access_logs_emergency ON data_access_logs(emergency_override, timestamp);
CREATE INDEX IF NOT EXISTS idx_data_access_logs_operation ON data_access_logs(operation_type, timestamp);

CREATE INDEX IF NOT EXISTS idx_emergency_overrides_tenant_status ON emergency_overrides(tenant_id, status);
CREATE INDEX IF NOT EXISTS idx_emergency_overrides_validity ON emergency_overrides(valid_from, valid_until);
CREATE INDEX IF NOT EXISTS idx_emergency_overrides_status ON emergency_overrides(status);

CREATE INDEX IF NOT EXISTS idx_region_infrastructure_active ON region_infrastructure(is_active);
CREATE INDEX IF NOT EXISTS idx_region_infrastructure_region ON region_infrastructure(region_code);

-- Create a function to automatically update the updated_at timestamp
CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ language 'plpgsql';

-- Create triggers for automatic timestamp updates
DROP TRIGGER IF EXISTS update_residency_policies_updated_at ON residency_policies;
CREATE TRIGGER update_residency_policies_updated_at
    BEFORE UPDATE ON residency_policies
    FOR EACH ROW
    EXECUTE FUNCTION update_updated_at_column();

DROP TRIGGER IF EXISTS update_region_infrastructure_updated_at ON region_infrastructure;
CREATE TRIGGER update_region_infrastructure_updated_at
    BEFORE UPDATE ON region_infrastructure
    FOR EACH ROW
    EXECUTE FUNCTION update_updated_at_column();

-- Insert sample data for testing
DO $$
DECLARE
    sample_policy_id UUID;
    sample_tenant_id VARCHAR(255) := 'sample-tenant-123';
    sample_learner_id VARCHAR(255) := 'sample-learner-456';
BEGIN
    -- Insert a sample residency policy
    INSERT INTO residency_policies (
        policy_id, tenant_id, learner_id, primary_region, allowed_regions,
        prohibited_regions, compliance_frameworks, data_classification,
        allow_cross_region_failover, require_encryption_at_rest,
        require_encryption_in_transit, data_retention_days,
        emergency_contact, created_by, created_at, updated_at, is_active
    ) VALUES (
        uuid_generate_v4(),
        sample_tenant_id,
        sample_learner_id,
        'us-east',
        '["us-west", "ca-central"]'::json,
        '[]'::json,
        '["ferpa"]'::json,
        'educational',
        true,
        true,
        true,
        2555, -- 7 years for educational records
        'admin@sample-org.edu',
        'system',
        NOW(),
        NOW(),
        true
    ) RETURNING policy_id INTO sample_policy_id;

    -- Insert a sample audit log
    INSERT INTO data_access_logs (
        log_id, policy_id, tenant_id, learner_id, user_id, operation_type,
        resource_type, resource_id, requested_region, actual_region,
        is_cross_region, compliance_check_result, request_id,
        response_status, timestamp
    ) VALUES (
        uuid_generate_v4(),
        sample_policy_id,
        sample_tenant_id,
        sample_learner_id,
        'sample-user-789',
        'read',
        'document',
        'sample-doc-001',
        'us-east',
        'us-east',
        false,
        'allowed',
        'req-' || gen_random_uuid()::text,
        200,
        NOW()
    );

END $$;

-- Create views for common queries
CREATE OR REPLACE VIEW active_residency_policies AS
SELECT 
    policy_id,
    tenant_id,
    learner_id,
    primary_region,
    allowed_regions,
    prohibited_regions,
    compliance_frameworks,
    data_classification,
    allow_cross_region_failover,
    created_at,
    updated_at
FROM residency_policies 
WHERE is_active = true;

CREATE OR REPLACE VIEW cross_region_access_summary AS
SELECT 
    tenant_id,
    COUNT(*) as total_access_attempts,
    COUNT(CASE WHEN is_cross_region THEN 1 END) as cross_region_attempts,
    COUNT(CASE WHEN compliance_check_result = 'denied' THEN 1 END) as denied_attempts,
    COUNT(CASE WHEN emergency_override THEN 1 END) as override_attempts,
    MAX(timestamp) as last_access
FROM data_access_logs
GROUP BY tenant_id;

CREATE OR REPLACE VIEW compliance_violations AS
SELECT 
    dal.tenant_id,
    dal.learner_id,
    dal.user_id,
    dal.operation_type,
    dal.resource_type,
    dal.resource_id,
    dal.requested_region,
    dal.actual_region,
    dal.compliance_check_result,
    dal.denial_reason,
    dal.timestamp,
    rp.compliance_frameworks
FROM data_access_logs dal
LEFT JOIN residency_policies rp ON dal.policy_id = rp.policy_id
WHERE dal.compliance_check_result = 'denied'
ORDER BY dal.timestamp DESC;

-- Add comments for documentation
COMMENT ON TABLE residency_policies IS 'Data residency policies for tenants and learners';
COMMENT ON TABLE region_infrastructure IS 'Regional infrastructure configuration for data storage and processing';
COMMENT ON TABLE data_access_logs IS 'Audit logs for all data access operations';
COMMENT ON TABLE emergency_overrides IS 'Emergency override requests for cross-region access';

COMMENT ON COLUMN residency_policies.primary_region IS 'Primary region where data should be stored and processed';
COMMENT ON COLUMN residency_policies.allowed_regions IS 'List of additional regions where data access is permitted';
COMMENT ON COLUMN residency_policies.prohibited_regions IS 'List of regions where data access is explicitly forbidden';
COMMENT ON COLUMN residency_policies.compliance_frameworks IS 'List of compliance frameworks that apply to this policy';

COMMENT ON VIEW active_residency_policies IS 'View showing only active residency policies';
COMMENT ON VIEW cross_region_access_summary IS 'Summary statistics for cross-region access patterns by tenant';
COMMENT ON VIEW compliance_violations IS 'View showing all compliance violations for audit purposes';

-- Grant permissions (adjust as needed for your environment)
-- GRANT SELECT ON ALL TABLES IN SCHEMA public TO residency_read_only;
-- GRANT ALL PRIVILEGES ON ALL TABLES IN SCHEMA public TO residency_app;

RAISE NOTICE 'Database initialization completed successfully';
