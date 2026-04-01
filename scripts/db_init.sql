-- UEM Platform - Database initialization
-- This runs automatically when the PostgreSQL container starts

-- Enable UUID generation
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";
CREATE EXTENSION IF NOT EXISTS "pg_trgm";  -- for fuzzy text search

-- Set timezone
SET timezone = 'UTC';

COMMENT ON DATABASE uem IS 'UEM Platform - Unified Endpoint Management';
