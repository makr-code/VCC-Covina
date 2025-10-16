-- PostgreSQL Cross-References Migration  
-- Migration: 003_create_uds3_cross_references.sql
-- Erstellt die Cross-References Tabelle für Dokument-Beziehungen und Multi-DB Queries
-- 
-- Diese Tabelle speichert Beziehungen zwischen Dokumenten und ermöglicht
-- effiziente Cross-Database Queries und Rekonstruktion von Dokumenten-Netzwerken.
--
-- Author: Covina Development Team
-- Date: 3. Oktober 2025
-- Version: 1.0.0

-- Create enum types for cross-references
CREATE TYPE reference_type_enum AS ENUM (
    'similarity',           -- Content similarity relationship
    'citation',            -- Document cites another document
    'dependency',          -- Document depends on another
    'spatial_proximity',   -- Geospatial proximity relationship
    'temporal_sequence',   -- Time-based sequence relationship
    'conversion_source',   -- Document is converted from another
    'extraction_parent',   -- Document extracted from archive/container
    'duplicate',           -- Documents are duplicates/near-duplicates
    'translation',         -- Document is translation of another
    'version',             -- Document is version of another
    'metadata_link',       -- Linked through metadata relationships
    'content_fragment',    -- Document contains fragment of another
    'aggregation_member',  -- Document is part of aggregated content
    'manual_link',         -- Manually created relationship
    'ai_generated'         -- AI-detected relationship
);

CREATE TYPE reference_direction_enum AS ENUM (
    'bidirectional',       -- Relationship works both ways
    'source_to_target',    -- One-way from source to target
    'target_to_source'     -- One-way from target to source
);

CREATE TYPE confidence_level_enum AS ENUM (
    'very_low',    -- 0.0 - 0.2
    'low',         -- 0.2 - 0.4  
    'medium',      -- 0.4 - 0.6
    'high',        -- 0.6 - 0.8
    'very_high'    -- 0.8 - 1.0
);

-- ============================================================================
-- UDS3 Cross-References Table
-- ============================================================================
-- Beziehungen zwischen Dokumenten für Multi-DB Reconstruction
CREATE TABLE uds3_cross_references (
    -- Primary Key
    id SERIAL PRIMARY KEY,
    
    -- Document References
    source_document_id VARCHAR(255) NOT NULL REFERENCES uds3_master_documents(document_id) ON DELETE CASCADE,
    target_document_id VARCHAR(255) NOT NULL REFERENCES uds3_master_documents(document_id) ON DELETE CASCADE,
    
    -- Relationship Information
    reference_type reference_type_enum NOT NULL,
    reference_direction reference_direction_enum DEFAULT 'bidirectional',
    relationship_strength REAL DEFAULT 0.5,
    confidence_score REAL DEFAULT 0.0,
    confidence_level confidence_level_enum GENERATED ALWAYS AS (
        CASE 
            WHEN confidence_score < 0.2 THEN 'very_low'
            WHEN confidence_score < 0.4 THEN 'low'
            WHEN confidence_score < 0.6 THEN 'medium'  
            WHEN confidence_score < 0.8 THEN 'high'
            ELSE 'very_high'
        END
    ) STORED,
    
    -- Source Information
    detected_by VARCHAR(100) NOT NULL,  -- Processor/algorithm that detected relationship
    detection_method VARCHAR(100),      -- Method used for detection
    processor_version VARCHAR(50),
    
    -- Timing Information
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    validated_at TIMESTAMP WITH TIME ZONE,
    
    -- Detailed Relationship Data
    relationship_metadata JSONB DEFAULT '{}',  -- Flexible metadata about relationship
    similarity_metrics JSONB DEFAULT '{}',    -- Detailed similarity scores
    spatial_data JSONB DEFAULT '{}',          -- Spatial relationship data if applicable
    temporal_data JSONB DEFAULT '{}',         -- Temporal relationship data if applicable
    
    -- Multi-Database Distribution Information
    postgresql_stored BOOLEAN DEFAULT TRUE,   -- Always true since we're in PostgreSQL
    couchdb_replicated BOOLEAN DEFAULT FALSE, -- Replicated to CouchDB for event sourcing
    chromadb_vectorized BOOLEAN DEFAULT FALSE, -- Relationship vectorized in ChromaDB
    neo4j_graphed BOOLEAN DEFAULT FALSE,       -- Relationship stored as Neo4j edge
    
    -- Validation and Quality
    manually_validated BOOLEAN DEFAULT FALSE,
    validation_notes TEXT,
    quality_score REAL,
    false_positive_likelihood REAL DEFAULT 0.0,
    
    -- Performance Optimization
    frequent_query_pair BOOLEAN DEFAULT FALSE,  -- Mark frequently queried pairs
    cache_priority INTEGER DEFAULT 0,           -- Cache priority (0-10)
    last_accessed TIMESTAMP WITH TIME ZONE,
    access_count INTEGER DEFAULT 0,
    
    -- Audit Trail  
    created_by VARCHAR(100) DEFAULT 'system',
    correlation_id VARCHAR(100),  -- Link to processing pipeline
    pipeline_run_id VARCHAR(100), -- Batch processing identifier
    
    -- Constraints
    CONSTRAINT valid_relationship_strength CHECK (relationship_strength >= 0.0 AND relationship_strength <= 1.0),
    CONSTRAINT valid_confidence_score CHECK (confidence_score >= 0.0 AND confidence_score <= 1.0),
    CONSTRAINT valid_quality_score CHECK (quality_score IS NULL OR (quality_score >= 0.0 AND quality_score <= 1.0)),
    CONSTRAINT valid_false_positive CHECK (false_positive_likelihood >= 0.0 AND false_positive_likelihood <= 1.0),
    CONSTRAINT valid_cache_priority CHECK (cache_priority >= 0 AND cache_priority <= 10),
    CONSTRAINT no_self_reference CHECK (source_document_id != target_document_id),
    CONSTRAINT valid_access_count CHECK (access_count >= 0)
);

-- ============================================================================
-- Indexes for Performance
-- ============================================================================

-- Primary relationship lookup indexes
CREATE INDEX idx_cross_references_source ON uds3_cross_references(source_document_id);
CREATE INDEX idx_cross_references_target ON uds3_cross_references(target_document_id);

-- Bidirectional relationship index for efficient lookup in both directions
CREATE INDEX idx_cross_references_bidirectional ON uds3_cross_references(
    LEAST(source_document_id, target_document_id),
    GREATEST(source_document_id, target_document_id)
);

-- Reference type and quality indexes
CREATE INDEX idx_cross_references_type ON uds3_cross_references(reference_type);
CREATE INDEX idx_cross_references_confidence ON uds3_cross_references(confidence_level, confidence_score);
CREATE INDEX idx_cross_references_strength ON uds3_cross_references(relationship_strength);

-- Composite indexes for common query patterns
CREATE INDEX idx_cross_references_source_type ON uds3_cross_references(source_document_id, reference_type);
CREATE INDEX idx_cross_references_target_type ON uds3_cross_references(target_document_id, reference_type);
CREATE INDEX idx_cross_references_type_confidence ON uds3_cross_references(reference_type, confidence_level);

-- Performance and caching indexes
CREATE INDEX idx_cross_references_frequent_pairs ON uds3_cross_references(frequent_query_pair, cache_priority) 
WHERE frequent_query_pair = TRUE;
CREATE INDEX idx_cross_references_last_accessed ON uds3_cross_references(last_accessed) 
WHERE last_accessed IS NOT NULL;
CREATE INDEX idx_cross_references_access_count ON uds3_cross_references(access_count DESC);

-- Multi-database distribution indexes
CREATE INDEX idx_cross_references_distribution ON uds3_cross_references(
    couchdb_replicated, chromadb_vectorized, neo4j_graphed
);

-- Quality and validation indexes
CREATE INDEX idx_cross_references_validated ON uds3_cross_references(manually_validated, validation_notes) 
WHERE manually_validated = TRUE;
CREATE INDEX idx_cross_references_quality ON uds3_cross_references(quality_score) 
WHERE quality_score IS NOT NULL;

-- Time-based indexes
CREATE INDEX idx_cross_references_created ON uds3_cross_references(created_at);
CREATE INDEX idx_cross_references_updated ON uds3_cross_references(updated_at);

-- JSONB indexes for flexible metadata queries
CREATE INDEX idx_cross_references_metadata ON uds3_cross_references USING GIN(relationship_metadata);
CREATE INDEX idx_cross_references_similarity ON uds3_cross_references USING GIN(similarity_metrics);
CREATE INDEX idx_cross_references_spatial ON uds3_cross_references USING GIN(spatial_data);

-- Detection source indexes
CREATE INDEX idx_cross_references_detected_by ON uds3_cross_references(detected_by);
CREATE INDEX idx_cross_references_method ON uds3_cross_references(detection_method);

-- Unique constraint to prevent duplicate relationships (considering direction)
CREATE UNIQUE INDEX idx_cross_references_unique_relationship ON uds3_cross_references(
    source_document_id, target_document_id, reference_type
);

-- ============================================================================
-- Triggers and Functions
-- ============================================================================

-- Function to update access statistics
CREATE OR REPLACE FUNCTION update_cross_reference_access()
RETURNS TRIGGER AS $$
BEGIN
    -- Update access count and timestamp
    NEW.access_count := OLD.access_count + 1;
    NEW.last_accessed := CURRENT_TIMESTAMP;
    
    -- Mark as frequent query pair if accessed enough times
    IF NEW.access_count >= 10 AND NOT OLD.frequent_query_pair THEN
        NEW.frequent_query_pair := TRUE;
        NEW.cache_priority := LEAST(OLD.cache_priority + 1, 10);
    END IF;
    
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

-- Function to automatically update updated_at
CREATE OR REPLACE FUNCTION update_cross_reference_timestamp()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at := CURRENT_TIMESTAMP;
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

-- Trigger for timestamp updates
CREATE TRIGGER trg_cross_references_update_timestamp
    BEFORE UPDATE ON uds3_cross_references
    FOR EACH ROW
    EXECUTE FUNCTION update_cross_reference_timestamp();

-- Function to ensure relationship consistency
CREATE OR REPLACE FUNCTION ensure_relationship_consistency()
RETURNS TRIGGER AS $$
BEGIN
    -- For bidirectional relationships, ensure we don't create reverse duplicates
    IF NEW.reference_direction = 'bidirectional' THEN
        -- Check if reverse relationship exists
        IF EXISTS (
            SELECT 1 FROM uds3_cross_references 
            WHERE source_document_id = NEW.target_document_id 
            AND target_document_id = NEW.source_document_id 
            AND reference_type = NEW.reference_type
            AND id != COALESCE(NEW.id, -1)
        ) THEN
            RAISE EXCEPTION 'Bidirectional relationship already exists in reverse direction';
        END IF;
    END IF;
    
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

-- Trigger for relationship consistency
CREATE TRIGGER trg_cross_references_consistency
    BEFORE INSERT OR UPDATE ON uds3_cross_references
    FOR EACH ROW
    EXECUTE FUNCTION ensure_relationship_consistency();

-- ============================================================================
-- Helper Functions for Cross-References
-- ============================================================================

-- Function to add a cross-reference relationship
CREATE OR REPLACE FUNCTION add_cross_reference(
    p_source_document_id VARCHAR(255),
    p_target_document_id VARCHAR(255),
    p_reference_type reference_type_enum,
    p_relationship_strength REAL DEFAULT 0.5,
    p_confidence_score REAL DEFAULT 0.0,
    p_detected_by VARCHAR(100) DEFAULT 'system',
    p_metadata JSONB DEFAULT '{}'
) RETURNS INTEGER AS $$
DECLARE
    new_ref_id INTEGER;
BEGIN
    INSERT INTO uds3_cross_references (
        source_document_id,
        target_document_id,
        reference_type,
        relationship_strength,
        confidence_score,
        detected_by,
        relationship_metadata
    ) VALUES (
        p_source_document_id,
        p_target_document_id,
        p_reference_type,
        p_relationship_strength,
        p_confidence_score,
        p_detected_by,
        p_metadata
    ) RETURNING id INTO new_ref_id;
    
    RETURN new_ref_id;
END;
$$ LANGUAGE plpgsql;

-- Function to get all related documents (with traversal depth limit)
CREATE OR REPLACE FUNCTION get_related_documents(
    p_document_id VARCHAR(255),
    p_max_depth INTEGER DEFAULT 2,
    p_min_confidence REAL DEFAULT 0.3
) RETURNS TABLE (
    related_document_id VARCHAR(255),
    relationship_path TEXT,
    combined_confidence REAL,
    depth_level INTEGER
) AS $$
WITH RECURSIVE document_relationships AS (
    -- Base case: direct relationships
    SELECT 
        CASE 
            WHEN cr.source_document_id = p_document_id THEN cr.target_document_id
            ELSE cr.source_document_id 
        END as related_document_id,
        cr.reference_type::TEXT as relationship_path,
        cr.confidence_score as combined_confidence,
        1 as depth_level
    FROM uds3_cross_references cr
    WHERE (cr.source_document_id = p_document_id OR cr.target_document_id = p_document_id)
    AND cr.confidence_score >= p_min_confidence
    
    UNION ALL
    
    -- Recursive case: relationships of relationships
    SELECT 
        CASE 
            WHEN cr.source_document_id = dr.related_document_id THEN cr.target_document_id
            ELSE cr.source_document_id 
        END as related_document_id,
        dr.relationship_path || ' -> ' || cr.reference_type::TEXT,
        dr.combined_confidence * cr.confidence_score as combined_confidence,
        dr.depth_level + 1
    FROM document_relationships dr
    JOIN uds3_cross_references cr ON (
        cr.source_document_id = dr.related_document_id OR 
        cr.target_document_id = dr.related_document_id
    )
    WHERE dr.depth_level < p_max_depth
    AND cr.confidence_score >= p_min_confidence
    AND CASE 
            WHEN cr.source_document_id = dr.related_document_id THEN cr.target_document_id
            ELSE cr.source_document_id 
        END != p_document_id  -- Avoid cycles back to original
)
SELECT DISTINCT * FROM document_relationships ORDER BY combined_confidence DESC, depth_level;
$$ LANGUAGE SQL;

-- Function to find similar documents by relationship type
CREATE OR REPLACE FUNCTION find_similar_documents(
    p_document_id VARCHAR(255),
    p_relationship_types reference_type_enum[] DEFAULT ARRAY['similarity'],
    p_min_strength REAL DEFAULT 0.5,
    p_limit INTEGER DEFAULT 10
) RETURNS TABLE (
    similar_document_id VARCHAR(255),
    reference_type reference_type_enum,
    relationship_strength REAL,
    confidence_score REAL
) AS $$
BEGIN
    RETURN QUERY
    SELECT 
        CASE 
            WHEN cr.source_document_id = p_document_id THEN cr.target_document_id
            ELSE cr.source_document_id 
        END as similar_document_id,
        cr.reference_type,
        cr.relationship_strength,
        cr.confidence_score
    FROM uds3_cross_references cr
    WHERE (cr.source_document_id = p_document_id OR cr.target_document_id = p_document_id)
    AND cr.reference_type = ANY(p_relationship_types)
    AND cr.relationship_strength >= p_min_strength
    ORDER BY cr.relationship_strength DESC, cr.confidence_score DESC
    LIMIT p_limit;
END;
$$ LANGUAGE plpgsql;

-- Function to mark cross-reference as distributed to specific database
CREATE OR REPLACE FUNCTION mark_cross_reference_distributed(
    p_reference_id INTEGER,
    p_database_type TEXT  -- 'couchdb', 'chromadb', 'neo4j'
) RETURNS BOOLEAN AS $$
BEGIN
    CASE p_database_type
        WHEN 'couchdb' THEN
            UPDATE uds3_cross_references 
            SET couchdb_replicated = TRUE, updated_at = CURRENT_TIMESTAMP
            WHERE id = p_reference_id;
        WHEN 'chromadb' THEN
            UPDATE uds3_cross_references 
            SET chromadb_vectorized = TRUE, updated_at = CURRENT_TIMESTAMP
            WHERE id = p_reference_id;
        WHEN 'neo4j' THEN
            UPDATE uds3_cross_references 
            SET neo4j_graphed = TRUE, updated_at = CURRENT_TIMESTAMP
            WHERE id = p_reference_id;
        ELSE
            RETURN FALSE;
    END CASE;
    
    RETURN FOUND;
END;
$$ LANGUAGE plpgsql;

-- ============================================================================
-- Views for Common Queries
-- ============================================================================

-- View for high-confidence relationships
CREATE VIEW v_high_confidence_relationships AS
SELECT 
    cr.*,
    sd.original_filename as source_filename,
    td.original_filename as target_filename
FROM uds3_cross_references cr
JOIN uds3_master_documents sd ON cr.source_document_id = sd.document_id
JOIN uds3_master_documents td ON cr.target_document_id = td.document_id
WHERE cr.confidence_level IN ('high', 'very_high')
AND cr.false_positive_likelihood < 0.3;

-- View for relationship statistics by type
CREATE VIEW v_relationship_type_stats AS
SELECT 
    reference_type,
    COUNT(*) as total_relationships,
    AVG(relationship_strength) as avg_strength,
    AVG(confidence_score) as avg_confidence,
    COUNT(*) FILTER (WHERE manually_validated = TRUE) as manually_validated_count,
    COUNT(*) FILTER (WHERE confidence_level IN ('high', 'very_high')) as high_confidence_count
FROM uds3_cross_references
GROUP BY reference_type;

-- View for documents with most relationships
CREATE VIEW v_most_connected_documents AS
SELECT 
    document_id,
    md.original_filename,
    COUNT(cr.id) as total_relationships,
    COUNT(cr.id) FILTER (WHERE cr.reference_type = 'similarity') as similarity_relationships,
    COUNT(cr.id) FILTER (WHERE cr.confidence_level IN ('high', 'very_high')) as high_confidence_relationships,
    AVG(cr.relationship_strength) as avg_relationship_strength
FROM uds3_master_documents md
LEFT JOIN uds3_cross_references cr ON (
    md.document_id = cr.source_document_id OR 
    md.document_id = cr.target_document_id
)
GROUP BY document_id, md.original_filename
HAVING COUNT(cr.id) > 0
ORDER BY total_relationships DESC;

-- ============================================================================
-- Comments and Documentation
-- ============================================================================

COMMENT ON TABLE uds3_cross_references IS 'Cross-document relationships for multi-database reconstruction and queries';
COMMENT ON COLUMN uds3_cross_references.relationship_strength IS 'Strength of relationship from 0.0 (weak) to 1.0 (strong)';
COMMENT ON COLUMN uds3_cross_references.confidence_score IS 'Confidence in relationship detection from 0.0 to 1.0';
COMMENT ON COLUMN uds3_cross_references.relationship_metadata IS 'Flexible JSONB storage for relationship-specific data';
COMMENT ON COLUMN uds3_cross_references.frequent_query_pair IS 'Automatically set TRUE for frequently accessed document pairs';

-- Migration completion
INSERT INTO schema_migrations (version, applied_at) VALUES ('003', CURRENT_TIMESTAMP)
ON CONFLICT (version) DO UPDATE SET applied_at = CURRENT_TIMESTAMP;

-- Success message
SELECT 'UDS3 Cross-References table created successfully!' as migration_result;