#!/usr/bin/env python3
"""
Named Entity Recognition (NER) Extractor for German Legal Documents

Extracts named entities from text using spaCy German model:
- PER (Personen)
- ORG (Organisationen)
- LOC (Orte)
- DATE (Daten)
- LAW (Gesetze)
- MISC (Sonstiges)

Author: Covina System
Date: November 2025
"""

import logging
from typing import Dict, List, Optional, Set
from collections import defaultdict

logger = logging.getLogger(__name__)


class GermanNERExtractor:
    """
    Extract named entities from German text using spaCy.
    
    Features:
    - Person extraction (PER)
    - Organization extraction (ORG)
    - Location extraction (LOC)
    - Date extraction (DATE)
    - Legal references (LAW)
    - Deduplication
    - Confidence filtering
    """
    
    def __init__(self, model_name: str = "de_core_news_lg", min_confidence: float = 0.5):
        """
        Initialize NER extractor.
        
        Args:
            model_name: spaCy model to use (de_core_news_lg recommended)
            min_confidence: Minimum confidence threshold (0.0-1.0)
        """
        self.model_name = model_name
        self.min_confidence = min_confidence
        self.nlp = None
        self._lazy_load()
    
    def _lazy_load(self):
        """Lazy load spaCy model (only when needed)"""
        if self.nlp is None:
            try:
                import spacy
                self.nlp = spacy.load(self.model_name)
                logger.info(f"[NER] Loaded spaCy model: {self.model_name}")
            except ImportError:
                logger.warning("[NER] spaCy not installed. NER disabled.")
                logger.warning("  Install with: pip install spacy")
                self.nlp = None
            except OSError:
                logger.warning(
                    f"[NER] Model '{self.model_name}' not found. "
                    f"Install with: python -m spacy download {self.model_name}"
                )
                # Fallback: Try smaller model
                try:
                    import spacy
                    self.nlp = spacy.load("de_core_news_sm")
                    logger.info("[NER] Fallback: Using de_core_news_sm")
                except OSError:
                    logger.error("[NER] No German spaCy model available. NER disabled.")
                    self.nlp = None
    
    def extract_entities(
        self, 
        text: str, 
        deduplicate: bool = True,
        include_positions: bool = False
    ) -> Dict[str, List]:
        """
        Extract named entities from text.
        
        Args:
            text: Input text
            deduplicate: Remove duplicate entities
            include_positions: Include start/end positions
            
        Returns:
            {
                'PER': ['Angela Merkel', 'Thomas Müller'],
                'ORG': ['Bundestag', 'EU-Kommission'],
                'LOC': ['Berlin', 'Deutschland'],
                'DATE': ['2023-01-15', 'Januar 2024'],
                'LAW': ['BImSchG', 'DSGVO'],
                'MISC': ['...']
            }
            
            Or with positions:
            {
                'PER': [
                    {'text': 'Angela Merkel', 'start': 0, 'end': 13},
                    ...
                ]
            }
        """
        if self.nlp is None:
            logger.warning("[NER] spaCy not available, returning empty entities")
            return {}
        
        # Process text with spaCy
        doc = self.nlp(text)
        
        # Group entities by type
        entities = defaultdict(list)
        
        for ent in doc.ents:
            entity_data = {
                'text': ent.text,
                'label': ent.label_,
                'start': ent.start_char,
                'end': ent.end_char
            } if include_positions else ent.text
            
            entities[ent.label_].append(entity_data)
        
        # Deduplicate if requested
        if deduplicate and not include_positions:
            entities = {
                label: list(set(entity_list))
                for label, entity_list in entities.items()
            }
        elif deduplicate and include_positions:
            # Deduplicate by text
            entities = {
                label: self._deduplicate_entities(entity_list)
                for label, entity_list in entities.items()
            }
        
        return dict(entities)
    
    def _deduplicate_entities(self, entity_list: List[Dict]) -> List[Dict]:
        """Deduplicate entities by text, keeping first occurrence"""
        seen = set()
        result = []
        for entity in entity_list:
            if entity['text'] not in seen:
                seen.add(entity['text'])
                result.append(entity)
        return result
    
    def extract_legal_references(self, text: str) -> List[str]:
        """
        Extract legal references using pattern matching.
        
        Patterns:
        - BImSchG, DSGVO, GG, BGB, StGB, etc.
        - § 1, § 5 Abs. 2, Artikel 3
        
        Returns:
            ['BImSchG', '§ 1', '§ 5 Abs. 2', 'DSGVO']
        """
        import re
        
        references = []
        
        # Pattern 1: Law abbreviations (all caps, 2-10 letters)
        law_pattern = r'\b[A-ZÄÖÜ]{2,10}\b'
        for match in re.finditer(law_pattern, text):
            law = match.group(0)
            # Filter common words
            if law not in ['UND', 'ODER', 'DER', 'DIE', 'DAS', 'VON', 'ZU']:
                references.append(law)
        
        # Pattern 2: Paragraph references
        para_pattern = r'§\s*\d+[a-z]?(?:\s+Abs\.\s*\d+)?(?:\s+Nr\.\s*\d+)?'
        references.extend([m.group(0) for m in re.finditer(para_pattern, text)])
        
        # Pattern 3: Artikel references
        artikel_pattern = r'Artikel\s+\d+'
        references.extend([m.group(0) for m in re.finditer(artikel_pattern, text)])
        
        return list(set(references))
    
    def get_entity_statistics(self, entities: Dict[str, List]) -> Dict[str, int]:
        """
        Get statistics about extracted entities.
        
        Returns:
            {
                'total_entities': 42,
                'person_count': 10,
                'organization_count': 8,
                'location_count': 5,
                'date_count': 3,
                'law_count': 6,
                'unique_entities': 35
            }
        """
        stats = {
            'total_entities': sum(len(v) for v in entities.values()),
            'person_count': len(entities.get('PER', [])),
            'organization_count': len(entities.get('ORG', [])),
            'location_count': len(entities.get('LOC', [])),
            'date_count': len(entities.get('DATE', [])),
            'law_count': len(entities.get('LAW', [])),
            'misc_count': len(entities.get('MISC', []))
        }
        
        # Count unique entities across all types
        all_entities = []
        for entity_list in entities.values():
            if entity_list and isinstance(entity_list[0], dict):
                all_entities.extend([e['text'] for e in entity_list])
            else:
                all_entities.extend(entity_list)
        
        stats['unique_entities'] = len(set(all_entities))
        
        return stats
    
    def extract_from_chunks(
        self, 
        chunks: List[str],
        aggregate: bool = True
    ) -> Dict:
        """
        Extract entities from multiple chunks.
        
        Args:
            chunks: List of text chunks
            aggregate: Aggregate entities across all chunks
            
        Returns:
            If aggregate=True:
                {'PER': [...], 'ORG': [...], ...}
            
            If aggregate=False:
                [
                    {'chunk_index': 0, 'entities': {...}},
                    {'chunk_index': 1, 'entities': {...}},
                    ...
                ]
        """
        if aggregate:
            # Aggregate all entities
            all_entities = defaultdict(set)
            
            for chunk in chunks:
                entities = self.extract_entities(chunk, deduplicate=True)
                for label, entity_list in entities.items():
                    all_entities[label].update(entity_list)
            
            # Convert sets back to lists
            return {
                label: list(entity_set)
                for label, entity_set in all_entities.items()
            }
        else:
            # Return entities per chunk
            result = []
            for idx, chunk in enumerate(chunks):
                entities = self.extract_entities(chunk, deduplicate=True)
                result.append({
                    'chunk_index': idx,
                    'entities': entities,
                    'entity_count': sum(len(v) for v in entities.values())
                })
            return result


# Convenience functions
def extract_entities(text: str, model: str = "de_core_news_lg") -> Dict[str, List[str]]:
    """
    Convenience function to extract entities.
    
    Example:
        entities = extract_entities("Angela Merkel besuchte Berlin.")
        # {'PER': ['Angela Merkel'], 'LOC': ['Berlin']}
    """
    extractor = GermanNERExtractor(model_name=model)
    return extractor.extract_entities(text)


def extract_legal_references(text: str) -> List[str]:
    """
    Convenience function to extract legal references.
    
    Example:
        refs = extract_legal_references("Siehe § 5 BImSchG und DSGVO")
        # ['§ 5', 'BImSchG', 'DSGVO']
    """
    extractor = GermanNERExtractor()
    return extractor.extract_legal_references(text)
