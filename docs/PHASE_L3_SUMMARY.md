# Legal Knowledge Graph – Phase L3: Query APIs

Version: 1.0  
Datum: 30. Oktober 2025  
Status: ✅ Implemented & Tested (Unit)

---

## Ziel

Ergonomische Abfrage-APIs für den Legal Knowledge Graph:
- Domänen-Liste nach Tier (1..3)
- Kind-Domänen für eine Domäne
- Pfad zur Wurzel (child -> ... -> root)
- Volltext-Suche über LegalConcepts (Fulltext-Index, Fallback: CONTAINS)

## Endpoints

1) GET /legal-graph/domains?tier=1|2|3
- Response: DomainSummary[] (id, name, tier, parent_id)

2) GET /legal-graph/domain/{domain_id}/children
- Response: DomainSummary[] (direkte Kinder)

3) GET /legal-graph/domain/{domain_id}/path
- Response: DomainPath { nodes: DomainSummary[] } (child -> ... -> root)

4) GET /legal-graph/search?keyword=...&page=1&page_size=20
- Response: QueryResult<SearchConceptResult>
- Verwendet Fulltext-Index `legal_concept_search` (name, definition, keywords)
- Fallback bei fehlender Prozedur: CONTAINS Query

## Implementierung

Datei: `backend/queries/legal_graph_queries.py`
- Service: `LegalGraphQueryService`
- Methoden: `list_domains_by_tier`, `get_domain_children`, `get_domain_path`, `search_concepts`
- Modelle: `DomainSummary`, `DomainPath`, `SearchConceptResult`, `QueryResult`

## Tests

Datei: `tests/api/test_legal_graph_new_endpoints.py`
- Unit-Tests mit FakeService (Dependency Override)
- 4 Tests PASS (ohne Neo4j)

Optionale Integrationstests (Neo4j erforderlich) können separat ergänzt werden.

## Hinweise

- Erfordert: Indizes und Taxonomie gesetzt (siehe `scripts/setup_legal_taxonomy.ps1`).
- Feature-Flag: `ENABLE_LEGAL_GRAPH_QUERIES=true` (default), Router ist registriert.
- Performance: Fulltext-Suche ist effizient; Fallback nutzt LIKE/CONTAINS und ist einfacher.

## Beispiele

Domänenliste (Tier 1):
```bash
GET /legal-graph/domains?tier=1
```

Pfad zur Wurzel:
```bash
GET /legal-graph/domain/baurecht/path
```

Suche nach Konzepten:
```bash
GET /legal-graph/search?keyword=bau&page=1&page_size=10
```

---

Nächste Schritte (optional):
- Paginierung für Domänenlisten hinzufügen
- Facettierte Suche (Domain/Jurisdiction-Filter) für Concepts
- Caching der häufigen Pfade (Tier 2/3 -> Root)
