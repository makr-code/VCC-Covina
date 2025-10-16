# Covina Admin Dashboard - Quick Reference
**Schnellstart-Anleitung für das Admin & Monitoring System**

## 🚀 Quick Start

### 1. Installation
```bash
# Installiere Dependencies
pip install matplotlib numpy rich psutil
```

### 2. Demo ausführen
```bash
# Komplette Demo mit allen Features
python examples/demo_admin_dashboard.py
```

### 3. CLI verwenden
```bash
# System Status anzeigen
python -m management_core.admin_cli status

# Live Dashboard starten
python -m management_core.admin_cli dashboard

# Charts generieren
python -m management_core.admin_cli charts

# Metriken anzeigen
python -m management_core.admin_cli metrics
```

## 📊 Chart Types

| Chart | Beschreibung | Datei |
|-------|--------------|-------|
| **Ingestion Timeline** | Dokumenten-Ingestion über Zeit | `create_ingestion_timeline_chart()` |
| **Error Rate** | Fehlerrate-Analyse mit Schwellwerten | `create_error_rate_chart()` |
| **Worker Performance** | Worker Success Rates & Executions | `create_worker_performance_chart()` |
| **DB Operations** | Verteilung der DB-Operationen | `create_database_operations_chart()` |
| **Quality Metrics** | Dokument-Qualitäts-Scores | `create_quality_metrics_chart()` |
| **Health Dashboard** | System-Health Übersicht | `create_system_health_dashboard()` |

## 🔌 API Endpoints

### Dashboard Overview
```bash
GET http://localhost:45678/admin/dashboard/overview
```

### Metriken abrufen
```bash
GET http://localhost:45678/admin/dashboard/metrics/ingestion_rate?time_range_minutes=60
```

### Charts generieren
```bash
POST http://localhost:45678/admin/dashboard/charts/generate
```

### Health Snapshot
```bash
GET http://localhost:45678/admin/dashboard/health-snapshot
```

### Metrik aufzeichnen
```bash
POST http://localhost:45678/admin/dashboard/metrics/record
Content-Type: application/json

{
  "metric_type": "ingestion_rate",
  "value": 45.5,
  "unit": "dpm"
}
```

## 📈 Metric Types

| Type | Beschreibung | Unit |
|------|--------------|------|
| `ingestion_rate` | Dokumente pro Minute | dpm |
| `processing_time` | Durchschnittliche Verarbeitungszeit | ms |
| `error_rate` | Fehlerrate | % |
| `queue_size` | Warteschlangen-Größe | items |
| `worker_performance` | Worker-Ausführungen | - |
| `database_operations` | DB-Operationen | count |
| `quality_score` | Dokument-Qualität | 0-1 |
| `system_health` | System-Health | - |
| `memory_usage` | Speichernutzung | % |
| `cpu_usage` | CPU-Auslastung | % |

## 💻 Python Code Examples

### Metriken aufzeichnen
```python
from management_core.admin_dashboard import get_admin_dashboard, MetricType

dashboard = get_admin_dashboard()

dashboard.metrics_collector.record_metric(
    MetricType.INGESTION_RATE,
    45.5,
    unit="dpm",
    metadata={"batch_id": "batch_123"}
)
```

### Charts generieren
```python
from management_core.admin_dashboard import get_admin_dashboard

dashboard = get_admin_dashboard()

# Metriken holen
metrics = dashboard.metrics_collector.get_metrics(
    MetricType.INGESTION_RATE
)

# Chart erstellen
chart_path = dashboard.visualizer.create_ingestion_timeline_chart(metrics)
print(f"Chart gespeichert: {chart_path}")
```

### Health Check
```python
dashboard = get_admin_dashboard()

# Metriken sammeln
await dashboard.collect_system_metrics()

# Health Snapshot generieren
health = dashboard.generate_health_snapshot()
print(f"Status: {health.status.value}")
print(f"Components: {len(health.components)}")
print(f"Alerts: {len(health.alerts)}")
```

### Statistiken abrufen
```python
stats = dashboard.metrics_collector.get_metric_statistics(
    MetricType.INGESTION_RATE,
    time_range_minutes=60
)

print(f"Mean: {stats['mean']:.1f}")
print(f"P95: {stats['p95']:.1f}")
print(f"Max: {stats['max']:.1f}")
```

## 🎨 CLI Commands

| Command | Beschreibung |
|---------|--------------|
| `status` | Aktueller System-Status |
| `dashboard` | Interaktives Live-Dashboard |
| `metrics` | Detaillierte Metriken |
| `charts` | Alle Charts generieren |
| `alerts` | Aktive Alerts anzeigen |
| `health` | System Health Check |
| `export` | Dashboard-Daten exportieren |

### CLI Optionen
```bash
# Dashboard mit custom Refresh
python -m management_core.admin_cli dashboard --refresh 10

# Export zu custom Datei
python -m management_core.admin_cli export -o my_export.json
```

## 🔧 Backend Integration

### Dashboard initialisieren
```python
from management_core.admin_dashboard import initialize_admin_dashboard
from pathlib import Path

dashboard = initialize_admin_dashboard(
    metrics_retention_hours=24,
    charts_output_dir=Path("dashboard_charts")
)

# Komponenten-Referenzen injizieren
dashboard.inject_component_references(
    backend=app,
    job_manager=job_manager,
    automation_framework=automation_framework
)
```

### Periodic Metrics Collection
```python
async def collect_metrics_periodically():
    """Sammle Metriken alle 60 Sekunden"""
    while True:
        await dashboard.collect_system_metrics()
        await asyncio.sleep(60)

# In startup event
@app.on_event("startup")
async def startup():
    asyncio.create_task(collect_metrics_periodically())
```

## 📊 Chart Konfiguration

### Output Directory
```python
dashboard.visualizer.output_dir = Path("my_charts")
```

### Chart Style
Charts verwenden `seaborn-v0_8-darkgrid` Style mit:
- **Resolution:** 150 DPI
- **Format:** PNG
- **Color Palette:** Professional (grün/gelb/rot für Status)

## 🚨 Alert Thresholds

| Metric | Warning | Critical |
|--------|---------|----------|
| Error Rate | 5% | 10% |
| CPU Usage | 70% | 90% |
| Memory Usage | 80% | 95% |
| Queue Size | 50 | 100 |

## 📁 Output Files

### Charts
```
dashboard_charts/
├── ingestion_timeline_<timestamp>.png
├── error_rate_<timestamp>.png
├── worker_performance_<timestamp>.png
├── db_operations_<timestamp>.png
├── quality_metrics_<timestamp>.png
└── health_dashboard_<timestamp>.png
```

### Data Export
```json
{
  "timestamp": "2025-10-08T18:30:00",
  "system_status": "healthy",
  "uptime_seconds": 86400,
  "components": {...},
  "metrics": {...},
  "alerts": [...],
  "statistics": {...}
}
```

## 🎯 Best Practices

### 1. Metrics Collection
- Sammle Metriken regelmäßig (alle 60s)
- Verwende aussagekräftige Metadata
- Behalte Retention im Blick (24h default)

### 2. Chart Generation
- Generiere Charts periodisch (alle 15-60 Min)
- Implementiere Chart-Rotation (alte löschen)
- Nutze geeignete Chart-Typen für Daten

### 3. Monitoring
- Prüfe Health Snapshot alle 5 Minuten
- Reagiere auf Alerts zeitnah
- Tracke Trends über Zeit

### 4. Performance
- In-Memory Metrics (schnell aber begrenzt)
- Chart-Generierung ~50-200ms
- CLI Dashboard 0.2 FPS Refresh

## 📞 Troubleshooting

### "Rich library not available"
```bash
pip install rich
```

### "ModuleNotFoundError: No module named 'management_core'"
```bash
# Stelle sicher, dass du im Covina Root-Verzeichnis bist
cd C:\VCC\Covina
python -m management_core.admin_cli status
```

### Charts werden nicht erstellt
```python
# Prüfe Output Directory
dashboard.visualizer.output_dir.mkdir(parents=True, exist_ok=True)
```

### Keine Metriken vorhanden
```python
# Prüfe, ob Metriken aufgezeichnet wurden
stats = dashboard.metrics_collector.get_metric_statistics(MetricType.INGESTION_RATE)
print(f"Metrics Count: {stats['count']}")
```

## ✅ Checkliste für Production

- [ ] Dashboard initialisiert
- [ ] Komponenten-Referenzen injiziert
- [ ] Metrics Collection läuft
- [ ] Charts werden generiert
- [ ] API Endpoints verfügbar
- [ ] CLI Tools getestet
- [ ] Alert-Thresholds konfiguriert
- [ ] Monitoring eingerichtet

## 🎊 Ready to Use!

Das Covina Admin Dashboard ist **production-ready** und kann sofort eingesetzt werden!

**Hilfreiche Links:**
- Vollständige Dokumentation: `docs/ADMIN_DASHBOARD_MONITORING_SYSTEM.md`
- Demo Script: `examples/demo_admin_dashboard.py`
- CLI Tool: `management_core/admin_cli.py`
- Core Implementation: `management_core/admin_dashboard.py`

**Support:**
- Bei Fragen zum Dashboard: Siehe `docs/ADMIN_DASHBOARD_MONITORING_SYSTEM.md`
- Bei API-Fragen: `GET /docs` im Backend für OpenAPI Docs
- Bei CLI-Hilfe: `python -m management_core.admin_cli --help`
