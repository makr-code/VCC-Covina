"""
Entity Graph Writer Tests
==========================

Tests for EntityGraphWriter using a dummy graph adapter (no real Neo4j).

Coverage:
- Node upserts (LegalConcept, Authority, Jurisdiction, LegalNorm)
- Relationship creation (MENTIONS_CONCEPT, CITES_NORM, ISSUED_BY, APPLIES_TO)
- ID normalization (lowercase, stripped)
- Timestamp handling (created_at, updated_at)
"""

import pytest
from ingestion.graph.entity_graph_writer import EntityGraphWriter


class DummyGraphAdapter:
    """Mock graph adapter for testing (no Neo4j)."""

    def __init__(self):
        self.executed_queries = []

    def execute_query(self, cypher: str, params: dict) -> dict:
        """Record query and return dummy success."""
        self.executed_queries.append({"cypher": cypher, "params": params})
        return {"success": True, "records": []}


@pytest.fixture
def dummy_adapter():
    """Provide a fresh dummy adapter for each test."""
    return DummyGraphAdapter()


@pytest.fixture
def writer(dummy_adapter):
    """Provide EntityGraphWriter with dummy adapter."""
    return EntityGraphWriter(graph_adapter=dummy_adapter)


def test_upsert_legal_concept(writer, dummy_adapter):
    """Test LegalConcept node upsert."""
    writer.upsert_legal_concept(
        concept_id="  BAURECHT  ",  # Test normalization
        name="Baurecht",
        tier=1,
        keywords=["Bau", "Bauordnung"],
        context_window="§ 3 BauGB regelt das Baurecht...",
    )

    assert len(dummy_adapter.executed_queries) == 1
    query = dummy_adapter.executed_queries[0]
    assert "MERGE (c:LegalConcept {id: $id})" in query["cypher"]
    assert query["params"]["id"] == "baurecht"  # normalized
    assert query["params"]["name"] == "Baurecht"
    assert query["params"]["tier"] == 1
    assert query["params"]["keywords"] == ["Bau", "Bauordnung"]
    assert "now" in query["params"]  # timestamp param
    assert "c.created_at = $now" in query["cypher"]
    assert "c.updated_at = $now" in query["cypher"]


def test_upsert_authority(writer, dummy_adapter):
    """Test Authority node upsert."""
    writer.upsert_authority(
        authority_id="BVerwG",
        name="Bundesverwaltungsgericht",
        level="federal",
        jurisdiction="deutschland",
        contact_info={"city": "Leipzig"},
    )

    assert len(dummy_adapter.executed_queries) == 1
    query = dummy_adapter.executed_queries[0]
    assert "MERGE (a:Authority {id: $id})" in query["cypher"]
    assert query["params"]["id"] == "bverwg"
    assert query["params"]["name"] == "Bundesverwaltungsgericht"
    assert query["params"]["level"] == "federal"
    assert query["params"]["contact_info"] == {"city": "Leipzig"}


def test_upsert_jurisdiction(writer, dummy_adapter):
    """Test Jurisdiction node upsert."""
    writer.upsert_jurisdiction(
        jurisdiction_id="BW",
        name="Baden-Württemberg",
        level="state",
        parent_id="DE",
    )

    assert len(dummy_adapter.executed_queries) == 1
    query = dummy_adapter.executed_queries[0]
    assert "MERGE (j:Jurisdiction {id: $id})" in query["cypher"]
    assert query["params"]["id"] == "bw"
    assert query["params"]["name"] == "Baden-Württemberg"
    assert query["params"]["level"] == "state"
    assert query["params"]["parent_id"] == "DE"


def test_upsert_legal_norm(writer, dummy_adapter):
    """Test LegalNorm node upsert."""
    writer.upsert_legal_norm(
        norm_id="§3_abs1_baugb",
        norm_text="§ 3 Abs. 1 BauGB",
        law_abbreviation="BauGB",
        article=None,
        paragraph="3",
        sentence="1",
    )

    assert len(dummy_adapter.executed_queries) == 1
    query = dummy_adapter.executed_queries[0]
    assert "MERGE (n:LegalNorm {id: $id})" in query["cypher"]
    assert query["params"]["id"] == "§3_abs1_baugb"
    assert query["params"]["norm_text"] == "§ 3 Abs. 1 BauGB"
    assert query["params"]["law_abbreviation"] == "BauGB"
    assert query["params"]["paragraph"] == "3"


def test_link_mentions_concept(writer, dummy_adapter):
    """Test MENTIONS_CONCEPT relationship."""
    writer.link_mentions_concept(
        document_id="doc123",
        concept_id="BAURECHT",
        count=5,
    )

    assert len(dummy_adapter.executed_queries) == 1
    query = dummy_adapter.executed_queries[0]
    assert "MERGE (d)-[r:MENTIONS_CONCEPT]->(c)" in query["cypher"]
    assert query["params"]["doc_id"] == "doc123"
    assert query["params"]["concept_id"] == "baurecht"  # normalized
    assert query["params"]["count"] == 5
    assert "now" in query["params"]  # timestamp param
    assert "r.first_seen_at = $now" in query["cypher"]


def test_link_cites_norm(writer, dummy_adapter):
    """Test CITES_NORM relationship."""
    writer.link_cites_norm(
        document_id="doc123",
        norm_id="§3_abs1_baugb",
        count=2,
        context="Nach § 3 Abs. 1 BauGB ist die Öffentlichkeit zu beteiligen...",
    )

    assert len(dummy_adapter.executed_queries) == 1
    query = dummy_adapter.executed_queries[0]
    assert "MERGE (d)-[r:CITES_NORM]->(n)" in query["cypher"]
    assert query["params"]["doc_id"] == "doc123"
    assert query["params"]["norm_id"] == "§3_abs1_baugb"
    assert query["params"]["count"] == 2
    assert "context" in query["params"]


def test_link_issued_by(writer, dummy_adapter):
    """Test ISSUED_BY relationship."""
    writer.link_issued_by(
        document_id="doc123",
        authority_id="BVerwG",
        effective_date="2024-01-15",
    )

    assert len(dummy_adapter.executed_queries) == 1
    query = dummy_adapter.executed_queries[0]
    assert "MERGE (d)-[r:ISSUED_BY]->(a)" in query["cypher"]
    assert query["params"]["doc_id"] == "doc123"
    assert query["params"]["authority_id"] == "bverwg"  # normalized
    assert query["params"]["effective_date"] == "2024-01-15"


def test_link_applies_to(writer, dummy_adapter):
    """Test APPLIES_TO relationship."""
    writer.link_applies_to(
        document_id="doc123",
        jurisdiction_id="BW",
    )

    assert len(dummy_adapter.executed_queries) == 1
    query = dummy_adapter.executed_queries[0]
    assert "MERGE (d)-[r:APPLIES_TO]->(j)" in query["cypher"]
    assert query["params"]["doc_id"] == "doc123"
    assert query["params"]["jurisdiction_id"] == "bw"  # normalized


def test_multiple_operations(writer, dummy_adapter):
    """Test multiple operations in sequence."""
    writer.upsert_legal_concept("baurecht", "Baurecht", tier=1)
    writer.upsert_authority("bverwg", "BVerwG", "federal")
    writer.link_mentions_concept("doc123", "baurecht", count=3)

    assert len(dummy_adapter.executed_queries) == 3
    assert "LegalConcept" in dummy_adapter.executed_queries[0]["cypher"]
    assert "Authority" in dummy_adapter.executed_queries[1]["cypher"]
    assert "MENTIONS_CONCEPT" in dummy_adapter.executed_queries[2]["cypher"]
