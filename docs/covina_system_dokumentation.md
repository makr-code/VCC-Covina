# Covina System - Technische Dokumentation

## Überblick

Das Covina Document Processing System ist eine fortschrittliche Lösung für die **automatisierte Verarbeitung und Analyse von Rechtsdokumenten** mit KI-basierter Klassifikation und RAG-Enhancement.

## Hauptfunktionen

### 🔍 Intelligente Dokumentenanalyse
- **Automatische Klassifikation** von Rechtsdokumenten
- **DSGVO-konforme** Verarbeitung personenbezogener Daten
- **Multi-Format-Unterstützung**: PDF, DOCX, TXT, RTF, ODT, **Markdown**

### 🎯 Kuratierte Inhalte
- **Händische Kuration** mit Metadaten-JSON-Dateien
- **Prioritäts-Boost** für kuratierte Dokumente im RAG-System
- **Quality-Scoring** basierend auf Metadaten-Vollständigkeit

### 🚀 RAG-Enhancement
- **Retrieval-Augmented Generation** für präzise Antworten
- **Semantische Suche** mit Embedding-Vectoren
- **Context-Aware Retrieval** mit Relevanz-Scoring

## Architektur

```
┌─────────────────┐    ┌──────────────────┐    ┌─────────────────┐
│   Frontend GUI  │───▶│  Backend API     │───▶│  UDS3 Framework │
│   Enhanced UI   │    │  FastAPI Server  │    │  Multi-DB Layer │
└─────────────────┘    └──────────────────┘    └─────────────────┘
                                │
                                ▼
                       ┌──────────────────┐
                       │   Databases      │
                       │ • PostgreSQL     │
                       │ • ChromaDB       │
                       │ • Neo4j Graph    │
                       │ • SQLite Fallback│
                       └──────────────────┘
```

## Installation

### Voraussetzungen
- Python 3.13+
- Node.js 18+ (optional für Web-Interface)
- PostgreSQL 15+ (optional, SQLite Fallback verfügbar)

### Setup
```bash
# Repository klonen
git clone https://github.com/covina/document-processing
cd document-processing

# Dependencies installieren
pip install -r requirements.txt

# Backend starten
python covina_backend.py

# GUI starten (separates Terminal)
python enhanced_covina_gui.py
```

## Konfiguration

### Backend-Konfiguration
Die Backend-Konfiguration erfolgt über `config.py`:

```python
# Database Settings
POSTGRESQL_URL = "postgresql://user:pass@localhost:5432/covina"
CHROMA_PERSIST_DIR = "./data/chroma"
NEO4J_URI = "bolt://localhost:7687"

# Processing Settings
MAX_CONCURRENT_JOBS = 3
DEFAULT_BATCH_SIZE = 50
ENABLE_DSGVO_COMPLIANCE = True
```

### Kuratierte Dateien
Für optimale RAG-Performance erstellen Sie Metadaten-JSON-Dateien:

```json
{
  "title": "Technische Dokumentation",
  "description": "Vollständige Systemdokumentation...",
  "keywords": ["API", "Backend", "RAG", "Documentation"],
  "curator": "Tech Team",
  "content_type": "technical_documentation",
  "importance_level": "high"
}
```

## API-Endpunkte

### Upload & Processing
- `POST /upload/files` - Datei-Upload
- `POST /upload/curated` - **Kuratierte Dateien** (hohe Priorität)
- `POST /upload/directory` - Verzeichnis-Upload

### Monitoring & Management
- `GET /health` - System-Status
- `GET /jobs` - Job-Übersicht
- `GET /monitoring/performance` - Performance-Metriken

### DSGVO & Compliance
- `GET /dsgvo/pii-report` - PII-Analyse-Bericht
- `POST /dsgvo/access-request` - DSGVO-Auskunftsanfrage
- `POST /dsgvo/erasure-request` - Löschungsanfrage

## Performance-Optimierung

### Batch-Processing
- **Kleine Batches** (10-25 Dateien) für kuratierte Inhalte
- **Große Batches** (50-100 Dateien) für Standard-Verarbeitung
- **Auto-Scaling** basierend auf System-Ressourcen

### Resource-Management
- **CPU-basierte Worker-Skalierung** (1-16 parallele Jobs)
- **Memory-Monitoring** mit automatischen Limits
- **Disk I/O Optimierung** für große Verzeichnisse

## Troubleshooting

### Häufige Probleme

#### Backend nicht erreichbar
```bash
# Backend-Status prüfen
curl http://localhost:8001/health

# Logs prüfen
tail -f covina_backend.log
```

#### Hohe Memory-Nutzung
- Batch-Größe reduzieren (`DEFAULT_BATCH_SIZE = 25`)
- Parallele Jobs limitieren (`MAX_CONCURRENT_JOBS = 2`)
- SQLite-Fallback aktivieren bei DB-Problemen

#### Neo4j Kompatibilität (Python 3.13)
```python
# Workaround für Socket-Issues
import socket
socket.EAI_ADDRFAMILY = socket.EAI_FAIL
```

## Support & Community

- 📧 **Support**: support@covina-system.de
- 🐛 **Issues**: [GitHub Issues](https://github.com/covina/document-processing/issues)
- 📚 **Wiki**: [Technical Wiki](https://github.com/covina/document-processing/wiki)
- 💬 **Discussions**: [GitHub Discussions](https://github.com/covina/document-processing/discussions)

## Roadmap

### Q4 2025
- ✅ Kuratierte Dateien-Unterstützung
- ✅ Enhanced GUI mit Resource-Monitoring
- 🔄 Web-Interface (React + FastAPI)
- 🔄 Advanced RAG mit LangChain

### Q1 2026
- 🔮 Multi-Language Support (EN/FR/ES)
- 🔮 Cloud-Deployment (AWS/Azure)
- 🔮 Advanced Analytics Dashboard
- 🔮 ML-basierte Auto-Curation

## Lizenz

Copyright (c) 2025 Covina System. Alle Rechte vorbehalten.

---

**Dokumentation-Version**: 1.2.0  
**Letzte Aktualisierung**: 03.10.2025  
**Nächste Review**: 01.11.2025