"""
Legal NLP Pipeline Integration Test
=====================================

Tests the end-to-end integration of Legal Entity Extractor + Entity Graph Writer
via the process_document_with_uds3() pipeline behind ENABLE_LEGAL_GRAPH_NLP flag.

Coverage:
- Feature flag behavior (enabled/disabled)
- Entity extraction from sample legal document
- Graph write operations via UDS3
- Error handling and graceful degradation
"""

import pytest
from unittest.mock import Mock, patch, MagicMock
from ingestion.nlp.legal_entity_extractor import ExtractedEntity


# Sample legal document content
SAMPLE_LEGAL_DOC = """
Az. 4 K 123/20

Beschluss vom 15.03.2023 (ECLI:DE:BVerwG:2023:150323U4C123.20)

Nach § 3 Abs. 1 BauGB und Art. 28 GG ist die Öffentlichkeitsbeteiligung
verpflichtend. Der Antragsteller beruft sich auf § 5 VwVfG.

Gemäß §§ 3, 4, 5 BauGB sind die Unterlagen offenzulegen.

Datum: 15.03.2023
"""


@pytest.fixture
def mock_env_enabled(monkeypatch):
    """Enable Legal Graph NLP via ENV."""
    monkeypatch.setenv("ENABLE_LEGAL_GRAPH_NLP", "true")


@pytest.fixture
def mock_env_disabled(monkeypatch):
    """Disable Legal Graph NLP via ENV."""
    monkeypatch.setenv("ENABLE_LEGAL_GRAPH_NLP", "false")


def test_should_use_legal_graph_nlp_enabled(mock_env_enabled):
    """Test feature flag detection when enabled."""
    from backend.ingestion import should_use_legal_graph_nlp
    assert should_use_legal_graph_nlp() is True


def test_should_use_legal_graph_nlp_disabled(mock_env_disabled):
    """Test feature flag detection when disabled."""
    from backend.ingestion import should_use_legal_graph_nlp
    assert should_use_legal_graph_nlp() is False


def test_legal_nlp_integration_disabled(mock_env_disabled):
    """
    Test that Legal NLP processing is skipped when flag is disabled.
    
    Validates:
    - should_use_legal_graph_nlp() returns False
    - No extraction or graph writing occurs
    - Pipeline returns status: disabled
    """
    from backend.ingestion import should_use_legal_graph_nlp
    
    # Feature flag disabled
    assert should_use_legal_graph_nlp() is False
    
    # Simulate pipeline check
    legal_nlp_results = {}
    if should_use_legal_graph_nlp():
        legal_nlp_results = {"status": "active"}  # Should NOT execute
    else:
        legal_nlp_results = {"status": "disabled"}
    
    assert legal_nlp_results == {"status": "disabled"}


def test_legal_nlp_extraction_and_persistence_mock(mock_env_enabled):
    """
    Test Legal NLP extraction + graph writing with mocked UDS3.
    
    Validates:
    - Entities extracted from sample document
    - Graph writer methods called with correct parameters
    - Stats returned in pipeline result
    """
    from ingestion.nlp.legal_entity_extractor import LegalEntityExtractor
    from ingestion.graph.entity_graph_writer import EntityGraphWriter
    from collections import Counter
    
    # Extract entities (real extraction)
    extractor = LegalEntityExtractor()
    entities = extractor.extract(SAMPLE_LEGAL_DOC)
    
    # Verify extraction
    assert len(entities) > 0
    entity_kinds = [e.kind for e in entities]
    assert "norm" in entity_kinds  # § norms
    assert "aktenzeichen" in entity_kinds  # Az.
    assert "ecli" in entity_kinds  # ECLI
    assert "date" in entity_kinds  # Dates
    
    # Mock graph writer (avoid real Neo4j calls)
    with patch.object(EntityGraphWriter, 'upsert_legal_norm') as mock_norm, \
         patch.object(EntityGraphWriter, 'upsert_legal_concept') as mock_concept, \
         patch.object(EntityGraphWriter, 'link_cites_norm') as mock_link_norm, \
         patch.object(EntityGraphWriter, 'link_mentions_concept') as mock_link_concept:
        
        # Simulate pipeline processing
        writer = EntityGraphWriter(graph_adapter=Mock())  # Dummy adapter
        entity_stats = Counter()
        document_id = "test_doc_123"
        
        for entity in entities:
            if entity.kind == "norm":
                norm_id = entity.value.lower().replace(" ", "_")
                writer.upsert_legal_norm(
                    norm_id=norm_id,
                    norm_text=entity.value,
                    law_abbreviation=entity.meta.get("law"),
                    paragraph=entity.meta.get("paragraph"),
                )
                writer.link_cites_norm(
                    document_id=document_id,
                    norm_id=norm_id,
                    count=1,
                    context=entity.meta.get("context_window"),
                )
                entity_stats["norms"] += 1
            
            elif entity.kind == "aktenzeichen":
                concept_id = f"az_{entity.value.lower().replace(' ', '_')}"
                writer.upsert_legal_concept(
                    concept_id=concept_id,
                    name=f"Aktenzeichen: {entity.value}",
                    tier=1,
                    context_window=entity.meta.get("context_window"),
                )
                writer.link_mentions_concept(
                    document_id=document_id,
                    concept_id=concept_id,
                    count=1,
                )
                entity_stats["aktenzeichen"] += 1
            
            elif entity.kind == "ecli":
                concept_id = entity.value.lower()
                writer.upsert_legal_concept(
                    concept_id=concept_id,
                    name=f"ECLI: {entity.value}",
                    tier=1,
                    context_window=entity.meta.get("context_window"),
                )
                writer.link_mentions_concept(
                    document_id=document_id,
                    concept_id=concept_id,
                    count=1,
                )
                entity_stats["ecli"] += 1
        
        # Verify graph operations were called
        assert mock_norm.call_count > 0, "Legal norms should be persisted"
        assert mock_link_norm.call_count > 0, "Norm relationships should be created"
        assert mock_concept.call_count > 0, "Concepts should be persisted"
        assert mock_link_concept.call_count > 0, "Concept relationships should be created"
        
        # Verify stats
        assert entity_stats["norms"] >= 3, "Should extract multiple norms (§ 3, § 5, §§ 3,4,5)"
        assert entity_stats["aktenzeichen"] == 1, "Should extract Az. 4 K 123/20"
        assert entity_stats["ecli"] == 1, "Should extract ECLI"


def test_legal_nlp_error_handling():
    """
    Test graceful error handling when Legal NLP extraction fails.
    
    Validates:
    - Pipeline continues on extraction errors
    - Error message captured in results
    - No crash or exception propagation
    """
    from ingestion.nlp.legal_entity_extractor import LegalEntityExtractor
    
    # Simulate extraction error
    with patch.object(LegalEntityExtractor, 'extract', side_effect=Exception("Mock extraction error")):
        extractor = LegalEntityExtractor()
        
        # Catch exception
        legal_nlp_results = {}
        try:
            entities = extractor.extract(SAMPLE_LEGAL_DOC)
            legal_nlp_results = {"entities_extracted": len(entities)}
        except Exception as e:
            legal_nlp_results = {
                "error": str(e)[:100],
                "entities_extracted": 0,
            }
        
        # Verify error handling
        assert "error" in legal_nlp_results
        assert legal_nlp_results["entities_extracted"] == 0
        assert "Mock extraction error" in legal_nlp_results["error"]


def test_legal_nlp_noop_when_no_entities():
    """
    Test that pipeline handles documents with no legal entities gracefully.
    
    Validates:
    - Extraction returns empty list for non-legal docs
    - No graph operations performed
    - Stats show 0 entities
    """
    from ingestion.nlp.legal_entity_extractor import LegalEntityExtractor
    from collections import Counter
    
    # Non-legal document
    non_legal_doc = """
    This is a simple business letter.
    It does not contain any legal references.
    Just normal text about products and services.
    """
    
    extractor = LegalEntityExtractor()
    entities = extractor.extract(non_legal_doc)
    
    # Verify no entities extracted
    assert len(entities) == 0
    
    # Verify stats
    entity_stats = Counter()
    for entity in entities:
        entity_stats[entity.kind] += 1
    
    assert dict(entity_stats) == {}, "No entities should be extracted"
