# UDS3 Backend Worker

Der **UDS3 Backend Worker** ist ein spezialisierter Worker für die Integration des UDS3 API Backends mit der optimierten Unified Database Strategy. Er ermöglicht die strategische Verteilung von Verwaltungsdokumenten auf Vector-, Graph- und Relational-Datenbanken mit automatischer Prozessanalyse und Compliance-Prüfung.

## 🎯 Funktionen

### Kernfeatures
- **UDS3 Backend Integration**: Vollständige Integration mit `uds3_api_backend.py`
- **Multi-Database Distribution**: Strategische Verteilung auf Vector-, Graph- und Relational-DBs
- **LLM-basierte Prozessanalyse**: Ollama LLM Integration für Verwaltungsprozess-Analyse
- **Knowledge Base Matching**: Automatische Zuordnung zu UDS3 Wissensbasis
- **Compliance-Prüfung**: Rechtliche Compliance-Bewertung nach deutschem Verwaltungsrecht
- **Quality Assessment**: Multi-dimensionale Qualitätsbewertung

### Worker Registry Kompatibilität
✅ **Standard Task Processing**: `process_task()`  
✅ **Document Processing**: `process_document()`  
✅ **Quality Assessment**: `assess_quality()`  
✅ **Batch Operations**: `batch_process()`  
✅ **Service Management**: `start_service()`, `stop_service()`

## 📋 Processing-Modi

### 1. ANALYSIS_ONLY
```python
worker = get_uds3_analysis_worker()
```
- Nur Analyse ohne DB-Speicherung
- LLM-basierte Prozessanalyse
- Knowledge Base Matching
- Ideal für: Content-Analyse, Compliance-Checks

### 2. STORE_UNIFIED
```python
worker = get_uds3_backend_worker(ProcessingMode.STORE_UNIFIED)
```
- Speicherung in alle Datenbank-Typen
- Vollständige UDS3 Integration
- Comprehensive Analysis + Storage
- Ideal für: Vollständige Dokumentverarbeitung

### 3. STORE_SELECTIVE
```python
worker = get_uds3_backend_worker(ProcessingMode.STORE_SELECTIVE)
```
- Intelligente DB-Auswahl basierend auf Dokument-Kategorie
- Optimierte Storage-Strategie
- Ressourcen-effizient
- Ideal für: Große Dokumentmengen

### 4. QUALITY_ASSESSMENT
```python
worker = get_uds3_quality_worker()
```
- Fokus auf Quality Scoring
- Ohne LLM-Processing (schneller)
- Compliance-Bewertung
- Ideal für: Quality Control Pipelines

### 5. BATCH_PROCESSING
```python
worker = get_uds3_batch_worker()
```
- Batch-orientierte Verarbeitung
- Hoher Durchsatz
- Automatische Batch-Bildung
- Ideal für: Bulk-Verarbeitung

## 🗂️ Dokument-Kategorien

Der Worker klassifiziert Dokumente automatisch in:

### ADMINISTRATIVE_DECISION
- Bescheide, Verfügungen, Genehmigungen
- **DB-Strategie**: Relational + Graph
- **Keywords**: bescheid, verfügung, genehmigung, ablehnung

### LEGAL_NORM
- Gesetze, Verordnungen, Richtlinien
- **DB-Strategie**: Vector + Graph
- **Keywords**: gesetz, verordnung, richtlinie, vorschrift

### PROCESS_DOCUMENTATION
- Verfahrensabläufe, Workflows
- **DB-Strategie**: Graph + Relational
- **Keywords**: verfahren, prozess, ablauf, workflow

### COMPLIANCE_DOCUMENT
- Compliance-Checklisten, Prüfunterlagen
- **DB-Strategie**: Vector + Relational
- **Keywords**: compliance, konformität, vorschrift, regelung

### KNOWLEDGE_ENTRY
- Wissensbasis-Einträge (Fallback)
- **DB-Strategie**: Vector only
- **Keywords**: Alle anderen Dokumente

## 🚀 Verwendung

### Basic Usage
```python
from ingestion_worker_uds3_backend import get_uds3_backend_worker, ProcessingMode

# Worker erstellen
worker = get_uds3_backend_worker(
    processing_mode=ProcessingMode.STORE_UNIFIED,
    enable_llm=True,
    batch_size=10
)

# Dokument verarbeiten
result = worker.process_document("bauantrag.pdf")

# Task-orientierte Verarbeitung
task = {
    'file_path': 'bescheid.txt',
    'content': 'Verwaltungsbescheid...',
    'metadata': {'author': 'Bauaufsichtsamt'}
}
task_result = worker.process_task(task)
```

### Quality Assessment
```python
quality_worker = get_uds3_quality_worker()

job_data = {
    'content': document_content,
    'metadata': document_metadata,
    'file_path': 'document.pdf'
}

quality_result = quality_worker.assess_quality(job_data)
print(f"Quality Score: {quality_result['quality_assessment']['overall_score']}")
```

### Batch Processing
```python
batch_worker = get_uds3_batch_worker()

# Dokumente zur Batch-Queue hinzufügen
for file_path in document_paths:
    batch_worker.add_to_batch(file_path)

# Batch wird automatisch verarbeitet bei Erreichen der batch_size
```

## 📊 Results & Outputs

### UDS3ProcessingResult
```python
@dataclass
class UDS3ProcessingResult:
    document_id: str
    processing_mode: ProcessingMode
    document_category: DocumentCategory
    
    # UDS3 Analysis
    process_analysis: Optional[Any]      # LLM-Analyse-Ergebnis
    knowledge_matches: List[Dict]        # Knowledge Base Matches
    element_suggestions: List[Dict]      # Prozess-Element-Vorschläge
    
    # Database Results
    vector_result: Optional[Dict]        # Vector DB Operationen
    graph_result: Optional[Dict]         # Graph DB Operationen  
    relational_result: Optional[Dict]    # Relational DB Operationen
    
    # Quality Metrics
    processing_duration: float
    quality_score: float                 # 0.0 - 1.0
    compliance_status: str               # "compliant"|"issues_found"|"needs_review"
    error_messages: List[str]
```

### Worker Registry Result
```python
{
    'status': 'completed',
    'worker_id': 'uds3_backend',
    'file_path': 'document.pdf',
    'processing_duration_seconds': 2.5,
    'quality_score': 0.85,
    'compliance_status': 'compliant',
    'uds3_result': {UDS3ProcessingResult},
    'database_operations': {
        'vector': [...],
        'graph': [...],
        'relational': [...]
    }
}
```

## 🔧 Configuration

### Environment Dependencies
- **UDS3 Backend**: `uds3_api_backend.py` (optional, Fallback verfügbar)
- **UDS3 Core**: `uds3_core.py` (optional, Fallback verfügbar)
- **Follow-up Tasks**: `ingestion_module_document_followup_task_system.py` (optional)
- **Config**: `config.py` (optional)

### LLM Configuration
- **Ollama Model**: Standardmäßig `llama3.1`
- **LLM Enable/Disable**: Über `enable_llm` Parameter
- **Timeout**: 30 Sekunden für LLM-Calls

### Batch Configuration
```python
worker = get_uds3_backend_worker(
    batch_size=50,              # Items pro Batch
    processing_mode=ProcessingMode.BATCH_PROCESSING
)
```

## 📈 Quality Metrics

### Quality Score Komponenten
- **Content Quality**: Länge, Struktur, Vollständigkeit
- **UDS3 Compliance**: Compliance mit UDS3 Standards
- **Database Distribution**: Erfolg der DB-Operationen
- **Process Analysis**: Qualität der LLM-Analyse
- **Knowledge Matching**: Relevanz der Knowledge Base Matches

### Compliance Status
- **compliant**: Alle Compliance-Checks bestanden
- **issues_found**: Compliance-Probleme identifiziert
- **needs_review**: Manuelle Überprüfung erforderlich

## 🧪 Testing

### Integration Test ausführen
```bash
python test_uds3_backend_worker_integration.py
```

### Einzeltest ausführen
```bash
python ingestion_worker_uds3_backend.py
```

### Test Coverage
- ✅ Processing-Modi (4 Modi)
- ✅ Dokument-Kategorisierung
- ✅ Worker Registry Integration
- ✅ Quality Assessment
- ✅ Batch Processing
- ✅ Error Handling
- ✅ Fallback-Modi

## 🔌 Worker Registry Integration

### Auto-Registration
Der Worker registriert sich automatisch bei der Worker Registry:

```python
# Standard UDS3 Backend Worker
registry.register_worker(
    worker_name="uds3_backend",
    processor_function=get_uds3_backend_worker,
    supported_formats=['.pdf', '.docx', '.txt', '.md', '.html', '.xml', '.json'],
    worker_type="uds3_backend"
)

# UDS3 Analysis Worker  
registry.register_worker(
    worker_name="uds3_analysis", 
    processor_function=get_uds3_analysis_worker,
    worker_type="uds3_analysis"
)

# UDS3 Quality Worker
registry.register_worker(
    worker_name="uds3_quality",
    processor_function=get_uds3_quality_worker,
    worker_type="quality"
)
```

## 🎛️ Follow-up Tasks Integration

Bei verfügbarem Follow-up Task System werden automatisch Tasks generiert:

### Compliance Tasks
- **Trigger**: Compliance-Issues gefunden
- **Priority**: HIGH
- **Type**: SECURITY_SCAN

### Knowledge Base Updates
- **Trigger**: Wenige Knowledge Matches gefunden
- **Priority**: MEDIUM  
- **Type**: BATCH_PROCESS

## 📊 Statistics & Monitoring

```python
stats = worker.get_stats()
# {
#     'documents_processed': 42,
#     'database_operations': 126,
#     'analysis_performed': 38,
#     'quality_assessments': 42,
#     'errors_encountered': 2
# }
```

## 🚨 Error Handling

### Graceful Degradation
- **UDS3 Backend nicht verfügbar**: Fallback ohne LLM-Analyse
- **Unified Strategy fehlt**: Simplified DB-Operations
- **LLM-Timeout**: Regelbasierte Fallback-Analyse
- **Follow-up Tasks fehlt**: Weiter ohne Task-Generierung

### Error Recovery
- Einzeldokument-Fehler stoppen nicht Batch-Processing
- Detaillierte Error-Messages in Results
- Comprehensive Logging für Debugging

## 📝 Beispiele

### Bauantrag-Verarbeitung
```python
# Bauantrag mit vollständiger UDS3 Analysis
worker = get_uds3_backend_worker(ProcessingMode.STORE_UNIFIED, enable_llm=True)

bauantrag_content = """
BAUGENEHMIGUNG
Aktenzeichen: BA-2024-001234
Das Bauvorhaben entspricht der BayBO...
"""

result = worker.process_document_with_uds3(
    file_path="bauantrag_001234.pdf",
    content=bauantrag_content,
    metadata={'authority': 'Bauaufsichtsamt München'},
    processing_mode=ProcessingMode.STORE_UNIFIED
)

print(f"Category: {result.document_category.value}")
print(f"Quality: {result.quality_score:.2f}")
print(f"Compliance: {result.compliance_status}")
```

### Quality-Pipeline
```python
# Quality-Pipeline für Document Validation
quality_worker = get_uds3_quality_worker()

for document in document_collection:
    quality_result = quality_worker.assess_quality({
        'content': document.content,
        'metadata': document.metadata,
        'file_path': document.path
    })
    
    if quality_result['quality_assessment']['overall_score'] < 0.7:
        print(f"Quality Issue: {document.path}")
        # Trigger manual review
```

## 🔄 Integration mit VERITAS

Der UDS3 Backend Worker ist vollständig integriert in das VERITAS-System:

- **Follow-up Tasks**: Automatische Task-Generierung für Compliance-Issues
- **Worker Registry**: Standard-konforme Registration und Task-Processing  
- **Quality Framework**: Integriert in VERITAS Quality Assessment Pipeline
- **Database Strategy**: Nutzt VERITAS UDS3 Multi-Database Architecture
- **Config System**: Verwendet VERITAS Config-Management

---

**Autor**: VERITAS Development Team  
**Version**: 1.0  
**Datum**: 13. September 2024  
**Lizenz**: VERITAS Protected Module