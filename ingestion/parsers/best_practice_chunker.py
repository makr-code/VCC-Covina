#!/usr/bin/env python3
"""
Document Chunking Strategy - Best Practices Implementation
===========================================================

Implements industry best practices for document chunking:
- Semantic chunking with structure awareness
- Context overlap for better retrieval
- Adaptive chunk sizing
- Metadata enrichment
- Multi-level indexing
- Heading hierarchy extraction
- Cross-reference detection

Author: Covina System
Date: November 2025
"""

import re
import hashlib
from typing import List, Dict, Any, Optional, Tuple, Set
from dataclasses import dataclass, field
import logging

logger = logging.getLogger(__name__)


@dataclass
class ChunkingConfig:
    """Configuration for chunking strategy"""
    # Size constraints
    min_chunk_size: int = 100  # Minimum characters
    max_chunk_size: int = 2000  # Maximum characters
    target_chunk_size: int = 500  # Preferred size
    
    # Overlap strategy
    enable_overlap: bool = True
    overlap_tokens: int = 50  # Characters to overlap
    overlap_percentage: float = 0.15  # 15% overlap
    
    # Splitting strategy
    respect_sentences: bool = True  # Don't split mid-sentence
    respect_paragraphs: bool = True  # Prefer paragraph boundaries
    
    # Multi-level indexing
    enable_multi_level: bool = True  # Store at multiple levels
    store_section_summaries: bool = True  # Store section-level chunks
    
    # Metadata enrichment
    extract_keywords: bool = True
    extract_entities: bool = False  # Requires NLP
    detect_cross_references: bool = True
    
    # Heading detection
    extract_headings: bool = True
    heading_levels: int = 6  # H1-H6


@dataclass
class EnrichedChunk:
    """
    Enhanced chunk with best-practice metadata.
    
    Extends basic chunks with:
    - Overlap context
    - Position information
    - Heading hierarchy
    - Keywords
    - Cross-references
    """
    # Core content
    text: str
    chunk_id: str
    
    # Position & structure
    document_id: str
    chunk_index: int
    total_chunks: int
    
    # Document structure
    section: Optional[str] = None
    section_title: Optional[str] = None
    subsection: Optional[str] = None
    heading_path: List[str] = field(default_factory=list)  # H1 > H2 > H3
    
    # Size & boundaries
    char_count: int = 0
    word_count: int = 0
    sentence_count: int = 0
    
    # Overlap context
    prev_overlap: Optional[str] = None
    next_overlap: Optional[str] = None
    
    # Enhanced metadata
    keywords: List[str] = field(default_factory=list)
    entities: List[Dict[str, str]] = field(default_factory=list)
    cross_references: List[str] = field(default_factory=list)
    
    # References
    reference: str = ""
    parent_reference: Optional[str] = None
    
    # Quality metrics
    completeness_score: float = 1.0  # 0-1
    
    # Additional metadata
    metadata: Dict[str, Any] = field(default_factory=dict)


class BestPracticeChunker:
    """
    Document chunker implementing industry best practices.
    
    Features:
    1. Semantic chunking - respects document structure
    2. Context overlap - improves boundary queries
    3. Adaptive sizing - balances size constraints
    4. Metadata enrichment - keywords, references
    5. Multi-level indexing - section + detail levels
    6. Heading extraction - builds navigation hierarchy
    7. Quality validation - ensures chunk completeness
    """
    
    # Cross-reference patterns
    CROSS_REF_PATTERNS = [
        re.compile(r'§\s*(\d+[a-z]?)\s*(?:Abs\.?\s*(\d+))?(?:\s*Nr\.?\s*(\d+))?'),
        re.compile(r'Artikel\s+(\d+)\s*(?:Absatz\s+(\d+))?', re.IGNORECASE),
        re.compile(r'siehe\s+(?:Abschnitt|Kapitel|Punkt)\s+([\d.]+)', re.IGNORECASE),
        re.compile(r'vgl\.\s+(?:Abschnitt|Kapitel)\s+([\d.]+)', re.IGNORECASE),
    ]
    
    # Heading patterns (markdown and text)
    HEADING_PATTERNS = [
        (re.compile(r'^(#{1})\s+(.+)$', re.MULTILINE), 1),  # # H1
        (re.compile(r'^(#{2})\s+(.+)$', re.MULTILINE), 2),  # ## H2
        (re.compile(r'^(#{3})\s+(.+)$', re.MULTILINE), 3),  # ### H3
        (re.compile(r'^(#{4})\s+(.+)$', re.MULTILINE), 4),  # #### H4
        (re.compile(r'^([A-ZÄÖÜ][A-ZÄÖÜ\s]{3,})$', re.MULTILINE), 1),  # ALL CAPS = H1
        (re.compile(r'^(\d+\.)\s+([A-ZÄÖÜ].+)$', re.MULTILINE), 2),  # 1. Title = H2
    ]
    
    def __init__(self, config: Optional[ChunkingConfig] = None):
        """Initialize chunker with configuration"""
        self.config = config or ChunkingConfig()
    
    def chunk_document(
        self,
        text: str,
        document_id: str = "",
        structured_chunks: Optional[List[Dict[str, Any]]] = None
    ) -> List[EnrichedChunk]:
        """
        Create enriched chunks from document text.
        
        Args:
            text: Full document text
            document_id: Unique document identifier
            structured_chunks: Pre-parsed structure (from StructuredDocumentParser)
            
        Returns:
            List of enriched chunks with best-practice metadata
        """
        if not document_id:
            document_id = self._generate_doc_id(text)
        
        # Use structured chunks if available, otherwise create basic chunks
        if structured_chunks:
            chunks = self._chunk_from_structure(text, structured_chunks, document_id)
        else:
            chunks = self._chunk_by_size(text, document_id)
        
        # Apply best practices
        chunks = self._add_overlap(chunks)
        chunks = self._extract_headings(text, chunks)
        chunks = self._extract_keywords(chunks)
        chunks = self._detect_cross_references(chunks)
        chunks = self._validate_chunks(chunks)
        
        # Add position information
        total = len(chunks)
        for i, chunk in enumerate(chunks):
            chunk.chunk_index = i
            chunk.total_chunks = total
        
        logger.info(f"Created {len(chunks)} enriched chunks for document {document_id}")
        return chunks
    
    def _chunk_from_structure(
        self,
        text: str,
        structured_chunks: List[Dict[str, Any]],
        document_id: str
    ) -> List[EnrichedChunk]:
        """Create enriched chunks from structured parser output"""
        enriched = []
        
        for i, struct_chunk in enumerate(structured_chunks):
            chunk_text = struct_chunk['text']
            
            # Check if chunk needs splitting (too large)
            if len(chunk_text) > self.config.max_chunk_size:
                # Split large chunk into smaller pieces
                sub_chunks = self._split_large_chunk(chunk_text, struct_chunk)
                enriched.extend(sub_chunks)
            else:
                # Create single enriched chunk
                chunk = EnrichedChunk(
                    text=chunk_text,
                    chunk_id=self._generate_chunk_id(document_id, i),
                    document_id=document_id,
                    chunk_index=i,
                    total_chunks=len(structured_chunks),
                    section=struct_chunk.get('section'),
                    section_title=struct_chunk.get('section_title'),
                    subsection=struct_chunk.get('subsection'),
                    reference=struct_chunk.get('reference', ''),
                    parent_reference=struct_chunk.get('parent_reference'),
                    metadata=struct_chunk.get('metadata', {})
                )
                
                # Calculate text metrics
                chunk.char_count = len(chunk_text)
                chunk.word_count = len(chunk_text.split())
                chunk.sentence_count = len(re.findall(r'[.!?]+', chunk_text))
                
                enriched.append(chunk)
        
        return enriched
    
    def _chunk_by_size(
        self,
        text: str,
        document_id: str
    ) -> List[EnrichedChunk]:
        """
        Fallback: Create size-based chunks.
        
        Uses intelligent splitting at sentence/paragraph boundaries.
        """
        chunks = []
        
        # Split into paragraphs first
        if self.config.respect_paragraphs:
            paragraphs = text.split('\n\n')
        else:
            paragraphs = [text]
        
        current_chunk = []
        current_size = 0
        chunk_index = 0
        
        for para in paragraphs:
            para_size = len(para)
            
            # If paragraph alone is too large, split it
            if para_size > self.config.max_chunk_size:
                # Save current chunk if exists
                if current_chunk:
                    chunk_text = '\n\n'.join(current_chunk)
                    chunks.append(self._create_basic_chunk(
                        chunk_text, document_id, chunk_index
                    ))
                    chunk_index += 1
                    current_chunk = []
                    current_size = 0
                
                # Split large paragraph
                sentences = self._split_sentences(para)
                for sentence in sentences:
                    if current_size + len(sentence) > self.config.max_chunk_size:
                        if current_chunk:
                            chunk_text = ' '.join(current_chunk)
                            chunks.append(self._create_basic_chunk(
                                chunk_text, document_id, chunk_index
                            ))
                            chunk_index += 1
                            current_chunk = []
                            current_size = 0
                    
                    current_chunk.append(sentence)
                    current_size += len(sentence)
            
            # Regular paragraph
            elif current_size + para_size > self.config.max_chunk_size:
                # Save current chunk
                if current_chunk:
                    chunk_text = '\n\n'.join(current_chunk)
                    chunks.append(self._create_basic_chunk(
                        chunk_text, document_id, chunk_index
                    ))
                    chunk_index += 1
                
                current_chunk = [para]
                current_size = para_size
            else:
                current_chunk.append(para)
                current_size += para_size
        
        # Save final chunk
        if current_chunk:
            chunk_text = '\n\n'.join(current_chunk)
            chunks.append(self._create_basic_chunk(
                chunk_text, document_id, chunk_index
            ))
        
        return chunks
    
    def _split_large_chunk(
        self,
        text: str,
        struct_metadata: Dict[str, Any]
    ) -> List[EnrichedChunk]:
        """Split a large structured chunk into smaller pieces"""
        sub_chunks = []
        
        # Split by sentences
        sentences = self._split_sentences(text)
        
        current_text = []
        current_size = 0
        
        for sentence in sentences:
            if current_size + len(sentence) > self.config.target_chunk_size and current_text:
                # Create chunk
                chunk_text = ' '.join(current_text)
                sub_chunks.append(EnrichedChunk(
                    text=chunk_text,
                    chunk_id=self._generate_chunk_id(
                        struct_metadata.get('document_id', ''),
                        len(sub_chunks)
                    ),
                    document_id=struct_metadata.get('document_id', ''),
                    chunk_index=len(sub_chunks),
                    total_chunks=0,  # Will be updated later
                    section=struct_metadata.get('section'),
                    section_title=struct_metadata.get('section_title'),
                    reference=struct_metadata.get('reference', ''),
                    char_count=len(chunk_text),
                    word_count=len(chunk_text.split()),
                    metadata=struct_metadata.get('metadata', {})
                ))
                
                current_text = []
                current_size = 0
            
            current_text.append(sentence)
            current_size += len(sentence)
        
        # Last sub-chunk
        if current_text:
            chunk_text = ' '.join(current_text)
            sub_chunks.append(EnrichedChunk(
                text=chunk_text,
                chunk_id=self._generate_chunk_id(
                    struct_metadata.get('document_id', ''),
                    len(sub_chunks)
                ),
                document_id=struct_metadata.get('document_id', ''),
                chunk_index=len(sub_chunks),
                total_chunks=0,
                section=struct_metadata.get('section'),
                section_title=struct_metadata.get('section_title'),
                reference=struct_metadata.get('reference', ''),
                char_count=len(chunk_text),
                word_count=len(chunk_text.split()),
                metadata=struct_metadata.get('metadata', {})
            ))
        
        return sub_chunks
    
    def _add_overlap(self, chunks: List[EnrichedChunk]) -> List[EnrichedChunk]:
        """Add context overlap between adjacent chunks"""
        if not self.config.enable_overlap or len(chunks) < 2:
            return chunks
        
        for i in range(len(chunks)):
            # Previous overlap
            if i > 0:
                prev_text = chunks[i - 1].text
                overlap_size = min(
                    self.config.overlap_tokens,
                    int(len(prev_text) * self.config.overlap_percentage)
                )
                chunks[i].prev_overlap = prev_text[-overlap_size:] if overlap_size > 0 else None
            
            # Next overlap
            if i < len(chunks) - 1:
                next_text = chunks[i + 1].text
                overlap_size = min(
                    self.config.overlap_tokens,
                    int(len(next_text) * self.config.overlap_percentage)
                )
                chunks[i].next_overlap = next_text[:overlap_size] if overlap_size > 0 else None
        
        return chunks
    
    def _extract_headings(
        self,
        full_text: str,
        chunks: List[EnrichedChunk]
    ) -> List[EnrichedChunk]:
        """Extract heading hierarchy and add to chunks"""
        if not self.config.extract_headings:
            return chunks
        
        # Find all headings in document
        headings = []
        for pattern, level in self.HEADING_PATTERNS:
            for match in pattern.finditer(full_text):
                pos = match.start()
                text = match.group(2) if match.lastindex >= 2 else match.group(0)
                headings.append((pos, level, text.strip()))
        
        # Sort by position
        headings.sort(key=lambda x: x[0])
        
        # Build heading hierarchy for each chunk
        for chunk in chunks:
            # Find chunk position in full text
            chunk_pos = full_text.find(chunk.text)
            if chunk_pos == -1:
                continue
            
            # Find applicable headings (before this chunk)
            path = []
            current_level = 0
            
            for pos, level, text in headings:
                if pos >= chunk_pos:
                    break
                
                # Add to path at appropriate level
                if level > current_level:
                    path.append(text)
                elif level == current_level:
                    if path:
                        path[-1] = text
                    else:
                        path.append(text)
                else:  # level < current_level
                    # Go back up the hierarchy
                    path = path[:level]
                    if path:
                        path[-1] = text
                    else:
                        path.append(text)
                
                current_level = level
            
            chunk.heading_path = path
        
        return chunks
    
    def _extract_keywords(self, chunks: List[EnrichedChunk]) -> List[EnrichedChunk]:
        """Extract keywords from chunks"""
        if not self.config.extract_keywords:
            return chunks
        
        # Simple keyword extraction (frequency-based)
        for chunk in chunks:
            words = chunk.text.lower().split()
            
            # Filter stop words and count frequency
            word_freq = {}
            for word in words:
                # Simple filtering
                if len(word) > 3 and word.isalnum():
                    word_freq[word] = word_freq.get(word, 0) + 1
            
            # Top keywords
            sorted_words = sorted(word_freq.items(), key=lambda x: x[1], reverse=True)
            chunk.keywords = [word for word, freq in sorted_words[:5]]
        
        return chunks
    
    def _detect_cross_references(
        self,
        chunks: List[EnrichedChunk]
    ) -> List[EnrichedChunk]:
        """Detect cross-references to other sections"""
        if not self.config.detect_cross_references:
            return chunks
        
        for chunk in chunks:
            refs = set()
            
            for pattern in self.CROSS_REF_PATTERNS:
                for match in pattern.finditer(chunk.text):
                    refs.add(match.group(0))
            
            chunk.cross_references = list(refs)
        
        return chunks
    
    def _validate_chunks(self, chunks: List[EnrichedChunk]) -> List[EnrichedChunk]:
        """Validate chunk quality and completeness"""
        for chunk in chunks:
            score = 1.0
            
            # Check minimum size
            if chunk.char_count < self.config.min_chunk_size:
                score -= 0.2
            
            # Check if chunk ends mid-sentence
            if chunk.text and not chunk.text.rstrip()[-1] in '.!?':
                score -= 0.1
            
            # Check if too small
            if chunk.word_count < 10:
                score -= 0.3
            
            chunk.completeness_score = max(0.0, score)
        
        return chunks
    
    def _split_sentences(self, text: str) -> List[str]:
        """Split text into sentences"""
        # Simple sentence splitting
        sentences = re.split(r'([.!?]+\s+)', text)
        
        # Recombine
        result = []
        for i in range(0, len(sentences) - 1, 2):
            sentence = sentences[i] + (sentences[i + 1] if i + 1 < len(sentences) else '')
            if sentence.strip():
                result.append(sentence.strip())
        
        return result if result else [text]
    
    def _create_basic_chunk(
        self,
        text: str,
        document_id: str,
        index: int
    ) -> EnrichedChunk:
        """Create a basic enriched chunk"""
        return EnrichedChunk(
            text=text,
            chunk_id=self._generate_chunk_id(document_id, index),
            document_id=document_id,
            chunk_index=index,
            total_chunks=0,
            char_count=len(text),
            word_count=len(text.split()),
            sentence_count=len(re.findall(r'[.!?]+', text))
        )
    
    def _generate_doc_id(self, text: str) -> str:
        """Generate document ID from content"""
        return hashlib.sha256(text[:1000].encode()).hexdigest()[:16]
    
    def _generate_chunk_id(self, document_id: str, index: int) -> str:
        """Generate unique chunk ID"""
        return f"{document_id}_chunk_{index}"
    
    def chunks_to_dict(self, chunks: List[EnrichedChunk]) -> List[Dict[str, Any]]:
        """Convert enriched chunks to dictionary format"""
        return [
            {
                'text': chunk.text,
                'chunk_id': chunk.chunk_id,
                'document_id': chunk.document_id,
                'chunk_index': chunk.chunk_index,
                'total_chunks': chunk.total_chunks,
                'section': chunk.section,
                'section_title': chunk.section_title,
                'subsection': chunk.subsection,
                'heading_path': chunk.heading_path,
                'char_count': chunk.char_count,
                'word_count': chunk.word_count,
                'sentence_count': chunk.sentence_count,
                'prev_overlap': chunk.prev_overlap,
                'next_overlap': chunk.next_overlap,
                'keywords': chunk.keywords,
                'entities': chunk.entities,
                'cross_references': chunk.cross_references,
                'reference': chunk.reference,
                'parent_reference': chunk.parent_reference,
                'completeness_score': chunk.completeness_score,
                'metadata': chunk.metadata
            }
            for chunk in chunks
        ]
