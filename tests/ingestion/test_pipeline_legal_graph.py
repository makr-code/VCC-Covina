"""Tests for Legal Graph NLP Pipeline Integration.

Validates:
- Extraction + Graph Writer integration
- Error handling and graceful degradation
- Entity counting and processing
"""
from __future__ import annotations

import pytest
from unittest.mock import Mock
from typing import List


def test_legal_graph_nlp_flag_value():
    """Feature flag should be configurable via ENV."""
    import os
    
    # Test default (false)
    os.environ.pop("ENABLE_LEGAL_GRAPH_NLP", None)
    flag_default = os.getenv("ENABLE_LEGAL_GRAPH_NLP", "false").lower() == "true"
    assert flag_default is False
    
    # Test enabled
    os.environ["ENABLE_LEGAL_GRAPH_NLP"] = "true"
    flag_enabled = os.getenv("ENABLE_LEGAL_GRAPH_NLP", "false").lower() == "true"
    assert flag_enabled is True
    
    # Cleanup
    os.environ.pop("ENABLE_LEGAL_GRAPH_NLP", None)


def test_extractor_integration():
    """Test LegalEntityExtractor can be imported and used."""
    from ingestion.nlp.legal_entity_extractor import LegalEntityExtractor
    
    extractor = LegalEntityExtractor()
    text = "Gemäß § 35 BauGB ist das Vorhaben zulässig. Az. 4 K 123/20."
    entities = extractor.extract(text)
    
    assert len(entities) >= 2
    assert any(e.kind == "norm" for e in entities)
    assert any(e.kind == "aktenzeichen" for e in entities)


def test_graph_writer_integration():
    """Test EntityGraphWriter can be imported and initialized."""
    from ingestion.graph.entity_graph_writer import EntityGraphWriter
    
    # Initialize with mock adapter
    mock_adapter = Mock()
    writer = EntityGraphWriter(graph_adapter=mock_adapter)
    
    assert writer is not None
    assert hasattr(writer, "upsert_legal_norm")
    assert hasattr(writer, "upsert_legal_concept")
    assert hasattr(writer, "link_cites_norm")
    assert hasattr(writer, "link_mentions_concept")


def test_pipeline_end_to_end_mock():
    """Test complete pipeline with mocked graph adapter."""
    from ingestion.nlp.legal_entity_extractor import LegalEntityExtractor
    from ingestion.graph.entity_graph_writer import EntityGraphWriter
    from collections import Counter
    
    # Setup
    mock_adapter = Mock()
    mock_adapter.execute.return_value = [{"success": True}]
    
    extractor = LegalEntityExtractor()
    writer = EntityGraphWriter(graph_adapter=mock_adapter)
    
    # Execute pipeline
    text = "Nach § 35 Abs. 2 BauGB und § 4 BImSchG. Az. 4 K 123/20."
    entities = extractor.extract(text)
    
    # Count entities
    stats = Counter(e.kind for e in entities)
    
    assert stats["norm"] >= 2  # § 35 BauGB, § 4 BImSchG
    assert stats["aktenzeichen"] >= 1  # Az. 4 K 123/20
    
    # Process norms (simulate pipeline logic)
    norm_count = 0
    for entity in entities:
        if entity.kind == "norm":
            norm_id = entity.value.lower().replace(" ", "_")
            # This will call the mock adapter's execute method
            result = writer.upsert_legal_norm(
                norm_id=norm_id,
                norm_text=entity.value,
                law_abbreviation=entity.meta.get("law"),
                paragraph=entity.meta.get("paragraph"),
            )
            norm_count += 1
    
    # Verify processing occurred
    assert norm_count >= 2  # At least 2 norms processed


def test_pipeline_counts_extracted_entities():
    """Pipeline should count extracted entities correctly."""
    from ingestion.nlp.legal_entity_extractor import LegalEntityExtractor
    from collections import Counter
    
    extractor = LegalEntityExtractor()
    text = "Test text with § 35 BauGB and Az. 4 K 123/20."
    entities = extractor.extract(text)
    
    stats = Counter(e.kind for e in entities)
    
    assert stats["norm"] == 1
    assert stats["aktenzeichen"] == 1


def test_graph_writer_methods_exist():
    """Verify graph writer has required methods."""
    from ingestion.graph.entity_graph_writer import EntityGraphWriter
    
    mock_adapter = Mock()
    writer = EntityGraphWriter(graph_adapter=mock_adapter)
    
    # Check all required methods exist
    assert callable(getattr(writer, "upsert_legal_norm", None))
    assert callable(getattr(writer, "upsert_legal_concept", None))
    assert callable(getattr(writer, "upsert_authority", None))
    assert callable(getattr(writer, "upsert_jurisdiction", None))
    assert callable(getattr(writer, "link_mentions_concept", None))
    assert callable(getattr(writer, "link_cites_norm", None))
    assert callable(getattr(writer, "link_issued_by", None))
    assert callable(getattr(writer, "link_applies_to", None))


def test_pipeline_with_empty_text():
    """Pipeline should handle empty text gracefully."""
    from ingestion.nlp.legal_entity_extractor import LegalEntityExtractor
    
    extractor = LegalEntityExtractor()
    entities = extractor.extract("")
    
    assert entities == []
    assert isinstance(entities, list)


def test_pipeline_with_no_entities():
    """Pipeline should handle text with no legal entities."""
    from ingestion.nlp.legal_entity_extractor import LegalEntityExtractor
    
    extractor = LegalEntityExtractor()
    text = "This is just plain text without any legal references."
    entities = extractor.extract(text)
    
    assert entities == []
    assert isinstance(entities, list)
