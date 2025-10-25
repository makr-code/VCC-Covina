"""
Test Script: Hybrid Search with Semantic, Keyword, and Regex Modes
===================================================================

Tests the enhanced SearchController with:
- Auto-detect mode
- Semantic search (ChromaDB embeddings)
- Keyword search (PostgreSQL ILIKE)
- Regex search (PostgreSQL ~)
- Hybrid multi-backend search

Author: VCC-Covina Team
Version: 3.1.0
Date: 2025-10-24
"""

import sys
import os

# Add parent directory to path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../..')))

from controllers.search_controller import SearchController
from uds3.uds3_polyglot_manager import UDS3PolyglotManager
import config


def print_results(results, title="Search Results"):
    """Pretty print search results."""
    print(f"\n{'='*80}")
    print(f"{title}")
    print(f"{'='*80}")
    print(f"Query: {results.get('query', 'N/A')}")
    print(f"Mode: {results.get('mode', 'N/A')}")
    print(f"Total Results: {results.get('total_results', 0)}")
    print(f"  - Relational: {len(results.get('relational', []))}")
    print(f"  - Vector: {len(results.get('vector', []))}")
    print(f"  - Graph: {len(results.get('graph', []))}")
    
    # Print top results from each backend
    print(f"\n--- PostgreSQL Results (Top 3) ---")
    for i, doc in enumerate(results.get('relational', [])[:3], 1):
        print(f"{i}. [{doc.get('source')}] {doc.get('title', 'No Title')[:60]}")
        print(f"   Relevance: {doc.get('relevance', 0):.2f} | ID: {doc.get('document_id', 'N/A')}")
    
    print(f"\n--- ChromaDB Results (Top 3) ---")
    for i, chunk in enumerate(results.get('vector', [])[:3], 1):
        content_preview = chunk.get('content', '')[:60].replace('\n', ' ')
        print(f"{i}. [{chunk.get('source')}] {content_preview}...")
        print(f"   Relevance: {chunk.get('relevance', 0):.2f} | Distance: {chunk.get('distance', 'N/A'):.3f}")
    
    print(f"\n--- Neo4j Results (Top 3) ---")
    for i, node in enumerate(results.get('graph', [])[:3], 1):
        props = node.get('properties', {})
        title = props.get('title', props.get('name', 'No Title'))
        print(f"{i}. [{node.get('source')}] {title[:60]}")
        print(f"   Relevance: {node.get('relevance', 0):.2f} | Labels: {node.get('labels', [])}")


def test_auto_detect():
    """Test 1: Auto-detect search mode from query pattern."""
    print("\n\n" + "="*80)
    print("TEST 1: Auto-Detect Mode")
    print("="*80)
    
    # Initialize UDS3 and SearchController
    uds3 = UDS3PolyglotManager(config)
    search_ctrl = SearchController(uds3)
    
    test_queries = [
        ("document", "keyword"),  # Simple keyword
        ("What is the main purpose of this system?", "semantic"),  # Natural language
        ("^[A-Z].*contract", "regex"),  # Regex pattern
        ("how to process invoices", "semantic"),  # Question
    ]
    
    for query, expected_mode in test_queries:
        detected_mode = search_ctrl.detect_search_mode(query)
        status = "✅" if detected_mode == expected_mode else "❌"
        print(f"{status} Query: '{query[:50]}...'")
        print(f"   Expected: {expected_mode} | Detected: {detected_mode}")


def test_keyword_search():
    """Test 2: Keyword search (basic ILIKE)."""
    print("\n\n" + "="*80)
    print("TEST 2: Keyword Search Mode")
    print("="*80)
    
    uds3 = UDS3PolyglotManager(config)
    search_ctrl = SearchController(uds3)
    
    query = "contract"
    results = search_ctrl.hybrid_search(query, limit=10, mode='keyword')
    print_results(results, f"Keyword Search: '{query}'")


def test_semantic_search():
    """Test 3: Semantic search (ChromaDB embeddings)."""
    print("\n\n" + "="*80)
    print("TEST 3: Semantic Search Mode")
    print("="*80)
    
    uds3 = UDS3PolyglotManager(config)
    search_ctrl = SearchController(uds3)
    
    query = "How do I process invoices and manage payments?"
    results = search_ctrl.hybrid_search(query, limit=10, mode='semantic')
    print_results(results, f"Semantic Search: '{query}'")


def test_regex_search():
    """Test 4: Regex search (PostgreSQL ~)."""
    print("\n\n" + "="*80)
    print("TEST 4: Regex Search Mode")
    print("="*80)
    
    uds3 = UDS3PolyglotManager(config)
    search_ctrl = SearchController(uds3)
    
    # Test regex pattern: Documents starting with capital letter + containing "contract"
    query = "^[A-Z].*contract"
    results = search_ctrl.hybrid_search(query, limit=10, mode='regex')
    print_results(results, f"Regex Search: '{query}'")


def test_hybrid_ranking():
    """Test 5: Hybrid search with merged + ranked results."""
    print("\n\n" + "="*80)
    print("TEST 5: Hybrid Search with Ranking")
    print("="*80)
    
    uds3 = UDS3PolyglotManager(config)
    search_ctrl = SearchController(uds3)
    
    query = "invoice processing workflow"
    results = search_ctrl.hybrid_search(query, limit=15, mode='auto')
    
    # Merge and rank
    merged = search_ctrl.merge_and_rank_results(results)
    
    print(f"\n{'='*80}")
    print(f"Hybrid Search: '{query}'")
    print(f"{'='*80}")
    print(f"Total Results: {len(merged)}")
    
    print(f"\n--- Top 10 Results (Weighted by Relevance) ---")
    for i, result in enumerate(merged[:10], 1):
        title = (
            result.get('title', '') or 
            result.get('content', '')[:50] or 
            result.get('properties', {}).get('title', 'Untitled')
        )
        print(f"{i}. [{result.get('source')}] {title[:60]}")
        print(f"   Final Score: {result.get('final_score', 0):.3f} | Relevance: {result.get('relevance', 0):.2f}")


def main():
    """Run all tests."""
    print("\n" + "="*80)
    print("Polyglot Admin - Hybrid Search Test Suite")
    print("="*80)
    print("Testing: Auto-Detect | Keyword | Semantic | Regex | Hybrid")
    print("="*80)
    
    try:
        # Test 1: Auto-detect mode
        test_auto_detect()
        
        # Test 2: Keyword search
        test_keyword_search()
        
        # Test 3: Semantic search
        test_semantic_search()
        
        # Test 4: Regex search
        test_regex_search()
        
        # Test 5: Hybrid ranking
        test_hybrid_ranking()
        
        print("\n\n" + "="*80)
        print("✅ All tests completed!")
        print("="*80)
    
    except Exception as e:
        print(f"\n\n❌ Test suite failed: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    main()
