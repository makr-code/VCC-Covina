#!/usr/bin/env python3
"""
German Law Parser - Hierarchical Structure Parser for German Legal Texts
=========================================================================

Parses German legal documents (Gesetze, Verordnungen, etc.) into their
hierarchical structure:

Structure Hierarchy:
1. § (Paragraph) - Top level section
2. (1), (2), ... (Absatz) - Subsections within a paragraph
3. 1., 2., ... (Nummer) - Numbered items within a subsection
4. a), b), ... (Buchstabe) - Lettered sub-items
5. Sätze (Sentences) - Individual sentences within any level

Example BImSchG:
    § 1 Zweck des Gesetzes
    (1) Zweck dieses Gesetzes ist es, ...
    (2) Soweit es sich um ... handelt, dient dieses Gesetz auch
    1. der integrierten Vermeidung ...
    2. dem Schutz und der Vorsorge ...

Author: Covina System
Date: November 2025
"""

import re
import logging
from dataclasses import dataclass, field
from typing import List, Optional, Dict, Any
from enum import Enum

logger = logging.getLogger(__name__)


class LegalTextType(Enum):
    """Types of German legal documents"""
    GESETZ = "Gesetz"  # Law
    VERORDNUNG = "Verordnung"  # Regulation
    SATZUNG = "Satzung"  # Statute
    RICHTLINIE = "Richtlinie"  # Directive
    BESCHLUSS = "Beschluss"  # Resolution
    UNKNOWN = "Unknown"


class StructureLevel(Enum):
    """Hierarchical levels in German legal texts"""
    PARAGRAPH = "paragraph"  # § 1, § 2, etc.
    ABSATZ = "absatz"  # (1), (2), etc.
    NUMMER = "nummer"  # 1., 2., etc.
    BUCHSTABE = "buchstabe"  # a), b), etc.
    SATZ = "satz"  # Individual sentence


@dataclass
class LegalTextChunk:
    """
    A semantic chunk from a legal text with structural metadata.
    
    This preserves the hierarchical context for better understanding
    and retrieval of legal provisions.
    """
    # Content
    text: str
    
    # Structural identifiers
    paragraph: Optional[str] = None  # e.g., "§ 1"
    paragraph_title: Optional[str] = None  # e.g., "Zweck des Gesetzes"
    absatz: Optional[int] = None  # e.g., 1, 2, 3
    nummer: Optional[int] = None  # e.g., 1, 2, 3
    buchstabe: Optional[str] = None  # e.g., "a", "b", "c"
    satz: Optional[int] = None  # e.g., 1, 2, 3
    
    # Hierarchy level
    level: StructureLevel = StructureLevel.PARAGRAPH
    
    # Full reference path for citation
    reference: str = ""
    
    # Parent references for context
    parent_reference: Optional[str] = None
    
    # Metadata
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    def get_full_reference(self) -> str:
        """Generate full legal reference (e.g., '§ 1 Abs. 2 Nr. 1 lit. a')"""
        parts = []
        
        if self.paragraph:
            parts.append(self.paragraph)
            if self.paragraph_title:
                parts.append(self.paragraph_title)
        
        if self.absatz:
            parts.append(f"Abs. {self.absatz}")
        
        if self.nummer:
            parts.append(f"Nr. {self.nummer}")
        
        if self.buchstabe:
            parts.append(f"lit. {self.buchstabe}")
        
        if self.satz and self.satz > 1:
            parts.append(f"Satz {self.satz}")
        
        return " ".join(parts)


class GermanLawParser:
    """
    Parser for German legal texts that recognizes hierarchical structure.
    
    Features:
    - Detects legal document type (Gesetz, Verordnung, etc.)
    - Parses § paragraphs with titles
    - Identifies Absätze (subsections)
    - Recognizes numbered items (Nummern)
    - Handles lettered sub-items (Buchstaben)
    - Splits into sentences when appropriate
    - Preserves structural context in metadata
    """
    
    # Regex patterns for structure detection
    PARAGRAPH_PATTERN = re.compile(r'^§\s*(\d+[a-z]?)\s*(.*?)$', re.MULTILINE)
    ABSATZ_PATTERN = re.compile(r'^\((\d+)\)\s*(.*?)$', re.MULTILINE)
    NUMMER_PATTERN = re.compile(r'^(\d+)\.\s+(.*?)$', re.MULTILINE)
    BUCHSTABE_PATTERN = re.compile(r'^\s*([a-z])\)\s+(.*?)$', re.MULTILINE)
    
    # Pattern for detecting legal text keywords
    LEGAL_KEYWORDS = [
        'Gesetz', 'Verordnung', 'Satzung', 'Richtlinie',
        'Beschluss', 'Vorschrift', 'Bestimmung', 'Regelung',
        'Absatz', 'Nummer', 'Buchstabe', 'Satz',
        'gilt', 'gelten', 'dient', 'regelt', 'bestimmt',
        'verpflichtet', 'berechtigt', 'verboten', 'erlaubt'
    ]
    
    def __init__(self, enable_sentence_splitting: bool = True):
        """
        Initialize the parser.
        
        Args:
            enable_sentence_splitting: Whether to split Absätze into sentences
                                     for very granular chunking
        """
        self.enable_sentence_splitting = enable_sentence_splitting
    
    def is_legal_text(self, text: str, filename: str = "") -> bool:
        """
        Detect if text is a German legal document.
        
        Args:
            text: Document content
            filename: Optional filename for additional hints
            
        Returns:
            True if text appears to be a legal document
        """
        # Check filename for legal indicators
        filename_lower = filename.lower()
        legal_extensions = ['gesetz', 'g.pdf', 'vo.pdf', 'verordnung']
        if any(ext in filename_lower for ext in legal_extensions):
            return True
        
        # Check for § symbols (strong indicator)
        paragraph_count = len(self.PARAGRAPH_PATTERN.findall(text))
        if paragraph_count >= 1:  # At least 1 paragraph with § symbol
            return True
        
        # Check for legal keywords density
        words = text.lower().split()
        if len(words) < 50:
            return False
        
        legal_word_count = sum(1 for word in words if any(kw.lower() in word for kw in self.LEGAL_KEYWORDS))
        legal_density = legal_word_count / len(words)
        
        # If >5% of words are legal keywords, likely a legal text
        if legal_density > 0.05:
            return True
        
        return False
    
    def detect_document_type(self, text: str, filename: str = "") -> LegalTextType:
        """Detect the type of legal document."""
        text_lower = text.lower()
        filename_lower = filename.lower()
        
        combined = text_lower + " " + filename_lower
        
        if 'gesetz' in combined or 'g.pdf' in filename_lower:
            return LegalTextType.GESETZ
        elif 'verordnung' in combined or 'vo.pdf' in filename_lower:
            return LegalTextType.VERORDNUNG
        elif 'satzung' in combined:
            return LegalTextType.SATZUNG
        elif 'richtlinie' in combined:
            return LegalTextType.RICHTLINIE
        elif 'beschluss' in combined:
            return LegalTextType.BESCHLUSS
        
        return LegalTextType.UNKNOWN
    
    def parse(self, text: str, filename: str = "", document_id: str = "") -> List[LegalTextChunk]:
        """
        Parse legal text into hierarchical chunks.
        
        Args:
            text: Legal document content
            filename: Optional filename for metadata
            document_id: Optional document identifier
            
        Returns:
            List of LegalTextChunk objects with structural metadata
        """
        if not self.is_legal_text(text, filename):
            logger.info(f"Text does not appear to be a legal document: {filename}")
            # Return single chunk with full text
            return [LegalTextChunk(
                text=text,
                level=StructureLevel.PARAGRAPH,
                reference="Full Document",
                metadata={
                    'filename': filename,
                    'document_id': document_id,
                    'is_legal_text': False
                }
            )]
        
        doc_type = self.detect_document_type(text, filename)
        logger.info(f"Parsing legal text: {filename} (Type: {doc_type.value})")
        
        chunks = []
        
        # Split text into paragraphs (§ sections)
        paragraphs = self._split_into_paragraphs(text)
        
        for para_num, para_title, para_text in paragraphs:
            # Parse each paragraph into Absätze
            absaetze = self._split_into_absaetze(para_text)
            
            if not absaetze:
                # No Absätze found, but check for direct Nummern (e.g., § 3 BImSchG)
                nummern = self._split_into_nummern(para_text)
                
                if not nummern:
                    # No structure, treat whole paragraph as one chunk
                    chunk = LegalTextChunk(
                        text=para_text,
                        paragraph=f"§ {para_num}",
                        paragraph_title=para_title,
                        level=StructureLevel.PARAGRAPH,
                        metadata={
                            'filename': filename,
                            'document_id': document_id,
                            'document_type': doc_type.value
                        }
                    )
                    chunk.reference = chunk.get_full_reference()
                    chunks.append(chunk)
                else:
                    # Process Nummern directly under paragraph (no Absatz)
                    for nummer_num, nummer_text in nummern:
                        # Check for lettered sub-items (Buchstaben)
                        buchstaben = self._split_into_buchstaben(nummer_text)
                        
                        if not buchstaben:
                            # No Buchstaben, create chunk for Nummer
                            chunk = LegalTextChunk(
                                text=nummer_text,
                                paragraph=f"§ {para_num}",
                                paragraph_title=para_title,
                                nummer=nummer_num,
                                level=StructureLevel.NUMMER,
                                metadata={
                                    'filename': filename,
                                    'document_id': document_id,
                                    'document_type': doc_type.value
                                }
                            )
                            chunk.reference = chunk.get_full_reference()
                            chunk.parent_reference = f"§ {para_num}"
                            chunks.append(chunk)
                        else:
                            # Process each Buchstabe
                            for buchstabe_letter, buchstabe_text in buchstaben:
                                chunk = LegalTextChunk(
                                    text=buchstabe_text,
                                    paragraph=f"§ {para_num}",
                                    paragraph_title=para_title,
                                    nummer=nummer_num,
                                    buchstabe=buchstabe_letter,
                                    level=StructureLevel.BUCHSTABE,
                                    metadata={
                                        'filename': filename,
                                        'document_id': document_id,
                                        'document_type': doc_type.value
                                    }
                                )
                                chunk.reference = chunk.get_full_reference()
                                chunk.parent_reference = f"§ {para_num} Nr. {nummer_num}"
                                chunks.append(chunk)
            else:
                # Process each Absatz
                for absatz_num, absatz_text in absaetze:
                    # Check for numbered items (Nummern)
                    nummern = self._split_into_nummern(absatz_text)
                    
                    if not nummern:
                        # No Nummern, create chunk for entire Absatz
                        chunk = LegalTextChunk(
                            text=absatz_text,
                            paragraph=f"§ {para_num}",
                            paragraph_title=para_title,
                            absatz=absatz_num,
                            level=StructureLevel.ABSATZ,
                            metadata={
                                'filename': filename,
                                'document_id': document_id,
                                'document_type': doc_type.value
                            }
                        )
                        chunk.reference = chunk.get_full_reference()
                        chunk.parent_reference = f"§ {para_num}"
                        chunks.append(chunk)
                    else:
                        # Process each Nummer
                        for nummer_num, nummer_text in nummern:
                            # Check for lettered sub-items (Buchstaben)
                            buchstaben = self._split_into_buchstaben(nummer_text)
                            
                            if not buchstaben:
                                # No Buchstaben, create chunk for Nummer
                                chunk = LegalTextChunk(
                                    text=nummer_text,
                                    paragraph=f"§ {para_num}",
                                    paragraph_title=para_title,
                                    absatz=absatz_num,
                                    nummer=nummer_num,
                                    level=StructureLevel.NUMMER,
                                    metadata={
                                        'filename': filename,
                                        'document_id': document_id,
                                        'document_type': doc_type.value
                                    }
                                )
                                chunk.reference = chunk.get_full_reference()
                                chunk.parent_reference = f"§ {para_num} Abs. {absatz_num}"
                                chunks.append(chunk)
                            else:
                                # Process each Buchstabe
                                for buchstabe_letter, buchstabe_text in buchstaben:
                                    chunk = LegalTextChunk(
                                        text=buchstabe_text,
                                        paragraph=f"§ {para_num}",
                                        paragraph_title=para_title,
                                        absatz=absatz_num,
                                        nummer=nummer_num,
                                        buchstabe=buchstabe_letter,
                                        level=StructureLevel.BUCHSTABE,
                                        metadata={
                                            'filename': filename,
                                            'document_id': document_id,
                                            'document_type': doc_type.value
                                        }
                                    )
                                    chunk.reference = chunk.get_full_reference()
                                    chunk.parent_reference = f"§ {para_num} Abs. {absatz_num} Nr. {nummer_num}"
                                    chunks.append(chunk)
        
        logger.info(f"Parsed {len(chunks)} chunks from legal text: {filename}")
        return chunks
    
    def _split_into_paragraphs(self, text: str) -> List[tuple]:
        """
        Split text into § paragraphs.
        
        Returns:
            List of (paragraph_number, title, text) tuples
        """
        paragraphs = []
        matches = list(self.PARAGRAPH_PATTERN.finditer(text))
        
        if not matches:
            return []
        
        for i, match in enumerate(matches):
            para_num = match.group(1)
            para_title = match.group(2).strip()
            
            # Extract text until next paragraph or end
            start_pos = match.end()
            if i + 1 < len(matches):
                end_pos = matches[i + 1].start()
            else:
                end_pos = len(text)
            
            para_text = text[start_pos:end_pos].strip()
            paragraphs.append((para_num, para_title, para_text))
        
        return paragraphs
    
    def _split_into_absaetze(self, text: str) -> List[tuple]:
        """
        Split paragraph text into Absätze.
        
        Returns:
            List of (absatz_number, text) tuples
        """
        absaetze = []
        matches = list(self.ABSATZ_PATTERN.finditer(text))
        
        if not matches:
            return []
        
        for i, match in enumerate(matches):
            absatz_num = int(match.group(1))
            
            # Extract text until next Absatz or end
            start_pos = match.start()
            if i + 1 < len(matches):
                end_pos = matches[i + 1].start()
            else:
                end_pos = len(text)
            
            absatz_text = text[start_pos:end_pos].strip()
            absaetze.append((absatz_num, absatz_text))
        
        return absaetze
    
    def _split_into_nummern(self, text: str) -> List[tuple]:
        """
        Split Absatz text into numbered items (Nummern).
        
        Returns:
            List of (nummer, text) tuples
        """
        nummern = []
        matches = list(self.NUMMER_PATTERN.finditer(text))
        
        if not matches:
            return []
        
        for i, match in enumerate(matches):
            nummer_num = int(match.group(1))
            
            # Extract text until next Nummer or end
            start_pos = match.start()
            if i + 1 < len(matches):
                end_pos = matches[i + 1].start()
            else:
                end_pos = len(text)
            
            nummer_text = text[start_pos:end_pos].strip()
            nummern.append((nummer_num, nummer_text))
        
        return nummern
    
    def _split_into_buchstaben(self, text: str) -> List[tuple]:
        """
        Split Nummer text into lettered sub-items (Buchstaben).
        
        Returns:
            List of (letter, text) tuples
        """
        buchstaben = []
        matches = list(self.BUCHSTABE_PATTERN.finditer(text))
        
        if not matches:
            return []
        
        for i, match in enumerate(matches):
            buchstabe = match.group(1)
            
            # Extract text until next Buchstabe or end
            start_pos = match.start()
            if i + 1 < len(matches):
                end_pos = matches[i + 1].start()
            else:
                end_pos = len(text)
            
            buchstabe_text = text[start_pos:end_pos].strip()
            buchstaben.append((buchstabe, buchstabe_text))
        
        return buchstaben
    
    def chunks_to_dict(self, chunks: List[LegalTextChunk]) -> List[Dict[str, Any]]:
        """Convert chunks to dictionary format for storage/serialization."""
        return [
            {
                'text': chunk.text,
                'paragraph': chunk.paragraph,
                'paragraph_title': chunk.paragraph_title,
                'absatz': chunk.absatz,
                'nummer': chunk.nummer,
                'buchstabe': chunk.buchstabe,
                'satz': chunk.satz,
                'level': chunk.level.value,
                'reference': chunk.reference,
                'parent_reference': chunk.parent_reference,
                'metadata': chunk.metadata
            }
            for chunk in chunks
        ]


# Convenience function for quick parsing
def parse_german_law(text: str, filename: str = "", document_id: str = "") -> List[LegalTextChunk]:
    """
    Quick function to parse German legal text.
    
    Args:
        text: Legal document content
        filename: Optional filename
        document_id: Optional document ID
        
    Returns:
        List of LegalTextChunk objects
    """
    parser = GermanLawParser()
    return parser.parse(text, filename, document_id)
