#!/usr/bin/env python3
"""
Tests for German Law Parser

Tests the hierarchical parsing of German legal texts including
BImSchG-style documents with § paragraphs, Absätze, Nummern, and Buchstaben.
"""

import pytest
from ingestion.parsers.german_law_parser import (
    GermanLawParser,
    LegalTextChunk,
    LegalTextType,
    StructureLevel,
    parse_german_law
)


# Sample BImSchG text for testing
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

NON_LEGAL_TEXT = """
This is a regular document that does not contain legal structure.
It has paragraphs and sentences, but no § symbols or legal formatting.
This should not be parsed as a legal text.
"""


class TestGermanLawParser:
    """Test suite for German Law Parser"""
    
    def test_parser_initialization(self):
        """Test parser can be initialized"""
        parser = GermanLawParser()
        assert parser is not None
        assert parser.enable_sentence_splitting is True
    
    def test_is_legal_text_detects_bimschg(self):
        """Test legal text detection with BImSchG sample"""
        parser = GermanLawParser()
        assert parser.is_legal_text(BIMSCHG_SAMPLE, "BImSchG.txt") is True
    
    def test_is_legal_text_rejects_non_legal(self):
        """Test legal text detection rejects non-legal text"""
        parser = GermanLawParser()
        assert parser.is_legal_text(NON_LEGAL_TEXT, "regular.txt") is False
    
    def test_detect_document_type_gesetz(self):
        """Test document type detection for Gesetz"""
        parser = GermanLawParser()
        doc_type = parser.detect_document_type(BIMSCHG_SAMPLE, "BImSchG.txt")
        assert doc_type == LegalTextType.GESETZ
    
    def test_parse_bimschg_basic(self):
        """Test basic parsing of BImSchG sample"""
        parser = GermanLawParser()
        chunks = parser.parse(BIMSCHG_SAMPLE, "BImSchG.txt")
        
        # Should create multiple chunks
        assert len(chunks) > 0
        
        # All chunks should be LegalTextChunk objects
        assert all(isinstance(chunk, LegalTextChunk) for chunk in chunks)
    
    def test_parse_bimschg_paragraphs(self):
        """Test that parser detects all § paragraphs"""
        parser = GermanLawParser()
        chunks = parser.parse(BIMSCHG_SAMPLE, "BImSchG.txt")
        
        # Extract unique paragraphs
        paragraphs = set(chunk.paragraph for chunk in chunks if chunk.paragraph)
        
        # Should detect § 1, § 2, § 3
        assert "§ 1" in paragraphs
        assert "§ 2" in paragraphs
        assert "§ 3" in paragraphs
    
    def test_parse_bimschg_paragraph_titles(self):
        """Test that parser extracts paragraph titles"""
        parser = GermanLawParser()
        chunks = parser.parse(BIMSCHG_SAMPLE, "BImSchG.txt")
        
        # Find § 1 chunks
        para_1_chunks = [c for c in chunks if c.paragraph == "§ 1"]
        
        # Should have title "Zweck des Gesetzes"
        assert any(c.paragraph_title == "Zweck des Gesetzes" for c in para_1_chunks)
    
    def test_parse_bimschg_absaetze(self):
        """Test that parser detects Absätze (subsections)"""
        parser = GermanLawParser()
        chunks = parser.parse(BIMSCHG_SAMPLE, "BImSchG.txt")
        
        # Find chunks with Absatz information
        absatz_chunks = [c for c in chunks if c.absatz is not None]
        
        # Should have multiple Absätze
        assert len(absatz_chunks) > 0
        
        # Check for § 1 Abs. 1 and § 1 Abs. 2
        para_1_abs_1 = [c for c in chunks if c.paragraph == "§ 1" and c.absatz == 1]
        para_1_abs_2 = [c for c in chunks if c.paragraph == "§ 1" and c.absatz == 2]
        
        assert len(para_1_abs_1) > 0
        assert len(para_1_abs_2) > 0
    
    def test_parse_bimschg_nummern(self):
        """Test that parser detects numbered items (Nummern)"""
        parser = GermanLawParser()
        chunks = parser.parse(BIMSCHG_SAMPLE, "BImSchG.txt")
        
        # Find chunks with Nummer information
        nummer_chunks = [c for c in chunks if c.nummer is not None]
        
        # Should have numbered items
        assert len(nummer_chunks) > 0
        
        # § 1 Abs. 2 should have Nr. 1 and Nr. 2
        para_1_abs_2_nr_1 = [
            c for c in chunks 
            if c.paragraph == "§ 1" and c.absatz == 2 and c.nummer == 1
        ]
        assert len(para_1_abs_2_nr_1) > 0
    
    def test_parse_bimschg_buchstaben(self):
        """Test that parser detects lettered sub-items (Buchstaben)"""
        parser = GermanLawParser()
        chunks = parser.parse(BIMSCHG_SAMPLE, "BImSchG.txt")
        
        # Find chunks with Buchstabe information
        buchstabe_chunks = [c for c in chunks if c.buchstabe is not None]
        
        # Should have lettered items (a, b, c in § 3 Nr. 1)
        assert len(buchstabe_chunks) > 0
        
        # Check for specific letters
        assert any(c.buchstabe == "a" for c in buchstabe_chunks)
        assert any(c.buchstabe == "b" for c in buchstabe_chunks)
        assert any(c.buchstabe == "c" for c in buchstabe_chunks)
    
    def test_parse_bimschg_references(self):
        """Test that chunks have proper reference paths"""
        parser = GermanLawParser()
        chunks = parser.parse(BIMSCHG_SAMPLE, "BImSchG.txt")
        
        # All chunks should have a reference
        assert all(chunk.reference for chunk in chunks)
        
        # Find a specific chunk and check its reference
        para_1_abs_2_nr_1 = next(
            (c for c in chunks 
             if c.paragraph == "§ 1" and c.absatz == 2 and c.nummer == 1),
            None
        )
        
        if para_1_abs_2_nr_1:
            # Reference should contain all hierarchical elements
            assert "§ 1" in para_1_abs_2_nr_1.reference
            assert "Abs. 2" in para_1_abs_2_nr_1.reference
            assert "Nr. 1" in para_1_abs_2_nr_1.reference
    
    def test_parse_bimschg_metadata(self):
        """Test that chunks have proper metadata"""
        parser = GermanLawParser()
        chunks = parser.parse(BIMSCHG_SAMPLE, "BImSchG.txt", document_id="test_123")
        
        # All chunks should have metadata
        assert all(chunk.metadata for chunk in chunks)
        
        # Check metadata content
        first_chunk = chunks[0]
        assert first_chunk.metadata.get('filename') == "BImSchG.txt"
        assert first_chunk.metadata.get('document_id') == "test_123"
        assert first_chunk.metadata.get('document_type') == "Gesetz"
    
    def test_parse_bimschg_structure_levels(self):
        """Test that different structure levels are detected"""
        parser = GermanLawParser()
        chunks = parser.parse(BIMSCHG_SAMPLE, "BImSchG.txt")
        
        # Extract unique levels
        levels = set(chunk.level for chunk in chunks)
        
        # Should have multiple structure levels
        assert len(levels) > 1
        assert StructureLevel.ABSATZ in levels
        assert StructureLevel.NUMMER in levels
        assert StructureLevel.BUCHSTABE in levels
    
    def test_chunks_to_dict_conversion(self):
        """Test conversion of chunks to dictionary format"""
        parser = GermanLawParser()
        chunks = parser.parse(BIMSCHG_SAMPLE, "BImSchG.txt")
        
        # Convert to dict
        chunks_dict = parser.chunks_to_dict(chunks)
        
        # Should be list of dicts
        assert isinstance(chunks_dict, list)
        assert len(chunks_dict) == len(chunks)
        assert all(isinstance(chunk_dict, dict) for chunk_dict in chunks_dict)
        
        # Check dict structure
        first_dict = chunks_dict[0]
        assert 'text' in first_dict
        assert 'paragraph' in first_dict
        assert 'level' in first_dict
        assert 'reference' in first_dict
        assert 'metadata' in first_dict
    
    def test_parse_non_legal_text_fallback(self):
        """Test that non-legal text returns single chunk"""
        parser = GermanLawParser()
        chunks = parser.parse(NON_LEGAL_TEXT, "regular.txt")
        
        # Should return single chunk with full text
        assert len(chunks) == 1
        assert chunks[0].text == NON_LEGAL_TEXT
        assert chunks[0].metadata.get('is_legal_text') is False
    
    def test_convenience_function(self):
        """Test the convenience parse_german_law function"""
        chunks = parse_german_law(BIMSCHG_SAMPLE, "BImSchG.txt", "test_doc")
        
        assert len(chunks) > 0
        assert all(isinstance(chunk, LegalTextChunk) for chunk in chunks)
    
    def test_parent_references(self):
        """Test that parent references are correctly set"""
        parser = GermanLawParser()
        chunks = parser.parse(BIMSCHG_SAMPLE, "BImSchG.txt")
        
        # Find a Nummer chunk
        nummer_chunk = next(
            (c for c in chunks if c.nummer is not None and c.absatz is not None),
            None
        )
        
        if nummer_chunk:
            # Parent should be the Absatz
            assert nummer_chunk.parent_reference
            assert "§" in nummer_chunk.parent_reference
            assert "Abs." in nummer_chunk.parent_reference
        
        # Find a Buchstabe chunk
        buchstabe_chunk = next(
            (c for c in chunks if c.buchstabe is not None),
            None
        )
        
        if buchstabe_chunk:
            # Parent should be the Nummer
            assert buchstabe_chunk.parent_reference
            assert "Nr." in buchstabe_chunk.parent_reference
    
    def test_legal_text_detection_by_filename(self):
        """Test detection based on filename patterns"""
        parser = GermanLawParser()
        
        # Should detect based on filename alone
        assert parser.is_legal_text("Some text", "bundesgesetz.pdf") is True
        assert parser.is_legal_text("Some text", "verordnung.pdf") is True
        assert parser.is_legal_text("Some text", "regular_doc.pdf") is False
    
    def test_chunk_text_content(self):
        """Test that chunk text contains expected content"""
        parser = GermanLawParser()
        chunks = parser.parse(BIMSCHG_SAMPLE, "BImSchG.txt")
        
        # Find § 1 Abs. 1
        para_1_abs_1 = next(
            (c for c in chunks if c.paragraph == "§ 1" and c.absatz == 1),
            None
        )
        
        assert para_1_abs_1 is not None
        assert "Zweck dieses Gesetzes" in para_1_abs_1.text
        assert "Menschen, Tiere und Pflanzen" in para_1_abs_1.text


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
