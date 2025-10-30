"""
Graph to Relational Analytics Sync

Synchronisiert aggregierte Daten aus dem Neo4j Knowledge Graph
in die PostgreSQL Analytics-Schicht (Hybrid Polyglot Pattern).

Features:
- Idempotente Upserts (ON CONFLICT)
- Date-basierte Buckets
- Dimension + Fact Synchronisation
- Feature Flag: ENABLE_GRAPH_ANALYTICS_SYNC (default: false)
- Manual Trigger via CLI oder Scheduled (Cron/Task Scheduler)

Usage:
    python -m ingestion.analytics.graph_to_relational_sync
"""
from __future__ import annotations

import os
import logging
from datetime import date, datetime
from typing import Dict, List, Any, Optional

logger = logging.getLogger(__name__)

# Feature Flag
ENABLE_SYNC = os.getenv("ENABLE_GRAPH_ANALYTICS_SYNC", "false").lower() == "true"


class GraphToRelationalSync:
    """
    Synchronisiert Neo4j Graph-Daten in PostgreSQL Analytics-Tabellen.
    
    Pattern:
    1. Query Neo4j für Aggregationen (Cypher)
    2. Transform zu Dimension/Fact Records
    3. Upsert in PostgreSQL (ON CONFLICT DO UPDATE)
    """
    
    def __init__(self, graph_adapter, relational_adapter):
        """
        Args:
            graph_adapter: Neo4j Backend (z.B. via UDS3Gateway.get_graph_adapter())
            relational_adapter: PostgreSQL Backend (z.B. via UDS3 relational_backend)
        """
        self.graph = graph_adapter
        self.relational = relational_adapter
        logger.info("[GraphToRelationalSync] Initialized")
    
    def sync_all(self, date_bucket: Optional[date] = None) -> Dict[str, int]:
        """
        Führt kompletten Sync durch: Dimensions + Facts.
        
        Args:
            date_bucket: Datum für Facts (default: heute)
        
        Returns:
            Dict mit Sync-Statistiken (domains_synced, concepts_synced, facts_synced)
        """
        if not ENABLE_SYNC:
            logger.info("[SYNC] Feature disabled (ENABLE_GRAPH_ANALYTICS_SYNC=false)")
            return {"status": "disabled", "domains_synced": 0, "concepts_synced": 0, "facts_synced": 0}
        
        if date_bucket is None:
            date_bucket = date.today()
        
        logger.info(f"[SYNC] Starting sync for date_bucket={date_bucket}")
        
        stats = {}
        
        # 1. Sync Dimensions (Master Data)
        stats["domains_synced"] = self.sync_domains()
        stats["concepts_synced"] = self.sync_concepts()
        stats["jurisdictions_synced"] = self.sync_jurisdictions()
        stats["authorities_synced"] = self.sync_authorities()
        
        # 2. Sync Facts (Aggregated Metrics)
        stats["facts_synced"] = self.sync_daily_facts(date_bucket)
        
        logger.info(f"[SYNC] Complete: {stats}")
        return stats
    
    def sync_domains(self) -> int:
        """Sync LegalDomain nodes → dim_domain."""
        query = """
        MATCH (d:LegalDomain)
        OPTIONAL MATCH (d)-[:SUBDOMAIN_OF]->(p:LegalDomain)
        RETURN d.id AS id, d.name AS name, d.tier AS tier, p.id AS parent_id
        """
        
        results = self.graph.execute_query(query, {})
        
        for row in results:
            upsert_sql = """
            INSERT INTO dim_domain (id, name, tier, parent_id, updated_at)
            VALUES (%s, %s, %s, %s, CURRENT_TIMESTAMP)
            ON CONFLICT (id) DO UPDATE SET
                name = EXCLUDED.name,
                tier = EXCLUDED.tier,
                parent_id = EXCLUDED.parent_id,
                updated_at = CURRENT_TIMESTAMP
            """
            self.relational.execute_query(
                upsert_sql, 
                params=(row["id"], row["name"], row["tier"], row.get("parent_id")),
                fetch=False,
                commit=True
            )
        
        logger.info(f"[SYNC] Synced {len(results)} domains")
        return len(results)
    
    def sync_concepts(self) -> int:
        """Sync LegalConcept nodes → dim_concept."""
        query = """
        MATCH (c:LegalConcept)
        RETURN c.concept_id AS id, c.name AS name, c.category AS category, c.domain AS domain_id
        """
        
        results = self.graph.execute_query(query, {})
        
        for row in results:
            upsert_sql = """
            INSERT INTO dim_concept (id, name, category, domain_id, updated_at)
            VALUES (%s, %s, %s, %s, CURRENT_TIMESTAMP)
            ON CONFLICT (id) DO UPDATE SET
                name = EXCLUDED.name,
                category = EXCLUDED.category,
                domain_id = EXCLUDED.domain_id,
                updated_at = CURRENT_TIMESTAMP
            """
            self.relational.execute_query(
                upsert_sql,
                params=(row["id"], row["name"], row.get("category"), row.get("domain_id")),
                fetch=False,
                commit=True
            )
        
        logger.info(f"[SYNC] Synced {len(results)} concepts")
        return len(results)
    
    def sync_jurisdictions(self) -> int:
        """Sync Jurisdiction nodes → dim_jurisdiction."""
        query = """
        MATCH (j:Jurisdiction)
        RETURN j.id AS id, j.ags AS ags, j.name AS name, j.level AS level
        """
        
        results = self.graph.execute_query(query, {})
        
        for row in results:
            upsert_sql = """
            INSERT INTO dim_jurisdiction (id, ags, name, level, updated_at)
            VALUES (%s, %s, %s, %s, CURRENT_TIMESTAMP)
            ON CONFLICT (id) DO UPDATE SET
                ags = EXCLUDED.ags,
                name = EXCLUDED.name,
                level = EXCLUDED.level,
                updated_at = CURRENT_TIMESTAMP
            """
            self.relational.execute_query(
                upsert_sql,
                params=(row["id"], row.get("ags"), row["name"], row.get("level")),
                fetch=False,
                commit=True
            )
        
        logger.info(f"[SYNC] Synced {len(results)} jurisdictions")
        return len(results)
    
    def sync_authorities(self) -> int:
        """Sync Authority nodes → dim_authority."""
        query = """
        MATCH (a:Authority)
        OPTIONAL MATCH (a)-[:APPLIES_TO]->(j:Jurisdiction)
        RETURN a.authority_id AS id, a.name AS name, a.authority_type AS authority_type, 
               a.level AS level, j.id AS jurisdiction_id
        """
        
        results = self.graph.execute_query(query, {})
        
        for row in results:
            upsert_sql = """
            INSERT INTO dim_authority (id, name, authority_type, level, jurisdiction_id, updated_at)
            VALUES (%s, %s, %s, %s, %s, CURRENT_TIMESTAMP)
            ON CONFLICT (id) DO UPDATE SET
                name = EXCLUDED.name,
                authority_type = EXCLUDED.authority_type,
                level = EXCLUDED.level,
                jurisdiction_id = EXCLUDED.jurisdiction_id,
                updated_at = CURRENT_TIMESTAMP
            """
            self.relational.execute_query(
                upsert_sql,
                params=(row["id"], row["name"], row.get("authority_type"), 
                        row.get("level"), row.get("jurisdiction_id")),
                fetch=False,
                commit=True
            )
        
        logger.info(f"[SYNC] Synced {len(results)} authorities")
        return len(results)
    
    def sync_daily_facts(self, date_bucket: date) -> int:
        """
        Sync aggregierte Facts für date_bucket.
        
        Queries:
        - Documents per Domain
        - Concept Mentions
        - Norm Citations
        """
        # Query: Documents per Domain
        query = """
        MATCH (doc:Document)-[:BELONGS_TO]->(d:LegalDomain)
        WHERE date(doc.created_at) = date($date_bucket)
        RETURN d.id AS domain_id, COUNT(DISTINCT doc) AS document_count
        """
        
        results = self.graph.execute_query(query, {"date_bucket": date_bucket.isoformat()})
        
        synced = 0
        for row in results:
            upsert_sql = """
            INSERT INTO legal_stats_daily 
                (date_bucket, domain_id, document_count, updated_at)
            VALUES (%s, %s, %s, CURRENT_TIMESTAMP)
            ON CONFLICT (date_bucket, domain_id, concept_id, jurisdiction_id, authority_id, law_id, norm_id) 
            DO UPDATE SET
                document_count = EXCLUDED.document_count,
                updated_at = CURRENT_TIMESTAMP
            """
            self.relational.execute_query(
                upsert_sql,
                params=(date_bucket, row["domain_id"], row["document_count"]),
                fetch=False,
                commit=True
            )
            synced += 1
        
        logger.info(f"[SYNC] Synced {synced} daily facts for {date_bucket}")
        return synced


def main():
    """CLI Entry Point für manuellen Sync."""
    if not ENABLE_SYNC:
        print("ERROR: Sync disabled (ENABLE_GRAPH_ANALYTICS_SYNC=false)")
        print("   Set ENABLE_GRAPH_ANALYTICS_SYNC=true to enable")
        return 1
    
    print("Starting Graph -> Relational Analytics Sync...")
    
    try:
        # Import UDS3 Gateway für Adapters
        from ingestion.infrastructure.clients.uds3_gateway import UDS3Gateway
        from uds3.database.database_manager import DatabaseManager
        
        # Initialisiere Adapters
        gateway = UDS3Gateway()
        graph_adapter = gateway.get_graph_adapter()
        
        # Relational Backend via UDS3
        db_manager = DatabaseManager({'relational': {'enabled': True}}, autostart=True)
        relational_adapter = db_manager.relational_backend
        
        if not relational_adapter:
            print("ERROR: PostgreSQL backend not available")
            return 1
        
        # Sync durchführen
        sync = GraphToRelationalSync(graph_adapter, relational_adapter)
        stats = sync.sync_all()
        
        print(f"\nSync Complete!")
        print(f"   Domains:       {stats.get('domains_synced', 0)}")
        print(f"   Concepts:      {stats.get('concepts_synced', 0)}")
        print(f"   Jurisdictions: {stats.get('jurisdictions_synced', 0)}")
        print(f"   Authorities:   {stats.get('authorities_synced', 0)}")
        print(f"   Facts:         {stats.get('facts_synced', 0)}")
        
        return 0
        
    except Exception as e:
        print(f"ERROR: {e}")
        import traceback
        traceback.print_exc()
        return 1


if __name__ == "__main__":
    import sys
    sys.exit(main())
