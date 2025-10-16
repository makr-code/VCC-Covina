# Admin API - Quick Start Guide

## Überblick

Die Covina Admin API bietet **8 spezialisierte Endpoints** für erweiterte System-Administration:

### 📊 Golden Dataset (4 Endpoints)
Ground Truth Management für AI-Training und Benchmarks

- `POST /admin/golden-dataset/entry` - Erstelle Eintrag
- `GET /admin/golden-dataset/entries` - Liste Einträge
- `GET /admin/golden-dataset/entry/{id}` - Hole Eintrag
- `DELETE /admin/golden-dataset/entry/{id}` - Lösche Eintrag

### 🤖 AI-as-Judge (1 Endpoint)
Automatische Qualitätsbewertung

- `POST /admin/ai-as-judge/evaluate` - Bewerte Dokument

### 🔍 Process Mining (2 Endpoints)
Workflow-Analyse und Optimierung

- `POST /admin/process-mining/analyze` - Analysiere Prozesse
- `GET /admin/process-mining/heatmap` - Auslastungs-Heatmap

### 📈 Quality Trends (1 Endpoint)
Qualitätstrend-Analyse

- `GET /admin/quality-trends` - Qualität über Zeit

---

## Quick Start

### 1. Backend starten

```bash
cd C:\VCC\Covina
python backend.py
```

Backend läuft auf: **http://localhost:45678**

### 2. API Dokumentation öffnen

**Swagger UI:** http://localhost:45678/docs  
**ReDoc:** http://localhost:45678/redoc

### 3. Tests ausführen

```bash
python tests/test_admin_api.py
```

---

## Beispiele

### Golden Dataset erstellen

```bash
curl -X POST "http://localhost:45678/admin/golden-dataset/entry" \
  -H "Content-Type: application/json" \
  -d '{
    "document_id": "doc_001",
    "classification": "VERTRAG",
    "entities": [{"type": "PERSON", "value": "Max Mustermann"}],
    "quality_score": 0.95
  }'
```

### AI-as-Judge Bewertung

```bash
curl -X POST "http://localhost:45678/admin/ai-as-judge/evaluate" \
  -H "Content-Type: application/json" \
  -d '{
    "document_id": "doc_001",
    "evaluation_criteria": ["classification", "quality"]
  }'
```

### Process Mining

```bash
curl -X POST "http://localhost:45678/admin/process-mining/analyze" \
  -H "Content-Type: application/json" \
  -d '{
    "include_bottlenecks": true,
    "include_variants": true
  }'
```

---

## Python Client

```python
import requests

BASE_URL = "http://localhost:45678"

# Golden Dataset
response = requests.post(f"{BASE_URL}/admin/golden-dataset/entry", json={
    "document_id": "doc_001",
    "classification": "VERTRAG",
    "entities": [],
    "quality_score": 0.95
})
print(response.json())

# AI-as-Judge
response = requests.post(f"{BASE_URL}/admin/ai-as-judge/evaluate", json={
    "document_id": "doc_001",
    "evaluation_criteria": ["classification", "quality"]
})
print(f"Score: {response.json()['overall_score']}")

# Process Mining
response = requests.post(f"{BASE_URL}/admin/process-mining/analyze", json={
    "include_bottlenecks": True
})
print(f"Avg Duration: {response.json()['average_duration_ms']} ms")
```

---

## Use Cases

### ✅ Use Case 1: Qualitätssicherung
1. Experten erstellen Golden Dataset
2. Dokumente verarbeiten
3. AI-as-Judge vergleicht mit Ground Truth
4. Automatische Eskalation bei niedrigem Score

### ✅ Use Case 2: Performance-Optimierung
1. Process Mining findet Bottlenecks
2. Heatmap zeigt Peak-Zeiten
3. Empfehlungen für Skalierung
4. Kontinuierliches Monitoring

### ✅ Use Case 3: Trend-Analyse
1. Tägliche Quality Trends
2. Wöchentliche Reports
3. Langzeit-Verbesserung tracken

---

## Dokumentation

**Vollständige API-Docs:** [docs/ADMIN_API.md](ADMIN_API.md)

**Test Suite:** [tests/test_admin_api.py](../tests/test_admin_api.py)

---

## Roadmap

### Phase 1: MVP ✅
- [x] Golden Dataset Management
- [x] AI-as-Judge Basic
- [x] Process Mining Basic
- [x] Quality Trends

### Phase 2: Erweitert
- [ ] Golden Dataset in PostgreSQL
- [ ] ML-basierte Anomalie-Erkennung
- [ ] Real-time Dashboards
- [ ] A/B-Testing Framework

### Phase 3: Enterprise
- [ ] Multi-Tenant Support
- [ ] Role-based Access Control
- [ ] Prometheus/Grafana Integration
- [ ] Advanced Analytics

---

**Version:** 1.0.0  
**Erstellt:** 6. Oktober 2025  
**Status:** ✅ Production Ready
