#!/usr/bin/env python3
"""
Legal text ingestion handler for German legal documents.

Handles specialized processing for legal texts (Gesetze, Verordnungen, etc.)
with hierarchical structure parsing and legal-specific metadata extraction.
"""

from typing import Dict, Any, Optional, List
import logging
from pathlib import Path

from .base import BaseIngestionHandler, HandlerContext
from ..parsers.german_law_parser import GermanLawParser, LegalTextChunk

logger = logging.getLogger(__name__)


class LegalIngestionHandler(BaseIngestionHandler):
    """
    Handler for legal documents (German laws, regulations, etc.)
    
    Features:
    - Detects legal text structure (§, Absatz, Nummer, etc.)
    - Creates hierarchical chunks preserving legal context
    - Extracts legal-specific metadata (references, document type, etc.)
    - Preserves citation information for cross-references
    """
    
    def __init__(self):
        super().__init__()
        self.parser = GermanLawParser(enable_sentence_splitting=False)
    
    def can_handle(self, context: HandlerContext) -> bool:
        """
        Determine if this handler can process the file.
        
        Checks:
        - File extension (.txt, .pdf that might contain legal text)
        - Filename patterns (Gesetz, Verordnung, etc.)
        - Content patterns (§ symbols, legal keywords)
        """
        # Check file extension
        suffix = context.file_path.suffix.lower()
        if suffix not in ['.txt', '.pdf', '.html', '.xml']:
            return False
        
        # Check filename for legal indicators
        filename = context.file_path.name.lower()
        legal_indicators = ['gesetz', 'verordnung', 'satzung', 'richtlinie', 'vo.', 'g.']
        if any(indicator in filename for indicator in legal_indicators):
            logger.info(f"Legal text detected by filename: {context.file_path.name}")
            return True
        
        # For content-based detection, we need the content first
        # This will be checked in extract_content if needed
        return False
    
    def extract_metadata(self, context: HandlerContext) -> Dict[str, Any]:
        """
        Extract metadata specific to legal documents.
        
        Returns basic metadata that will be enriched during content extraction.
        """
        metadata = {
            "handler": "legal",
            "file": str(context.file_path),
            "filename": context.file_path.name,
            "is_legal_text": None,  # Will be determined during parsing
            "document_type": None,
            "total_chunks": 0,
            "structure_levels": []
        }
        
        return metadata
    
    def extract_content(self, context: HandlerContext, metadata: Dict[str, Any]) -> Optional[str]:
        """
        Extract and parse legal text content.
        
        Returns the full text, but also stores parsed chunks in metadata
        for specialized processing.
        """
        try:
            # Read file content
            with open(context.file_path, 'r', encoding='utf-8', errors='ignore') as f:
                content = f.read()
            
            # Check if this is actually a legal text
            if not self.parser.is_legal_text(content, context.file_path.name):
                logger.info(f"File is not a legal text: {context.file_path.name}")
                metadata['is_legal_text'] = False
                return content
            
            # Parse legal structure
            logger.info(f"Parsing legal structure for: {context.file_path.name}")
            chunks = self.parser.parse(
                content,
                filename=context.file_path.name,
                document_id=str(context.file_path)
            )
            
            # Update metadata with parsing results
            metadata['is_legal_text'] = True
            metadata['total_chunks'] = len(chunks)
            
            if chunks:
                # Detect document type from first chunk
                if chunks[0].metadata.get('document_type'):
                    metadata['document_type'] = chunks[0].metadata['document_type']
                
                # Collect unique structure levels
                levels = set(chunk.level.value for chunk in chunks)
                metadata['structure_levels'] = sorted(list(levels))
            
            # Store parsed chunks for later use
            metadata['legal_chunks'] = self.parser.chunks_to_dict(chunks)
            
            logger.info(
                f"Legal text parsed: {context.file_path.name} - "
                f"{len(chunks)} chunks, levels: {metadata['structure_levels']}"
            )
            
            return content
            
        except Exception as e:
            logger.error(f"Error extracting legal text content from {context.file_path}: {e}")
            return None
    
    def get_legal_chunks(self, metadata: Dict[str, Any]) -> List[Dict[str, Any]]:
        """
        Retrieve the parsed legal chunks from metadata.
        
        This allows the ingestion pipeline to use structured chunks
        instead of simple character-based chunking.
        """
        return metadata.get('legal_chunks', [])


__all__ = ["LegalIngestionHandler"]
