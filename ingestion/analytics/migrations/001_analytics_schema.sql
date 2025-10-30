-- ============================================================================
-- Legal Knowledge Graph Analytics Schema
-- Version: 1.0
-- Date: 30. Oktober 2025
-- Purpose: Schnelle Aggregationen für Trends/Zählungen (Hybrid Polyglot)
-- ============================================================================

-- ============================================================================
-- DIMENSION TABLES (Master Data aus Neo4j Graph)
-- ============================================================================

CREATE TABLE IF NOT EXISTS dim_domain (
    id TEXT PRIMARY KEY,
    name TEXT NOT NULL,
    tier INTEGER NOT NULL CHECK (tier BETWEEN 1 AND 3),
    parent_id TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_dim_domain_tier ON dim_domain(tier);
CREATE INDEX IF NOT EXISTS idx_dim_domain_parent ON dim_domain(parent_id);

COMMENT ON TABLE dim_domain IS 'Legal Domains Dimension (from Neo4j LegalDomain nodes)';

-- ----------------------------------------------------------------------------

CREATE TABLE IF NOT EXISTS dim_concept (
    id TEXT PRIMARY KEY,
    name TEXT NOT NULL,
    category TEXT,
    domain_id TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_dim_concept_domain ON dim_concept(domain_id);
CREATE INDEX IF NOT EXISTS idx_dim_concept_category ON dim_concept(category);

COMMENT ON TABLE dim_concept IS 'Legal Concepts Dimension (from Neo4j LegalConcept nodes)';

-- ----------------------------------------------------------------------------

CREATE TABLE IF NOT EXISTS dim_jurisdiction (
    id TEXT PRIMARY KEY,
    ags TEXT,
    name TEXT NOT NULL,
    level TEXT CHECK (level IN ('bund', 'land', 'kreis', 'kommune')),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_dim_jurisdiction_level ON dim_jurisdiction(level);
CREATE INDEX IF NOT EXISTS idx_dim_jurisdiction_ags ON dim_jurisdiction(ags);

COMMENT ON TABLE dim_jurisdiction IS 'Jurisdictions Dimension (from Neo4j Jurisdiction nodes)';

-- ----------------------------------------------------------------------------

CREATE TABLE IF NOT EXISTS dim_authority (
    id TEXT PRIMARY KEY,
    name TEXT NOT NULL,
    authority_type TEXT,
    level TEXT,
    jurisdiction_id TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_dim_authority_type ON dim_authority(authority_type);
CREATE INDEX IF NOT EXISTS idx_dim_authority_jurisdiction ON dim_authority(jurisdiction_id);

COMMENT ON TABLE dim_authority IS 'Authorities Dimension (from Neo4j Authority nodes)';

-- ----------------------------------------------------------------------------

CREATE TABLE IF NOT EXISTS dim_law (
    id TEXT PRIMARY KEY,
    code TEXT NOT NULL,
    name TEXT NOT NULL,
    jurisdiction_id TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_dim_law_code ON dim_law(code);
CREATE INDEX IF NOT EXISTS idx_dim_law_jurisdiction ON dim_law(jurisdiction_id);

COMMENT ON TABLE dim_law IS 'Laws Dimension (e.g., BImSchG, BauGB)';

-- ----------------------------------------------------------------------------

CREATE TABLE IF NOT EXISTS dim_norm (
    id TEXT PRIMARY KEY,
    law_id TEXT NOT NULL,
    paragraph TEXT,
    full_citation TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_dim_norm_law ON dim_norm(law_id);

COMMENT ON TABLE dim_norm IS 'Legal Norms Dimension (§ 35 BauGB, § 3 BImSchG, etc.)';

-- ============================================================================
-- FACT TABLE (Daily Aggregations)
-- ============================================================================

CREATE TABLE IF NOT EXISTS legal_stats_daily (
    id SERIAL PRIMARY KEY,
    date_bucket DATE NOT NULL,
    domain_id TEXT,
    concept_id TEXT,
    jurisdiction_id TEXT,
    authority_id TEXT,
    law_id TEXT,
    norm_id TEXT,
    
    -- Metrics
    document_count INTEGER DEFAULT 0,
    concept_mentions INTEGER DEFAULT 0,
    norm_citations INTEGER DEFAULT 0,
    
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    
    -- Unique constraint für idempotente Upserts
    UNIQUE(date_bucket, domain_id, concept_id, jurisdiction_id, authority_id, law_id, norm_id)
);

CREATE INDEX IF NOT EXISTS idx_stats_date ON legal_stats_daily(date_bucket DESC);
CREATE INDEX IF NOT EXISTS idx_stats_domain ON legal_stats_daily(domain_id);
CREATE INDEX IF NOT EXISTS idx_stats_concept ON legal_stats_daily(concept_id);
CREATE INDEX IF NOT EXISTS idx_stats_jurisdiction ON legal_stats_daily(jurisdiction_id);
CREATE INDEX IF NOT EXISTS idx_stats_authority ON legal_stats_daily(authority_id);
CREATE INDEX IF NOT EXISTS idx_stats_law ON legal_stats_daily(law_id);

COMMENT ON TABLE legal_stats_daily IS 'Daily aggregated stats (Facts) from Neo4j Graph queries';

-- ============================================================================
-- SNAPSHOT TABLE (Point-in-Time Aggregations)
-- ============================================================================

CREATE TABLE IF NOT EXISTS legal_stats_snapshot (
    id SERIAL PRIMARY KEY,
    snapshot_date DATE NOT NULL,
    domain_id TEXT,
    concept_id TEXT,
    jurisdiction_id TEXT,
    
    -- Cumulative Metrics
    total_documents INTEGER DEFAULT 0,
    total_concepts INTEGER DEFAULT 0,
    total_norms INTEGER DEFAULT 0,
    total_authorities INTEGER DEFAULT 0,
    
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    
    UNIQUE(snapshot_date, domain_id, concept_id, jurisdiction_id)
);

CREATE INDEX IF NOT EXISTS idx_snapshot_date ON legal_stats_snapshot(snapshot_date DESC);
CREATE INDEX IF NOT EXISTS idx_snapshot_domain ON legal_stats_snapshot(domain_id);

COMMENT ON TABLE legal_stats_snapshot IS 'Point-in-time snapshots for trend analysis';

-- ============================================================================
-- MATERIALIZED VIEWS (für schnelle Queries)
-- ============================================================================

-- Laws per Domain (aggregiert über alle Zeiträume)
CREATE MATERIALIZED VIEW IF NOT EXISTS mv_laws_per_domain AS
SELECT 
    d.id AS domain_id,
    d.name AS domain_name,
    d.tier,
    COUNT(DISTINCT s.law_id) AS law_count,
    COUNT(DISTINCT s.norm_id) AS norm_count,
    SUM(s.norm_citations) AS total_citations
FROM dim_domain d
LEFT JOIN legal_stats_daily s ON d.id = s.domain_id
GROUP BY d.id, d.name, d.tier
ORDER BY law_count DESC;

CREATE UNIQUE INDEX IF NOT EXISTS idx_mv_laws_domain ON mv_laws_per_domain(domain_id);

-- Norms per Jurisdiction
CREATE MATERIALIZED VIEW IF NOT EXISTS mv_norms_per_jurisdiction AS
SELECT 
    j.id AS jurisdiction_id,
    j.name AS jurisdiction_name,
    j.level,
    COUNT(DISTINCT s.norm_id) AS norm_count,
    SUM(s.norm_citations) AS total_citations
FROM dim_jurisdiction j
LEFT JOIN legal_stats_daily s ON j.id = s.jurisdiction_id
GROUP BY j.id, j.name, j.level
ORDER BY norm_count DESC;

CREATE UNIQUE INDEX IF NOT EXISTS idx_mv_norms_jurisdiction ON mv_norms_per_jurisdiction(jurisdiction_id);

-- Documents per Concept
CREATE MATERIALIZED VIEW IF NOT EXISTS mv_docs_per_concept AS
SELECT 
    c.id AS concept_id,
    c.name AS concept_name,
    c.domain_id,
    COUNT(DISTINCT s.id) AS document_count,
    SUM(s.concept_mentions) AS total_mentions
FROM dim_concept c
LEFT JOIN legal_stats_daily s ON c.id = s.concept_id
GROUP BY c.id, c.name, c.domain_id
ORDER BY document_count DESC;

CREATE UNIQUE INDEX IF NOT EXISTS idx_mv_docs_concept ON mv_docs_per_concept(concept_id);

-- ============================================================================
-- REFRESH FUNCTIONS (für MV Updates)
-- ============================================================================

-- Refresh all materialized views
CREATE OR REPLACE FUNCTION refresh_all_analytics_views() RETURNS void AS $$
BEGIN
    REFRESH MATERIALIZED VIEW CONCURRENTLY mv_laws_per_domain;
    REFRESH MATERIALIZED VIEW CONCURRENTLY mv_norms_per_jurisdiction;
    REFRESH MATERIALIZED VIEW CONCURRENTLY mv_docs_per_concept;
END;
$$ LANGUAGE plpgsql;

COMMENT ON FUNCTION refresh_all_analytics_views IS 'Refresh all analytics materialized views (call after sync job)';

-- ============================================================================
-- NOTES
-- ============================================================================

-- 1. Partitioning: legal_stats_daily kann später nach date_bucket partitioniert werden (monatlich/jährlich)
-- 2. Retention: Alte Snapshots/Facts optional archivieren (>1 Jahr)
-- 3. Sync Strategy: Idempotente Upserts via ON CONFLICT (date_bucket, domain_id, ...)
-- 4. Performance: Indizes sind auf Filter-Spalten (domain_id, jurisdiction_id, etc.)
-- 5. Materialized Views: REFRESH CONCURRENTLY erfordert UNIQUE Index (siehe oben)
