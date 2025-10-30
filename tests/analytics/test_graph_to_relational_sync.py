"""
Tests für Graph → Relational Analytics Sync

Nutzt Mini-Graph Seeds und validiert PostgreSQL Counts.
"""
import pytest
from unittest.mock import Mock, MagicMock
from datetime import date

from ingestion.analytics.graph_to_relational_sync import GraphToRelationalSync


@pytest.fixture
def mock_graph():
    """Mock Neo4j Adapter mit Test-Daten."""
    adapter = Mock()
    
    # Query-Response Mapping
    def execute_query_mock(query, params):
        # Domains Query
        if "MATCH (d:LegalDomain)" in query and "RETURN d.id" in query:
            return [
                {"id": "baurecht", "name": "Baurecht", "tier": 2, "parent_id": "oeffentliches_recht"},
                {"id": "oeffentliches_recht", "name": "Öffentliches Recht", "tier": 1, "parent_id": None},
            ]
        # Concepts Query
        elif "MATCH (c:LegalConcept)" in query:
            return [
                {"id": "bauplanung", "name": "Bauplanungsrecht", "category": "recht", "domain_id": "baurecht"},
            ]
        # Jurisdictions Query
        elif "MATCH (j:Jurisdiction)" in query:
            return [
                {"id": "de", "ags": None, "name": "Deutschland", "level": "bund"},
            ]
        # Authorities Query
        elif "MATCH (a:Authority)" in query:
            return [
                {"id": "bauamt", "name": "Bauamt", "authority_type": "agency", "level": "kommune", "jurisdiction_id": "de"},
            ]
        # Daily Facts Query
        elif "MATCH (doc:Document)" in query:
            return [
                {"domain_id": "baurecht", "document_count": 5},
            ]
        else:
            return []
    
    adapter.execute_query = Mock(side_effect=execute_query_mock)
    return adapter


@pytest.fixture
def mock_relational():
    """Mock PostgreSQL Adapter."""
    adapter = Mock()
    adapter.execute = Mock(return_value=None)
    return adapter


def test_sync_domains(mock_graph, mock_relational):
    """Test Domain Sync (LegalDomain → dim_domain)."""
    sync = GraphToRelationalSync(mock_graph, mock_relational)
    
    count = sync.sync_domains()
    
    assert count == 2
    assert mock_relational.execute.call_count == 2
    # Prüfe Upsert SQL
    call_args = mock_relational.execute.call_args_list[0]
    assert "INSERT INTO dim_domain" in call_args[0][0]
    assert "ON CONFLICT (id) DO UPDATE" in call_args[0][0]


def test_sync_concepts(mock_graph, mock_relational):
    """Test Concept Sync (LegalConcept → dim_concept)."""
    sync = GraphToRelationalSync(mock_graph, mock_relational)
    
    count = sync.sync_concepts()
    
    assert count == 1
    assert mock_relational.execute.call_count == 1


def test_sync_jurisdictions(mock_graph, mock_relational):
    """Test Jurisdiction Sync."""
    sync = GraphToRelationalSync(mock_graph, mock_relational)
    
    count = sync.sync_jurisdictions()
    
    assert count == 1
    assert mock_relational.execute.call_count == 1


def test_sync_authorities(mock_graph, mock_relational):
    """Test Authority Sync."""
    sync = GraphToRelationalSync(mock_graph, mock_relational)
    
    count = sync.sync_authorities()
    
    assert count == 1
    assert mock_relational.execute.call_count == 1


def test_sync_daily_facts(mock_graph, mock_relational):
    """Test Daily Facts Sync."""
    sync = GraphToRelationalSync(mock_graph, mock_relational)
    
    today = date.today()
    count = sync.sync_daily_facts(today)
    
    assert count == 1
    assert mock_relational.execute.call_count == 1
    # Prüfe date_bucket Parameter
    call_args = mock_relational.execute.call_args_list[0]
    assert call_args[0][1][0] == today


def test_sync_all(mock_graph, mock_relational, monkeypatch):
    """Test kompletter Sync (Dimensions + Facts)."""
    # Enable feature flag BEFORE importing module
    monkeypatch.setenv("ENABLE_GRAPH_ANALYTICS_SYNC", "true")
    
    # Reload module to pick up new env var
    import importlib
    import ingestion.analytics.graph_to_relational_sync as sync_module
    importlib.reload(sync_module)
    
    sync = sync_module.GraphToRelationalSync(mock_graph, mock_relational)
    stats = sync.sync_all()
    
    assert stats["domains_synced"] == 2
    assert stats["concepts_synced"] == 1
    assert stats["jurisdictions_synced"] == 1
    assert stats["authorities_synced"] == 1
    assert stats["facts_synced"] == 1


def test_sync_disabled_by_default(mock_graph, mock_relational, monkeypatch):
    """Test dass Sync standardmäßig disabled ist."""
    monkeypatch.setenv("ENABLE_GRAPH_ANALYTICS_SYNC", "false")
    
    # Reload module to pick up env var
    import importlib
    import ingestion.analytics.graph_to_relational_sync as sync_module
    importlib.reload(sync_module)
    
    sync = sync_module.GraphToRelationalSync(mock_graph, mock_relational)
    stats = sync.sync_all()
    
    assert stats.get("status") == "disabled" or stats.get("domains_synced") == 0
    assert mock_relational.execute.call_count == 0
