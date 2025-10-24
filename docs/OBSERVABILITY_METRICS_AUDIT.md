# Observability & Metrics Audit Report
**Datum:** 21. Oktober 2025  
**System:** Covina Document Management (Main + Ingestion Backend)  
**Auditor:** GitHub Copilot  
**Status:** 🟡 TEILWEISE IMPLEMENTIERT

---

## Executive Summary

**Zweck:** Bewertung der Observability-Infrastruktur (Metriken, Tracing, Logs, Dashboards, Alerts, SLOs).

**Bewertung:**
- ✅ **Strukturiertes Logging:** Vorhanden (Python logging, Formatierung)
- ⚠️ **Technische Metriken:** Teilweise (Pool-Stats via `/db/pool`, keine Worker-Queue-Metriken)
- ❌ **Business-Metriken:** Nicht implementiert (Dokumente/min, Fehlerquote, Recovery-Erfolg)
- ❌ **Distributed Tracing:** Nicht vorhanden (OpenTelemetry fehlt)
- ❌ **PII-Log-Redaktion:** Nicht implementiert (Risiko: Datenlecks in Logs)
- ❌ **Dashboards/Alerts:** Nicht vorhanden (kein Grafana/Prometheus)[reine Datenbereitstellung]
- ❌ **SLO/SLAs:** Nicht definiert

**Risiko-Einschätzung:** 🟡 MEDIUM  
**Empfohlene Maßnahmen:** 5 Quick Wins + 3 mittel- bis langfristige Maßnahmen

---

## 1. Technische Metriken

### 1.1 Vorhandene Metriken

✅ **PostgreSQL Connection Pool:**
- Endpoint: `GET /db/pool`
- Metriken: `total_created`, `total_reused`, `total_errors`, `reuse_rate`
- Location: `main_backend.py` Line ~595

✅ **System Resources (Health):**
- CPU/Memory/Disk Prozent
- Location: `main_backend.py` Line ~580 (`health_check()`)

✅ **Worker Pool Konfiguration:**
- I/O Workers: 36
- CPU Workers: 36
- Location: `.env.production`, `ingestion_backend.py`

### 1.2 Fehlende Metriken

❌ **Worker-Queue-Länge:**
- Keine Queue-Tiefe für I/O/CPU Pools
- Kein Monitoring für Backlog/Starvation
- **Risiko:** Überlastung unsichtbar

❌ **Chunk-Dauer:**
- Keine Latenz-Metriken pro Dokument/Chunk
- Keine P95/P99-Latenzen
- **Risiko:** Performance-Regression unerkannt

❌ **DB-Latenzen (pro DB):**
- Keine separaten Metriken für PostgreSQL/ChromaDB/Neo4j/CouchDB
- Kein Latenz-Tracking für Batch vs. Single Insert
- **Risiko:** Bottlenecks nicht isolierbar

❌ **SAGA-Step-Dauer:**
- Keine Metriken für individuelle SAGA-Steps
- Kein Compensation-Tracking
- **Risiko:** SAGA-Performance unklar

### 1.3 Empfohlene Quick Wins

**QW-1: Prometheus Client Library integrieren**
```bash
pip install prometheus-client
```

**QW-2: Basic Metrics exportieren**
```python
from prometheus_client import Counter, Histogram, Gauge, make_asgi_app

# Counters
documents_processed = Counter('covina_documents_processed_total', 'Total processed', ['status'])
db_operations = Counter('covina_db_operations_total', 'DB ops', ['database', 'operation'])

# Histograms
document_latency = Histogram('covina_document_processing_seconds', 'Latency')
db_latency = Histogram('covina_db_operation_seconds', 'DB latency', ['database'])

# Gauges
queue_depth = Gauge('covina_queue_depth', 'Queue depth', ['pool'])
pool_connections = Gauge('covina_pool_connections', 'Pool conns', ['state'])

# Endpoint
metrics_app = make_asgi_app()
app.mount("/metrics", metrics_app)
```

**Location:** `main_backend.py`, `ingestion_backend.py`

---

## 2. Business-Metriken

### 2.1 Fehlende Metriken

❌ **Dokumente/Minute:**
- Kein Throughput-Tracking
- **Impact:** SLA-Validation unmöglich

❌ **Fehlerquote:**
- Keine aggregierte Error-Rate
- **Impact:** Service-Qualität unklar

❌ **Blocked Files:**
- Anzahl blockierter Files (Recovery-System)
- **Impact:** Operational Health unklar

❌ **Recovery-Erfolg:**
- Keine Success-Rate für Auto-Resume/Retry
- **Impact:** Resilienz-Qualität unbekannt

### 2.2 Empfohlene Implementierung

```python
# Business Metrics
documents_per_minute = Gauge('covina_documents_per_minute', 'Docs/min')
error_rate = Gauge('covina_error_rate', 'Error rate')
blocked_files = Gauge('covina_blocked_files_total', 'Blocked files')
recovery_success_rate = Gauge('covina_recovery_success_rate', 'Recovery success')

# Update in process_document():
start_time = time.time()
try:
    # ... processing ...
    documents_processed.labels(status='success').inc()
finally:
    duration = time.time() - start_time
    document_latency.observe(duration)
```

---

## 3. Distributed Tracing (OpenTelemetry)

### 3.1 Status

❌ **OpenTelemetry:** Nicht implementiert
- Keine Trace-Context-Propagation über Ingestion → UDS3 → DBs
- Keine Span-Instrumentierung
- **Risiko:** Request-Flow nicht nachvollziehbar, Bottlenecks schwer zu diagnostizieren

### 3.2 Empfohlene Implementierung

**QW-3: OpenTelemetry Integration**
```bash
pip install opentelemetry-api opentelemetry-sdk opentelemetry-instrumentation-fastapi opentelemetry-exporter-otlp
```

```python
from opentelemetry import trace
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import BatchSpanProcessor
from opentelemetry.exporter.otlp.proto.grpc.trace_exporter import OTLPSpanExporter
from opentelemetry.instrumentation.fastapi import FastAPIInstrumentor

# Setup
trace.set_tracer_provider(TracerProvider())
otlp_exporter = OTLPSpanExporter(endpoint="http://localhost:4317")
trace.get_tracer_provider().add_span_processor(BatchSpanProcessor(otlp_exporter))

# Auto-Instrumentation
FastAPIInstrumentor.instrument_app(app)

# Manual Spans
tracer = trace.get_tracer(__name__)
with tracer.start_as_current_span("process_document"):
    # ... processing ...
```

**Backend:** Jaeger oder Grafana Tempo
**Cost:** ~1-2 Tage Setup + Infra

---

## 4. Log-Redaktion (PII-Maskierung)

### 4.1 Status

❌ **PII in Logs:** RISIKO HOCH
- Dateinamen können PII enthalten (z.B. "Max_Mustermann_Vertrag.pdf")
- Dokument-Content in Debug-Logs
- User-IDs/E-Mails in Auth-Logs
- **Compliance-Risiko:** DSGVO Art. 5, Art. 32

### 4.2 Empfohlene Maskierung

**QW-4: Log-Filter für PII**
```python
import re
import logging

class PIIRedactionFilter(logging.Filter):
    """Maskiert PII in Log-Nachrichten"""
    
    PII_PATTERNS = [
        (re.compile(r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b'), '[EMAIL]'),
        (re.compile(r'\b\d{3}-\d{2}-\d{4}\b'), '[SSN]'),  # US SSN
        (re.compile(r'\b\d{2}\.\d{2}\.\d{4}\b'), '[DATE]'),  # Geburtsdatum
        (re.compile(r'(password|pwd|secret)["\']?\s*[:=]\s*["\']?[^\s"\']+', re.I), r'\1=[REDACTED]'),
    ]
    
    def filter(self, record):
        msg = record.getMessage()
        for pattern, replacement in self.PII_PATTERNS:
            msg = pattern.sub(replacement, msg)
        record.msg = msg
        record.args = ()
        return True

# Aktivierung
logger.addFilter(PIIRedactionFilter())
```

**Location:** `main_backend.py`, `ingestion_backend.py` (nach logging.basicConfig)

---

## 5. Dashboards & Alerts

### 5.1 Status

❌ **Dashboards:** Nicht vorhanden
- Kein Grafana-Setup
- Keine Visualisierung für Metriken
- **Impact:** Operativer Blindflug

❌ **Alerts:** Nicht konfiguriert
- Keine Alertmanager-Integration
- Keine On-Call-Benachrichtigungen
- **Risiko:** Ausfälle unbemerkt

### 5.2 Empfohlene Metriken für Dashboards

**Dashboard 1: Performance**
- P95/P99-Latenzen (Dokument-Processing, DB-Ops)
- Throughput (Dokumente/min)
- Queue-Tiefe (I/O/CPU Pools)
- Pool-Auslastung (PostgreSQL Connections)

**Dashboard 2: Reliability**
- Error-Rate (gesamt, pro DB)
- Retry-Count (SAGA, Recovery)
- Dead-Letter-Anteil
- Timeout-Rate

**Dashboard 3: Capacity**
- Platte/TMP (data/uploads)
- File-Deskriptoren (ulimit tracking)
- RAM (Worker Pools)
- Pool-Auslastung (PostgreSQL, pgBouncer)

### 5.3 Empfohlene Alerts

**Alert 1: Kritische Fehlerrate**
- Trigger: Error-Rate > 5% über 5min
- Severity: P1 (Page)

**Alert 2: Hohe Latenz**
- Trigger: P95 > 5s über 10min
- Severity: P2 (Notify)

**Alert 3: Queue Stau**
- Trigger: Queue-Tiefe > 1000 über 15min
- Severity: P2 (Notify)

**Alert 4: Plattenplatz**
- Trigger: `/data/uploads` > 90%
- Severity: P1 (Page)

**Alert 5: Pool-Erschöpfung**
- Trigger: PostgreSQL Pool > 95% over 5min
- Severity: P2 (Notify)

---

## 6. SLO/SLA Definitionen

### 6.1 Status

❌ **SLOs:** Nicht definiert
❌ **SLAs:** Nicht definiert
❌ **Error Budget:** Nicht getrackt

### 6.2 Empfohlene SLOs

**SLO 1: Verfügbarkeit**
- Target: 99.5% Uptime (monatlich)
- Measurement: `/health` endpoint
- Error Budget: 3.6h/Monat

**SLO 2: Latenz**
- Target: P95 < 2s (Dokument-Processing)
- Measurement: `document_latency` Histogram
- Error Budget: 5% Anfragen > 2s

**SLO 3: Throughput**
- Target: 100 Dokumente/min (sustained)
- Measurement: `documents_per_minute` Gauge
- Error Budget: 95% der Zeit > 100/min

**SLO 4: Fehlerrate**
- Target: < 1% Failed Documents
- Measurement: `documents_processed{status='failed'}`
- Error Budget: 1% aller Dokumente

### 6.3 RTO/RPO

**RTO (Recovery Time Objective):**
- Target: < 15 Minuten
- Aktuell: ⚠️ Nicht getestet

**RPO (Recovery Point Objective):**
- Target: < 5 Minuten Datenverlust
- Aktuell: ✅ PostgreSQL Auto-Resume reduziert RPO

---

## 7. Strukturiertes Logging

### 7.1 Status

✅ **Python Logging:** Implementiert
- Format: Timestamp, Name, Level, Message
- Location: `main_backend.py`, `ingestion_backend.py`

⚠️ **Strukturierung:** Teilweise
- Kein JSON-Logging
- Keine Correlation IDs
- **Impact:** Log-Aggregation/Suche suboptimal

### 7.2 Empfohlene Verbesserung

**QW-5: JSON Structured Logging**
```bash
pip install python-json-logger
```

```python
from pythonjsonlogger import jsonlogger

logHandler = logging.StreamHandler()
formatter = jsonlogger.JsonFormatter(
    '%(asctime)s %(name)s %(levelname)s %(message)s',
    timestamp=True
)
logHandler.setFormatter(formatter)
logger.addHandler(logHandler)

# Mit Correlation ID
import contextvars
correlation_id = contextvars.ContextVar('correlation_id', default=None)

class CorrelationFilter(logging.Filter):
    def filter(self, record):
        record.correlation_id = correlation_id.get()
        return True

logger.addFilter(CorrelationFilter())
```

---

## 8. Compliance-Checkliste

| Anforderung | Status | Priorität | Aufwand |
|-------------|--------|-----------|---------|
| Technische Metriken (Worker-Queue, Chunk-Dauer) | ❌ | P1 | 2d |
| Business-Metriken (Docs/min, Error-Rate) | ❌ | P1 | 1d |
| Distributed Tracing (OpenTelemetry) | ❌ | P2 | 3d |
| PII-Log-Redaktion | ❌ | P0 | 4h |
| Prometheus Integration | ❌ | P1 | 1d |
| Grafana Dashboards (3 Panels) | ❌ | P2 | 2d |
| Alertmanager + On-Call | ❌ | P2 | 1d |
| SLO/SLA Definitionen | ❌ | P3 | 4h |
| JSON Structured Logging | ❌ | P2 | 4h |
| Correlation IDs | ❌ | P2 | 1d |

---

## 9. Quick Wins (Priorisiert)

### Top 5 Quick Wins (1-2 Tage):

1. **PII-Log-Redaktion** (4h, P0, DSGVO-Risiko)
2. **Prometheus Client** (1d, P1, Foundation)
3. **Basic Business-Metriken** (1d, P1, SLA-Tracking)
4. **JSON Logging** (4h, P2, Aggregation)
5. **Pool-Stats Gauge** (2h, P1, Existing Endpoint)

### Mittelfristig (1-2 Wochen):

6. **Grafana Dashboards** (2d, P2, 3 Panels)
7. **OpenTelemetry** (3d, P2, Tracing)
8. **Alertmanager** (1d, P2, On-Call)

### Langfristig (1 Monat):

9. **SLO Error Budget Tracking** (1w, P3)
10. **Correlation IDs (Request Tracking)** (1d, P2)

---

## 10. Risiko-Bewertung

| Risiko | Wahrscheinlichkeit | Impact | Gesamt | Maßnahme |
|--------|-------------------|--------|--------|----------|
| PII in Logs (DSGVO) | HOCH | HOCH | 🔴 KRITISCH | QW-4 (4h) |
| Performance-Regression unsichtbar | MITTEL | HOCH | 🟡 MEDIUM | QW-2 (1d) |
| Ausfälle unbemerkt | MITTEL | HOCH | 🟡 MEDIUM | Alerts (1d) |
| Bottlenecks nicht isolierbar | MITTEL | MITTEL | 🟡 MEDIUM | OTel (3d) |
| SLA-Verletzung ungetrackt | NIEDRIG | MITTEL | 🟢 LOW | SLO (4h) |

---

## 11. Empfohlene nächste Schritte

**Sofort (heute):**
1. PII-Log-Redaktion implementieren (4h, QW-4)

**Diese Woche:**
2. Prometheus Client + Basic Metrics (1d, QW-2)
3. Business-Metriken (Docs/min, Error-Rate) (1d)
4. JSON Structured Logging (4h, QW-5)

**Nächste Woche:**
5. Grafana Dashboard Setup (2d)
6. Alertmanager Konfiguration (1d)

**Nächster Monat:**
7. OpenTelemetry Integration (3d)
8. SLO/Error Budget Tracking (1w)

---

## 12. Zusammenfassung

**Status:** 🟡 TEILWEISE IMPLEMENTIERT (30% Coverage)

**Stärken:**
- ✅ Strukturiertes Logging vorhanden
- ✅ Pool-Stats exposiert (`/db/pool`)
- ✅ Health-Endpoints implementiert

**Schwächen:**
- ❌ Keine Business-Metriken
- ❌ Kein Distributed Tracing
- ❌ PII-Risiko in Logs (DSGVO)
- ❌ Keine Dashboards/Alerts

**Empfehlung:** 5 Quick Wins (1-2 Tage) umsetzen, dann Dashboards/Alerts aufbauen.

**Nächster Audit:** Nach Prometheus/Grafana-Integration (in 2 Wochen)

---

**Audit abgeschlossen:** 21. Oktober 2025  
**Nächste Review:** 4. November 2025  
**Verantwortlich:** DevOps Team
