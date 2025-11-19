#!/usr/bin/env python3
"""
Legal Citation Parser and Resolver

Parses legal citations from German legal texts and creates graph relationships:
- § 5 Abs. 1
- Artikel 3 DSGVO
- § 1 Abs. 2 Nr. 1 lit. a BImSchG

Author: Covina System
Date: November 2025
"""

import re
import logging
from typing import List, Dict, Optional, Tuple
from dataclasses import dataclass
from enum import Enum

logger = logging.getLogger(__name__)


class CitationType(Enum):
    """Types of legal citations"""
    PARAGRAPH = "paragraph"         # § 5
    ARTIKEL = "artikel"             # Artikel 3
    ABSATZ = "absatz"              # Abs. 1
    NUMMER = "nummer"              # Nr. 1
    BUCHSTABE = "buchstabe"        # lit. a / Buchstabe a
    LAW_REFERENCE = "law"          # BImSchG, DSGVO


@dataclass
class Citation:
    """Legal citation with all components"""
    type: CitationType
    text: str                       # Original text: "§ 5 Abs. 1"
    paragraph: Optional[str] = None # "5", "5a"
    absatz: Optional[int] = None    # 1, 2, 3
    nummer: Optional[int] = None    # 1, 2, 3
    buchstabe: Optional[str] = None # "a", "b", "c"
    law_name: Optional[str] = None  # "BImSchG", "DSGVO"
    start_pos: int = 0
    end_pos: int = 0
    
    def to_reference(self) -> str:
        """
        Convert to canonical reference string.
        
        Examples:
            § 5 Abs. 1 Nr. 2 lit. a BImSchG
            Artikel 3 DSGVO
        """
        parts = []
        
        if self.paragraph:
            parts.append(f"§ {self.paragraph}")
        
        if self.absatz:
            parts.append(f"Abs. {self.absatz}")
        
        if self.nummer:
            parts.append(f"Nr. {self.nummer}")
        
        if self.buchstabe:
            parts.append(f"lit. {self.buchstabe}")
        
        if self.law_name:
            parts.append(self.law_name)
        
        return " ".join(parts)
    
    def to_dict(self) -> Dict:
        """Convert to dictionary for storage"""
        return {
            'type': self.type.value,
            'text': self.text,
            'reference': self.to_reference(),
            'paragraph': self.paragraph,
            'absatz': self.absatz,
            'nummer': self.nummer,
            'buchstabe': self.buchstabe,
            'law_name': self.law_name,
            'start_pos': self.start_pos,
            'end_pos': self.end_pos
        }


class LegalCitationParser:
    """
    Parse legal citations from German legal texts.
    
    Supported patterns:
    - § 5
    - § 5a
    - § 5 Abs. 1
    - § 5 Abs. 1 Nr. 2
    - § 5 Abs. 1 Nr. 2 lit. a
    - Artikel 3
    - Artikel 3 Abs. 1
    - § 5 BImSchG
    - § 5 Abs. 1 BImSchG
    """
    
    # Regex patterns
    PARAGRAPH_PATTERN = r'§\s*(\d+[a-z]?)'
    ABSATZ_PATTERN = r'Abs(?:atz)?\.\s*(\d+)'
    NUMMER_PATTERN = r'(?:Nr\.|Nummer)\s*(\d+)'
    BUCHSTABE_PATTERN = r'(?:lit\.|Buchstabe)\s*([a-z])'
    ARTIKEL_PATTERN = r'Artikel\s+(\d+)'
    LAW_PATTERN = r'\b([A-ZÄÖÜ]{2,10})\b'
    
    def parse(self, text: str) -> List[Citation]:
        """
        Parse all citations from text.
        
        Args:
            text: Input text
            
        Returns:
            List of Citation objects
        """
        citations = []
        
        # Find all paragraph references (§ X ...)
        for match in re.finditer(self.PARAGRAPH_PATTERN, text):
            citation = self._parse_paragraph_citation(text, match)
            if citation:
                citations.append(citation)
        
        # Find all Artikel references
        for match in re.finditer(self.ARTIKEL_PATTERN, text):
            citation = self._parse_artikel_citation(text, match)
            if citation:
                citations.append(citation)
        
        return citations
    
    def _parse_paragraph_citation(self, text: str, match: re.Match) -> Optional[Citation]:
        """
        Parse a paragraph citation starting at match position.
        
        Example: § 5 Abs. 1 Nr. 2 lit. a BImSchG
        """
        start_pos = match.start()
        paragraph = match.group(1)
        
        # Look ahead for additional components (expanded to 150 chars)
        rest_text = text[match.end():match.end() + 150]
        
        # Parse Absatz
        absatz = None
        absatz_match = re.search(self.ABSATZ_PATTERN, rest_text)
        if absatz_match:
            absatz = int(absatz_match.group(1))
        
        # Parse Nummer
        nummer = None
        nummer_match = re.search(self.NUMMER_PATTERN, rest_text)
        if nummer_match:
            nummer = int(nummer_match.group(1))
        
        # Parse Buchstabe
        buchstabe = None
        buchstabe_match = re.search(self.BUCHSTABE_PATTERN, rest_text)
        if buchstabe_match:
            buchstabe = buchstabe_match.group(1)
        
        # Determine furthest component position
        furthest_pos = 0
        if buchstabe_match:
            furthest_pos = buchstabe_match.end()
        elif nummer_match:
            furthest_pos = nummer_match.end()
        elif absatz_match:
            furthest_pos = absatz_match.end()
        
        # Look for law name AFTER all components
        law_name = None
        if furthest_pos > 0:
            # Search after the last component
            law_search_text = rest_text[furthest_pos:furthest_pos + 50]
        else:
            law_search_text = rest_text[:50]
        
        law_match = re.search(self.LAW_PATTERN, law_search_text)
        if law_match:
            potential_law = law_match.group(1)
            # Filter common German words
            if potential_law not in ['UND', 'ODER', 'DER', 'DIE', 'DAS', 'VON', 'AUS', 'IST', 'DIES']:
                law_name = potential_law
        
        # Determine end position
        end_pos = match.end()
        if law_match and law_name:
            # Law is after components
            if furthest_pos > 0:
                end_pos = match.end() + furthest_pos + law_match.end()
            else:
                end_pos = match.end() + law_match.end()
        elif buchstabe_match:
            end_pos = match.end() + buchstabe_match.end()
        elif nummer_match:
            end_pos = match.end() + nummer_match.end()
        elif absatz_match:
            end_pos = match.end() + absatz_match.end()
        
        # Extract original text
        original_text = text[start_pos:end_pos].strip()
        
        citation = Citation(
            type=CitationType.PARAGRAPH,
            text=original_text,
            paragraph=paragraph,
            absatz=absatz,
            nummer=nummer,
            buchstabe=buchstabe,
            law_name=law_name,
            start_pos=start_pos,
            end_pos=end_pos
        )
        
        return citation
    
    def _parse_artikel_citation(self, text: str, match: re.Match) -> Optional[Citation]:
        """
        Parse an Artikel citation.
        
        Example: Artikel 3 DSGVO
        """
        start_pos = match.start()
        artikel = match.group(1)
        
        # Look ahead for law name
        rest_text = text[match.end():match.end() + 50]
        
        law_name = None
        law_match = re.search(self.LAW_PATTERN, rest_text)
        if law_match:
            potential_law = law_match.group(1)
            if potential_law not in ['UND', 'ODER', 'DER', 'DIE', 'DAS']:
                law_name = potential_law
        
        end_pos = match.end()
        if law_match and law_name:
            end_pos = match.end() + law_match.end()
        
        original_text = text[start_pos:end_pos]
        
        citation = Citation(
            type=CitationType.ARTIKEL,
            text=original_text,
            paragraph=artikel,  # Store as paragraph for consistency
            law_name=law_name,
            start_pos=start_pos,
            end_pos=end_pos
        )
        
        return citation
    
    def find_cross_references(self, text: str) -> List[str]:
        """
        Find all cross-references in text.
        
        Returns:
            ['§ 5 Abs. 1', '§ 10', 'Artikel 3 DSGVO']
        """
        citations = self.parse(text)
        return [c.to_reference() for c in citations]
    
    def group_by_law(self, citations: List[Citation]) -> Dict[str, List[Citation]]:
        """
        Group citations by law name.
        
        Returns:
            {
                'BImSchG': [Citation(...), Citation(...)],
                'DSGVO': [Citation(...)]
            }
        """
        grouped = {}
        for citation in citations:
            law = citation.law_name or 'unknown'
            if law not in grouped:
                grouped[law] = []
            grouped[law].append(citation)
        return grouped


class CitationGraphBuilder:
    """
    Build Neo4j graph relationships from citations.
    
    Creates:
        (SourceDoc)-[:REFERENCES {citation: "§ 5 Abs. 1"}]->(TargetDoc)
    """
    
    def __init__(self, neo4j_driver=None):
        """
        Initialize graph builder.
        
        Args:
            neo4j_driver: Neo4j driver instance
        """
        self.driver = neo4j_driver
    
    def create_citation_relationship(
        self,
        source_doc_id: str,
        target_doc_id: str,
        citation: Citation
    ):
        """
        Create citation relationship in Neo4j.
        
        Cypher:
            MATCH (source:Document {id: $source_id})
            MATCH (target:Document {id: $target_id})
            CREATE (source)-[:REFERENCES {
                citation: "§ 5 Abs. 1",
                type: "paragraph",
                paragraph: "5",
                absatz: 1
            }]->(target)
        """
        if not self.driver:
            logger.warning("[Citation] No Neo4j driver available")
            return
        
        query = """
        MATCH (source:Document {id: $source_id})
        MATCH (target:Document {id: $target_id})
        CREATE (source)-[:REFERENCES {
            citation: $citation,
            type: $type,
            paragraph: $paragraph,
            absatz: $absatz,
            nummer: $nummer,
            buchstabe: $buchstabe,
            law_name: $law_name
        }]->(target)
        """
        
        params = {
            'source_id': source_doc_id,
            'target_id': target_doc_id,
            'citation': citation.to_reference(),
            'type': citation.type.value,
            'paragraph': citation.paragraph,
            'absatz': citation.absatz,
            'nummer': citation.nummer,
            'buchstabe': citation.buchstabe,
            'law_name': citation.law_name
        }
        
        try:
            with self.driver.session() as session:
                session.run(query, params)
            logger.info(f"[Citation] Created relationship: {source_doc_id} -> {target_doc_id}")
        except Exception as e:
            logger.error(f"[Citation] Failed to create relationship: {e}")


# Convenience functions
def parse_citations(text: str) -> List[Citation]:
    """
    Convenience function to parse citations.
    
    Example:
        citations = parse_citations("Siehe § 5 Abs. 1 BImSchG")
        # [Citation(paragraph='5', absatz=1, law_name='BImSchG')]
    """
    parser = LegalCitationParser()
    return parser.parse(text)


def find_cross_references(text: str) -> List[str]:
    """
    Convenience function to find cross-references.
    
    Example:
        refs = find_cross_references("Siehe § 5 und Artikel 3 DSGVO")
        # ['§ 5', 'Artikel 3 DSGVO']
    """
    parser = LegalCitationParser()
    return parser.find_cross_references(text)
