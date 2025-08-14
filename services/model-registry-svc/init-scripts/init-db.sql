-- AIVO Model Registry - Database Initialization
-- S2-02 Implementation: Create database and extensions

-- Create additional databases if needed
CREATE DATABASE test_model_registry;

-- Create extensions for enhanced functionality
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";
CREATE EXTENSION IF NOT EXISTS "pg_stat_statements";

-- Grant permissions
GRANT ALL PRIVILEGES ON DATABASE model_registry TO postgres;
GRANT ALL PRIVILEGES ON DATABASE test_model_registry TO postgres;
