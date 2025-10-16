-- PostgreSQL Master Registry Migration
-- Migration: 001_create_uds3_master_documents.sql
-- Erstellt die Master Documents Registry für UDS3 Multi-Database Distribution
-- 
-- Diese Tabelle dient als zentrale Registry für alle verarbeiteten Dokumente
-- und koordiniert die Distribution auf die verschiedenen Backend-Datenbanken.
--
-- Author: Covina Development Team
-- Date: 3. Oktober 2025
-- Version: 1.0.0

-- Enable UUID extension if not exists
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";
CREATE EXTENSION IF NOT EXISTS "pg_trgm";  -- For trigram text search

-- Create enum types for better type safety
CREATE TYPE processing_status_type AS ENUM (
    'pending',
    'processing', 
    'completed',
    'failed',
    'archived'
);

CREATE TYPE document_category_type AS ENUM (
    'image',
    'document', 
    'media',
    'geospatial',
    'email',
    'archive',
    'office',
    'web',
    'unknown'
);

-- ============================================================================
-- UDS3 Master Documents Registry
-- ============================================================================
-- Zentrale Registry für alle Dokumente mit Cross-DB References
CREATE TABLE uds3_master_documents (
    -- Primary Identification
    document_id VARCHAR(255) PRIMARY KEY,
    uuid UUID UNIQUE DEFAULT uuid_generate_v4(),
    
    -- File Information
    file_path VARCHAR(500) NOT NULL,
    original_filename TEXT,
    file_size_bytes BIGINT,
    file_hash_sha256 CHAR(64),
    mime_type VARCHAR(100),
    
    -- Processing Information  
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    processing_status processing_status_type DEFAULT 'pending',
    processor_version VARCHAR(50),
    
    -- Document Classification
    document_category document_category_type DEFAULT 'unknown',
    confidence_score REAL DEFAULT 0.0,
    
    -- Multi-DB Distribution Tracking
    postgresql_refs JSONB DEFAULT '{}',      -- References to PostgreSQL data
    couchdb_refs JSONB DEFAULT '{}',         -- References to CouchDB documents  
    chromadb_refs JSONB DEFAULT '{}',        -- References to ChromaDB collections
    neo4j_refs JSONB DEFAULT '{}',           -- References to Neo4j nodes
    
    -- Adaptive Strategy Information
    distribution_strategy VARCHAR(50) DEFAULT 'adaptive',  -- Current strategy used
    fallback_applied BOOLEAN DEFAULT FALSE,
    
    -- Search and Performance
    search_vector tsvector,                   -- Full-text search vector
    metadata_json JSONB DEFAULT '{}',        -- Flexible metadata storage
    
    -- Audit Trail
    created_by VARCHAR(100) DEFAULT 'system',
    last_processor VARCHAR(100),
    
    -- Constraints
    CONSTRAINT valid_file_hash CHECK (file_hash_sha256 ~ '^[a-fA-F0-9]{64}$' OR file_hash_sha256 IS NULL),
    CONSTRAINT valid_confidence CHECK (confidence_score >= 0.0 AND confidence_score <= 1.0),
    CONSTRAINT valid_file_size CHECK (file_size_bytes >= 0)
);

-- ============================================================================
-- Indexes for Performance
-- ============================================================================

-- Primary performance indexes
CREATE INDEX idx_master_documents_status ON uds3_master_documents(processing_status);
CREATE INDEX idx_master_documents_category ON uds3_master_documents(document_category);
CREATE INDEX idx_master_documents_created ON uds3_master_documents(created_at);
CREATE INDEX idx_master_documents_updated ON uds3_master_documents(updated_at);

-- Hash-based lookups for deduplication
CREATE UNIQUE INDEX idx_master_documents_hash ON uds3_master_documents(file_hash_sha256) 
WHERE file_hash_sha256 IS NOT NULL;

-- Full-text search index  
CREATE INDEX idx_master_documents_search ON uds3_master_documents USING GIN(search_vector);

-- JSONB indexes for multi-db references (PostgreSQL specific)
CREATE INDEX idx_master_documents_postgresql_refs ON uds3_master_documents USING GIN(postgresql_refs);
CREATE INDEX idx_master_documents_couchdb_refs ON uds3_master_documents USING GIN(couchdb_refs);
CREATE INDEX idx_master_documents_chromadb_refs ON uds3_master_documents USING GIN(chromadb_refs);
CREATE INDEX idx_master_documents_neo4j_refs ON uds3_master_documents USING GIN(neo4j_refs);

-- Metadata search index
CREATE INDEX idx_master_documents_metadata ON uds3_master_documents USING GIN(metadata_json);

-- Composite indexes for common queries
CREATE INDEX idx_master_documents_category_status ON uds3_master_documents(document_category, processing_status);
CREATE INDEX idx_master_documents_strategy_fallback ON uds3_master_documents(distribution_strategy, fallback_applied);

-- ============================================================================
-- Triggers for Automatic Updates
-- ============================================================================

-- Function to update search vector automatically
CREATE OR REPLACE FUNCTION update_master_documents_search_vector() 
RETURNS TRIGGER AS $$
BEGIN
    -- Build search vector from filename, metadata, and path
    NEW.search_vector := 
        setweight(to_tsvector('english', COALESCE(NEW.original_filename, '')), 'A') ||
        setweight(to_tsvector('english', COALESCE(NEW.file_path, '')), 'B') ||
        setweight(to_tsvector('english', COALESCE(NEW.metadata_json->>'title', '')), 'A') ||
        setweight(to_tsvector('english', COALESCE(NEW.metadata_json->>'description', '')), 'B') ||
        setweight(to_tsvector('english', COALESCE(NEW.metadata_json->>'keywords', '')), 'C');
    
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

-- Trigger to update search vector on insert/update
CREATE TRIGGER trg_update_search_vector 
    BEFORE INSERT OR UPDATE ON uds3_master_documents
    FOR EACH ROW 
    EXECUTE FUNCTION update_master_documents_search_vector();

-- Function to automatically update updated_at timestamp
CREATE OR REPLACE FUNCTION update_updated_at_timestamp()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = CURRENT_TIMESTAMP;
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

-- Trigger to update timestamp on update
CREATE TRIGGER trg_update_updated_at
    BEFORE UPDATE ON uds3_master_documents
    FOR EACH ROW
    EXECUTE FUNCTION update_updated_at_timestamp();

-- ============================================================================
-- Helper Functions for Multi-DB References
-- ============================================================================

-- Function to add PostgreSQL reference
CREATE OR REPLACE FUNCTION add_postgresql_ref(
    p_document_id VARCHAR(255),
    p_table_name TEXT,
    p_record_id TEXT,
    p_description TEXT DEFAULT NULL
) RETURNS BOOLEAN AS $$
DECLARE
    current_refs JSONB;
BEGIN
    -- Get current references
    SELECT postgresql_refs INTO current_refs 
    FROM uds3_master_documents 
    WHERE document_id = p_document_id;
    
    -- Add new reference
    current_refs = COALESCE(current_refs, '{}'::jsonb) || 
                   jsonb_build_object(
                       p_table_name, 
                       jsonb_build_object(
                           'record_id', p_record_id,
                           'created_at', CURRENT_TIMESTAMP,
                           'description', p_description
                       )
                   );
    
    -- Update the record
    UPDATE uds3_master_documents 
    SET postgresql_refs = current_refs,
        updated_at = CURRENT_TIMESTAMP
    WHERE document_id = p_document_id;
    
    RETURN FOUND;
END;
$$ LANGUAGE plpgsql;

-- Function to add CouchDB reference  
CREATE OR REPLACE FUNCTION add_couchdb_ref(
    p_document_id VARCHAR(255),
    p_database_name TEXT,
    p_doc_id TEXT,
    p_rev TEXT DEFAULT NULL
) RETURNS BOOLEAN AS $$
DECLARE
    current_refs JSONB;
BEGIN
    SELECT couchdb_refs INTO current_refs 
    FROM uds3_master_documents 
    WHERE document_id = p_document_id;
    
    current_refs = COALESCE(current_refs, '{}'::jsonb) || 
                   jsonb_build_object(
                       p_database_name,
                       jsonb_build_object(
                           'doc_id', p_doc_id,
                           'rev', p_rev,
                           'created_at', CURRENT_TIMESTAMP
                       )
                   );
    
    UPDATE uds3_master_documents 
    SET couchdb_refs = current_refs,
        updated_at = CURRENT_TIMESTAMP
    WHERE document_id = p_document_id;
    
    RETURN FOUND;
END;
$$ LANGUAGE plpgsql;

-- Function to add ChromaDB reference
CREATE OR REPLACE FUNCTION add_chromadb_ref(
    p_document_id VARCHAR(255),
    p_collection_name TEXT,
    p_vector_id TEXT,
    p_embedding_model TEXT DEFAULT NULL
) RETURNS BOOLEAN AS $$
DECLARE
    current_refs JSONB;
BEGIN
    SELECT chromadb_refs INTO current_refs 
    FROM uds3_master_documents 
    WHERE document_id = p_document_id;
    
    current_refs = COALESCE(current_refs, '{}'::jsonb) || 
                   jsonb_build_object(
                       p_collection_name,
                       jsonb_build_object(
                           'vector_id', p_vector_id,
                           'embedding_model', p_embedding_model,
                           'created_at', CURRENT_TIMESTAMP
                       )
                   );
    
    UPDATE uds3_master_documents 
    SET chromadb_refs = current_refs,
        updated_at = CURRENT_TIMESTAMP
    WHERE document_id = p_document_id;
    
    RETURN FOUND;
END;
$$ LANGUAGE plpgsql;

-- Function to add Neo4j reference
CREATE OR REPLACE FUNCTION add_neo4j_ref(
    p_document_id VARCHAR(255),
    p_node_label TEXT,
    p_node_id TEXT,
    p_properties JSONB DEFAULT NULL
) RETURNS BOOLEAN AS $$
DECLARE
    current_refs JSONB;
BEGIN
    SELECT neo4j_refs INTO current_refs 
    FROM uds3_master_documents 
    WHERE document_id = p_document_id;
    
    current_refs = COALESCE(current_refs, '{}'::jsonb) || 
                   jsonb_build_object(
                       p_node_label,
                       jsonb_build_object(
                           'node_id', p_node_id,
                           'properties', p_properties,
                           'created_at', CURRENT_TIMESTAMP
                       )
                   );
    
    UPDATE uds3_master_documents 
    SET neo4j_refs = current_refs,
        updated_at = CURRENT_TIMESTAMP
    WHERE document_id = p_document_id;
    
    RETURN FOUND;
END;
$$ LANGUAGE plpgsql;

-- ============================================================================
-- Views for Common Queries
-- ============================================================================

-- View for documents with their processing status overview
CREATE VIEW v_document_processing_overview AS
SELECT 
    document_id,
    uuid,
    original_filename,
    document_category,
    processing_status,
    distribution_strategy,
    fallback_applied,
    created_at,
    updated_at,
    -- Count references per database type
    (CASE WHEN postgresql_refs = '{}'::jsonb THEN 0 ELSE jsonb_object_keys(postgresql_refs) END) as postgresql_ref_count,
    (CASE WHEN couchdb_refs = '{}'::jsonb THEN 0 ELSE jsonb_object_keys(couchdb_refs) END) as couchdb_ref_count,
    (CASE WHEN chromadb_refs = '{}'::jsonb THEN 0 ELSE jsonb_object_keys(chromadb_refs) END) as chromadb_ref_count,
    (CASE WHEN neo4j_refs = '{}'::jsonb THEN 0 ELSE jsonb_object_keys(neo4j_refs) END) as neo4j_ref_count
FROM uds3_master_documents;

-- View for search-ready documents
CREATE VIEW v_searchable_documents AS  
SELECT 
    document_id,
    original_filename,
    document_category,
    search_vector,
    metadata_json,
    confidence_score,
    processing_status
FROM uds3_master_documents
WHERE processing_status IN ('completed', 'processing')
AND search_vector IS NOT NULL;

-- ============================================================================
-- Sample Data and Comments
-- ============================================================================

-- Add helpful comments
COMMENT ON TABLE uds3_master_documents IS 'Central registry for all UDS3 processed documents with cross-database references';
COMMENT ON COLUMN uds3_master_documents.document_id IS 'Unique identifier for document across all databases';
COMMENT ON COLUMN uds3_master_documents.postgresql_refs IS 'JSONB references to PostgreSQL table records';
COMMENT ON COLUMN uds3_master_documents.couchdb_refs IS 'JSONB references to CouchDB documents';
COMMENT ON COLUMN uds3_master_documents.chromadb_refs IS 'JSONB references to ChromaDB vector collections';
COMMENT ON COLUMN uds3_master_documents.neo4j_refs IS 'JSONB references to Neo4j graph nodes';
COMMENT ON COLUMN uds3_master_documents.distribution_strategy IS 'Adaptive strategy used for document distribution';

-- Grant permissions (adjust as needed for your environment)
-- GRANT SELECT, INSERT, UPDATE ON uds3_master_documents TO uds3_application;
-- GRANT USAGE ON SEQUENCE uds3_master_documents_uuid_seq TO uds3_application;

-- Migration completion marker
INSERT INTO schema_migrations (version, applied_at) VALUES ('001', CURRENT_TIMESTAMP)
ON CONFLICT (version) DO UPDATE SET applied_at = CURRENT_TIMESTAMP;

-- Success message
SELECT 'UDS3 Master Documents Registry created successfully!' as migration_result;