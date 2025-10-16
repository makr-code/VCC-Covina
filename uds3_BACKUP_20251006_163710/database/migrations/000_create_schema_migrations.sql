-- Schema Migrations Tracking Table
-- Migration: 000_create_schema_migrations.sql
-- Erstellt die Schema Migrations Tracking Tabelle für PostgreSQL Migration Management
--
-- Author: Covina Development Team
-- Date: 3. Oktober 2025
-- Version: 1.0.0

-- ============================================================================
-- Schema Migrations Tracking Table
-- ============================================================================
-- Diese Tabelle verfolgt alle angewandten Database Migrations
CREATE TABLE IF NOT EXISTS schema_migrations (
    version VARCHAR(50) PRIMARY KEY,
    applied_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    description TEXT,
    checksum CHAR(32),  -- MD5 hash of migration file
    execution_time_ms INTEGER,
    applied_by VARCHAR(100) DEFAULT USER
);

-- Index for chronological queries
CREATE INDEX IF NOT EXISTS idx_schema_migrations_applied_at ON schema_migrations(applied_at);

-- Comments
COMMENT ON TABLE schema_migrations IS 'Tracks all applied database migrations for UDS3 Multi-DB system';
COMMENT ON COLUMN schema_migrations.version IS 'Migration version identifier (e.g., 001, 002, 003)';
COMMENT ON COLUMN schema_migrations.checksum IS 'MD5 hash to verify migration file integrity';

-- Success message
SELECT 'Schema migrations tracking table ready!' as migration_result;