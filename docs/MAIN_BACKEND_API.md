# Covina Main Backend API Documentation

**Version:** 1.0.0  
**Port:** 45678 (Main Backend)  
**Ingestion Backend:** Port 45679  
**Datum:** 17. Oktober 2025

---

## 🎯 Übersicht

Das Covina Main Backend ist für folgende Funktionen zuständig:
- **Gap Detection:** Knowledge Gap Management
- **Golden Dataset:** Validierte Trainingsdaten
- **Compliance:** DSGVO, GDPR, regulatorische Checks
- **Governance:** Policies und Rules Management
- **Query API:** Dokumentensuche (Semantic & Full-Text)
- **Review Queue:** Manuelles Review von Dokumenten
- **Handelsregister:** Integration mit Handelsregister-Daten

**Hinweis:** Upload und Ingestion laufen auf dem separaten Ingestion Backend (Port 45679)

---

## 📊 System Endpoints

### GET / - API Info
**Beschreibung:** Root endpoint mit API-Informationen

**Response:**
```json
{
  "service": "Covina Main Backend API",
  "version": "1.0.0",
  "backend_type": "main",
  "port": 45678,
  "status": "operational",
  "features": [
    "Query API",
    "DSGVO Compliance",
    "Review Queue",
    "Handelsregister"
  ],
  "ingestion_backend": "http://127.0.0.1:45679",
  "docs": "/docs",
  "health": "/health"
}
```

### GET /health - System Health Check
**Beschreibung:** Aktueller System-Status mit verfügbaren Features

**Response:**
```json
{
  "status": "healthy",
  "backend_type": "main",
  "port": 45678,
  "ingestion_backend": "http://127.0.0.1:45679",
  "features_available": {
    "gap_detection": true,
    "postgres": true,
    "compliance": true,
    "governance": true,
    "golden_dataset": true,
    "query_api": true,
    "review_queue": true,
    "dsgvo": true
  },
  "system_resources": {
    "cpu_percent": 15.2,
    "memory_percent": 45.8,
    "disk_percent": 62.3
  }
}
```

---

## 🔍 Gap Detection API

### GET /gaps - Liste alle Knowledge Gaps
**Beschreibung:** Hole alle Knowledge Gaps mit optionalen Filtern

**Query Parameters:**
- `status` (optional): Filter nach Status (open, in_progress, resolved, deferred)
- `gap_type` (optional): Filter nach Typ (process, reference, compliance)
- `severity` (optional): Filter nach Schweregrad (low, medium, high, critical)
- `limit` (default: 50, max: 500): Maximale Anzahl Ergebnisse

**Curl Example:**
```bash
curl "http://127.0.0.1:45678/gaps?status=open&severity=high&limit=20"
```

**Response:**
```json
{
  "gaps": [
    {
      "id": 1,
      "gap_type": "missing_regulation",
      "description": "Fehlende Referenz zu BImSchV §5",
      "severity": "high",
      "status": "open",
      "detected_at": "2025-10-17T10:30:00",
      "tags": ["regulatory", "environmental"],
      "metadata": {...}
    }
  ],
  "count": 1
}
```

### GET /gaps/{gap_id} - Hole einzelnen Gap
**Beschreibung:** Details zu einem spezifischen Knowledge Gap

**Curl Example:**
```bash
curl "http://127.0.0.1:45678/gaps/1"
```

### POST /gaps - Erstelle neuen Gap
**Beschreibung:** Lege einen neuen Knowledge Gap an

**Request Body:**
```json
{
  "gap_type": "missing_regulation",
  "description": "Fehlende Referenz zu BImSchV §5",
  "severity": "high",
  "status": "open",
  "source": "document_123",
  "context": "Umweltschutz",
  "tags": ["regulatory", "environmental"],
  "metadata": {
    "department": "compliance"
  }
}
```

**Curl Example:**
```bash
curl -X POST "http://127.0.0.1:45678/gaps" \
  -H "Content-Type: application/json" \
  -d '{"gap_type":"missing_regulation","description":"Test Gap","severity":"medium"}'
```

### PUT /gaps/{gap_id} - Aktualisiere Gap
**Beschreibung:** Update eines existierenden Knowledge Gap

### POST /gaps/{gap_id}/resolve - Markiere als gelöst
**Beschreibung:** Setze Gap Status auf "resolved"

**Query Parameters:**
- `resolution` (required): Beschreibung der Lösung
- `user` (optional): Benutzer der den Gap gelöst hat

**Curl Example:**
```bash
curl -X POST "http://127.0.0.1:45678/gaps/1/resolve?resolution=Referenz%20hinzugefügt&user=admin"
```

### GET /gaps/statistics - Gap Statistiken
**Beschreibung:** Statistische Übersicht über alle Knowledge Gaps

**Response:**
```json
{
  "total": 42,
  "by_status": {
    "open": 15,
    "in_progress": 8,
    "resolved": 19
  },
  "by_severity": {
    "low": 10,
    "medium": 20,
    "high": 10,
    "critical": 2
  },
  "top_types": {
    "missing_regulation": 12,
    "unclear_process": 8,
    "data_quality": 5
  }
}
```

---

## 📚 Golden Dataset API

### GET /golden-dataset - Liste Golden Dataset Einträge
**Beschreibung:** Hole alle validierten Golden Dataset Einträge

**Query Parameters:**
- `document_type` (optional): Filter nach Dokumenttyp
- `validation_status` (optional): Filter nach Validierungsstatus
- `min_quality` (default: 0.0): Minimaler Quality Score (0.0-1.0)
- `limit` (default: 100, max: 1000): Maximale Anzahl

**Curl Example:**
```bash
curl "http://127.0.0.1:45678/golden-dataset?min_quality=0.8&limit=50"
```

### POST /golden-dataset - Füge Eintrag hinzu
**Beschreibung:** Füge einen neuen Golden Dataset Eintrag hinzu

**Request Body:**
```json
{
  "document_id": "doc_12345",
  "document_type": "regulation",
  "classification": "BImSchV",
  "quality_score": 0.95,
  "validation_status": "validated",
  "validated_by": "expert_user",
  "metadata": {
    "source": "manual_curation",
    "notes": "High quality example"
  }
}
```

---

## ⚖️ Compliance API

### POST /compliance/check - Führe Compliance Check durch
**Beschreibung:** Führe einen Compliance Check durch (DSGVO, GDPR, etc.)

**Request Body:**
```json
{
  "check_type": "dsgvo",
  "document_id": "doc_12345",
  "status": "pending",
  "findings": [],
  "risk_level": "medium",
  "metadata": {
    "department": "legal"
  }
}
```

**Curl Example:**
```bash
curl -X POST "http://127.0.0.1:45678/compliance/check" \
  -H "Content-Type: application/json" \
  -d '{"check_type":"dsgvo","document_id":"doc_123","risk_level":"medium"}'
```

### GET /compliance/checks - Liste Compliance Checks
**Beschreibung:** Liste alle durchgeführten Compliance Checks

**Query Parameters:**
- `check_type` (optional): Filter nach Typ (dsgvo, gdpr, regulatory)
- `status` (optional): Filter nach Status
- `limit` (default: 50, max: 500): Maximale Anzahl

### GET /compliance/dsgvo/status - DSGVO Status
**Beschreibung:** Aktueller DSGVO Compliance Status

**Response:**
```json
{
  "compliance_level": "high",
  "last_check": "2025-10-17T10:00:00",
  "findings": [],
  "recommendations": [
    "Regelmäßige Überprüfung der Datenaufbewahrungsrichtlinien",
    "Dokumentation der Verarbeitungstätigkeiten aktualisieren"
  ]
}
```

---

## 🛡️ Governance API

### GET /governance/policies - Liste Governance Policies
**Beschreibung:** Hole alle Governance Policies

**Query Parameters:**
- `policy_type` (optional): Filter nach Typ (retention, access, classification)
- `active_only` (default: true): Nur aktive Policies
- `limit` (default: 100, max: 500): Maximale Anzahl

**Curl Example:**
```bash
curl "http://127.0.0.1:45678/governance/policies?policy_type=retention&active_only=true"
```

### POST /governance/policies - Erstelle Policy
**Beschreibung:** Erstelle eine neue Governance Policy

**Request Body:**
```json
{
  "policy_id": "pol_retention_001",
  "policy_type": "retention",
  "title": "7-Jahres Aufbewahrungspflicht",
  "description": "Steuerrelevante Dokumente müssen 7 Jahre aufbewahrt werden",
  "rules": {
    "retention_period_years": 7,
    "applies_to": ["invoices", "tax_documents"],
    "auto_delete": false
  },
  "active": true
}
```

---

## 🔎 Query API

### POST /query/documents - Dokument-Suche
**Beschreibung:** Suche nach Dokumenten mit Query-Text und Filtern

**Request Body:**
```json
{
  "query_text": "BImSchV Grenzwerte",
  "filters": {
    "document_type": "regulation",
    "date_from": "2020-01-01",
    "date_to": "2025-12-31"
  },
  "limit": 10,
  "offset": 0
}
```

**Curl Example:**
```bash
curl -X POST "http://127.0.0.1:45678/query/documents" \
  -H "Content-Type: application/json" \
  -d '{"query_text":"BImSchV","limit":10}'
```

### GET /query/semantic - Semantic Search
**Beschreibung:** Semantische Suche über Dokumente (ChromaDB Vector Search)

**Query Parameters:**
- `query` (required): Suchtext
- `limit` (default: 10, max: 100): Maximale Anzahl Ergebnisse
- `threshold` (default: 0.7): Ähnlichkeits-Schwellwert (0.0-1.0)

**Curl Example:**
```bash
curl "http://127.0.0.1:45678/query/semantic?query=Grenzwerte%20Luftqualität&limit=20&threshold=0.75"
```

**Response:**
```json
{
  "results": [
    {
      "document_id": "doc_456",
      "title": "BImSchV Anlage 1 - Grenzwerte",
      "similarity_score": 0.92,
      "snippet": "... Grenzwerte für Luftqualität gemäß §5 ..."
    }
  ],
  "query": "Grenzwerte Luftqualität",
  "count": 1,
  "threshold": 0.75
}
```

---

## 📋 Review Queue API

### GET /review-queue - Liste Review Queue Items
**Beschreibung:** Hole alle Items in der Review Queue

**Query Parameters:**
- `review_type` (optional): Filter nach Typ (classification, quality, compliance)
- `status` (default: "pending"): Filter nach Status
- `priority` (optional): Filter nach Priorität (low, normal, high, urgent)
- `limit` (default: 50, max: 500): Maximale Anzahl

**Curl Example:**
```bash
curl "http://127.0.0.1:45678/review-queue?status=pending&priority=high&limit=20"
```

### POST /review-queue - Füge Item hinzu
**Beschreibung:** Füge ein neues Item zur Review Queue hinzu

**Request Body:**
```json
{
  "item_id": "review_001",
  "document_id": "doc_789",
  "review_type": "classification",
  "status": "pending",
  "priority": "high",
  "assigned_to": "reviewer_user",
  "metadata": {
    "reason": "Automatic classification unsure",
    "confidence": 0.65
  }
}
```

### PUT /review-queue/{item_id} - Aktualisiere Item
**Beschreibung:** Update eines Review Queue Items

---

## 🏢 Handelsregister API

### GET /handelsregister/search - Handelsregister Suche
**Beschreibung:** Suche im Handelsregister

**Query Parameters:**
- `company_name` (optional): Firmenname
- `registration_number` (optional): Handelsregisternummer
- `location` (optional): Standort/Stadt

**Curl Example:**
```bash
curl "http://127.0.0.1:45678/handelsregister/search?company_name=Musterfirma%20GmbH&location=Berlin"
```

---

## 🔗 Integration mit Ingestion Backend

Das Main Backend arbeitet eng mit dem Ingestion Backend zusammen:

**Main Backend (Port 45678):**
- Queries, Compliance, Governance, Review Queue

**Ingestion Backend (Port 45679):**
- Upload, Job Management, Document Processing

**Workflow:**
1. Dokumente hochladen → **Ingestion Backend** (`POST /upload/files`)
2. Job Status prüfen → **Ingestion Backend** (`GET /jobs/{job_id}`)
3. Dokumente suchen → **Main Backend** (`POST /query/documents`)
4. Compliance prüfen → **Main Backend** (`POST /compliance/check`)
5. Gaps verwalten → **Main Backend** (`GET /gaps`)

---

## 📝 Beispiel-Workflow

### 1. System Health Check
```bash
curl http://127.0.0.1:45678/health
```

### 2. Neuen Gap erstellen
```bash
curl -X POST http://127.0.0.1:45678/gaps \
  -H "Content-Type: application/json" \
  -d '{
    "gap_type": "missing_regulation",
    "description": "Fehlende BImSchV Referenz",
    "severity": "high"
  }'
```

### 3. Gap-Statistiken abrufen
```bash
curl http://127.0.0.1:45678/gaps/statistics
```

### 4. Semantic Search
```bash
curl "http://127.0.0.1:45678/query/semantic?query=Umweltschutz&limit=10"
```

### 5. DSGVO Status prüfen
```bash
curl http://127.0.0.1:45678/compliance/dsgvo/status
```

---

## 🚀 Swagger Documentation

Interaktive API-Dokumentation verfügbar unter:
- **Swagger UI:** http://127.0.0.1:45678/docs
- **ReDoc:** http://127.0.0.1:45678/redoc

---

## 📊 Status Codes

- **200 OK:** Erfolgreiche Anfrage
- **201 Created:** Ressource erfolgreich erstellt
- **400 Bad Request:** Ungültige Anfrage
- **404 Not Found:** Ressource nicht gefunden
- **500 Internal Server Error:** Server-Fehler
- **503 Service Unavailable:** Service nicht verfügbar

---

## 🔒 Authentication & Security

**Aktuell:** Keine Authentication (Development)  
**Produktion TODO:**
- OAuth2 / JWT Token Authentication
- API Key Management
- Rate Limiting
- CORS Policy Verschärfung

---

## 📞 Support

Bei Fragen oder Problemen:
- **Logs:** Check Backend Logs für detaillierte Fehlermeldungen
- **Health Check:** Prüfe `/health` für System-Status
- **Swagger Docs:** Nutze `/docs` für interaktive Tests

---

**Erstellt:** 17. Oktober 2025  
**Version:** 1.0.0  
**Covina Document Management System**
