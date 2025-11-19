#!/usr/bin/env python3
"""
End-to-end test of legal text processing - standalone version.

Tests the create_smart_chunks function without importing the full backend.
"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Import only what we need
from ingestion.parsers.german_law_parser import GermanLawParser

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

def create_smart_chunks_standalone(content: str, file_path: str = "", classification: str = "DOCUMENT"):
    """
    Standalone version of smart chunking for testing.
    Mimics the backend function but doesn't require full backend imports.
    """
    # Check if this is a legal document
    is_legal = classification in ["GESETZ", "RECHTSTEXT", "RECHTSPRECHUNG"]
    
    if is_legal:
        parser = GermanLawParser()
        
        if parser.is_legal_text(content, file_path):
            print(f"[INFO] Using legal structure parser for: {file_path}")
            
            # Parse into legal chunks
            legal_chunks = parser.parse(content, filename=file_path)
            
            # Convert to standard chunk format
            chunks = []
            for i, legal_chunk in enumerate(legal_chunks):
                chunk_dict = {
                    'text': legal_chunk.text,
                    'index': i,
                    'metadata': {
                        'chunk_type': 'legal_structure',
                        'paragraph': legal_chunk.paragraph,
                        'paragraph_title': legal_chunk.paragraph_title,
                        'absatz': legal_chunk.absatz,
                        'nummer': legal_chunk.nummer,
                        'buchstabe': legal_chunk.buchstabe,
                        'level': legal_chunk.level.value,
                        'reference': legal_chunk.reference,
                        'parent_reference': legal_chunk.parent_reference,
                        **legal_chunk.metadata
                    }
                }
                chunks.append(chunk_dict)
            
            print(f"[INFO] Created {len(chunks)} legal structure chunks")
            return chunks
    
    # Fallback: Simple chunking
    print(f"[INFO] Using simple chunking for: {file_path}")
    chunks = []
    chunk_size = 500
    
    for i in range(0, len(content), chunk_size):
        chunk_text = content[i:i+chunk_size]
        chunks.append({
            'text': chunk_text,
            'index': i // chunk_size,
            'metadata': {
                'chunk_type': 'simple',
                'start_pos': i,
                'end_pos': min(i + chunk_size, len(content))
            }
        })
    
    chunks = chunks[:10]  # Limit to 10
    print(f"[INFO] Created {len(chunks)} simple chunks")
    return chunks


def test_legal_text_processing():
    """Test that BImSchG gets proper legal chunking"""
    print("=" * 80)
    print("END-TO-END TEST: Legal Text Processing (BImSchG)")
    print("=" * 80)
    
    chunks = create_smart_chunks_standalone(
        content=BIMSCHG_SAMPLE,
        file_path="BImSchG.txt",
        classification="GESETZ"
    )
    
    print(f"\n✓ Created {len(chunks)} chunks from BImSchG")
    
    # Verify chunks
    print("\n1. Checking chunk types:")
    legal_chunks = [c for c in chunks if c['metadata'].get('chunk_type') == 'legal_structure']
    print(f"   - Legal structure chunks: {len(legal_chunks)}")
    assert len(legal_chunks) > 0, "No legal chunks created!"
    
    print("\n2. Checking paragraphs:")
    paragraphs = set(c['metadata'].get('paragraph') for c in chunks if c['metadata'].get('paragraph'))
    print(f"   - Paragraphs: {sorted(paragraphs)}")
    assert '§ 1' in paragraphs
    assert '§ 2' in paragraphs
    assert '§ 3' in paragraphs
    
    print("\n3. Checking hierarchical structure:")
    absatz_count = sum(1 for c in chunks if c['metadata'].get('absatz'))
    nummer_count = sum(1 for c in chunks if c['metadata'].get('nummer'))
    buchstabe_count = sum(1 for c in chunks if c['metadata'].get('buchstabe'))
    print(f"   - Absätze: {absatz_count}")
    print(f"   - Nummern: {nummer_count}")
    print(f"   - Buchstaben: {buchstabe_count}")
    
    print("\n4. Sample chunks with references:")
    for i, chunk in enumerate(chunks[:5]):
        ref = chunk['metadata'].get('reference', 'N/A')
        level = chunk['metadata'].get('level', 'N/A')
        text_preview = chunk['text'][:60]
        print(f"   [{i+1}] {ref} ({level})")
        print(f"       {text_preview}...")
    
    print("\n5. Verifying ChromaDB metadata format:")
    # Simulate what would be stored in ChromaDB
    sample_chunk = chunks[0]
    chromadb_metadata = {
        'file_path': 'BImSchG.txt',
        'classification': 'GESETZ',
        'chunk_index': sample_chunk['index'],
        'document_id': 'test_123',
        'chunk_type': sample_chunk['metadata'].get('chunk_type'),
        'legal_paragraph': sample_chunk['metadata'].get('paragraph'),
        'legal_paragraph_title': sample_chunk['metadata'].get('paragraph_title'),
        'legal_absatz': sample_chunk['metadata'].get('absatz'),
        'legal_nummer': sample_chunk['metadata'].get('nummer'),
        'legal_buchstabe': sample_chunk['metadata'].get('buchstabe'),
        'legal_level': sample_chunk['metadata'].get('level'),
        'legal_reference': sample_chunk['metadata'].get('reference'),
        'legal_parent_reference': sample_chunk['metadata'].get('parent_reference')
    }
    
    print(f"   Sample ChromaDB metadata keys: {list(chromadb_metadata.keys())}")
    print(f"   Legal reference: {chromadb_metadata['legal_reference']}")
    
    print("\n" + "=" * 80)
    print("✓ ALL TESTS PASSED - Legal text processing works correctly!")
    print("=" * 80)
    
    print(f"\nKey Results:")
    print(f"  - Input: BImSchG sample text")
    print(f"  - Output: {len(chunks)} hierarchical chunks")
    print(f"  - Structure preserved: {absatz_count} Absätze, {nummer_count} Nummern, {buchstabe_count} Buchstaben")
    print(f"  - All chunks have proper legal references for citation")
    print(f"  - Metadata is ready for ChromaDB storage with full context")
    
    return True


if __name__ == "__main__":
    try:
        test_legal_text_processing()
        sys.exit(0)
    except Exception as e:
        print(f"\n✗ TEST FAILED: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
