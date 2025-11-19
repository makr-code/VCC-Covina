# Ingestion Quality Improvements - Roadmap

## Übersicht

Die aktuelle Ingestion-Pipeline ist bereits sehr fortgeschritten mit:
- ✅ Legal text parsing (§, Absatz, Nummer)
- ✅ Best-practice chunking (overlap, keywords, quality scoring)
- ✅ Complete polyglot JSON export
- ✅ 4 database persistence (PostgreSQL, ChromaDB, Neo4j, CouchDB)

## Vorgeschlagene Verbesserungen

### 1. Named Entity Recognition (NER) - HOCH

**Problem**: Aktuell werden keine Entitäten wie Personen, Organisationen, Orte, Daten extrahiert.

**Lösung**: spaCy NER Integration

**Implementierung**:
```python
# ingestion/ner_extractor.py
import spacy

class GermanNERExtractor:
    """Extract named entities from German text"""
    
    def __init__(self):
        # Load German model: de_core_news_lg
        self.nlp = spacy.load("de_core_news_lg")
    
    def extract_entities(self, text: str) -> Dict[str, List[str]]:
        """
        Extract named entities from text.
        
        Returns:
            {
                'PER': ['Angela Merkel', 'Thomas Müller'],
                'ORG': ['Bundestag', 'EU-Kommission'],
                'LOC': ['Berlin', 'Deutschland'],
                'DATE': ['2023-01-15', 'Januar 2024'],
                'MONEY': ['1.000.000 EUR'],
                'LAW': ['BImSchG', 'DSGVO']
            }
        """
        doc = self.nlp(text)
        
        entities = {}
        for ent in doc.ents:
            if ent.label_ not in entities:
                entities[ent.label_] = []
            entities[ent.label_].append(ent.text)
        
        return entities
```

**Integration in Ingestion**:
```python
# In process_document_with_uds3():

# Extract entities
ner_extractor = GermanNERExtractor()
entities = ner_extractor.extract_entities(content)

# Add to metadata
metadata.update({
    'entities': entities,
    'entity_count': sum(len(v) for v in entities.values()),
    'person_count': len(entities.get('PER', [])),
    'organization_count': len(entities.get('ORG', [])),
    'location_count': len(entities.get('LOC', []))
})

# Store in ChromaDB chunks
for chunk in chunks:
    chunk_entities = ner_extractor.extract_entities(chunk.text)
    chunk.metadata['entities'] = chunk_entities
```

**Vorteile**:
- 🔍 Bessere Suche nach Personen/Organisationen
- 📊 Entity-basierte Analytics
- 🔗 Cross-Document Entity Linking
- 💡 Kontext-Anreicherung

**Aufwand**: 2-3 Tage  
**Abhängigkeiten**: `pip install spacy && python -m spacy download de_core_news_lg`

---

### 2. Legal Citation Parsing - HOCH

**Problem**: Cross-References werden erkannt, aber nicht aufgelöst.

**Lösung**: Citation Resolver mit Graph-Linking

**Implementierung**:
```python
# ingestion/parsers/citation_resolver.py

class LegalCitationResolver:
    """Resolve legal citations and create graph relationships"""
    
    def parse_citation(self, text: str) -> List[Citation]:
        """
        Parse citations like:
        - § 5 Abs. 1
        - Artikel 3 DSGVO
        - § 1 Abs. 2 Nr. 1 BImSchG
        
        Returns list of Citation objects
        """
        citations = []
        
        # § Pattern
        pattern_paragraph = r'§\s*(\d+[a-z]?)\s*(?:Abs\.\s*(\d+))?\s*(?:Nr\.\s*(\d+))?'
        
        # Artikel Pattern
        pattern_artikel = r'Artikel\s*(\d+)\s*([A-Z]+)?'
        
        for match in re.finditer(pattern_paragraph, text):
            citations.append(Citation(
                type='paragraph',
                paragraph=match.group(1),
                absatz=match.group(2),
                nummer=match.group(3),
                source_text=match.group(0)
            ))
        
        return citations
    
    def resolve_to_document(self, citation: Citation, corpus_index) -> Optional[str]:
        """
        Resolve citation to actual document ID.
        
        Example: § 5 Abs. 1 → document_id_of_containing_law
        """
        # Query ChromaDB or Neo4j for document containing this citation
        pass
    
    def create_graph_relationships(self, source_doc_id: str, citations: List[Citation]):
        """
        Create Neo4j relationships between documents.
        
        (SourceDoc)-[REFERENCES {citation: "§ 5 Abs. 1"}]->(TargetDoc)
        """
        pass
```

**Neo4j Graph Enhancement**:
```cypher
// Create citation relationships
MATCH (source:Document {id: $source_id})
MATCH (target:Document {id: $target_id})
CREATE (source)-[:REFERENCES {
    citation: "§ 5 Abs. 1",
    type: "paragraph",
    paragraph: "5",
    absatz: "1"
}]->(target)
```

**Vorteile**:
- 🔗 Automatische Cross-Reference Links
- 📊 Citation Graph Analysis
- 🔍 "Finde alle Dokumente die § 5 referenzieren"
- 💡 Abhängigkeits-Analyse

**Aufwand**: 3-4 Tage

---

### 3. Document Similarity & Clustering - MITTEL

**Problem**: Keine Ähnlichkeitsanalyse zwischen Dokumenten.

**Lösung**: Embedding-basierte Similarity + Clustering

**Implementierung**:
```python
# ingestion/similarity_analyzer.py

class DocumentSimilarityAnalyzer:
    """Analyze document similarity using embeddings"""
    
    def compute_similarity(self, doc1_id: str, doc2_id: str) -> float:
        """
        Compute cosine similarity between two documents.
        Uses average of chunk embeddings.
        """
        # Get embeddings from ChromaDB
        embeddings1 = self.get_document_embeddings(doc1_id)
        embeddings2 = self.get_document_embeddings(doc2_id)
        
        # Average embeddings
        avg_emb1 = np.mean(embeddings1, axis=0)
        avg_emb2 = np.mean(embeddings2, axis=0)
        
        # Cosine similarity
        return cosine_similarity([avg_emb1], [avg_emb2])[0][0]
    
    def find_similar_documents(self, doc_id: str, top_k: int = 5) -> List[Tuple[str, float]]:
        """Find top-k most similar documents"""
        pass
    
    def cluster_documents(self, doc_ids: List[str], n_clusters: int = 5):
        """Cluster documents using K-means on embeddings"""
        from sklearn.cluster import KMeans
        
        embeddings = [self.get_document_embeddings(doc_id) for doc_id in doc_ids]
        kmeans = KMeans(n_clusters=n_clusters)
        clusters = kmeans.fit_predict(embeddings)
        
        return clusters
```

**Neo4j Integration**:
```cypher
// Create similarity relationships
MATCH (doc1:Document {id: $doc1_id})
MATCH (doc2:Document {id: $doc2_id})
CREATE (doc1)-[:SIMILAR_TO {
    similarity_score: $score,
    method: "embedding_cosine"
}]->(doc2)
```

**Vorteile**:
- 🔍 "Finde ähnliche Dokumente"
- 📊 Automatische Kategorisierung
- 💡 Duplikat-Erkennung
- 🎯 Themen-Clustering

**Aufwand**: 2-3 Tage

---

### 4. Multi-Language Support - MITTEL

**Problem**: Nur deutsche Texte optimal unterstützt.

**Lösung**: Multi-Language NER + Parsers

**Implementierung**:
```python
# ingestion/language_detector.py

class LanguageDetector:
    """Detect document language"""
    
    def detect(self, text: str) -> str:
        """
        Detect language using langdetect.
        
        Returns: 'de', 'en', 'fr', etc.
        """
        from langdetect import detect
        return detect(text)

# ingestion/parsers/multilang_parser.py

class MultiLanguageLegalParser:
    """Legal parser for multiple languages"""
    
    def __init__(self, language: str):
        self.language = language
        self.parser = self._get_parser(language)
    
    def _get_parser(self, lang: str):
        if lang == 'de':
            return GermanLawParser()
        elif lang == 'en':
            return EnglishLegalParser()  # New
        elif lang == 'fr':
            return FrenchLegalParser()   # New
        else:
            return GenericStructuredParser()
```

**Vorteile**:
- 🌍 Internationale Dokumente
- 🔍 Multi-Language Search
- 📊 Cross-Language Analytics

**Aufwand**: 4-5 Tage (pro Sprache)

---

### 5. Table & Figure Extraction - HOCH

**Problem**: Tabellen und Abbildungen werden als Text extrahiert, Struktur geht verloren.

**Lösung**: Structured Table Extraction

**Implementierung**:
```python
# ingestion/table_extractor.py

class TableExtractor:
    """Extract tables from documents"""
    
    def extract_tables(self, file_path: str) -> List[Table]:
        """
        Extract tables from PDF/DOCX/HTML.
        
        Returns:
            [
                Table(
                    rows=[
                        ['Header1', 'Header2', 'Header3'],
                        ['Value1', 'Value2', 'Value3']
                    ],
                    caption="Tabelle 1: Messwerte",
                    page=5
                )
            ]
        """
        if file_path.endswith('.pdf'):
            return self._extract_from_pdf(file_path)
        elif file_path.endswith('.docx'):
            return self._extract_from_docx(file_path)
    
    def _extract_from_pdf(self, file_path: str) -> List[Table]:
        """Use camelot or tabula for PDF table extraction"""
        import camelot
        tables = camelot.read_pdf(file_path, pages='all')
        return [self._convert_to_table(t) for t in tables]
    
    def table_to_markdown(self, table: Table) -> str:
        """Convert table to Markdown format"""
        pass
    
    def table_to_json(self, table: Table) -> Dict:
        """Convert table to structured JSON"""
        return {
            'caption': table.caption,
            'headers': table.rows[0],
            'data': table.rows[1:],
            'page': table.page
        }
```

**ChromaDB Storage**:
```python
# Store tables as separate chunks
chunk_metadata = {
    'type': 'table',
    'table_index': 0,
    'caption': 'Tabelle 1: Messwerte',
    'row_count': 10,
    'col_count': 5,
    'page': 5
}
```

**Vorteile**:
- 📊 Strukturierte Tabellen-Suche
- 🔍 "Finde alle Tabellen mit Messwerten"
- 💡 Data Extraction aus Tabellen
- 📈 Analytics auf Tabellendaten

**Aufwand**: 3-4 Tage  
**Abhängigkeiten**: `pip install camelot-py[cv]` oder `tabula-py`

---

### 6. OCR Integration - MITTEL

**Problem**: Gescannte PDFs (Bilder) können nicht verarbeitet werden.

**Lösung**: Tesseract OCR Integration

**Implementierung**:
```python
# ingestion/ocr_processor.py

class OCRProcessor:
    """Process scanned documents with OCR"""
    
    def __init__(self):
        import pytesseract
        self.tesseract = pytesseract
    
    def is_scanned_pdf(self, file_path: str) -> bool:
        """Detect if PDF is scanned (no text layer)"""
        from pdfminer.high_level import extract_text
        text = extract_text(file_path)
        return len(text.strip()) < 100  # Heuristic
    
    def extract_text_ocr(self, file_path: str, lang: str = 'deu') -> str:
        """
        Extract text from scanned PDF using OCR.
        
        Args:
            file_path: Path to PDF
            lang: Language code ('deu', 'eng', etc.)
        """
        from pdf2image import convert_from_path
        
        # Convert PDF pages to images
        images = convert_from_path(file_path)
        
        # OCR each page
        text_pages = []
        for i, image in enumerate(images):
            text = self.tesseract.image_to_string(image, lang=lang)
            text_pages.append(f"--- Seite {i+1} ---\n{text}")
        
        return '\n\n'.join(text_pages)
```

**Integration**:
```python
# In extract_text_from_file():

if file_path.endswith('.pdf'):
    ocr_processor = OCRProcessor()
    
    if ocr_processor.is_scanned_pdf(file_path):
        logger.info(f"Scanned PDF detected, using OCR: {file_path}")
        text = ocr_processor.extract_text_ocr(file_path, lang='deu')
    else:
        text = extract_text_from_pdf(file_path)
```

**Vorteile**:
- 📄 Gescannte Dokumente verarbeitbar
- 🔍 Mehr Dokumente durchsuchbar
- 📚 Legacy-Dokumente nutzbar

**Aufwand**: 2-3 Tage  
**Abhängigkeiten**: `tesseract-ocr`, `pytesseract`, `pdf2image`

---

### 7. Metadata Enrichment (External APIs) - NIEDRIG

**Problem**: Nur interne Metadaten verfügbar.

**Lösung**: Integration externer Datenquellen

**Implementierung**:
```python
# ingestion/external_enrichment.py

class ExternalMetadataEnricher:
    """Enrich documents with external metadata"""
    
    def enrich_law_document(self, doc_id: str, law_name: str) -> Dict:
        """
        Enrich legal document with external data.
        
        Sources:
        - gesetze-im-internet.de API
        - EUR-Lex API (EU laws)
        - Bundesanzeiger API
        """
        metadata = {}
        
        # Get publication date
        metadata['publication_date'] = self._get_publication_date(law_name)
        
        # Get amendments
        metadata['amendments'] = self._get_amendments(law_name)
        
        # Get current version
        metadata['current_version'] = self._get_current_version(law_name)
        
        return metadata
    
    def enrich_company_document(self, doc_id: str, company_name: str) -> Dict:
        """
        Enrich with Handelsregister data.
        Already implemented in ingestion/services/handelsregister_client.py!
        """
        pass
```

**Vorteile**:
- 📅 Aktualitäts-Information
- 🔗 Externe Links
- 💡 Kontext-Anreicherung

**Aufwand**: 3-4 Tage (abhängig von APIs)

---

### 8. Quality Metrics Enhancement - NIEDRIG

**Problem**: Quality Score ist einfach (nur Länge + Keywords).

**Lösung**: Erweiterte Quality Metrics

**Implementierung**:
```python
# ingestion/quality_scorer.py

class AdvancedQualityScorer:
    """Compute advanced quality metrics"""
    
    def compute_quality(self, content: str, metadata: Dict) -> Dict[str, float]:
        """
        Compute comprehensive quality metrics.
        
        Returns:
            {
                'completeness': 0.95,      # Has all expected sections
                'readability': 0.85,        # Flesch reading ease
                'structure': 0.90,          # Has clear structure
                'consistency': 0.88,        # Consistent formatting
                'overall': 0.89             # Weighted average
            }
        """
        scores = {}
        
        # Completeness (has title, sections, content)
        scores['completeness'] = self._score_completeness(content, metadata)
        
        # Readability (Flesch Reading Ease for German)
        scores['readability'] = self._score_readability(content)
        
        # Structure (has headings, paragraphs, lists)
        scores['structure'] = self._score_structure(content)
        
        # Consistency (consistent formatting, no encoding errors)
        scores['consistency'] = self._score_consistency(content)
        
        # Overall score (weighted)
        scores['overall'] = (
            scores['completeness'] * 0.3 +
            scores['readability'] * 0.2 +
            scores['structure'] * 0.3 +
            scores['consistency'] * 0.2
        )
        
        return scores
    
    def _score_readability(self, text: str) -> float:
        """Flesch Reading Ease (German version)"""
        import textstat
        score = textstat.flesch_reading_ease(text)
        # Normalize to 0-1
        return max(0, min(1, score / 100))
```

**Vorteile**:
- 📊 Bessere Qualitäts-Bewertung
- 🔍 Filter nach Qualität
- 💡 Verbesserungs-Vorschläge

**Aufwand**: 1-2 Tage

---

### 9. Incremental Update Support - HOCH

**Problem**: Dokumente werden immer komplett neu verarbeitet.

**Lösung**: Incremental Updates mit Change Detection

**Implementierung**:
```python
# ingestion/change_detector.py

class DocumentChangeDetector:
    """Detect changes in documents"""
    
    def compute_hash(self, file_path: str) -> str:
        """Compute content hash (SHA256)"""
        import hashlib
        with open(file_path, 'rb') as f:
            return hashlib.sha256(f.read()).hexdigest()
    
    def has_changed(self, file_path: str, previous_hash: str) -> bool:
        """Check if document has changed"""
        current_hash = self.compute_hash(file_path)
        return current_hash != previous_hash
    
    def detect_changes(self, old_content: str, new_content: str) -> ChangeSet:
        """
        Detect what changed in document.
        
        Returns:
            ChangeSet(
                added_paragraphs=[...],
                removed_paragraphs=[...],
                modified_paragraphs=[...]
            )
        """
        import difflib
        differ = difflib.Differ()
        diff = list(differ.compare(old_content.splitlines(), new_content.splitlines()))
        
        # Parse diff to extract changes
        pass
```

**Smart Re-indexing**:
```python
# Only re-index changed chunks
if detector.has_changed(file_path, previous_hash):
    changes = detector.detect_changes(old_content, new_content)
    
    # Update only modified chunks
    for modified_para in changes.modified_paragraphs:
        update_chunk(doc_id, modified_para)
    
    # Add new chunks
    for added_para in changes.added_paragraphs:
        add_chunk(doc_id, added_para)
    
    # Remove deleted chunks
    for removed_para in changes.removed_paragraphs:
        delete_chunk(doc_id, removed_para)
```

**Vorteile**:
- ⚡ Schnellere Updates
- 💾 Weniger Ressourcen
- 📊 Change Tracking
- 🕒 Versionshistorie

**Aufwand**: 4-5 Tage

---

### 10. Semantic Section Detection - MITTEL

**Problem**: Sections werden nur durch Struktur erkannt, nicht semantisch.

**Lösung**: ML-basierte Section Classification

**Implementierung**:
```python
# ingestion/section_classifier.py

class SemanticSectionClassifier:
    """Classify document sections semantically"""
    
    def __init__(self):
        # Use transformer model for classification
        from transformers import pipeline
        self.classifier = pipeline(
            "text-classification",
            model="deepset/gbert-base"  # German BERT
        )
    
    def classify_section(self, text: str) -> str:
        """
        Classify section type.
        
        Returns: 'introduction', 'definition', 'regulation', 
                 'penalty', 'transitional', 'final'
        """
        # For legal documents
        legal_sections = [
            'Zweck',           # Purpose
            'Begriffsbestimmungen',  # Definitions
            'Anwendungsbereich',     # Scope
            'Pflichten',             # Obligations
            'Rechte',                # Rights
            'Sanktionen',            # Penalties
            'Übergangsbestimmungen', # Transitional
            'Schlussbestimmungen'    # Final provisions
        ]
        
        result = self.classifier(text)
        return result[0]['label']
```

**Vorteile**:
- 🎯 Bessere Suche ("Finde alle Definitionen")
- 📊 Section-basierte Analytics
- 💡 Automatische Strukturierung

**Aufwand**: 3-4 Tage

---

## Priorisierung

### Quick Wins (1-2 Wochen)
1. ✅ **NER Integration** (Hoch, 2-3 Tage)
2. ✅ **Table Extraction** (Hoch, 3-4 Tage)
3. ✅ **Citation Parsing** (Hoch, 3-4 Tage)

### Medium Term (2-4 Wochen)
4. ✅ **OCR Integration** (Mittel, 2-3 Tage)
5. ✅ **Document Similarity** (Mittel, 2-3 Tage)
6. ✅ **Quality Metrics** (Niedrig, 1-2 Tage)
7. ✅ **Semantic Sections** (Mittel, 3-4 Tage)

### Long Term (1-3 Monate)
8. ✅ **Incremental Updates** (Hoch, 4-5 Tage)
9. ✅ **Multi-Language** (Mittel, 4-5 Tage pro Sprache)
10. ✅ **External APIs** (Niedrig, 3-4 Tage)

## ROI Analysis

| Feature | Aufwand | Impact | ROI |
|---------|---------|--------|-----|
| NER | 2-3d | Sehr Hoch | ⭐⭐⭐⭐⭐ |
| Citation Parsing | 3-4d | Sehr Hoch | ⭐⭐⭐⭐⭐ |
| Table Extraction | 3-4d | Hoch | ⭐⭐⭐⭐ |
| OCR | 2-3d | Mittel-Hoch | ⭐⭐⭐⭐ |
| Document Similarity | 2-3d | Mittel | ⭐⭐⭐ |
| Incremental Updates | 4-5d | Hoch | ⭐⭐⭐⭐ |
| Quality Metrics | 1-2d | Niedrig-Mittel | ⭐⭐⭐ |
| Semantic Sections | 3-4d | Mittel | ⭐⭐⭐ |
| Multi-Language | 4-5d | Mittel | ⭐⭐⭐ |
| External APIs | 3-4d | Niedrig | ⭐⭐ |

## Empfehlung: Phase 1 Implementation

**Start mit Top 3** (High ROI, 8-11 Tage):

1. **Named Entity Recognition** (2-3 Tage)
   - Immediate value: Person/Org/Location extraction
   - Foundation for advanced features
   - Easy integration

2. **Legal Citation Parsing** (3-4 Tage)
   - Core feature for legal documents
   - Enables graph analysis
   - High user value

3. **Table Extraction** (3-4 Tage)
   - Common pain point
   - Structured data capture
   - Enhanced search

**Total**: 8-11 Tage für signifikante Verbesserungen

## Nächste Schritte

Welche Features sollen priorisiert werden?
- Top 3 sofort starten?
- Andere Prioritäten?
- Spezielle Anforderungen?
