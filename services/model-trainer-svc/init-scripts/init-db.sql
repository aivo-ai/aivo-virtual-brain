-- Model Trainer Service Database Initialization
-- Creates the database and user for the trainer service

-- Create database (if not exists)
SELECT 'CREATE DATABASE model_trainer'
WHERE NOT EXISTS (SELECT FROM pg_database WHERE datname = 'model_trainer')\gexec

-- Create test database (if not exists) 
SELECT 'CREATE DATABASE test_model_trainer'
WHERE NOT EXISTS (SELECT FROM pg_database WHERE datname = 'test_model_trainer')\gexec

-- Ensure trainer user has proper permissions
GRANT ALL PRIVILEGES ON DATABASE model_trainer TO trainer;
GRANT ALL PRIVILEGES ON DATABASE test_model_trainer TO trainer;
