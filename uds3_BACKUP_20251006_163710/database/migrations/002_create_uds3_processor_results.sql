-- PostgreSQL Processor Results Migration
-- Migration: 002_create_uds3_processor_results.sql
-- Erstellt die Processor Results Tabelle für detaillierte UDS3 Processing Results
-- 
-- Diese Tabelle speichert alle Ergebnisse der verschiedenen UDS3 Processors
-- und ermöglicht die Rekonstruktion der kompletten Processing Pipeline.
--
-- Author: Covina Development Team
-- Date: 3. Oktober 2025
-- Version: 1.0.0

-- Create enum types for processor results
CREATE TYPE result_type_enum AS ENUM (
    'metadata_extraction',
    'content_extraction', 
    'embedding_generation',
    'relationship_detection',
    'spatial_analysis',
    'classification',
    'quality_assessment',
    'security_scan',
    'thumbnail_generation',
    'format_conversion',
    'error_result'
);

CREATE TYPE processor_status_enum AS ENUM (
    'pending',
    'running',
    'completed',
    'failed',
    'cancelled',
    'timeout'
);

-- ============================================================================
-- UDS3 Processor Results Table
-- ============================================================================
-- Detaillierte Ergebnisse aller UDS3 Processor Runs für jeden Document
CREATE TABLE uds3_processor_results (
    -- Primary Key
    id SERIAL PRIMARY KEY,
    
    -- Document Reference
    document_id VARCHAR(255) NOT NULL REFERENCES uds3_master_documents(document_id) ON DELETE CASCADE,
    
    -- Processor Information
    processor_name VARCHAR(100) NOT NULL,
    processor_version VARCHAR(50),
    processor_config_hash CHAR(32),  -- MD5 of processor configuration
    
    -- Execution Information
    processing_timestamp TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    started_at TIMESTAMP WITH TIME ZONE,
    completed_at TIMESTAMP WITH TIME ZONE,
    execution_time_ms INTEGER,
    
    -- Result Information
    result_type result_type_enum NOT NULL,
    processor_status processor_status_enum DEFAULT 'pending',
    confidence_score REAL DEFAULT 0.0,
    
    -- Result Data (flexible JSON storage)
    result_data JSONB DEFAULT '{}',
    metadata_extracted JSONB DEFAULT '{}',
    
    -- Error Handling
    error_message TEXT,
    error_code VARCHAR(50),
    stack_trace TEXT,
    
    -- Performance Metrics
    memory_usage_mb INTEGER,
    cpu_usage_percent REAL,
    disk_io_kb INTEGER,
    
    -- Distribution Tracking
    distributed_to_postgresql BOOLEAN DEFAULT FALSE,
    distributed_to_couchdb BOOLEAN DEFAULT FALSE,
    distributed_to_chromadb BOOLEAN DEFAULT FALSE,
    distributed_to_neo4j BOOLEAN DEFAULT FALSE,
    distribution_timestamp TIMESTAMP WITH TIME ZONE,
    
    -- Quality and Validation
    validation_passed BOOLEAN,
    quality_score REAL,
    warnings JSONB DEFAULT '[]',
    
    -- Audit Information
    created_by VARCHAR(100) DEFAULT 'system',
    pipeline_run_id VARCHAR(100),  -- Link to pipeline execution
    correlation_id VARCHAR(100),   -- For distributed tracing
    
    -- Constraints
    CONSTRAINT valid_confidence CHECK (confidence_score >= 0.0 AND confidence_score <= 1.0),
    CONSTRAINT valid_quality CHECK (quality_score IS NULL OR (quality_score >= 0.0 AND quality_score <= 1.0)),
    CONSTRAINT valid_execution_time CHECK (execution_time_ms >= 0),
    CONSTRAINT valid_memory_usage CHECK (memory_usage_mb >= 0),
    CONSTRAINT valid_cpu_usage CHECK (cpu_usage_percent >= 0.0 AND cpu_usage_percent <= 100.0)
);

-- ============================================================================
-- Indexes for Performance
-- ============================================================================

-- Primary lookup indexes
CREATE INDEX idx_processor_results_document ON uds3_processor_results(document_id);
CREATE INDEX idx_processor_results_processor ON uds3_processor_results(processor_name);
CREATE INDEX idx_processor_results_timestamp ON uds3_processor_results(processing_timestamp);
CREATE INDEX idx_processor_results_status ON uds3_processor_results(processor_status);

-- Composite indexes for common queries
CREATE INDEX idx_processor_results_doc_processor ON uds3_processor_results(document_id, processor_name);
CREATE INDEX idx_processor_results_doc_status ON uds3_processor_results(document_id, processor_status);
CREATE INDEX idx_processor_results_processor_status ON uds3_processor_results(processor_name, processor_status);

-- Result type and quality indexes
CREATE INDEX idx_processor_results_result_type ON uds3_processor_results(result_type);
CREATE INDEX idx_processor_results_quality ON uds3_processor_results(quality_score) WHERE quality_score IS NOT NULL;
CREATE INDEX idx_processor_results_confidence ON uds3_processor_results(confidence_score);

-- Distribution tracking indexes
CREATE INDEX idx_processor_results_distribution ON uds3_processor_results(distribution_timestamp) 
WHERE distribution_timestamp IS NOT NULL;

CREATE INDEX idx_processor_results_distributed_dbs ON uds3_processor_results(
    distributed_to_postgresql, distributed_to_couchdb, distributed_to_chromadb, distributed_to_neo4j
);

-- JSONB indexes for flexible queries
CREATE INDEX idx_processor_results_data ON uds3_processor_results USING GIN(result_data);
CREATE INDEX idx_processor_results_metadata ON uds3_processor_results USING GIN(metadata_extracted);
CREATE INDEX idx_processor_results_warnings ON uds3_processor_results USING GIN(warnings);

-- Performance metrics indexes for monitoring
CREATE INDEX idx_processor_results_performance ON uds3_processor_results(
    execution_time_ms, memory_usage_mb, cpu_usage_percent
);

-- Pipeline and tracing indexes
CREATE INDEX idx_processor_results_pipeline ON uds3_processor_results(pipeline_run_id) 
WHERE pipeline_run_id IS NOT NULL;
CREATE INDEX idx_processor_results_correlation ON uds3_processor_results(correlation_id) 
WHERE correlation_id IS NOT NULL;

-- ============================================================================
-- Triggers and Functions
-- ============================================================================

-- Function to calculate execution time automatically
CREATE OR REPLACE FUNCTION calculate_execution_time()
RETURNS TRIGGER AS $$
BEGIN
    -- Calculate execution time if both timestamps are available
    IF NEW.started_at IS NOT NULL AND NEW.completed_at IS NOT NULL THEN
        NEW.execution_time_ms := EXTRACT(EPOCH FROM (NEW.completed_at - NEW.started_at)) * 1000;
    END IF;
    
    -- Set processing timestamp if not set
    IF NEW.processing_timestamp IS NULL THEN
        NEW.processing_timestamp := COALESCE(NEW.completed_at, NEW.started_at, CURRENT_TIMESTAMP);
    END IF;
    
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

-- Trigger to calculate execution time
CREATE TRIGGER trg_calculate_execution_time
    BEFORE INSERT OR UPDATE ON uds3_processor_results
    FOR EACH ROW
    EXECUTE FUNCTION calculate_execution_time();

-- Function to update document processing status
CREATE OR REPLACE FUNCTION update_document_processing_status()
RETURNS TRIGGER AS $$
DECLARE
    total_processors INTEGER;
    completed_processors INTEGER;
    failed_processors INTEGER;
    new_status processing_status_type;
BEGIN
    -- Count processor results for this document
    SELECT 
        COUNT(*),
        COUNT(*) FILTER (WHERE processor_status = 'completed'),
        COUNT(*) FILTER (WHERE processor_status = 'failed')
    INTO total_processors, completed_processors, failed_processors
    FROM uds3_processor_results 
    WHERE document_id = COALESCE(NEW.document_id, OLD.document_id);
    
    -- Determine new document status
    IF failed_processors > 0 AND completed_processors = 0 THEN
        new_status := 'failed';
    ELSIF completed_processors = total_processors AND total_processors > 0 THEN
        new_status := 'completed';
    ELSIF completed_processors > 0 OR total_processors > 0 THEN
        new_status := 'processing';
    ELSE
        new_status := 'pending';
    END IF;
    
    -- Update master document status
    UPDATE uds3_master_documents 
    SET 
        processing_status = new_status,
        updated_at = CURRENT_TIMESTAMP,
        last_processor = COALESCE(NEW.processor_name, OLD.processor_name)
    WHERE document_id = COALESCE(NEW.document_id, OLD.document_id);
    
    RETURN COALESCE(NEW, OLD);
END;
$$ LANGUAGE plpgsql;

-- Trigger to update document status when processor results change
CREATE TRIGGER trg_update_document_status
    AFTER INSERT OR UPDATE OR DELETE ON uds3_processor_results
    FOR EACH ROW
    EXECUTE FUNCTION update_document_processing_status();

-- ============================================================================
-- Helper Functions for Processor Results
-- ============================================================================

-- Function to add processor result with automatic metadata
CREATE OR REPLACE FUNCTION add_processor_result(
    p_document_id VARCHAR(255),
    p_processor_name VARCHAR(100),
    p_result_type result_type_enum,
    p_result_data JSONB DEFAULT '{}',
    p_confidence_score REAL DEFAULT 1.0,
    p_processor_version VARCHAR(50) DEFAULT NULL
) RETURNS INTEGER AS $$
DECLARE
    new_result_id INTEGER;
BEGIN
    INSERT INTO uds3_processor_results (
        document_id,
        processor_name,
        processor_version,
        result_type,
        result_data,
        confidence_score,
        processor_status,
        started_at,
        completed_at
    ) VALUES (
        p_document_id,
        p_processor_name,
        p_processor_version,
        p_result_type,
        p_result_data,
        p_confidence_score,
        'completed',
        CURRENT_TIMESTAMP,
        CURRENT_TIMESTAMP
    ) RETURNING id INTO new_result_id;
    
    RETURN new_result_id;
END;
$$ LANGUAGE plpgsql;

-- Function to mark processor result as distributed to specific database
CREATE OR REPLACE FUNCTION mark_distributed_to_db(
    p_result_id INTEGER,
    p_database_type TEXT  -- 'postgresql', 'couchdb', 'chromadb', 'neo4j'
) RETURNS BOOLEAN AS $$
BEGIN
    CASE p_database_type
        WHEN 'postgresql' THEN
            UPDATE uds3_processor_results 
            SET distributed_to_postgresql = TRUE, distribution_timestamp = CURRENT_TIMESTAMP
            WHERE id = p_result_id;
        WHEN 'couchdb' THEN
            UPDATE uds3_processor_results 
            SET distributed_to_couchdb = TRUE, distribution_timestamp = CURRENT_TIMESTAMP
            WHERE id = p_result_id;
        WHEN 'chromadb' THEN
            UPDATE uds3_processor_results 
            SET distributed_to_chromadb = TRUE, distribution_timestamp = CURRENT_TIMESTAMP
            WHERE id = p_result_id;
        WHEN 'neo4j' THEN
            UPDATE uds3_processor_results 
            SET distributed_to_neo4j = TRUE, distribution_timestamp = CURRENT_TIMESTAMP
            WHERE id = p_result_id;
        ELSE
            RETURN FALSE;
    END CASE;
    
    RETURN FOUND;
END;
$$ LANGUAGE plpgsql;

-- Function to get processor results summary for document
CREATE OR REPLACE FUNCTION get_document_processor_summary(p_document_id VARCHAR(255))
RETURNS TABLE (
    processor_name VARCHAR(100),
    result_type result_type_enum,
    processor_status processor_status_enum,
    confidence_score REAL,
    execution_time_ms INTEGER,
    distributed_count INTEGER
) AS $$
BEGIN
    RETURN QUERY
    SELECT 
        pr.processor_name,
        pr.result_type,
        pr.processor_status,
        pr.confidence_score,
        pr.execution_time_ms,
        (CASE WHEN pr.distributed_to_postgresql THEN 1 ELSE 0 END +
         CASE WHEN pr.distributed_to_couchdb THEN 1 ELSE 0 END +
         CASE WHEN pr.distributed_to_chromadb THEN 1 ELSE 0 END +
         CASE WHEN pr.distributed_to_neo4j THEN 1 ELSE 0 END)::INTEGER as distributed_count
    FROM uds3_processor_results pr
    WHERE pr.document_id = p_document_id
    ORDER BY pr.processing_timestamp DESC;
END;
$$ LANGUAGE plpgsql;

-- ============================================================================
-- Views for Common Queries
-- ============================================================================

-- View for processor performance analysis
CREATE VIEW v_processor_performance AS
SELECT 
    processor_name,
    processor_version,
    COUNT(*) as total_runs,
    COUNT(*) FILTER (WHERE processor_status = 'completed') as successful_runs,
    COUNT(*) FILTER (WHERE processor_status = 'failed') as failed_runs,
    AVG(execution_time_ms) as avg_execution_time_ms,
    AVG(confidence_score) as avg_confidence_score,
    AVG(memory_usage_mb) as avg_memory_usage_mb,
    MAX(processing_timestamp) as last_run
FROM uds3_processor_results
GROUP BY processor_name, processor_version;

-- View for document processing status
CREATE VIEW v_document_processing_status AS
SELECT 
    md.document_id,
    md.original_filename,
    md.document_category,
    md.processing_status,
    COUNT(pr.id) as total_processor_results,
    COUNT(pr.id) FILTER (WHERE pr.processor_status = 'completed') as completed_results,
    COUNT(pr.id) FILTER (WHERE pr.processor_status = 'failed') as failed_results,
    AVG(pr.confidence_score) as avg_confidence,
    MAX(pr.processing_timestamp) as last_processed,
    -- Distribution status
    BOOL_OR(pr.distributed_to_postgresql) as has_postgresql_data,
    BOOL_OR(pr.distributed_to_couchdb) as has_couchdb_data,
    BOOL_OR(pr.distributed_to_chromadb) as has_chromadb_data,
    BOOL_OR(pr.distributed_to_neo4j) as has_neo4j_data
FROM uds3_master_documents md
LEFT JOIN uds3_processor_results pr ON md.document_id = pr.document_id
GROUP BY md.document_id, md.original_filename, md.document_category, md.processing_status;

-- View for failed processors analysis
CREATE VIEW v_failed_processors AS
SELECT 
    processor_name,
    error_code,
    error_message,
    COUNT(*) as failure_count,
    MAX(processing_timestamp) as last_failure,
    AVG(execution_time_ms) as avg_failure_time_ms
FROM uds3_processor_results
WHERE processor_status = 'failed'
GROUP BY processor_name, error_code, error_message
ORDER BY failure_count DESC;

-- ============================================================================
-- Comments and Documentation
-- ============================================================================

COMMENT ON TABLE uds3_processor_results IS 'Detailed results from all UDS3 processor executions';
COMMENT ON COLUMN uds3_processor_results.result_data IS 'Flexible JSONB storage for processor output data';
COMMENT ON COLUMN uds3_processor_results.metadata_extracted IS 'Extracted metadata from processor analysis';
COMMENT ON COLUMN uds3_processor_results.distribution_timestamp IS 'When this result was distributed to databases';
COMMENT ON COLUMN uds3_processor_results.correlation_id IS 'For distributed tracing across microservices';

-- Migration completion
INSERT INTO schema_migrations (version, applied_at) VALUES ('002', CURRENT_TIMESTAMP)
ON CONFLICT (version) DO UPDATE SET applied_at = CURRENT_TIMESTAMP;

-- Success message
SELECT 'UDS3 Processor Results table created successfully!' as migration_result;