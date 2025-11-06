"""
Neo4j Constraints & Indices for Temporal Canon and Process Graph

Provides index/constraint setup for:
- Temporal Canon (Year, Month, Day, Date)
- Process entities (Process, Step, Role, OrgUnit, System, Control, LegalRef, InfoObject)

Uses async graph_adapter interface compatible with UDS3.
"""
from __future__ import annotations
from typing import Iterable


# ============================================================================
# TEMPORAL CANON CONSTRAINTS
# ============================================================================
TEMPORAL_CONSTRAINTS: Iterable[str] = (
    # Unique constraints for temporal identifiers
    "CREATE CONSTRAINT date_iso_unique IF NOT EXISTS FOR (d:Date) REQUIRE d.iso IS UNIQUE",
    "CREATE CONSTRAINT year_y_unique IF NOT EXISTS FOR (y:Year) REQUIRE y.y IS UNIQUE",
    # Composite uniqueness for Month (year + month) and Day (year + month + day)
    "CREATE CONSTRAINT month_ym_unique IF NOT EXISTS FOR (m:Month) REQUIRE (m.y, m.m) IS UNIQUE",
    "CREATE CONSTRAINT day_ymd_unique IF NOT EXISTS FOR (d:Day) REQUIRE (d.y, d.m, d.d) IS UNIQUE",
)

# ============================================================================
# TEMPORAL CANON INDICES
# ============================================================================
TEMPORAL_INDICES: Iterable[str] = (
    # Composite indices for temporal navigation
    "CREATE INDEX month_y_m IF NOT EXISTS FOR (m:Month) ON (m.y, m.m)",
    "CREATE INDEX day_y_m_d IF NOT EXISTS FOR (d:Day) ON (d.y, d.m, d.d)",
    # Single-field indices for date components
    "CREATE INDEX date_year IF NOT EXISTS FOR (d:Date) ON (d.year)",
    "CREATE INDEX date_month IF NOT EXISTS FOR (d:Date) ON (d.month)",
    "CREATE INDEX date_day IF NOT EXISTS FOR (d:Date) ON (d.day)",
)

# ============================================================================
# PROCESS ENTITY CONSTRAINTS
# ============================================================================
PROCESS_CONSTRAINTS: Iterable[str] = (
    # Unique identifiers for all UPS entities
    "CREATE CONSTRAINT process_id_unique IF NOT EXISTS FOR (p:Process) REQUIRE p.id IS UNIQUE",
    "CREATE CONSTRAINT step_id_unique IF NOT EXISTS FOR (s:Step) REQUIRE s.id IS UNIQUE",
    "CREATE CONSTRAINT role_id_unique IF NOT EXISTS FOR (r:Role) REQUIRE r.id IS UNIQUE",
    "CREATE CONSTRAINT org_unit_id_unique IF NOT EXISTS FOR (o:OrgUnit) REQUIRE o.id IS UNIQUE",
    "CREATE CONSTRAINT system_id_unique IF NOT EXISTS FOR (s:System) REQUIRE s.id IS UNIQUE",
    "CREATE CONSTRAINT control_id_unique IF NOT EXISTS FOR (c:Control) REQUIRE c.id IS UNIQUE",
    "CREATE CONSTRAINT legal_ref_id_unique IF NOT EXISTS FOR (l:LegalRef) REQUIRE l.id IS UNIQUE",
    "CREATE CONSTRAINT info_object_id_unique IF NOT EXISTS FOR (i:InfoObject) REQUIRE i.id IS UNIQUE",
    # Document & Time-related helpers
    "CREATE CONSTRAINT document_id_unique IF NOT EXISTS FOR (d:Document) REQUIRE d.id IS UNIQUE",
    "CREATE CONSTRAINT recurrence_id_unique IF NOT EXISTS FOR (r:Recurrence) REQUIRE r.id IS UNIQUE",
    "CREATE CONSTRAINT step_occurrence_id_unique IF NOT EXISTS FOR (o:StepOccurrence) REQUIRE o.id IS UNIQUE",
)

# ============================================================================
# PROCESS ENTITY INDICES
# ============================================================================
PROCESS_INDICES: Iterable[str] = (
    # Process indices
    "CREATE INDEX process_key IF NOT EXISTS FOR (p:Process) ON (p.key)",
    "CREATE INDEX process_version IF NOT EXISTS FOR (p:Process) ON (p.version)",
    "CREATE INDEX process_created_at IF NOT EXISTS FOR (p:Process) ON (p.created_at)",
    "CREATE INDEX process_updated_at IF NOT EXISTS FOR (p:Process) ON (p.updated_at)",
    
    # Step indices
    "CREATE INDEX step_key IF NOT EXISTS FOR (s:Step) ON (s.key)",
    "CREATE INDEX step_type IF NOT EXISTS FOR (s:Step) ON (s.type)",
    "CREATE INDEX step_created_at IF NOT EXISTS FOR (s:Step) ON (s.created_at)",
    
    # Role indices
    "CREATE INDEX role_name IF NOT EXISTS FOR (r:Role) ON (r.name)",
    "CREATE INDEX role_level IF NOT EXISTS FOR (r:Role) ON (r.level)",
    
    # OrgUnit indices
    "CREATE INDEX org_unit_name IF NOT EXISTS FOR (o:OrgUnit) ON (o.name)",
    "CREATE INDEX org_unit_level IF NOT EXISTS FOR (o:OrgUnit) ON (o.level)",
    
    # System indices
    "CREATE INDEX system_name IF NOT EXISTS FOR (s:System) ON (s.name)",
    "CREATE INDEX system_type IF NOT EXISTS FOR (s:System) ON (s.type)",
    
    # Control indices
    "CREATE INDEX control_type IF NOT EXISTS FOR (c:Control) ON (c.type)",
    "CREATE INDEX control_criticality IF NOT EXISTS FOR (c:Control) ON (c.criticality)",
    
    # LegalRef indices
    "CREATE INDEX legal_ref_source IF NOT EXISTS FOR (l:LegalRef) ON (l.source)",
    "CREATE INDEX legal_ref_article IF NOT EXISTS FOR (l:LegalRef) ON (l.article)",
    
    # InfoObject indices
    "CREATE INDEX info_object_type IF NOT EXISTS FOR (i:InfoObject) ON (i.type)",
    "CREATE INDEX info_object_key IF NOT EXISTS FOR (i:InfoObject) ON (i.key)",

    # Document indices
    "CREATE INDEX document_key IF NOT EXISTS FOR (d:Document) ON (d.key)",
    "CREATE INDEX document_type IF NOT EXISTS FOR (d:Document) ON (d.type)",
    "CREATE INDEX document_created_at IF NOT EXISTS FOR (d:Document) ON (d.created_at)",
    "CREATE INDEX document_published_at IF NOT EXISTS FOR (d:Document) ON (d.published_at)",
    
    # Recurrence indices
    "CREATE INDEX recurrence_freq IF NOT EXISTS FOR (r:Recurrence) ON (r.freq)",
    "CREATE INDEX recurrence_until IF NOT EXISTS FOR (r:Recurrence) ON (r.until)",
    
    # StepOccurrence indices
    "CREATE INDEX step_occurrence_step_id IF NOT EXISTS FOR (o:StepOccurrence) ON (o.step_id)",
    "CREATE INDEX step_occurrence_occurred_at IF NOT EXISTS FOR (o:StepOccurrence) ON (o.occurred_at)",
)

# ============================================================================
# FULLTEXT SEARCH INDICES
# ============================================================================
FULLTEXT_INDICES: Iterable[str] = (
    # Process fulltext search (name, description, metadata)
    "CREATE FULLTEXT INDEX process_search IF NOT EXISTS FOR (p:Process) ON EACH [p.name, p.description]",
    
    # Step fulltext search (name, description, instructions)
    "CREATE FULLTEXT INDEX step_search IF NOT EXISTS FOR (s:Step) ON EACH [s.name, s.description, s.instructions]",
    
    # Role fulltext search (name, description)
    "CREATE FULLTEXT INDEX role_search IF NOT EXISTS FOR (r:Role) ON EACH [r.name, r.description]",
    
    # OrgUnit fulltext search (name, description)
    "CREATE FULLTEXT INDEX org_unit_search IF NOT EXISTS FOR (o:OrgUnit) ON EACH [o.name, o.description]",
)

# ============================================================================
# COMBINED QUERIES
# ============================================================================
ALL_CONSTRAINTS = TEMPORAL_CONSTRAINTS + PROCESS_CONSTRAINTS
ALL_INDICES = TEMPORAL_INDICES + PROCESS_INDICES + FULLTEXT_INDICES


# ============================================================================
# SETUP FUNCTION
# ============================================================================
def setup_temporal_indices(graph_adapter) -> int:
    """
    Create temporal canon constraints and indices.
    
    Args:
        graph_adapter: UDS3 graph adapter with execute_query(cypher, params) method
        
    Returns:
        Number of queries executed
    """
    count = 0
    for query in TEMPORAL_CONSTRAINTS + TEMPORAL_INDICES:
        graph_adapter.execute_query(query, {})
        count += 1
    return count


def setup_process_indices(graph_adapter) -> int:
    """
    Create process entity constraints and indices.
    
    Args:
        graph_adapter: UDS3 graph adapter with execute_query(cypher, params) method
        
    Returns:
        Number of queries executed
    """
    count = 0
    for query in PROCESS_CONSTRAINTS + PROCESS_INDICES + FULLTEXT_INDICES:
        graph_adapter.execute_query(query, {})
        count += 1
    return count


def setup_all_indices(graph_adapter) -> dict[str, int]:
    """
    Create all temporal and process constraints/indices.
    
    Args:
        graph_adapter: UDS3 graph adapter with execute_query(cypher, params) method
        
    Returns:
        Dict with counts: {temporal: int, process: int, total: int}
    """
    temporal_count = setup_temporal_indices(graph_adapter)
    process_count = setup_process_indices(graph_adapter)
    
    return {
        "temporal": temporal_count,
        "process": process_count,
        "total": temporal_count + process_count,
    }
