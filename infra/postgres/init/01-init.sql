-- aivo-virtual-brains PostgreSQL initialization
-- This script runs when the PostgreSQL container starts for the first time

-- Create additional databases for different services
CREATE DATABASE aivo_auth;
CREATE DATABASE aivo_analytics;

-- Create service-specific users
CREATE USER auth_service WITH PASSWORD 'auth123';
CREATE USER analytics_service WITH PASSWORD 'analytics123';

-- Grant permissions
GRANT ALL PRIVILEGES ON DATABASE aivo_auth TO auth_service;
GRANT ALL PRIVILEGES ON DATABASE aivo_analytics TO analytics_service;

-- Enable common extensions
\c aivo_dev;
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";
CREATE EXTENSION IF NOT EXISTS "pgcrypto";
CREATE EXTENSION IF NOT EXISTS "pg_trgm";

\c aivo_auth;
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";
CREATE EXTENSION IF NOT EXISTS "pgcrypto";

\c aivo_analytics;
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";
CREATE EXTENSION IF NOT EXISTS "pg_trgm";

-- Create a sample table in the main database
\c aivo_dev;
CREATE TABLE IF NOT EXISTS health_check (
    id SERIAL PRIMARY KEY,
    service_name VARCHAR(100) NOT NULL,
    status VARCHAR(20) DEFAULT 'healthy',
    checked_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

INSERT INTO health_check (service_name) VALUES ('postgres_init');
