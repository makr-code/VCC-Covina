from __future__ import annotations
from typing import Iterable

INDEX_QUERIES: Iterable[str] = (
    "CREATE INDEX legal_domain_id IF NOT EXISTS FOR (d:LegalDomain) ON (d.id)",
    "CREATE INDEX legal_domain_tier IF NOT EXISTS FOR (d:LegalDomain) ON (d.tier)",
    "CREATE INDEX legal_concept_id IF NOT EXISTS FOR (c:LegalConcept) ON (c.id)",
    "CREATE INDEX jurisdiction_id IF NOT EXISTS FOR (j:Jurisdiction) ON (j.id)",
    "CREATE INDEX jurisdiction_ags IF NOT EXISTS FOR (j:Jurisdiction) ON (j.ags)",
    "CREATE INDEX authority_id IF NOT EXISTS FOR (a:Authority) ON (a.id)",
    "CREATE FULLTEXT INDEX legal_concept_search IF NOT EXISTS FOR (c:LegalConcept) ON EACH [c.name, c.definition, c.keywords]",
)

async def setup_indices(repo) -> int:
    """Execute index creation queries via repository.execute(cypher, params)."""
    count = 0
    for q in INDEX_QUERIES:
        await repo.execute(q, {})
        count += 1
    return count
