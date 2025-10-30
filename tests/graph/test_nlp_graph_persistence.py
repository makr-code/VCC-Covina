"""
Phase L4: Tests für NLP → Graph Persistence
Unit-Tests für Node-Creation, Linking, Idempotenz, Checkpointing.
"""

import pytest
import json
import tempfile
import os
from ingestion.graph.nlp_graph_persistence import NLPGraphPersister, batch_persist_from_jsonl


class MockNeo4jWrapper:
    """Mock für UDS3 Neo4j Wrapper zu Test-Zwecken."""
    
    def __init__(self):
        self.executed_queries = []
        self.nodes_created = {}
        self.relations_created = []
    
    def execute_cypher(self, query: str, params: dict):
        """Mock execute_cypher: speichert Queries und simuliert MERGE."""
        self.executed_queries.append((query, params))
        
        # Simuliere MERGE-Verhalten für verschiedene Node-Typen
        if "LegalConcept" in query:
            node_id = params.get("id")
            if node_id not in self.nodes_created:
                self.nodes_created[node_id] = {"type": "LegalConcept", "params": params}
            return [{"id": node_id}]
        
        elif "LegalNorm" in query:
            node_id = params.get("id")
            if node_id not in self.nodes_created:
                self.nodes_created[node_id] = {"type": "LegalNorm", "params": params}
            return [{"id": node_id}]
        
        elif "Authority" in query:
            node_id = params.get("id")
            if node_id not in self.nodes_created:
                self.nodes_created[node_id] = {"type": "Authority", "params": params}
            return [{"id": node_id}]
        
        elif "MENTIONS" in query or "CITES" in query or "REFERENCES_AUTHORITY" in query:
            self.relations_created.append(params)
            return [{"r": "relation"}]
        
        return []


def test_nlp_graph_persister_creation():
    """Test: NLPGraphPersister kann initialisiert werden."""
    mock_neo4j = MockNeo4jWrapper()
    persister = NLPGraphPersister(neo4j_wrapper=mock_neo4j, dry_run=False)
    
    assert persister.neo4j == mock_neo4j
    assert persister.dry_run == False
    assert persister.stats["docs_processed"] == 0


def test_create_legal_concept_node():
    """Test: LegalConcept Node wird erstellt."""
    mock_neo4j = MockNeo4jWrapper()
    persister = NLPGraphPersister(neo4j_wrapper=mock_neo4j, dry_run=False)
    
    entity = {"text": "Deutsche Bundesbank", "label": "ORG", "start": 100, "end": 119}
    concept_id = persister._create_legal_concept_node(entity, "test.md")
    
    assert concept_id is not None
    assert concept_id.startswith("nlp_org_")
    assert "nlp_org_Deutsche Bundesbank" in mock_neo4j.nodes_created
    assert persister.stats["entities_created"] == 1


def test_create_legal_norm_node():
    """Test: LegalNorm Node wird aus CITES_NORM Relation erstellt."""
    mock_neo4j = MockNeo4jWrapper()
    persister = NLPGraphPersister(neo4j_wrapper=mock_neo4j, dry_run=False)
    
    relation = {"type": "CITES_NORM", "object": "§ 5 BImSchG", "start": 200, "end": 211}
    norm_id = persister._create_legal_norm_node(relation)
    
    assert norm_id is not None
    assert norm_id.startswith("nlp_norm_")
    assert "nlp_norm_§ 5 BImSchG" in mock_neo4j.nodes_created
    assert persister.stats["entities_created"] == 1


def test_create_authority_node():
    """Test: Authority Node wird aus HAS_JURISDICTION Relation erstellt."""
    mock_neo4j = MockNeo4jWrapper()
    persister = NLPGraphPersister(neo4j_wrapper=mock_neo4j, dry_run=False)
    
    relation = {"type": "HAS_JURISDICTION", "subject": "Bauamt", "object": "Baurecht", "start": 300, "end": 350}
    authority_id = persister._create_authority_node(relation)
    
    assert authority_id is not None
    assert authority_id.startswith("nlp_authority_")
    assert "nlp_authority_Bauamt" in mock_neo4j.nodes_created
    assert persister.stats["entities_created"] == 1


def test_process_jsonl_record():
    """Test: JSONL-Record wird vollständig verarbeitet (Entities + Relations)."""
    mock_neo4j = MockNeo4jWrapper()
    persister = NLPGraphPersister(neo4j_wrapper=mock_neo4j, dry_run=False)
    
    record = {
        "path": "test_doc.md",
        "entities": [
            {"text": "Bundesbank", "label": "ORG", "start": 0, "end": 10},
            {"text": "Berlin", "label": "LOC", "start": 20, "end": 26},
        ],
        "relations": [
            {"type": "CITES_NORM", "object": "§ 3 BGB", "start": 100, "end": 107},
            {"type": "HAS_JURISDICTION", "subject": "Finanzamt", "object": "Steuerrecht", "start": 200, "end": 250},
        ],
        "domain": "Unbekannt"
    }
    
    persister.process_jsonl_record(record)
    
    assert persister.stats["docs_processed"] == 1
    assert persister.stats["entities_created"] == 4  # 2 entities + 1 norm + 1 authority
    assert persister.stats["relations_created"] == 4  # 2 MENTIONS + 1 CITES + 1 REFERENCES_AUTHORITY


def test_idempotent_processing():
    """Test: Mehrfache Verarbeitung desselben Records ist idempotent."""
    mock_neo4j = MockNeo4jWrapper()
    persister = NLPGraphPersister(neo4j_wrapper=mock_neo4j, dry_run=False)
    
    record = {
        "path": "test.md",
        "entities": [{"text": "Test Entity", "label": "ORG", "start": 0, "end": 11}],
        "relations": [],
        "domain": "Unbekannt"
    }
    
    # Erste Verarbeitung
    persister.process_jsonl_record(record)
    entities_after_first = persister.stats["entities_created"]
    
    # Zweite Verarbeitung (sollte MERGE triggern, nicht CREATE)
    persister.process_jsonl_record(record)
    entities_after_second = persister.stats["entities_created"]
    
    # Entity-Count erhöht sich, aber Node wurde nur einmal erstellt (MERGE)
    assert entities_after_second == entities_after_first * 2
    assert len(mock_neo4j.nodes_created) == 1  # Nur ein Node trotz 2x Processing


def test_batch_persist_from_jsonl():
    """Test: Batch-Persistence aus JSONL mit Checkpointing."""
    # Erstelle temporäre JSONL-Datei
    with tempfile.NamedTemporaryFile(mode='w', suffix='.jsonl', delete=False, encoding='utf-8') as f:
        for i in range(25):
            record = {
                "path": f"doc_{i}.md",
                "entities": [{"text": f"Entity {i}", "label": "ORG", "start": 0, "end": 10}],
                "relations": [],
                "domain": "Unbekannt"
            }
            f.write(json.dumps(record) + "\n")
        temp_path = f.name
    
    try:
        mock_neo4j = MockNeo4jWrapper()
        stats = batch_persist_from_jsonl(
            jsonl_path=temp_path,
            neo4j_wrapper=mock_neo4j,
            checkpoint_interval=10,
            dry_run=False
        )
        
        assert stats["docs_processed"] == 25
        assert stats["entities_created"] == 25
        assert stats["errors"] == 0
    finally:
        os.unlink(temp_path)


def test_dry_run_mode():
    """Test: Dry-Run-Modus erstellt keine echten Nodes."""
    mock_neo4j = MockNeo4jWrapper()
    persister = NLPGraphPersister(neo4j_wrapper=mock_neo4j, dry_run=True)
    
    record = {
        "path": "test.md",
        "entities": [{"text": "Test", "label": "ORG", "start": 0, "end": 4}],
        "relations": [{"type": "CITES_NORM", "object": "§ 1 BGB", "start": 10, "end": 17}],
        "domain": "Unbekannt"
    }
    
    persister.process_jsonl_record(record)
    
    assert persister.stats["docs_processed"] == 1
    assert len(mock_neo4j.nodes_created) == 0  # Keine Nodes im Dry-Run
    assert len(mock_neo4j.relations_created) == 0


def test_error_handling():
    """Test: Fehlerhafte JSONL-Records werden isoliert behandelt."""
    mock_neo4j = MockNeo4jWrapper()
    persister = NLPGraphPersister(neo4j_wrapper=mock_neo4j, dry_run=False)
    
    # Record mit Fehler-Flag
    error_record = {"path": "error.md", "error": "File not found"}
    persister.process_jsonl_record(error_record)
    
    assert persister.stats["errors"] == 1
    assert persister.stats["docs_processed"] == 0


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
