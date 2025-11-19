#!/usr/bin/env python3
"""
Structured Document Parser - Generic Hierarchical Document Parser
==================================================================

A flexible parser that can handle various document structures:
- Legal texts (§, Artikel, etc.)
- Technical standards (1.1, 1.1.1, etc.)
- Business documents (numbered sections)
- Scientific papers (chapters, sections, subsections)
- Contracts, regulations, etc.

The parser automatically detects document structure patterns and creates
semantic chunks that preserve hierarchical relationships.

Author: Covina System
Date: November 2025
"""

import re
import logging
from dataclasses import dataclass, field
from typing import List, Optional, Dict, Any, Set, Tuple
from enum import Enum

logger = logging.getLogger(__name__)


class DocumentType(Enum):
    """Types of structured documents"""
    LEGAL = "legal"  # § based (German law)
    ARTICLE = "article"  # Artikel based (EU regulations, DSGVO)
    HIERARCHICAL_DECIMAL = "hierarchical_decimal"  # 1.1.1 style (DIN, ISO, technical)
    HIERARCHICAL_NUMERIC = "hierarchical_numeric"  # 1, 1.1, 1.1.1 mixed
    BUSINESS = "business"  # Standard business docs
    SCIENTIFIC = "scientific"  # Academic papers
    UNKNOWN = "unknown"


class StructureElementType(Enum):
    """Generic structure element types"""
    SECTION = "section"  # Top level (§, Artikel, Chapter, 1.)
    SUBSECTION = "subsection"  # (1), 1.1, 2.1
    ITEM = "item"  # 1., a), bullet point
    SUBITEM = "subitem"  # a), i), sub-bullet
    PARAGRAPH = "paragraph"  # Plain text paragraph
    HEADING = "heading"  # Title/heading


@dataclass
class StructurePattern:
    """Configuration for a document structure pattern"""
    name: str
    section_pattern: Optional[re.Pattern] = None
    subsection_pattern: Optional[re.Pattern] = None
    item_pattern: Optional[re.Pattern] = None
    subitem_pattern: Optional[re.Pattern] = None
    heading_pattern: Optional[re.Pattern] = None
    
    # Detection keywords for this pattern
    keywords: List[str] = field(default_factory=list)
    
    # Minimum matches needed for detection
    min_matches: int = 1


@dataclass
class StructuredChunk:
    """
    A semantic chunk from any structured document.
    
    Flexible enough to represent various document hierarchies.
    """
    # Content
    text: str
    
    # Structural identifiers (flexible)
    section: Optional[str] = None  # § 1, Artikel 1, 1., Chapter 1
    section_title: Optional[str] = None
    subsection: Optional[str] = None  # (1), 1.1, Section A
    item: Optional[str] = None  # 1., a), bullet
    subitem: Optional[str] = None  # i), aa), sub-bullet
    
    # Element type
    element_type: StructureElementType = StructureElementType.PARAGRAPH
    
    # Full reference path
    reference: str = ""
    
    # Parent reference for navigation
    parent_reference: Optional[str] = None
    
    # Additional metadata
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    # Depth in hierarchy (0 = top level)
    depth: int = 0
    
    def get_full_reference(self) -> str:
        """Generate full reference path"""
        parts = []
        
        if self.section:
            parts.append(self.section)
            if self.section_title:
                parts.append(self.section_title)
        
        if self.subsection:
            parts.append(self.subsection)
        
        if self.item:
            parts.append(self.item)
        
        if self.subitem:
            parts.append(self.subitem)
        
        return " ".join(parts) if parts else "Document"


class StructuredDocumentParser:
    """
    Generic parser for structured documents.
    
    Automatically detects and parses various document structures:
    - Legal texts (§, Absatz, Nummer, Buchstabe)
    - Technical standards (1.1, 1.1.1, 1.1.1.1)
    - Business documents (numbered sections and headings)
    - Scientific papers (chapters, sections, subsections)
    - Mixed structures
    """
    
    # Define common structure patterns
    PATTERNS = {
        'german_law': StructurePattern(
            name='german_law',
            section_pattern=re.compile(r'^§\s*(\d+[a-z]?)\s*(.*?)$', re.MULTILINE),
            subsection_pattern=re.compile(r'^\((\d+)\)\s*(.*?)$', re.MULTILINE),
            item_pattern=re.compile(r'^(\d+)\.\s+(.*?)$', re.MULTILINE),
            subitem_pattern=re.compile(r'^\s*([a-z])\)\s+(.*?)$', re.MULTILINE),
            keywords=['Gesetz', 'Verordnung', 'Absatz', 'Nummer', '§'],
            min_matches=1
        ),
        'eu_article': StructurePattern(
            name='eu_article',
            section_pattern=re.compile(r'^Artikel\s+(\d+)\s*(.*?)$', re.MULTILINE | re.IGNORECASE),
            subsection_pattern=re.compile(r'^\((\d+)\)\s*(.*?)$', re.MULTILINE),
            item_pattern=re.compile(r'^([a-z])\)\s+(.*?)$', re.MULTILINE),
            subitem_pattern=re.compile(r'^\s*([ivxlcdm]+)\)\s+(.*?)$', re.MULTILINE | re.IGNORECASE),
            keywords=['Artikel', 'Verordnung', 'Richtlinie', 'DSGVO', 'Regulation'],
            min_matches=1
        ),
        'hierarchical_decimal': StructurePattern(
            name='hierarchical_decimal',
            section_pattern=re.compile(r'^(\d+)\s+(.*?)$', re.MULTILINE),
            subsection_pattern=re.compile(r'^(\d+\.\d+)\s+(.*?)$', re.MULTILINE),
            item_pattern=re.compile(r'^(\d+\.\d+\.\d+)\s+(.*?)$', re.MULTILINE),
            subitem_pattern=re.compile(r'^(\d+\.\d+\.\d+\.\d+)\s+(.*?)$', re.MULTILINE),
            keywords=['DIN', 'ISO', 'Norm', 'Standard', 'Specification'],
            min_matches=2
        ),
        'generic_numbered': StructurePattern(
            name='generic_numbered',
            section_pattern=re.compile(r'^(\d+\.)\s+(.*?)$', re.MULTILINE),
            subsection_pattern=re.compile(r'^(\d+\.\d+\.?)\s+(.*?)$', re.MULTILINE),
            item_pattern=re.compile(r'^\s*[-•*]\s+(.*?)$', re.MULTILINE),
            heading_pattern=re.compile(r'^([A-ZÄÖÜ][A-Za-zäöüßÄÖÜ\s]+)$', re.MULTILINE),
            keywords=[],
            min_matches=1
        ),
    }
    
    # Common heading patterns
    HEADING_PATTERNS = [
        re.compile(r'^#+\s+(.*?)$', re.MULTILINE),  # Markdown headings
        re.compile(r'^([A-ZÄÖÜ][A-ZÄÖÜ\s]{2,})$', re.MULTILINE),  # ALL CAPS
        re.compile(r'^(\d+\.\s+[A-ZÄÖÜ].*?)$', re.MULTILINE),  # 1. Capitalized
    ]
    
    # Common bullet/list patterns
    BULLET_PATTERNS = [
        re.compile(r'^\s*[-•*]\s+(.*?)$', re.MULTILINE),
        re.compile(r'^\s*[○◦▪▫]\s+(.*?)$', re.MULTILINE),
    ]
    
    def __init__(self):
        """Initialize the parser"""
        self.detected_pattern = None
        self.document_type = DocumentType.UNKNOWN
    
    def detect_structure(self, text: str, filename: str = "") -> Optional[StructurePattern]:
        """
        Automatically detect document structure.
        
        Returns the best matching structure pattern.
        """
        best_pattern = None
        best_score = 0
        
        for pattern_name, pattern in self.PATTERNS.items():
            score = 0
            
            # Check section pattern matches
            if pattern.section_pattern:
                matches = len(pattern.section_pattern.findall(text))
                if matches >= pattern.min_matches:
                    score += matches * 10
            
            # Check for keywords in text
            text_lower = text.lower()
            filename_lower = filename.lower()
            combined = text_lower + " " + filename_lower
            
            for keyword in pattern.keywords:
                if keyword.lower() in combined:
                    score += 5
            
            # Check subsection patterns
            if pattern.subsection_pattern:
                matches = len(pattern.subsection_pattern.findall(text))
                if matches > 0:
                    score += matches * 2
            
            if score > best_score:
                best_score = score
                best_pattern = pattern
        
        if best_score > 0:
            logger.info(f"Detected structure pattern: {best_pattern.name} (score: {best_score})")
            return best_pattern
        
        return None
    
    def is_structured_document(self, text: str, filename: str = "") -> bool:
        """
        Detect if document has any recognizable structure.
        """
        pattern = self.detect_structure(text, filename)
        return pattern is not None
    
    def parse(self, text: str, filename: str = "", document_id: str = "") -> List[StructuredChunk]:
        """
        Parse document into hierarchical chunks.
        
        Automatically detects structure and applies appropriate parsing.
        """
        # Detect structure pattern
        pattern = self.detect_structure(text, filename)
        
        if not pattern:
            # No structure detected - return as single chunk
            logger.info(f"No structure detected in: {filename}")
            return [StructuredChunk(
                text=text,
                element_type=StructureElementType.PARAGRAPH,
                reference="Full Document",
                metadata={
                    'filename': filename,
                    'document_id': document_id,
                    'is_structured': False
                }
            )]
        
        self.detected_pattern = pattern
        logger.info(f"Parsing structured document: {filename} (pattern: {pattern.name})")
        
        chunks = []
        
        # Parse based on detected pattern
        if pattern.name == 'german_law':
            chunks = self._parse_german_law_structure(text, filename, document_id, pattern)
        elif pattern.name == 'eu_article':
            chunks = self._parse_article_structure(text, filename, document_id, pattern)
        elif pattern.name in ['hierarchical_decimal', 'generic_numbered']:
            chunks = self._parse_hierarchical_structure(text, filename, document_id, pattern)
        else:
            chunks = self._parse_generic_structure(text, filename, document_id, pattern)
        
        logger.info(f"Parsed {len(chunks)} chunks from structured document: {filename}")
        return chunks
    
    def _parse_german_law_structure(
        self, 
        text: str, 
        filename: str, 
        document_id: str, 
        pattern: StructurePattern
    ) -> List[StructuredChunk]:
        """Parse German law structure (§, Absatz, Nummer, Buchstabe)"""
        chunks = []
        
        # Split into sections (§)
        sections = self._split_by_pattern(text, pattern.section_pattern)
        
        for section_num, section_title, section_text in sections:
            # Check for subsections (Absätze)
            subsections = self._split_by_pattern(section_text, pattern.subsection_pattern)
            
            if not subsections:
                # No subsections - check for direct items
                items = self._split_by_pattern(section_text, pattern.item_pattern)
                
                if not items:
                    # Just section text
                    chunk = StructuredChunk(
                        text=section_text,
                        section=f"§ {section_num}",
                        section_title=section_title,
                        element_type=StructureElementType.SECTION,
                        depth=0,
                        metadata={'filename': filename, 'document_id': document_id}
                    )
                    chunk.reference = chunk.get_full_reference()
                    chunks.append(chunk)
                else:
                    # Process items directly under section
                    chunks.extend(self._process_items(
                        items, f"§ {section_num}", section_title, None,
                        pattern, filename, document_id, depth=1
                    ))
            else:
                # Process subsections
                for subsection_num, _, subsection_text in subsections:
                    items = self._split_by_pattern(subsection_text, pattern.item_pattern)
                    
                    if not items:
                        # Just subsection
                        chunk = StructuredChunk(
                            text=subsection_text,
                            section=f"§ {section_num}",
                            section_title=section_title,
                            subsection=f"({subsection_num})",
                            element_type=StructureElementType.SUBSECTION,
                            depth=1,
                            metadata={'filename': filename, 'document_id': document_id}
                        )
                        chunk.reference = chunk.get_full_reference()
                        chunk.parent_reference = f"§ {section_num}"
                        chunks.append(chunk)
                    else:
                        # Process items under subsection
                        chunks.extend(self._process_items(
                            items, f"§ {section_num}", section_title, f"({subsection_num})",
                            pattern, filename, document_id, depth=2
                        ))
        
        return chunks
    
    def _parse_article_structure(
        self, 
        text: str, 
        filename: str, 
        document_id: str, 
        pattern: StructurePattern
    ) -> List[StructuredChunk]:
        """Parse Article-based structure (EU regulations, DSGVO)"""
        chunks = []
        
        sections = self._split_by_pattern(text, pattern.section_pattern)
        
        for section_num, section_title, section_text in sections:
            subsections = self._split_by_pattern(section_text, pattern.subsection_pattern)
            
            if not subsections:
                items = self._split_by_pattern(section_text, pattern.item_pattern)
                
                if not items:
                    chunk = StructuredChunk(
                        text=section_text,
                        section=f"Artikel {section_num}",
                        section_title=section_title,
                        element_type=StructureElementType.SECTION,
                        depth=0,
                        metadata={'filename': filename, 'document_id': document_id}
                    )
                    chunk.reference = chunk.get_full_reference()
                    chunks.append(chunk)
                else:
                    chunks.extend(self._process_items(
                        items, f"Artikel {section_num}", section_title, None,
                        pattern, filename, document_id, depth=1
                    ))
            else:
                for subsection_num, _, subsection_text in subsections:
                    items = self._split_by_pattern(subsection_text, pattern.item_pattern)
                    
                    if not items:
                        chunk = StructuredChunk(
                            text=subsection_text,
                            section=f"Artikel {section_num}",
                            section_title=section_title,
                            subsection=f"({subsection_num})",
                            element_type=StructureElementType.SUBSECTION,
                            depth=1,
                            metadata={'filename': filename, 'document_id': document_id}
                        )
                        chunk.reference = chunk.get_full_reference()
                        chunk.parent_reference = f"Artikel {section_num}"
                        chunks.append(chunk)
                    else:
                        chunks.extend(self._process_items(
                            items, f"Artikel {section_num}", section_title, f"({subsection_num})",
                            pattern, filename, document_id, depth=2
                        ))
        
        return chunks
    
    def _parse_hierarchical_structure(
        self, 
        text: str, 
        filename: str, 
        document_id: str, 
        pattern: StructurePattern
    ) -> List[StructuredChunk]:
        """Parse hierarchical decimal structure (1.1.1.1 style)"""
        chunks = []
        lines = text.split('\n')
        
        current_section = None
        current_subsection = None
        buffer = []
        
        for line in lines:
            # Check section (1, 2, 3)
            if pattern.section_pattern and pattern.section_pattern.match(line):
                if buffer:
                    # Save previous chunk
                    chunks.append(self._create_chunk_from_buffer(
                        buffer, current_section, current_subsection,
                        filename, document_id
                    ))
                    buffer = []
                
                match = pattern.section_pattern.match(line)
                current_section = match.group(1)
                current_subsection = None
                buffer.append(line)
            
            # Check subsection (1.1, 1.2)
            elif pattern.subsection_pattern and pattern.subsection_pattern.match(line):
                if buffer:
                    chunks.append(self._create_chunk_from_buffer(
                        buffer, current_section, current_subsection,
                        filename, document_id
                    ))
                    buffer = []
                
                match = pattern.subsection_pattern.match(line)
                current_subsection = match.group(1)
                buffer.append(line)
            
            # Regular line
            else:
                buffer.append(line)
        
        # Save last buffer
        if buffer:
            chunks.append(self._create_chunk_from_buffer(
                buffer, current_section, current_subsection,
                filename, document_id
            ))
        
        return chunks
    
    def _parse_generic_structure(
        self, 
        text: str, 
        filename: str, 
        document_id: str, 
        pattern: StructurePattern
    ) -> List[StructuredChunk]:
        """Generic fallback parser for any structure"""
        return self._parse_hierarchical_structure(text, filename, document_id, pattern)
    
    def _split_by_pattern(
        self, 
        text: str, 
        pattern: Optional[re.Pattern]
    ) -> List[Tuple[str, str, str]]:
        """
        Split text by pattern and extract sections.
        
        Returns list of (number, title, content) tuples.
        """
        if not pattern:
            return []
        
        results = []
        matches = list(pattern.finditer(text))
        
        if not matches:
            return []
        
        for i, match in enumerate(matches):
            num = match.group(1)
            title = match.group(2).strip() if match.lastindex >= 2 else ""
            
            # Extract content until next match or end
            start_pos = match.end()
            if i + 1 < len(matches):
                end_pos = matches[i + 1].start()
            else:
                end_pos = len(text)
            
            content = text[start_pos:end_pos].strip()
            results.append((num, title, content))
        
        return results
    
    def _process_items(
        self,
        items: List[Tuple[str, str, str]],
        section: str,
        section_title: str,
        subsection: Optional[str],
        pattern: StructurePattern,
        filename: str,
        document_id: str,
        depth: int
    ) -> List[StructuredChunk]:
        """Process numbered items with optional sub-items"""
        chunks = []
        
        for item_num, _, item_text in items:
            # Check for sub-items
            subitems = self._split_by_pattern(item_text, pattern.subitem_pattern)
            
            if not subitems:
                chunk = StructuredChunk(
                    text=item_text,
                    section=section,
                    section_title=section_title,
                    subsection=subsection,
                    item=f"{item_num}.",
                    element_type=StructureElementType.ITEM,
                    depth=depth,
                    metadata={'filename': filename, 'document_id': document_id}
                )
                chunk.reference = chunk.get_full_reference()
                parent_parts = [section]
                if subsection:
                    parent_parts.append(subsection)
                chunk.parent_reference = " ".join(parent_parts)
                chunks.append(chunk)
            else:
                for subitem_num, _, subitem_text in subitems:
                    chunk = StructuredChunk(
                        text=subitem_text,
                        section=section,
                        section_title=section_title,
                        subsection=subsection,
                        item=f"{item_num}.",
                        subitem=f"{subitem_num})",
                        element_type=StructureElementType.SUBITEM,
                        depth=depth + 1,
                        metadata={'filename': filename, 'document_id': document_id}
                    )
                    chunk.reference = chunk.get_full_reference()
                    parent_parts = [section]
                    if subsection:
                        parent_parts.append(subsection)
                    parent_parts.append(f"{item_num}.")
                    chunk.parent_reference = " ".join(parent_parts)
                    chunks.append(chunk)
        
        return chunks
    
    def _create_chunk_from_buffer(
        self,
        buffer: List[str],
        section: Optional[str],
        subsection: Optional[str],
        filename: str,
        document_id: str
    ) -> StructuredChunk:
        """Create chunk from text buffer"""
        text = '\n'.join(buffer)
        
        # Determine depth
        depth = 0
        if section:
            depth = 1
        if subsection:
            depth = 2
        
        chunk = StructuredChunk(
            text=text,
            section=section,
            subsection=subsection,
            element_type=StructureElementType.SUBSECTION if subsection else StructureElementType.SECTION,
            depth=depth,
            metadata={'filename': filename, 'document_id': document_id}
        )
        chunk.reference = chunk.get_full_reference()
        
        if section and subsection:
            chunk.parent_reference = section
        
        return chunk
    
    def chunks_to_dict(self, chunks: List[StructuredChunk]) -> List[Dict[str, Any]]:
        """Convert chunks to dictionary format"""
        return [
            {
                'text': chunk.text,
                'section': chunk.section,
                'section_title': chunk.section_title,
                'subsection': chunk.subsection,
                'item': chunk.item,
                'subitem': chunk.subitem,
                'element_type': chunk.element_type.value,
                'reference': chunk.reference,
                'parent_reference': chunk.parent_reference,
                'depth': chunk.depth,
                'metadata': chunk.metadata
            }
            for chunk in chunks
        ]


# Convenience function
def parse_structured_document(
    text: str, 
    filename: str = "", 
    document_id: str = ""
) -> List[StructuredChunk]:
    """
    Parse any structured document.
    
    Automatically detects structure and returns appropriate chunks.
    """
    parser = StructuredDocumentParser()
    return parser.parse(text, filename, document_id)
