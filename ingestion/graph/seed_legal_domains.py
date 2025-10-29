from __future__ import annotations
import asyncio
from pathlib import Path

from ingestion.graph.legal_domain_taxonomy import TaxonomySeed, LegalDomainTaxonomyLoader
from ingestion.infrastructure.repositories.graph_repository import Neo4jGraphRepository


async def main(seed_path: str | Path = None) -> dict:
    seed_file = Path(seed_path) if seed_path else Path(__file__).resolve().parents[1] / "data" / "legal_domains_seed.json"
    seed = TaxonomySeed.load(seed_file)

    repo = Neo4jGraphRepository()  # nutzt UDS3Gateway intern
    loader = LegalDomainTaxonomyLoader(repo)
    result = await loader.load(seed)

    print(f"Seeded Legal Domains: {result['nodes']} nodes, {result['relationships']} relationships")
    return result


if __name__ == "__main__":
    asyncio.run(main())
