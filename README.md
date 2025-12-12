# Covina - VCC Ingestion Pipeline

**Die Dokumenten-Ingestion und Validierungs-Pipeline des Virtual Compliance Center (VCC)**

## 📋 Übersicht

**Version:** 3.4.10+ (Production Ready) ⭐⭐⭐⭐⭐  
**Status:** Microservices Architecture - Fully Operational

Covina ist die zentrale **Ingestion-Pipeline** des [Virtual Compliance Center (VCC)](https://github.com/makr-code/VCC) Ökosystems. Das System orchestriert einen geschlossenen Prozesskreis für Dokumenten-Aufnahme, Wissenslücken-Erkennung und kontinuierliche Datenvalidierung.

### 🎯 Kernaufgabe

Covina bildet das **Rückgrat der Datenaufnahme** im VCC und stellt sicher, dass alle Dokumente:
- ✅ **Erfasst** werden (automatisierte Ingestion)
- ✅ **Validiert** werden (Qualitätssicherung, DSGVO-Compliance)
- ✅ **Anonymisiert** werden (PII-Redaction, Datenschutz)
- ✅ **Analysiert** werden (Gap Detection, Wissenslücken)
- ✅ **Persistiert** werden (UDS3 Polyglot Persistence)

### 🔄 Prozesskreis (Closed-Loop)

```
┌─────────────────────────────────────────────────────────────┐
│               COVINA PROZESSKREIS (Closed-Loop)             │
│                                                             │
│  INGESTION → GAP DETECTION → VALIDATION → [INGESTION]      │
│  (Aufnahme)  (Lücken)        (Prüfung)     (Nacherfassung) │
└─────────────────────────────────────────────────────────────┘
         ↓                    ↓                    ↓
   ┌──────────┐         ┌──────────┐         ┌──────────┐
   │ VERITAS  │         │  CLARA   │         │ ThemisDB │
   │ (ChatAI) │         │  (LoRa)  │         │  (Data)  │
   └──────────┘         └──────────┘         └──────────┘
```

**Technologie-Stack:**
Python 3.9+, FastAPI, ChromaDB, Neo4j, PostgreSQL, CouchDB, WebSockets

## ✨ Hauptfunktionen

### 🔹 Dokumenten-Ingestion
- Hochperformante Batch-Verarbeitung (187+ Dokumente/Sekunde)
- Multi-Format Support (PDF, DOC, TXT, HTML, etc.)
- Worker Pool Architecture (36 I/O + 36 CPU Workers)
- Streaming Upload für große Dateien (Memory-optimiert)
- Auto-Resume Mechanismus bei System-Restart

### 🔹 Validierung & Compliance
- **DSGVO-Compliance:** Automatisierte PII-Erkennung und Redaction
- **Datenqualität:** Quality Metrics, Anomalie-Erkennung
- **Gap Detection:** KI-gestützte Wissenslücken-Analyse
- **Review Queue:** Manuelle Freigabe-Workflows

### 🔹 Anonymisierung & Datenschutz
- Named Entity Recognition (NER) für PII-Erkennung
- Automatische Schwärzung sensibler Daten
- Audit-Trail für alle Datenverarbeitungen
- DSGVO-konforme Speicherung

### 🔹 UDS3 Polyglot Persistence
- **PostgreSQL:** Relationale Master-Daten & Metadaten
- **ChromaDB:** Vektoren für semantische Suche (Real Embeddings)
- **Neo4j:** Wissensgraph & Beziehungen
- **CouchDB:** Vollständige Dokumentenspeicherung

## 🏗️ Architektur

### Microservices (Dual-Backend)

Covina nutzt eine **Microservices-Architektur** mit zwei spezialisierten Backends:

```
Main Backend (Port 45678)          Ingestion Backend (Port 45679)
├─ Query APIs                      ├─ Document Upload
├─ DSGVO Compliance                ├─ Batch Processing  
├─ Review Queue                    ├─ Worker Pool (36 I/O + 36 CPU)
├─ Golden Datasets                 ├─ UDS3 Integration
├─ Graph Patterns                  ├─ Job Management
└─ Governance Policies             └─ WebSocket Updates
```

**Vorteile:**
- ✅ Komplette Isolation (Ingestion blockiert nie Query-APIs)
- ✅ Unabhängige Skalierung (je nach Last)
- ✅ Fehler-Isolation (Crash in einem Service isoliert)
- ✅ Deployment-Flexibilität (unabhängige Updates)

### VCC Ecosystem Integration

Covina ist integraler Bestandteil des **VCC (Virtual Compliance Center)** Ökosystems:

**Covina ↔ VERITAS (Legal ChatAI):**
- Liefert validierte Daten für Chat-Kontext
- Empfängt User-Feedback und Anfragen für fehlende Dokumente

**Covina ↔ Clara (LoRa, Golden-Datasets, LLM-as-Judge):**
- Liefert validierte Dokumente als Training-Daten
- Empfängt LLM-Bewertungen und Quality-Scores

**Covina ↔ ThemisDB (Persistence):**
- Bidirektionale Synchronisation
- ThemisDB als VCC-weite Sharding-Lösung

## 🚀 Schnellstart

### Voraussetzungen
- Python 3.9+
- PostgreSQL, ChromaDB, Neo4j, CouchDB (siehe Datenbank-Setup)

### Installation & Start

```bash
# Repository klonen
git clone https://github.com/makr-code/VCC-Covina.git
cd VCC-Covina

# Virtuelle Umgebung erstellen
python -m venv venv
source venv/bin/activate  # Linux/Mac
# oder: .\venv\Scripts\activate  # Windows

# Abhängigkeiten installieren
pip install -r requirements.txt

# Umgebungsvariablen konfigurieren
cp .env.example .env.production
# .env.production editieren (Datenbank-Verbindungen)

# Services starten (PowerShell)
.\scripts\start_services.ps1

# Oder einzeln starten:
python backend/main.py          # Main Backend (Port 45678)
python backend/ingestion.py     # Ingestion Backend (Port 45679)
```

### Health Checks

```bash
curl http://localhost:45678/health  # Main Backend
curl http://localhost:45679/health  # Ingestion Backend
```

## 📚 Dokumentation

### Quickstart & Guides
- [QUICKSTART.md](QUICKSTART.md) - Schnellstart-Anleitung für Entwickler
- [DEVELOPMENT.md](DEVELOPMENT.md) - Entwickler-Dokumentation
- [CONTRIBUTING.md](CONTRIBUTING.md) - Beitragsrichtlinien

### Architektur & Design
- [MICROSERVICES_ARCHITECTURE.md](docs/MICROSERVICES_ARCHITECTURE.md) - Microservices-Design
- [VCC_COVINA_EVOLUTION_STRATEGY.md](docs/VCC_COVINA_EVOLUTION_STRATEGY.md) - Langfristige Strategie
- [INGESTION_ARCHITECTURE_COMPLETE_ANALYSIS.md](docs/INGESTION_ARCHITECTURE_COMPLETE_ANALYSIS.md) - Ingestion-Architektur

### Performance & Optimierung
- [PERFORMANCE_BASELINE_REPORT.md](docs/PERFORMANCE_BASELINE_REPORT.md) - Performance-Tests & Benchmarks
- [UPLOAD_SOLUTIONS_ROADMAP.md](docs/UPLOAD_SOLUTIONS_ROADMAP.md) - Upload-Optimierungs-Roadmap
- [PRODUCTION_DEPLOYMENT_OPTIMIZATIONS.md](docs/PRODUCTION_DEPLOYMENT_OPTIMIZATIONS.md) - Production Optimierungen

### Roadmap & Releases
- [ROADMAP.md](ROADMAP.md) - Entwicklungs-Roadmap 2025-2027
- [CHANGELOG.md](CHANGELOG.md) - Versions-Historie

**Umfang:** 100+ Dokumentations-Dateien im `/docs` Verzeichnis

## 🎯 Production Features

### Robustheit & Zuverlässigkeit
- ✅ **Auto-Resume:** Automatische Fortsetzung unterbrochener Jobs
- ✅ **Ghost Cleanup:** Bereinigung inkonsistenter Job-States
- ✅ **Circuit Breaker:** Automatische Fehler-Isolation
- ✅ **Memory Manager:** Speicher-Überwachung & -Optimierung
- ✅ **Error Recovery:** Automatisches Retry mit Exponential Backoff

### Monitoring & Observability
- ✅ **Prometheus Metrics:** Performance-Metriken exportiert
- ✅ **Structured Logging:** JSON-Logs für zentrale Aggregation
- ✅ **Health Endpoints:** Service-Health-Checks
- ✅ **WebSocket Updates:** Real-Time Job-Status Updates

### Security & Compliance
- ✅ **DSGVO-konform:** Automatisierte PII-Redaction
- ✅ **Audit-Trail:** Vollständige Nachvollziehbarkeit aller Operationen
- ✅ **Access Control:** Role-Based Access Control (RBAC)
- ✅ **Encryption:** Verschlüsselte Datenspeicherung

## 🔗 VCC Ecosystem

Covina ist Teil des **Virtual Compliance Center (VCC)** Projekts:

### VCC Services
- **[VCC](https://github.com/makr-code/VCC)** - Virtual Compliance Center (Hauptprojekt)
- **[Covina](https://github.com/makr-code/VCC-Covina)** - Ingestion Pipeline (dieses Repository)
- **VERITAS** - Legal ChatAI User Frontend
- **Clara** - LoRa Golden-Datasets & LLM-as-Judge
- **ThemisDB** - VCC-weite Persistence Layer

### Integration Points
- Event-Driven Architecture (Apache Kafka geplant)
- Shared Data Layer (UDS3 Polyglot Persistence)
- OpenAPI 3.1 Standardization
- WebSocket Real-Time Updates

## 📊 Performance

**Aktuelle Benchmarks (v3.4.10):**
- **Upload-Throughput:** 187 Dokumente/Sekunde (100% Success Rate)
- **Query-Throughput:** 280 Queries/Sekunde (P95: <1100ms)
- **Worker Pool:** 36 I/O Threads + 36 CPU Processes
- **Memory-Optimiert:** Streaming Upload (-83% Memory Usage)

**Skalierungs-Roadmap:**
- **Phase 1 (Linux):** 250-320 docs/sec, 1000-2000 q/sec
- **Phase 2 (SSD/NVMe):** 500-1200 docs/sec
- **Phase 3 (Horizontal):** 2000-6000 docs/sec
- **Phase 4 (Cloud-Native):** 10K-50K docs/sec

Siehe [UPLOAD_SOLUTIONS_ROADMAP.md](docs/UPLOAD_SOLUTIONS_ROADMAP.md) für Details.

## 🛠️ Technologie-Stack

### Backend
- **Python 3.9+** - Hauptprogrammiersprache
- **FastAPI** - High-Performance Web Framework
- **Uvicorn** - ASGI Server
- **Pydantic** - Datenvalidierung

### Databases (UDS3 Polyglot Persistence)
- **PostgreSQL** - Relationale Daten, Metadaten
- **ChromaDB** - Vektor-Embeddings, Semantische Suche
- **Neo4j** - Knowledge Graph, Beziehungen
- **CouchDB** - Dokumenten-Storage

### AI/ML
- **sentence-transformers** - Text Embeddings (all-MiniLM-L6-v2)
- **spaCy** - Named Entity Recognition (NER)
- **LLM Integration** - Für Gap Detection & Validation

### Infrastructure
- **Docker** - Containerisierung
- **Kubernetes** - Orchestration (geplant)
- **Prometheus** - Metrics & Monitoring
- **WebSockets** - Real-Time Updates

## 📄 Lizenz

Private Repository - Alle Rechte vorbehalten

## 👤 Autor

**makr-code** - [GitHub](https://github.com/makr-code)

## 🙏 Acknowledgments

Teil des **Virtual Compliance Center (VCC)** Ökosystems - Eine umfassende Lösung für Compliance-Management mit:
- **Covina:** Ingestion & Validation Pipeline
- **VERITAS:** Legal ChatAI User Frontend  
- **Clara:** Golden-Datasets & LLM-as-Judge
- **ThemisDB:** Distributed Persistence Layer

---

**Status:** ✅ **Production Ready** (v3.4.10+)  
**Rating:** ⭐⭐⭐⭐⭐ 5.0/5  
**Letzte Aktualisierung:** Dezember 2025
