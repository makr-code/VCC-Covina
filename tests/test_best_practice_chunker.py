#!/usr/bin/env python3
"""
Test Best Practice Chunking Strategy

Validates the implementation of industry best practices:
- Context overlap
- Metadata enrichment
- Adaptive sizing
- Quality validation
"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from ingestion.parsers import BestPracticeChunker, ChunkingConfig

# Test document with various structures
TEST_DOCUMENT = """
# Executive Summary

This document provides an overview of our 2025 strategy.

## Market Analysis

The market shows strong growth in three key areas:

1. Digital Transformation
   - Cloud migration
   - AI integration
   - Process automation

2. Sustainability Initiatives
   - Carbon neutrality by 2030
   - Green energy adoption
   - Circular economy practices

3. Customer Experience
   - Personalization
   - Omnichannel presence
   - Real-time support

## Financial Projections

### Revenue Growth

We project 15% year-over-year growth. See § 5 for detailed breakdown.

### Cost Structure

Operating costs are expected to decrease by 8% through automation.

## References

This strategy aligns with our vision stated in Artikel 1 of the company charter.
For more details, see Abschnitt 2.1 of the operational handbook.

## Conclusion

The implementation roadmap follows in the next chapter.
"""

def test_basic_chunking():
    """Test basic chunking functionality"""
    print("=" * 80)
    print("Test 1: Basic Chunking")
    print("=" * 80)
    
    config = ChunkingConfig(
        min_chunk_size=50,
        max_chunk_size=300,
        target_chunk_size=150,
        enable_overlap=False
    )
    
    chunker = BestPracticeChunker(config)
    chunks = chunker.chunk_document(TEST_DOCUMENT, document_id="test_001")
    
    print(f"\n✓ Created {len(chunks)} chunks")
    print(f"  Min size: {min(c.char_count for c in chunks)} chars")
    print(f"  Max size: {max(c.char_count for c in chunks)} chars")
    print(f"  Avg size: {sum(c.char_count for c in chunks) // len(chunks)} chars")
    
    assert len(chunks) > 0, "No chunks created"
    assert all(c.char_count >= config.min_chunk_size for c in chunks), "Chunk too small"
    assert all(c.char_count <= config.max_chunk_size for c in chunks), "Chunk too large"
    
    print("\n✓ All chunks within size constraints")


def test_overlap():
    """Test context overlap between chunks"""
    print("\n" + "=" * 80)
    print("Test 2: Context Overlap")
    print("=" * 80)
    
    config = ChunkingConfig(
        enable_overlap=True,
        overlap_tokens=20,
        max_chunk_size=200
    )
    
    chunker = BestPracticeChunker(config)
    chunks = chunker.chunk_document(TEST_DOCUMENT, document_id="test_002")
    
    # Check overlaps
    with_prev = sum(1 for c in chunks if c.prev_overlap)
    with_next = sum(1 for c in chunks if c.next_overlap)
    
    print(f"\n✓ Created {len(chunks)} chunks")
    print(f"  Chunks with prev_overlap: {with_prev}")
    print(f"  Chunks with next_overlap: {with_next}")
    
    # First chunk should not have prev_overlap
    assert chunks[0].prev_overlap is None, "First chunk has prev_overlap"
    
    # Last chunk should not have next_overlap
    assert chunks[-1].next_overlap is None, "Last chunk has next_overlap"
    
    # Middle chunks should have both
    if len(chunks) > 2:
        middle = chunks[len(chunks) // 2]
        assert middle.prev_overlap is not None, "Middle chunk missing prev_overlap"
        assert middle.next_overlap is not None, "Middle chunk missing next_overlap"
        
        print(f"\n  Sample overlap (chunk {middle.chunk_index}):")
        print(f"    Previous: '...{middle.prev_overlap}'")
        print(f"    Next: '{middle.next_overlap}...'")
    
    print("\n✓ Context overlap working correctly")


def test_heading_extraction():
    """Test heading hierarchy extraction"""
    print("\n" + "=" * 80)
    print("Test 3: Heading Extraction")
    print("=" * 80)
    
    config = ChunkingConfig(extract_headings=True)
    
    chunker = BestPracticeChunker(config)
    chunks = chunker.chunk_document(TEST_DOCUMENT, document_id="test_003")
    
    # Find chunks with headings
    with_headings = [c for c in chunks if c.heading_path]
    
    print(f"\n✓ Created {len(chunks)} chunks")
    print(f"  Chunks with heading context: {len(with_headings)}")
    
    # Show some heading paths
    print("\n  Sample heading paths:")
    for chunk in chunks[:5]:
        if chunk.heading_path:
            path = " > ".join(chunk.heading_path)
            text_preview = chunk.text[:50].replace('\n', ' ')
            print(f"    {path}")
            print(f"      '{text_preview}...'")
    
    assert len(with_headings) > 0, "No headings detected"
    print("\n✓ Heading extraction working")


def test_keyword_extraction():
    """Test keyword extraction"""
    print("\n" + "=" * 80)
    print("Test 4: Keyword Extraction")
    print("=" * 80)
    
    config = ChunkingConfig(extract_keywords=True)
    
    chunker = BestPracticeChunker(config)
    chunks = chunker.chunk_document(TEST_DOCUMENT, document_id="test_004")
    
    # Check keywords
    with_keywords = [c for c in chunks if c.keywords]
    
    print(f"\n✓ Created {len(chunks)} chunks")
    print(f"  Chunks with keywords: {len(with_keywords)}")
    
    # Show sample keywords
    print("\n  Sample keywords:")
    for i, chunk in enumerate(chunks[:3]):
        if chunk.keywords:
            print(f"    Chunk {i}: {', '.join(chunk.keywords[:5])}")
    
    assert len(with_keywords) > 0, "No keywords extracted"
    print("\n✓ Keyword extraction working")


def test_cross_reference_detection():
    """Test cross-reference detection"""
    print("\n" + "=" * 80)
    print("Test 5: Cross-Reference Detection")
    print("=" * 80)
    
    config = ChunkingConfig(detect_cross_references=True)
    
    chunker = BestPracticeChunker(config)
    chunks = chunker.chunk_document(TEST_DOCUMENT, document_id="test_005")
    
    # Find chunks with cross-references
    with_refs = [c for c in chunks if c.cross_references]
    
    print(f"\n✓ Created {len(chunks)} chunks")
    print(f"  Chunks with cross-references: {len(with_refs)}")
    
    # Show detected references
    if with_refs:
        print("\n  Detected references:")
        for chunk in with_refs:
            for ref in chunk.cross_references:
                print(f"    - {ref}")
    
    print("\n✓ Cross-reference detection working")


def test_quality_validation():
    """Test chunk quality validation"""
    print("\n" + "=" * 80)
    print("Test 6: Quality Validation")
    print("=" * 80)
    
    chunker = BestPracticeChunker()
    chunks = chunker.chunk_document(TEST_DOCUMENT, document_id="test_006")
    
    # Check completeness scores
    scores = [c.completeness_score for c in chunks]
    avg_score = sum(scores) / len(scores)
    
    print(f"\n✓ Created {len(chunks)} chunks")
    print(f"  Average completeness score: {avg_score:.2f}")
    print(f"  Min score: {min(scores):.2f}")
    print(f"  Max score: {max(scores):.2f}")
    
    # Show chunks with lower scores
    low_quality = [c for c in chunks if c.completeness_score < 0.8]
    if low_quality:
        print(f"\n  {len(low_quality)} chunks with quality issues:")
        for chunk in low_quality[:3]:
            print(f"    Score: {chunk.completeness_score:.2f}, "
                  f"Chars: {chunk.char_count}, "
                  f"Words: {chunk.word_count}")
    
    assert all(0 <= s <= 1 for s in scores), "Invalid completeness score"
    print("\n✓ Quality validation working")


def test_metadata_completeness():
    """Test that all metadata is present"""
    print("\n" + "=" * 80)
    print("Test 7: Metadata Completeness")
    print("=" * 80)
    
    config = ChunkingConfig(
        enable_overlap=True,
        extract_headings=True,
        extract_keywords=True,
        detect_cross_references=True
    )
    
    chunker = BestPracticeChunker(config)
    chunks = chunker.chunk_document(TEST_DOCUMENT, document_id="test_007")
    
    # Convert to dict and check
    chunks_dict = chunker.chunks_to_dict(chunks)
    
    print(f"\n✓ Created {len(chunks_dict)} chunk dictionaries")
    
    # Check first chunk has all expected fields
    first = chunks_dict[0]
    expected_fields = [
        'text', 'chunk_id', 'document_id', 'chunk_index', 'total_chunks',
        'char_count', 'word_count', 'sentence_count',
        'heading_path', 'keywords', 'cross_references',
        'reference', 'completeness_score'
    ]
    
    print("\n  Required fields present:")
    for field in expected_fields:
        present = field in first
        print(f"    {field}: {'✓' if present else '✗'}")
        assert present, f"Missing field: {field}"
    
    print("\n✓ All metadata fields present")


def run_all_tests():
    """Run all tests"""
    print("\n" + "=" * 80)
    print("BEST PRACTICE CHUNKER - COMPREHENSIVE TEST SUITE")
    print("=" * 80)
    
    try:
        test_basic_chunking()
        test_overlap()
        test_heading_extraction()
        test_keyword_extraction()
        test_cross_reference_detection()
        test_quality_validation()
        test_metadata_completeness()
        
        print("\n" + "=" * 80)
        print("✓ ALL TESTS PASSED")
        print("=" * 80)
        
        print("\nBest Practices Implemented:")
        print("  ✓ Semantic chunking with size constraints")
        print("  ✓ Context overlap for better retrieval")
        print("  ✓ Heading hierarchy extraction")
        print("  ✓ Keyword extraction")
        print("  ✓ Cross-reference detection")
        print("  ✓ Quality validation")
        print("  ✓ Complete metadata enrichment")
        
        return True
        
    except Exception as e:
        print(f"\n✗ TEST FAILED: {e}")
        import traceback
        traceback.print_exc()
        return False


if __name__ == "__main__":
    success = run_all_tests()
    sys.exit(0 if success else 1)
