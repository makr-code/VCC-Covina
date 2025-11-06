"""Graph Layer - Neo4j persistence for processes.

Components:
- temporal_canon: Temporal nodes (Year/Month/Day/Date) and relations
- process_writer: Process/Step/Role graph persistence
- indices: Index and constraint management

Usage:
    from processes.graph import TemporalCanon, ProcessGraphWriter
    
    canon = TemporalCanon(graph_adapter)
    canon.link_occurs_on('Step', 'step_123', '2025-10-30')
    
    writer = ProcessGraphWriter(graph_adapter)
    writer.upsert_process(process_id, key, title, version)
"""

from .temporal_canon import TemporalCanon

__all__ = [
    "TemporalCanon",
]
