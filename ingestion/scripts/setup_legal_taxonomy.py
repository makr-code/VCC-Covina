"""Setup Legal Domain Taxonomy in Neo4j.

Usage:
    python -m ingestion.scripts.setup_legal_taxonomy

Environment:
    Requires Neo4j connection via UDS3 (configured in config.py)

Features:
    - Creates indices for Legal Knowledge Graph
    - Loads legal domain taxonomy from seed file
    - Idempotent (safe to run multiple times)
    - Validates setup after completion
"""
from __future__ import annotations

import asyncio
import sys
from pathlib import Path

# Add parent to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent.parent))


async def main():
    """Setup legal taxonomy in Neo4j."""
    from uds3.database.database_manager import DatabaseManager
    from ingestion.graph.legal_domain_taxonomy import TaxonomySeed, LegalDomainTaxonomyLoader
    from ingestion.graph.setup_indices import setup_indices

    print("🚀 Starting Legal Domain Taxonomy Setup...")
    print("=" * 60)

    # Initialize UDS3
    print("\n1. Connecting to Neo4j via UDS3...")
    try:
        backend_config = {
            'graph': {'enabled': True}  # Neo4j for taxonomy setup
        }
        db = DatabaseManager(backend_config, autostart=True)
        if not db.graph_backend:
            print("❌ ERROR: Neo4j backend not available")
            print("   Check UDS3 configuration in config.py")
            return 1
        print("✅ Connected to Neo4j")
    except Exception as e:
        print(f"❌ ERROR: Failed to connect to Neo4j: {e}")
        return 1

    # Adapter for Neo4j
    class Neo4jAdapter:
        def __init__(self, backend):
            self.backend = backend

        async def execute(self, cypher: str, params: dict) -> None:
            """Execute Cypher query via backend.execute_query()."""
            self.backend.execute_query(cypher, params)

    adapter = Neo4jAdapter(db.graph_backend)

    # Step 1: Setup Indices
    print("\n2. Creating indices...")
    try:
        index_count = await setup_indices(adapter)
        print(f"✅ Created {index_count} indices")
    except Exception as e:
        print(f"❌ ERROR: Failed to create indices: {e}")
        return 1

    # Step 2: Load Taxonomy
    print("\n3. Loading legal domain taxonomy...")
    try:
        seed_path = Path(__file__).parent.parent / "data" / "legal_domains_seed.json"
        if not seed_path.exists():
            print(f"❌ ERROR: Seed file not found: {seed_path}")
            return 1

        seed = TaxonomySeed.load(seed_path)
        print(f"   Loaded seed version: {seed.version} (updated: {seed.last_updated})")
        print(f"   Total domains in seed: {len(seed.nodes)}")

        loader = LegalDomainTaxonomyLoader(adapter)
        stats = await loader.load(seed)

        print(f"✅ Loaded {stats['nodes']} nodes and {stats['relationships']} relationships")
    except Exception as e:
        print(f"❌ ERROR: Failed to load taxonomy: {e}")
        import traceback
        traceback.print_exc()
        return 1

    # Step 3: Validate
    print("\n4. Validating setup...")
    try:
        # Count nodes
        count_query = "MATCH (d:LegalDomain) RETURN count(d) as cnt"
        result = db.graph_backend.execute_query(count_query, {})
        node_count = result[0]["cnt"]
        print(f"   Total LegalDomain nodes in Neo4j: {node_count}")

        # Count relationships
        rel_query = "MATCH ()-[r:SUBDOMAIN_OF]->() RETURN count(r) as cnt"
        rel_result = db.graph_backend.execute_query(rel_query, {})
        rel_count = rel_result[0]["cnt"]
        print(f"   Total SUBDOMAIN_OF relationships: {rel_count}")

        # Check tier 1 domains
        tier1_query = "MATCH (d:LegalDomain {tier: 1}) RETURN d.id as id, d.name as name"
        tier1_result = db.graph_backend.execute_query(tier1_query, {})
        print(f"\n   Tier 1 domains ({len(tier1_result)}):")
        for domain in tier1_result:
            print(f"     - {domain['id']}: {domain['name']}")

        # Validate expected counts
        if node_count != stats["nodes"]:
            print(f"\n⚠️  WARNING: Node count mismatch (expected {stats['nodes']}, got {node_count})")
        if rel_count != stats["relationships"]:
            print(f"\n⚠️  WARNING: Relationship count mismatch (expected {stats['relationships']}, got {rel_count})")

        print("\n✅ Validation complete")
    except Exception as e:
        print(f"❌ ERROR: Validation failed: {e}")
        return 1

    print("\n" + "=" * 60)
    print("🎉 Legal Domain Taxonomy Setup Complete!")
    print("\nNext steps:")
    print("  - Run Phase L2: Legal Entity Extraction")
    print("  - Test queries: MATCH (d:LegalDomain {tier: 1}) RETURN d")
    print("  - Check hierarchy: MATCH path=(:LegalDomain)-[:SUBDOMAIN_OF*]->() RETURN path LIMIT 10")
    return 0


if __name__ == "__main__":
    exit_code = asyncio.run(main())
    sys.exit(exit_code)
