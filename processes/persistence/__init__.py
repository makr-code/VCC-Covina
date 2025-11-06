"""Persistence Layer - Process storage across UDS3 databases.

Components:
- relational: PostgreSQL persistence (master data)
- document: CouchDB persistence (full content)
- vector: ChromaDB persistence (embeddings)
- graph: Neo4j graph writes (via graph module)

Usage:
    from processes.persistence import ProcessStore
    
    store = ProcessStore(uds3_gateway)
    await store.save_process(process, steps, roles)
    await store.save_inference_result(inference_result)
"""

__all__ = []
