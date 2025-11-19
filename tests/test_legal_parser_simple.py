#!/usr/bin/env python3
"""
Simple test script for German Law Parser
Tests basic functionality without pytest
"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from ingestion.parsers.german_law_parser import GermanLawParser, LegalTextType, StructureLevel

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

def test_parser():
    """Run basic tests on the parser"""
    print("=" * 80)
    print("German Law Parser - Basic Functionality Test")
    print("=" * 80)
    
    parser = GermanLawParser()
    print("✓ Parser initialized")
    
    # Test 1: Legal text detection
    print("\nTest 1: Legal text detection")
    is_legal = parser.is_legal_text(BIMSCHG_SAMPLE, "BImSchG.txt")
    print(f"  Is legal text: {is_legal}")
    assert is_legal, "Failed to detect legal text"
    print("  ✓ Legal text detection works")
    
    # Test 2: Document type detection
    print("\nTest 2: Document type detection")
    doc_type = parser.detect_document_type(BIMSCHG_SAMPLE, "BImSchG.txt")
    print(f"  Document type: {doc_type.value}")
    assert doc_type == LegalTextType.GESETZ, "Failed to detect Gesetz type"
    print("  ✓ Document type detection works")
    
    # Test 3: Parse structure
    print("\nTest 3: Parse hierarchical structure")
    chunks = parser.parse(BIMSCHG_SAMPLE, "BImSchG.txt", "test_doc")
    print(f"  Total chunks created: {len(chunks)}")
    assert len(chunks) > 0, "No chunks created"
    print("  ✓ Parsing creates chunks")
    
    # Test 4: Check paragraphs
    print("\nTest 4: Check § paragraphs")
    paragraphs = set(c.paragraph for c in chunks if c.paragraph)
    print(f"  Paragraphs found: {sorted(paragraphs)}")
    assert "§ 1" in paragraphs, "§ 1 not found"
    assert "§ 2" in paragraphs, "§ 2 not found"
    assert "§ 3" in paragraphs, "§ 3 not found"
    print("  ✓ All paragraphs detected")
    
    # Test 5: Check Absätze
    print("\nTest 5: Check Absätze (subsections)")
    absatz_chunks = [c for c in chunks if c.absatz is not None]
    print(f"  Absatz chunks: {len(absatz_chunks)}")
    assert len(absatz_chunks) > 0, "No Absätze found"
    print("  ✓ Absätze detected")
    
    # Test 6: Check Nummern
    print("\nTest 6: Check numbered items (Nummern)")
    nummer_chunks = [c for c in chunks if c.nummer is not None]
    print(f"  Nummer chunks: {len(nummer_chunks)}")
    assert len(nummer_chunks) > 0, "No Nummern found"
    print("  ✓ Nummern detected")
    
    # Test 7: Check Buchstaben
    print("\nTest 7: Check lettered items (Buchstaben)")
    buchstabe_chunks = [c for c in chunks if c.buchstabe is not None]
    print(f"  Buchstabe chunks: {len(buchstabe_chunks)}")
    assert len(buchstabe_chunks) > 0, "No Buchstaben found"
    
    buchstaben = set(c.buchstabe for c in buchstabe_chunks)
    print(f"  Letters found: {sorted(buchstaben)}")
    assert "a" in buchstaben, "Letter a not found"
    print("  ✓ Buchstaben detected")
    
    # Test 8: Check references
    print("\nTest 8: Check legal references")
    sample_chunk = next((c for c in chunks if c.absatz and c.nummer), None)
    if sample_chunk:
        print(f"  Sample reference: {sample_chunk.reference}")
        assert "§" in sample_chunk.reference, "Reference missing §"
        assert "Abs." in sample_chunk.reference, "Reference missing Abs."
        print("  ✓ References properly formatted")
    
    # Test 9: Display sample chunks
    print("\nTest 9: Sample chunk details")
    print("\n  Sample chunks:")
    for i, chunk in enumerate(chunks[:5]):
        print(f"\n  Chunk {i+1}:")
        print(f"    Reference: {chunk.reference}")
        print(f"    Level: {chunk.level.value}")
        print(f"    Text preview: {chunk.text[:80]}...")
    
    # Test 10: Metadata
    print("\nTest 10: Check metadata")
    first_chunk = chunks[0]
    print(f"  Metadata keys: {list(first_chunk.metadata.keys())}")
    assert 'filename' in first_chunk.metadata, "Metadata missing filename"
    assert 'document_type' in first_chunk.metadata, "Metadata missing document_type"
    print("  ✓ Metadata present")
    
    print("\n" + "=" * 80)
    print("✓ ALL TESTS PASSED")
    print("=" * 80)
    
    return chunks


if __name__ == "__main__":
    try:
        chunks = test_parser()
        print(f"\nSuccessfully parsed {len(chunks)} chunks from BImSchG sample")
        sys.exit(0)
    except Exception as e:
        print(f"\n✗ TEST FAILED: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
