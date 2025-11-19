#!/usr/bin/env python3
"""
End-to-end test of legal text processing through the ingestion pipeline.

This test simulates uploading a legal text and verifies that:
1. The text is detected as legal
2. Hierarchical chunking is applied
3. Legal metadata is preserved
4. The chunks can be used for embedding and storage
"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from backend.ingestion import create_smart_chunks

# Sample BImSchG text
BIMSCHG_SAMPLE = """§ 1 Zweck des Gesetzes

(1) Zweck dieses Gesetzes ist es, Menschen, Tiere und Pflanzen, den Boden, das Wasser, die Atmosphäre sowie Kultur- und sonstige Sachgüter vor schädlichen Umwelteinwirkungen zu schützen und dem Entstehen schädlicher Umwelteinwirkungen vorzubeugen.

(2) Soweit es sich um genehmigungsbedürftige Anlagen handelt, dient dieses Gesetz auch
1. der integrierten Vermeidung und Verminderung schädlicher Umwelteinwirkungen durch Emissionen in Luft, Wasser und Boden unter Einbeziehung der Abfallwirtschaft, um ein hohes Schutzniveau für die Umwelt insgesamt zu erreichen, sowie
2. dem Schutz und der Vorsorge gegen Gefahren, erhebliche Nachteile und erhebliche Belästigungen, die auf andere Weise herbeigeführt werden.

§ 2 Geltungsbereich

(1) Die Vorschriften dieses Gesetzes gelten für Anlagen, soweit sie nicht in Absatz 2 ausgenommen sind.

(2) Ausgenommen sind
1. Anlagen, die der Verteidigung dienen,
2. Anlagen im Sinne der StVO.

§ 3 Begriffsbestimmungen

Zum Zweck dieses Gesetzes gelten folgende Begriffsbestimmungen:
1. Anlagen sind
   a) Betriebsstätten und sonstige ortsfeste Einrichtungen,
   b) Maschinen, Geräte und sonstige ortsveränderliche technische Einrichtungen,
   c) Grundstücke, auf denen Stoffe gelagert werden.
2. Emissionen sind die von einer Anlage ausgehenden Luftverunreinigungen.
"""

REGULAR_DOCUMENT = """
This is a regular business document.
It contains information about our company operations.
There are no legal paragraphs or special structure here.
Just plain text in paragraphs.
"""

def test_legal_text_chunking():
    """Test that legal text gets smart chunking"""
    print("=" * 80)
    print("Test: Legal Text Smart Chunking (BImSchG)")
    print("=" * 80)
    
    chunks = create_smart_chunks(
        content=BIMSCHG_SAMPLE,
        file_path="BImSchG.txt",
        classification="GESETZ"
    )
    
    print(f"\n✓ Created {len(chunks)} chunks")
    
    # Check that we got structure-based chunks
    legal_chunks = [c for c in chunks if c['metadata'].get('chunk_type') == 'legal_structure']
    simple_chunks = [c for c in chunks if c['metadata'].get('chunk_type') == 'simple']
    
    print(f"  - Legal structure chunks: {len(legal_chunks)}")
    print(f"  - Simple chunks: {len(simple_chunks)}")
    
    assert len(legal_chunks) > 0, "No legal structure chunks created!"
    assert len(simple_chunks) == 0, "Should not have simple chunks for legal text"
    
    # Check that chunks have legal metadata
    print("\n✓ Checking chunk metadata:")
    for i, chunk in enumerate(chunks[:3]):
        meta = chunk['metadata']
        print(f"\n  Chunk {i+1}:")
        print(f"    Reference: {meta.get('reference', 'N/A')}")
        print(f"    Paragraph: {meta.get('paragraph', 'N/A')}")
        print(f"    Level: {meta.get('level', 'N/A')}")
        print(f"    Text preview: {chunk['text'][:80]}...")
    
    # Verify specific chunks exist
    print("\n✓ Verifying specific legal elements:")
    
    # Should have § 1 Abs. 1
    has_para_1_abs_1 = any(
        c['metadata'].get('paragraph') == '§ 1' and c['metadata'].get('absatz') == 1
        for c in chunks
    )
    print(f"  - Has § 1 Abs. 1: {has_para_1_abs_1}")
    assert has_para_1_abs_1, "Missing § 1 Abs. 1"
    
    # Should have § 1 Abs. 2 Nr. 1
    has_para_1_abs_2_nr_1 = any(
        c['metadata'].get('paragraph') == '§ 1' and 
        c['metadata'].get('absatz') == 2 and
        c['metadata'].get('nummer') == 1
        for c in chunks
    )
    print(f"  - Has § 1 Abs. 2 Nr. 1: {has_para_1_abs_2_nr_1}")
    assert has_para_1_abs_2_nr_1, "Missing § 1 Abs. 2 Nr. 1"
    
    # Should have Buchstaben (a, b, c)
    buchstaben = set(
        c['metadata'].get('buchstabe')
        for c in chunks
        if c['metadata'].get('buchstabe')
    )
    print(f"  - Buchstaben found: {sorted(buchstaben)}")
    assert 'a' in buchstaben, "Missing Buchstabe a"
    assert 'b' in buchstaben, "Missing Buchstabe b"
    assert 'c' in buchstaben, "Missing Buchstabe c"
    
    print("\n✓ All legal structure elements present")
    return chunks


def test_regular_document_chunking():
    """Test that regular documents get simple chunking"""
    print("\n" + "=" * 80)
    print("Test: Regular Document Simple Chunking")
    print("=" * 80)
    
    chunks = create_smart_chunks(
        content=REGULAR_DOCUMENT,
        file_path="business_doc.txt",
        classification="DOCUMENT"
    )
    
    print(f"\n✓ Created {len(chunks)} chunks")
    
    # Check that we got simple chunks
    legal_chunks = [c for c in chunks if c['metadata'].get('chunk_type') == 'legal_structure']
    simple_chunks = [c for c in chunks if c['metadata'].get('chunk_type') == 'simple']
    
    print(f"  - Legal structure chunks: {len(legal_chunks)}")
    print(f"  - Simple chunks: {len(simple_chunks)}")
    
    assert len(simple_chunks) > 0, "No simple chunks created!"
    assert len(legal_chunks) == 0, "Should not have legal chunks for regular text"
    
    print("\n✓ Regular document correctly uses simple chunking")
    return chunks


def test_chunk_format():
    """Test that chunks are in the correct format for embedding"""
    print("\n" + "=" * 80)
    print("Test: Chunk Format for Embedding")
    print("=" * 80)
    
    chunks = create_smart_chunks(
        content=BIMSCHG_SAMPLE,
        file_path="BImSchG.txt",
        classification="GESETZ"
    )
    
    print("\n✓ Checking chunk structure:")
    
    for chunk in chunks:
        # Each chunk should have these keys
        assert 'text' in chunk, "Chunk missing 'text' key"
        assert 'index' in chunk, "Chunk missing 'index' key"
        assert 'metadata' in chunk, "Chunk missing 'metadata' key"
        
        # Text should be a string
        assert isinstance(chunk['text'], str), "Chunk text is not a string"
        assert len(chunk['text']) > 0, "Chunk text is empty"
        
        # Metadata should be a dict
        assert isinstance(chunk['metadata'], dict), "Chunk metadata is not a dict"
    
    print(f"  - All {len(chunks)} chunks have correct structure")
    print(f"  - All chunks have non-empty text")
    print(f"  - All chunks have metadata dict")
    
    print("\n✓ Chunk format is correct for embedding pipeline")


if __name__ == "__main__":
    try:
        print("\n" + "=" * 80)
        print("END-TO-END LEGAL TEXT INTEGRATION TEST")
        print("=" * 80)
        
        legal_chunks = test_legal_text_chunking()
        regular_chunks = test_regular_document_chunking()
        test_chunk_format()
        
        print("\n" + "=" * 80)
        print("✓ ALL INTEGRATION TESTS PASSED")
        print("=" * 80)
        
        print(f"\nSummary:")
        print(f"  - Legal text (BImSchG): {len(legal_chunks)} structure-based chunks")
        print(f"  - Regular document: {len(regular_chunks)} simple chunks")
        print(f"  - Chunk format validated for embedding pipeline")
        
        sys.exit(0)
        
    except Exception as e:
        print(f"\n✗ TEST FAILED: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
