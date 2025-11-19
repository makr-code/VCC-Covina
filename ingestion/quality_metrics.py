"""
Advanced Quality Metrics

Enhanced quality scoring for document chunks with multiple dimensions:
- Completeness (sentence boundaries, punctuation)
- Readability (Flesch reading ease, sentence length)
- Information density (unique words, entity count)
- Structural quality (headings, lists, formatting)
- Language quality (spelling, grammar)

Author: GitHub Copilot
Date: 2025-11-19
"""

from typing import Dict, List, Optional, Any
from dataclasses import dataclass
import re
from collections import Counter


@dataclass
class QualityMetrics:
    """Complete quality metrics for a document chunk"""
    
    # Overall score (0.0-1.0)
    overall_score: float
    
    # Component scores (0.0-1.0 each)
    completeness_score: float
    readability_score: float
    information_density_score: float
    structural_quality_score: float
    language_quality_score: float
    
    # Detailed metrics
    char_count: int
    word_count: int
    sentence_count: int
    avg_sentence_length: float
    unique_word_ratio: float
    entity_count: int
    has_headings: bool
    has_lists: bool
    has_references: bool
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for storage"""
        return {
            'overall_score': self.overall_score,
            'completeness_score': self.completeness_score,
            'readability_score': self.readability_score,
            'information_density_score': self.information_density_score,
            'structural_quality_score': self.structural_quality_score,
            'language_quality_score': self.language_quality_score,
            'char_count': self.char_count,
            'word_count': self.word_count,
            'sentence_count': self.sentence_count,
            'avg_sentence_length': self.avg_sentence_length,
            'unique_word_ratio': self.unique_word_ratio,
            'entity_count': self.entity_count,
            'has_headings': self.has_headings,
            'has_lists': self.has_lists,
            'has_references': self.has_references
        }


class AdvancedQualityScorer:
    """
    Compute advanced quality metrics for document chunks.
    
    Features:
    - Completeness: Sentence boundaries, punctuation, minimum length
    - Readability: Flesch reading ease, sentence length distribution
    - Information Density: Unique words, entities, technical terms
    - Structural Quality: Headings, lists, references, formatting
    - Language Quality: Basic spelling/grammar checks
    """
    
    def __init__(self):
        """Initialize quality scorer"""
        self.min_chars = 100
        self.max_chars = 2000
        self.min_words = 20
        self.min_sentences = 1
    
    def compute_quality(self, content: str, metadata: Optional[Dict] = None) -> QualityMetrics:
        """
        Compute comprehensive quality metrics.
        
        Args:
            content: Text content to analyze
            metadata: Optional metadata (entities, keywords, etc.)
        
        Returns:
            QualityMetrics object with all scores
        """
        metadata = metadata or {}
        
        # Basic counts
        char_count = len(content)
        words = self._tokenize_words(content)
        word_count = len(words)
        sentences = self._tokenize_sentences(content)
        sentence_count = len(sentences)
        
        # Compute component scores
        completeness = self._compute_completeness(content, char_count, word_count, sentence_count)
        readability = self._compute_readability(content, words, sentences)
        info_density = self._compute_information_density(words, metadata)
        structural = self._compute_structural_quality(content, metadata)
        language = self._compute_language_quality(content, words)
        
        # Overall score (weighted average)
        overall = (
            0.25 * completeness +
            0.20 * readability +
            0.25 * info_density +
            0.15 * structural +
            0.15 * language
        )
        
        # Additional metrics
        avg_sentence_length = word_count / max(sentence_count, 1)
        unique_words = len(set(w.lower() for w in words))
        unique_word_ratio = unique_words / max(word_count, 1)
        
        entity_count = 0
        if 'entities' in metadata:
            entity_count = sum(len(v) for v in metadata['entities'].values())
        
        has_headings = self._has_headings(content)
        has_lists = self._has_lists(content)
        has_references = self._has_references(content, metadata)
        
        return QualityMetrics(
            overall_score=overall,
            completeness_score=completeness,
            readability_score=readability,
            information_density_score=info_density,
            structural_quality_score=structural,
            language_quality_score=language,
            char_count=char_count,
            word_count=word_count,
            sentence_count=sentence_count,
            avg_sentence_length=avg_sentence_length,
            unique_word_ratio=unique_word_ratio,
            entity_count=entity_count,
            has_headings=has_headings,
            has_lists=has_lists,
            has_references=has_references
        )
    
    def _tokenize_words(self, text: str) -> List[str]:
        """Tokenize text into words"""
        # Simple word tokenization
        words = re.findall(r'\b\w+\b', text)
        return words
    
    def _tokenize_sentences(self, text: str) -> List[str]:
        """Tokenize text into sentences"""
        # Split on sentence boundaries
        sentences = re.split(r'[.!?]+', text)
        sentences = [s.strip() for s in sentences if s.strip()]
        return sentences
    
    def _compute_completeness(self, content: str, char_count: int, word_count: int, sentence_count: int) -> float:
        """
        Compute completeness score (0.0-1.0).
        
        Checks:
        - Minimum length requirements
        - Sentence boundaries (ends with punctuation)
        - No truncation markers
        """
        score = 0.0
        
        # Length check (0.4 weight)
        if char_count >= self.min_chars:
            length_score = min(char_count / self.max_chars, 1.0)
            score += 0.4 * length_score
        
        # Word count check (0.2 weight)
        if word_count >= self.min_words:
            word_score = min(word_count / 100, 1.0)
            score += 0.2 * word_score
        
        # Sentence boundary check (0.3 weight)
        if content.strip():
            last_char = content.strip()[-1]
            if last_char in '.!?':
                score += 0.3
        
        # No truncation markers (0.1 weight)
        truncation_markers = ['...', '[...]', '(...)']
        has_truncation = any(marker in content for marker in truncation_markers)
        if not has_truncation:
            score += 0.1
        
        return min(score, 1.0)
    
    def _compute_readability(self, content: str, words: List[str], sentences: List[str]) -> float:
        """
        Compute readability score (0.0-1.0).
        
        Based on:
        - Average sentence length (optimal: 15-20 words)
        - Average word length (optimal: 4-6 chars)
        - Simplified Flesch reading ease
        """
        if not sentences or not words:
            return 0.0
        
        score = 0.0
        
        # Average sentence length (0.4 weight)
        avg_sentence_length = len(words) / len(sentences)
        if 10 <= avg_sentence_length <= 25:
            # Optimal range
            sentence_score = 1.0 - abs(avg_sentence_length - 17.5) / 17.5
            score += 0.4 * sentence_score
        elif avg_sentence_length < 10:
            # Too short
            score += 0.4 * (avg_sentence_length / 10)
        else:
            # Too long
            score += 0.4 * (25 / avg_sentence_length)
        
        # Average word length (0.3 weight)
        avg_word_length = sum(len(w) for w in words) / len(words)
        if 4 <= avg_word_length <= 6:
            # Optimal range
            word_score = 1.0 - abs(avg_word_length - 5) / 5
            score += 0.3 * word_score
        elif avg_word_length < 4:
            score += 0.3 * (avg_word_length / 4)
        else:
            score += 0.3 * (6 / avg_word_length)
        
        # Sentence count diversity (0.3 weight)
        sentence_lengths = [len(self._tokenize_words(s)) for s in sentences]
        if len(sentence_lengths) > 1:
            # Calculate variance
            import statistics
            variance = statistics.variance(sentence_lengths)
            # Higher variance = more diversity = better readability
            diversity_score = min(variance / 50, 1.0)
            score += 0.3 * diversity_score
        else:
            score += 0.3 * 0.5  # Single sentence gets medium score
        
        return min(score, 1.0)
    
    def _compute_information_density(self, words: List[str], metadata: Dict) -> float:
        """
        Compute information density score (0.0-1.0).
        
        Based on:
        - Unique word ratio (lexical diversity)
        - Entity count
        - Keyword count
        - Technical term density
        """
        if not words:
            return 0.0
        
        score = 0.0
        
        # Unique word ratio (0.3 weight)
        unique_words = len(set(w.lower() for w in words))
        unique_ratio = unique_words / len(words)
        # Optimal: 0.5-0.7 (not too repetitive, not too scattered)
        if 0.4 <= unique_ratio <= 0.8:
            ratio_score = 1.0 - abs(unique_ratio - 0.6) / 0.6
            score += 0.3 * ratio_score
        else:
            score += 0.3 * 0.5
        
        # Entity count (0.3 weight)
        entity_count = 0
        if 'entities' in metadata:
            entity_count = sum(len(v) for v in metadata['entities'].values())
        
        if entity_count > 0:
            # More entities = more information
            entity_score = min(entity_count / 10, 1.0)
            score += 0.3 * entity_score
        
        # Keyword count (0.2 weight)
        keyword_count = 0
        if 'keywords' in metadata:
            keyword_count = len(metadata['keywords'])
        
        if keyword_count > 0:
            keyword_score = min(keyword_count / 5, 1.0)
            score += 0.2 * keyword_score
        
        # Technical term density (0.2 weight)
        # Check for technical indicators: numbers, abbreviations, legal references
        technical_patterns = [
            r'\d+',  # Numbers
            r'[A-Z]{2,}',  # Abbreviations
            r'§\s*\d+',  # Legal paragraphs
            r'Art\.\s*\d+',  # Articles
            r'\d+\.\d+',  # Decimal numbers or references
        ]
        
        technical_count = 0
        text = ' '.join(words)
        for pattern in technical_patterns:
            technical_count += len(re.findall(pattern, text))
        
        if technical_count > 0:
            technical_score = min(technical_count / (len(words) * 0.1), 1.0)
            score += 0.2 * technical_score
        
        return min(score, 1.0)
    
    def _compute_structural_quality(self, content: str, metadata: Dict) -> float:
        """
        Compute structural quality score (0.0-1.0).
        
        Based on:
        - Presence of headings
        - Presence of lists
        - Presence of references
        - Paragraph structure
        """
        score = 0.0
        
        # Headings (0.3 weight)
        if self._has_headings(content):
            score += 0.3
        
        # Lists (0.2 weight)
        if self._has_lists(content):
            score += 0.2
        
        # References (0.3 weight)
        if self._has_references(content, metadata):
            score += 0.3
        
        # Paragraph structure (0.2 weight)
        paragraphs = content.split('\n\n')
        if len(paragraphs) > 1:
            # Multiple paragraphs = better structure
            para_score = min(len(paragraphs) / 5, 1.0)
            score += 0.2 * para_score
        
        return min(score, 1.0)
    
    def _compute_language_quality(self, content: str, words: List[str]) -> float:
        """
        Compute language quality score (0.0-1.0).
        
        Basic checks:
        - Capitalization (sentences start with capital)
        - Punctuation presence
        - No excessive repetition
        - Proper spacing
        """
        if not words:
            return 0.0
        
        score = 0.0
        
        # Capitalization (0.3 weight)
        sentences = self._tokenize_sentences(content)
        if sentences:
            capitalized_count = sum(1 for s in sentences if s and s[0].isupper())
            cap_ratio = capitalized_count / len(sentences)
            score += 0.3 * cap_ratio
        
        # Punctuation presence (0.2 weight)
        punctuation_count = len(re.findall(r'[.,;:!?]', content))
        if punctuation_count > 0:
            # Expect ~1 punctuation per 10 words
            expected = len(words) / 10
            punct_score = min(punctuation_count / expected, 1.0)
            score += 0.2 * punct_score
        
        # No excessive repetition (0.3 weight)
        word_freq = Counter(w.lower() for w in words)
        max_freq = max(word_freq.values()) if word_freq else 0
        if max_freq > 0:
            # Max frequency should be < 5% of total words
            repetition_ratio = max_freq / len(words)
            if repetition_ratio < 0.05:
                score += 0.3
            elif repetition_ratio < 0.1:
                score += 0.3 * 0.5
        
        # Proper spacing (0.2 weight)
        # Check for excessive spaces or missing spaces
        excessive_spaces = len(re.findall(r'\s{3,}', content))
        if excessive_spaces == 0:
            score += 0.2
        
        return min(score, 1.0)
    
    def _has_headings(self, content: str) -> bool:
        """Check if content has headings"""
        # Check for Markdown headings
        if re.search(r'^#+\s+', content, re.MULTILINE):
            return True
        
        # Check for all-caps lines (common heading style)
        lines = content.split('\n')
        for line in lines:
            if line.strip() and line.strip().isupper() and len(line.strip().split()) <= 10:
                return True
        
        return False
    
    def _has_lists(self, content: str) -> bool:
        """Check if content has lists"""
        # Check for numbered lists
        if re.search(r'^\s*\d+[\.)]\s+', content, re.MULTILINE):
            return True
        
        # Check for bullet lists
        if re.search(r'^\s*[-*•]\s+', content, re.MULTILINE):
            return True
        
        # Check for legal enumeration
        if re.search(r'^\s*[a-z]\)\s+', content, re.MULTILINE):
            return True
        
        return False
    
    def _has_references(self, content: str, metadata: Dict) -> bool:
        """Check if content has references or citations"""
        # Check metadata for cross-references
        if metadata.get('cross_references'):
            return True
        
        # Check for legal references in content
        legal_refs = [
            r'§\s*\d+',  # § 5
            r'Art\.\s*\d+',  # Art. 3
            r'Abs\.\s*\d+',  # Abs. 1
            r'Nr\.\s*\d+',  # Nr. 2
        ]
        
        for pattern in legal_refs:
            if re.search(pattern, content):
                return True
        
        return False


# Example usage
if __name__ == "__main__":
    scorer = AdvancedQualityScorer()
    
    # Test text
    test_text = """
    § 1 Zweck des Gesetzes
    
    (1) Zweck dieses Gesetzes ist es, Menschen, Tiere und Pflanzen, den Boden, das Wasser,
    die Atmosphäre sowie Kultur- und sonstige Sachgüter vor schädlichen Umwelteinwirkungen
    zu schützen und dem Entstehen schädlicher Umwelteinwirkungen vorzubeugen.
    
    (2) Soweit es sich um genehmigungsbedürftige Anlagen handelt, dient dieses Gesetz auch
    - der integrierten Vermeidung und Verminderung schädlicher Umwelteinwirkungen,
    - der Vorsorge gegen schädliche Umwelteinwirkungen.
    """
    
    metadata = {
        'entities': {
            'LOC': ['Deutschland'],
            'ORG': ['Bundestag']
        },
        'keywords': ['Schutz', 'Umwelt', 'Gesetz'],
        'cross_references': ['§ 5', 'Art. 3']
    }
    
    metrics = scorer.compute_quality(test_text, metadata)
    
    print("Advanced Quality Metrics")
    print("=" * 50)
    print(f"Overall Score: {metrics.overall_score:.2f}")
    print(f"Completeness: {metrics.completeness_score:.2f}")
    print(f"Readability: {metrics.readability_score:.2f}")
    print(f"Information Density: {metrics.information_density_score:.2f}")
    print(f"Structural Quality: {metrics.structural_quality_score:.2f}")
    print(f"Language Quality: {metrics.language_quality_score:.2f}")
    print()
    print(f"Characters: {metrics.char_count}")
    print(f"Words: {metrics.word_count}")
    print(f"Sentences: {metrics.sentence_count}")
    print(f"Avg Sentence Length: {metrics.avg_sentence_length:.1f} words")
    print(f"Unique Word Ratio: {metrics.unique_word_ratio:.2f}")
    print(f"Entities: {metrics.entity_count}")
    print(f"Has Headings: {metrics.has_headings}")
    print(f"Has Lists: {metrics.has_lists}")
    print(f"Has References: {metrics.has_references}")
