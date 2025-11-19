#!/usr/bin/env python3
"""
Test Polyglot Document Aggregator

Validates that the aggregator creates complete JSON with:
- Relational data (PostgreSQL)
- Vector data (ChromaDB chunks)
- Graph data (Neo4j nodes)
- File data (text + binary)
"""

import sys
import os
import json
import tempfile
from pathlib import Path

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from ingestion.polyglot_aggregator import PolyglotDocumentAggregator, create_polyglot_document


def test_basic_aggregation():
    """Test basic aggregation without binary file"""
    print("=" * 80)
    print("Test 1: Basic Polyglot Aggregation")
    print("=" * 80)
    
    aggregator = PolyglotDocumentAggregator()
    
    # Create test data
    relational_data = {
        "document_id": "test_001",
        "file_path": "test.pdf",
        "classification": "GESETZ",
        "quality_score": 0.95
    }
    
    vector_data = [
        {
            "chunk_id": "test_001_chunk_0",
            "text": "§ 1 Zweck des Gesetzes",
            "metadata": {
                "paragraph": "§ 1",
                "keywords": ["zweck", "gesetz"]
            }
        },
        {
            "chunk_id": "test_001_chunk_1",
            "text": "(1) Zweck dieses Gesetzes ist...",
            "metadata": {
                "paragraph": "§ 1",
                "absatz": 1
            }
        }
    ]
    
    graph_data = {
        "node_id": "test_001",
        "node_type": "Document",
        "relationships": []
    }
    
    text_content = "§ 1 Zweck des Gesetzes\n(1) Zweck dieses Gesetzes ist..."
    
    # Aggregate
    result = aggregator.aggregate_document(
        document_id="test_001",
        file_path="test.pdf",
        classification="GESETZ",
        relational_data=relational_data,
        vector_data=vector_data,
        graph_data=graph_data,
        text_content=text_content
    )
    
    # Validate structure
    print("\n✓ Aggregation created")
    assert "document_id" in result
    assert "relational" in result
    assert "vector" in result
    assert "graph" in result
    assert "file" in result
    assert "statistics" in result
    
    print(f"  Document ID: {result['document_id']}")
    print(f"  Relational: {len(result['relational'])} fields")
    print(f"  Vector: {result['vector']['total_chunks']} chunks")
    print(f"  Graph: {result['graph']['node_type']}")
    print(f"  File: {result['file']['text_length']} chars")
    print(f"  Completeness: {result['statistics']['polyglot_completeness']:.0%}")
    
    # Check completeness
    stats = result['statistics']
    assert stats['has_relational'] is True
    assert stats['has_vector'] is True
    assert stats['has_graph'] is True
    assert stats['has_text'] is True
    assert stats['has_binary'] is False  # No binary file provided
    
    print("\n✓ All 4 polyglot components present (text only)")


def test_with_binary_file():
    """Test aggregation with binary file"""
    print("\n" + "=" * 80)
    print("Test 2: Polyglot Aggregation with Binary File")
    print("=" * 80)
    
    # Create temporary test file
    with tempfile.NamedTemporaryFile(mode='w', suffix='.txt', delete=False) as f:
        f.write("Test binary content\nLine 2\nLine 3")
        temp_file = f.name
    
    try:
        aggregator = PolyglotDocumentAggregator()
        
        # Provide all data for 100% completeness
        result = aggregator.aggregate_document(
            document_id="test_002",
            file_path=temp_file,
            classification="DOCUMENT",
            relational_data={"test": "data"},
            vector_data=[{"chunk_id": "test", "text": "test"}],
            graph_data={"node_id": "test"},
            text_content="Test binary content\nLine 2\nLine 3",
            binary_file_path=temp_file
        )
        
        print("\n✓ Aggregation with binary file created")
        
        # Check binary data
        assert "file" in result
        assert "binary_data" in result["file"]
        assert "content_type" in result["file"]
        assert "size" in result["file"]
        
        print(f"  Filename: {result['file']['filename']}")
        print(f"  Content Type: {result['file']['content_type']}")
        print(f"  Size: {result['file']['size']} bytes")
        print(f"  Binary Data: {len(result['file']['binary_data'])} chars (base64)")
        print(f"  Completeness: {result['statistics']['polyglot_completeness']:.0%}")
        
        # Check completeness (should be 100% now)
        assert result['statistics']['has_binary'] is True
        assert result['statistics']['polyglot_completeness'] == 1.0
        
        print("\n✓ Complete polyglot dataset (100%)")
        
    finally:
        # Cleanup
        if os.path.exists(temp_file):
            os.unlink(temp_file)


def test_json_serialization():
    """Test saving and loading from JSON"""
    print("\n" + "=" * 80)
    print("Test 3: JSON Serialization")
    print("=" * 80)
    
    aggregator = PolyglotDocumentAggregator()
    
    # Create test data
    result = aggregator.aggregate_document(
        document_id="test_003",
        file_path="test.pdf",
        classification="GESETZ",
        text_content="Test content"
    )
    
    # Save to JSON
    with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
        json_path = f.name
    
    try:
        aggregator.save_to_json(result, json_path)
        print(f"\n✓ Saved to JSON: {json_path}")
        
        # Check file exists
        assert os.path.exists(json_path)
        assert os.path.getsize(json_path) > 0
        
        # Load back
        loaded = aggregator.load_from_json(json_path)
        print(f"✓ Loaded from JSON")
        
        # Validate content
        assert loaded['document_id'] == result['document_id']
        assert loaded['metadata'] == result['metadata']
        assert loaded['statistics'] == result['statistics']
        
        print(f"  Document ID matches: {loaded['document_id']}")
        print(f"  Metadata matches: {len(loaded['metadata'])} fields")
        print(f"  Statistics match: {len(loaded['statistics'])} fields")
        
        print("\n✓ JSON serialization working correctly")
        
    finally:
        if os.path.exists(json_path):
            os.unlink(json_path)


def test_convenience_function():
    """Test convenience function"""
    print("\n" + "=" * 80)
    print("Test 4: Convenience Function")
    print("=" * 80)
    
    result = create_polyglot_document(
        document_id="test_004",
        file_path="test.pdf",
        classification="GESETZ",
        text_content="Simple test"
    )
    
    print("\n✓ Convenience function works")
    assert result['document_id'] == "test_004"
    assert result['metadata']['classification'] == "GESETZ"
    
    print(f"  Document ID: {result['document_id']}")
    print(f"  Classification: {result['metadata']['classification']}")


def test_json_structure():
    """Validate expected JSON structure for Themis"""
    print("\n" + "=" * 80)
    print("Test 5: Themis-Compatible JSON Structure")
    print("=" * 80)
    
    # Create complete test data
    vector_data = [
        {
            "chunk_id": "test_chunk_0",
            "text": "Test chunk",
            "metadata": {"paragraph": "§ 1"}
        }
    ]
    
    result = create_polyglot_document(
        document_id="test_005",
        file_path="BImSchG.pdf",
        classification="GESETZ",
        relational_data={"test": "data"},
        vector_data=vector_data,
        graph_data={"node": "test"},
        text_content="Full text content"
    )
    
    print("\n✓ Themis-compatible JSON created")
    print("\nJSON Structure:")
    print(f"  document_id: {result['document_id']}")
    print(f"  version: {result['version']}")
    print(f"  created_at: {result['created_at']}")
    print(f"  metadata: {list(result['metadata'].keys())}")
    print(f"  relational: {list(result['relational'].keys())}")
    print(f"  vector: total_chunks={result['vector']['total_chunks']}")
    print(f"  graph: {list(result['graph'].keys())}")
    print(f"  file: {list(result['file'].keys())}")
    print(f"  statistics: {list(result['statistics'].keys())}")
    
    # Required fields for Themis
    required_top_level = ['document_id', 'version', 'metadata', 'relational', 'vector', 'graph', 'file']
    for field in required_top_level:
        assert field in result, f"Missing required field: {field}"
        print(f"  ✓ {field}")
    
    print("\n✓ All required fields present")


def run_all_tests():
    """Run all tests"""
    print("\n" + "=" * 80)
    print("POLYGLOT DOCUMENT AGGREGATOR - TEST SUITE")
    print("=" * 80)
    
    try:
        test_basic_aggregation()
        test_with_binary_file()
        test_json_serialization()
        test_convenience_function()
        test_json_structure()
        
        print("\n" + "=" * 80)
        print("✓ ALL TESTS PASSED")
        print("=" * 80)
        
        print("\nPolyglot Aggregation Features:")
        print("  ✓ Aggregates data from all 4 databases")
        print("  ✓ Includes binary file data (base64)")
        print("  ✓ Calculates completeness score")
        print("  ✓ JSON serialization/deserialization")
        print("  ✓ Themis-compatible format")
        
        return True
        
    except Exception as e:
        print(f"\n✗ TEST FAILED: {e}")
        import traceback
        traceback.print_exc()
        return False


if __name__ == "__main__":
    success = run_all_tests()
    sys.exit(0 if success else 1)
