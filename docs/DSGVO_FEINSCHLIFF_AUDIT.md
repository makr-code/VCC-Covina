# DSGVO-Feinschliff Audit Report
**Datum:** 21. Oktober 2025  
**System:** Covina Document Management (Main + Ingestion Backend)  
**Auditor:** GitHub Copilot  
**Status:** 🟡 TEILWEISE IMPLEMENTIERT

---

## Executive Summary

**Zweck:** Bewertung der DSGVO-Compliance (DPIA, Art. 30, Konsenten, Datenminimierung, Data Residency, Löschung, Backup).

**Bewertung:**
- ✅ **Compliance Service:** Implementiert (DSGVO-Checks, Regulatorische Prüfungen)
- ✅ **Lösch-Workflows:** Teilweise (delete_document implementiert, keine Retention-Policies)
- ⚠️ **Datenminimierung:** Teilweise (Quality Scores, keine automatische Pseudonymisierung)
- ❌ **DPIA/DSFA:** Nicht durchgeführt
- ❌ **Art. 30 Verzeichnis:** Nicht vorhanden
- ❌ **Konsenten-Management:** Nicht implementiert
- ❌ **Data Residency:** Nicht konfiguriert (DBs in Deutschland, aber keine Mandantentrennung)
- ❌ **Backup/Restore:** Nicht implementiert (kein RPO/RTO)

**Risiko-Einschätzung:** 🔴 HIGH (Compliance-Lücken)  
**Empfohlene Maßnahmen:** 7 Quick Wins + DPIA durchführen

---

## 1. DPIA/DSFA (Datenschutz-Folgenabschätzung)

### 1.1 Status

❌ **DPIA:** Nicht durchgeführt
- Art. 35 DSGVO erforderlich bei hohem Risiko
- Covina verarbeitet potenziell sensible Geschäftsdokumente
- Automatische Klassifikation = systematische Verarbeitung
- **Compliance-Risiko:** Art. 83 DSGVO (bis zu 4% Jahresumsatz)

❌ **Schwellenwert-Analyse:** Fehlt
- Keine Bewertung ob DPIA-Pflicht besteht
- Keine Dokumentation der Ausnahmen
- **Risiko:** Aufsichtsbehörden-Rückfragen

### 1.2 DPIA-Pflicht Prüfung

**Kriterien (Art. 35 Abs. 3 DSGVO):**

| Kriterium | Trifft zu? | Details |
|-----------|------------|---------|
| Systematische umfangreiche Bewertung | ✅ JA | AI-basierte Klassifikation |
| Automatisierte Verarbeitung mit Rechtswirkung | ⚠️ UNKLAR | Abhängig von Use Case |
| Umfangreiche Verarbeitung sensibler Daten | ⚠️ MÖGLICH | Verträge, Rechnungen, HR-Docs |
| Systematische Überwachung | ❌ NEIN | Keine Personenüberwachung |
| Neue Technologien | ⚠️ JA | AI/ML für Klassifikation |

**Fazit:** DPIA **WAHRSCHEINLICH ERFORDERLICH** (3/5 Kriterien erfüllt)

### 1.3 Empfohlene DPIA-Durchführung

**QW-1: DPIA Template erstellen**

Datei: `docs/DPIA_COVINA.md`

```markdown
# Datenschutz-Folgenabschätzung (DPIA) - Covina System

## 1. Beschreibung der Verarbeitungstätigkeit
- Zweck: Automatische Klassifikation von Geschäftsdokumenten
- Kategorien betroffener Personen: Mitarbeiter, Geschäftspartner, Kunden
- Kategorien personenbezogener Daten: Namen, Adressen, Vertragsdaten, ggf. HR-Daten

## 2. Notwendigkeit und Verhältnismäßigkeit
- Erforderlichkeit: [JA/NEIN] - Begründung
- Geeignetheit: [JA/NEIN] - Begründung
- Angemessenheit: [JA/NEIN] - Begründung

## 3. Risiken für Rechte und Freiheiten
### Risiko 1: Unbefugter Zugriff
- Wahrscheinlichkeit: [NIEDRIG/MITTEL/HOCH]
- Schwere: [NIEDRIG/MITTEL/HOCH]
- Maßnahmen: AuthN/AuthZ, Encryption at Rest/Transit

### Risiko 2: Datenverlust
- Wahrscheinlichkeit: [NIEDRIG]
- Schwere: [HOCH]
- Maßnahmen: Backup/Restore (FEHLEND!)

## 4. Abhilfemaßnahmen
- [ ] Verschlüsselung (TLS implementiert, At-Rest fehlt)
- [ ] Zugriffskontrolle (OAuth2/RBAC implementiert)
- [ ] Logging & Monitoring (Teilweise)
- [ ] Backup/Restore (NICHT IMPLEMENTIERT)
- [ ] Pseudonymisierung (NICHT IMPLEMENTIERT)

## 5. Konsultation Datenschutzbeauftragter
- Datum: [TBD]
- Ergebnis: [TBD]
```

**Aufwand:** 1-2 Tage (DSB-Konsultation erforderlich)

---

## 2. Art. 30 Verzeichnis von Verarbeitungstätigkeiten

### 2.1 Status

❌ **Verzeichnis:** Nicht vorhanden
- Art. 30 DSGVO verpflichtend für >250 Mitarbeiter ODER risikoreiche Verarbeitung
- Covina = risikoreiche Verarbeitung → Pflicht gilt
- **Compliance-Risiko:** Art. 83 DSGVO (Bußgeld)

### 2.2 Erforderliche Inhalte (Art. 30 Abs. 1)

| Feld | Status | Beispiel Covina |
|------|--------|-----------------|
| Name/Kontakt Verantwortlicher | ❌ | [Organisation] |
| Zwecke der Verarbeitung | ❌ | "Dokumentenklassifikation, Compliance-Prüfung" |
| Kategorien betroffener Personen | ❌ | "Mitarbeiter, Geschäftspartner" |
| Kategorien personenbezogener Daten | ❌ | "Namen, Vertragsdaten, Finanzdaten" |
| Kategorien von Empfängern | ❌ | "Interne Fachabteilungen" |
| Drittlandübermittlung | ❌ | "NEIN" (alle DBs in DE) |
| Löschfristen | ❌ | "Nach 10 Jahren" (Beispiel) |
| TOM-Beschreibung | ⚠️ | Teilweise in Audits dokumentiert |

### 2.3 Empfohlene Implementierung

**QW-2: Art. 30 Verzeichnis Template**

Datei: `docs/ART_30_VERZEICHNIS.md`

```markdown
# Verzeichnis von Verarbeitungstätigkeiten (Art. 30 DSGVO)

## Verarbeitung 1: Dokumentenklassifikation

### Verantwortlicher
- Name: [Organisation/Firma]
- Anschrift: [Adresse]
- Vertreter: [Name DSB]
- Kontakt: [E-Mail]

### Zwecke der Verarbeitung
- Automatische Klassifikation hochgeladener Geschäftsdokumente
- Compliance-Prüfung (DSGVO, Regulatorik)
- Wissensmanagement und Retrieval

### Rechtsgrundlage
- Art. 6 Abs. 1 lit. b DSGVO (Vertragserfüllung)
- Art. 6 Abs. 1 lit. f DSGVO (berechtigtes Interesse)

### Kategorien betroffener Personen
- Mitarbeiter (Upload von HR-Dokumenten)
- Geschäftspartner (Verträge, Rechnungen)
- Kunden (Verträge, Korrespondenz)

### Kategorien personenbezogener Daten
- Stammdaten (Namen, Adressen, Kontaktdaten)
- Vertragsdaten (Laufzeiten, Konditionen)
- Finanzdaten (Rechnungen, Zahlungsinformationen)
- ggf. besondere Kategorien (z.B. HR-Gesundheitsdaten - falls verarbeitet)

### Kategorien von Empfängern
- Interne Fachabteilungen (HR, Finance, Legal)
- IT-Administration (System-Wartung)

### Drittlandübermittlung
- NEIN (alle Datenbanken in Deutschland)

### Löschfristen
- Standard: 10 Jahre nach Vertragsende (HGB §257)
- Ausnahme: Kürzere Fristen auf Antrag (Art. 17 DSGVO)
- Legal Hold: Aussetzung bei laufenden Verfahren

### Technische und organisatorische Maßnahmen (TOM)
- Verschlüsselung: TLS 1.2+ (Transit), At-Rest (geplant)
- Zugriffskontrolle: OAuth2/JWT + RBAC
- Logging: Strukturierte Logs (PII-Redaktion geplant)
- Backup: Nicht implementiert (KRITISCH)
- Pseudonymisierung: Nicht implementiert

### Letzte Aktualisierung
- Datum: [21.10.2025]
- Nächste Review: [21.01.2026]
```

**Aufwand:** 4-8 Stunden + regelmäßige Updates

---

## 3. Konsenten & Legitimationsgrundlagen

### 3.1 Status

❌ **Consent Management:** Nicht implementiert
- Keine Einwilligungen dokumentiert
- Keine Widerrufsfunktion
- **Risiko:** Art. 7 DSGVO - ungültige Verarbeitung

⚠️ **Legitimationsgrundlagen:** Unklar
- Welche Art. 6 Abs. 1 DSGVO Grundlage wird verwendet?
- Vertragserfüllung (lit. b)?
- Berechtigtes Interesse (lit. f)?
- **Risiko:** Keine Dokumentation = keine Rechtfertigung

### 3.2 Art. 6 DSGVO Analyse

**Mögliche Rechtsgrundlagen für Covina:**

| Rechtsgrundlage | Anwendbar? | Begründung |
|-----------------|------------|------------|
| Art. 6 Abs. 1 lit. a (Einwilligung) | ⚠️ OPTIONAL | Für freiwillige Features (z.B. Newsletter) |
| Art. 6 Abs. 1 lit. b (Vertragserfüllung) | ✅ JA | DMS als vertragliche Leistung |
| Art. 6 Abs. 1 lit. c (Rechtliche Verpflichtung) | ✅ JA | HGB §257 Aufbewahrungspflicht |
| Art. 6 Abs. 1 lit. f (Berechtigtes Interesse) | ✅ JA | Effizienz, Wissensmanagement |

**Empfehlung:** **Primär lit. b + c, sekundär lit. f**

### 3.3 Empfohlene Implementierung

**QW-3: Consent Management (Optional, für lit. a)**

```python
# Database Schema
CREATE TABLE user_consents (
    id SERIAL PRIMARY KEY,
    user_id TEXT NOT NULL,
    purpose TEXT NOT NULL,  -- 'marketing', 'analytics', 'feature_x'
    consented BOOLEAN NOT NULL,
    consented_at TIMESTAMP,
    withdrawn_at TIMESTAMP,
    consent_text TEXT,  -- Exact wording shown to user
    ip_address TEXT,
    user_agent TEXT
);

# API Endpoint
@app.post("/user/consent")
async def record_consent(
    user_id: str,
    purpose: str,
    consented: bool,
    _principal: Principal = Depends(get_current_user)
):
    """Dokumentiert Nutzer-Einwilligung (Art. 7 DSGVO)"""
    # Validate user owns consent
    if _principal.username != user_id:
        raise HTTPException(403)
    
    # Record
    db.execute(
        "INSERT INTO user_consents (user_id, purpose, consented, consented_at, ip_address) VALUES (%s, %s, %s, %s, %s)",
        (user_id, purpose, consented, datetime.now(), request.client.host)
    )
    
    return {"status": "recorded"}

# Widerruf
@app.delete("/user/consent/{purpose}")
async def withdraw_consent(purpose: str, _principal: Principal = Depends(get_current_user)):
    """Widerruf der Einwilligung (Art. 7 Abs. 3 DSGVO)"""
    db.execute(
        "UPDATE user_consents SET consented = false, withdrawn_at = %s WHERE user_id = %s AND purpose = %s",
        (datetime.now(), _principal.username, purpose)
    )
    return {"status": "withdrawn"}
```

**Aufwand:** 1 Tag (falls Einwilligungen benötigt)

**QW-4: Rechtsgrundlagen-Dokumentation**

Datei: `docs/RECHTSGRUNDLAGEN.md`

```markdown
# Rechtsgrundlagen für Datenverarbeitung (Covina)

## 1. Dokumentenklassifikation
- **Rechtsgrundlage:** Art. 6 Abs. 1 lit. b DSGVO (Vertragserfüllung)
- **Begründung:** DMS-Leistung ist Kern des Vertrags mit Kunden
- **Alternativen:** lit. f (berechtigtes Interesse an effizienter Dokumentenverwaltung)

## 2. Compliance-Prüfung
- **Rechtsgrundlage:** Art. 6 Abs. 1 lit. c DSGVO (Rechtliche Verpflichtung)
- **Begründung:** HGB §257 Aufbewahrungspflicht, DSGVO-Compliance

## 3. Logging & Monitoring
- **Rechtsgrundlage:** Art. 6 Abs. 1 lit. f DSGVO (Berechtigtes Interesse)
- **Begründung:** IT-Sicherheit, Fehlerdiagnose
- **Interessenabwägung:** Sicherheitsinteresse > Betroffeneninteresse (minimale Logs)

## 4. Analytics (falls implementiert)
- **Rechtsgrundlage:** Art. 6 Abs. 1 lit. a DSGVO (Einwilligung)
- **Begründung:** Freiwillige Optimierung
- **Widerruf:** Jederzeit möglich
```

**Aufwand:** 2-4 Stunden

---

## 4. Datenminimierung & Pseudonymisierung

### 4.1 Status

⚠️ **Datenminimierung:** Teilweise
- Quality Scores werden berechnet (relevant)
- Keine automatische Entfernung von Überflüssigem
- **Risiko:** Art. 5 Abs. 1 lit. c DSGVO (Datenminimierung)

❌ **Pseudonymisierung:** Nicht implementiert
- Namen/IDs werden im Klartext gespeichert
- Keine automatische Pseudonymisierung
- **Risiko:** Art. 32 DSGVO (TOM-Anforderung)

### 4.2 Empfohlene Implementierung

**QW-5: Pseudonymisierung Helper**

```python
import hashlib
import hmac

class Pseudonymizer:
    def __init__(self, secret_key: str):
        self.secret = secret_key.encode()
    
    def pseudonymize(self, identifier: str) -> str:
        """HMAC-basierte Pseudonymisierung (deterministisch)"""
        return hmac.new(self.secret, identifier.encode(), hashlib.sha256).hexdigest()[:16]
    
    def pseudonymize_document(self, doc: Dict[str, Any]) -> Dict[str, Any]:
        """Pseudonymisiert PII-Felder in Dokument"""
        if 'author' in doc:
            doc['author_pseudo'] = self.pseudonymize(doc['author'])
            del doc['author']
        
        if 'email' in doc:
            doc['email_pseudo'] = self.pseudonymize(doc['email'])
            del doc['email']
        
        return doc

# Usage
pseudonymizer = Pseudonymizer(os.getenv('PSEUDONYM_SECRET'))

# In process_document()
doc_metadata = pseudonymizer.pseudonymize_document(doc_metadata)
```

**Benefit:** 
- Erfüllt Art. 32 DSGVO (TOM)
- Reduziert Risiko bei Datenleck
- Deterministisch (gleiche Person = gleiches Pseudonym)

**Aufwand:** 1 Tag

**QW-6: Datenminimierung by Design**

```python
# Metadata Filtering
ALLOWED_METADATA_KEYS = {
    'document_id', 'classification', 'created_at', 
    'quality_score', 'processing_status', 'file_path'
}

def minimize_metadata(metadata: Dict[str, Any]) -> Dict[str, Any]:
    """Entfernt alle nicht-essentiellen Metadaten"""
    return {k: v for k, v in metadata.items() if k in ALLOWED_METADATA_KEYS}

# In insert_document()
metadata = minimize_metadata(metadata)
```

**Aufwand:** 4 Stunden

---

## 5. Data Residency & Mandantenfähigkeit

### 5.1 Status

⚠️ **Data Residency:** Teilweise
- Alle DBs in Deutschland (192.168.178.94)
- Keine Geo-Fencing Konfiguration
- **Risiko:** Keine garantierte EU-Residency in Cloud-Deployment

❌ **Tenant Isolation:** Nicht implementiert
- Keine Mandanten-Trennung in DBs
- Alle Daten in shared tables/collections
- **Risiko:** Multi-Tenant Datenleck

### 5.2 Empfohlene Implementierung

**QW-7: Tenant-ID in allen Tabellen**

```sql
-- Migration Script
ALTER TABLE documents ADD COLUMN tenant_id TEXT;
ALTER TABLE job_files ADD COLUMN tenant_id TEXT;
CREATE INDEX idx_documents_tenant_id ON documents (tenant_id);

-- Row-Level Security (PostgreSQL)
ALTER TABLE documents ENABLE ROW LEVEL SECURITY;

CREATE POLICY tenant_isolation ON documents
    USING (tenant_id = current_setting('app.current_tenant')::text);
```

```python
# Tenant Context
from contextvars import ContextVar

current_tenant = ContextVar('current_tenant', default=None)

# Middleware
@app.middleware("http")
async def tenant_middleware(request: Request, call_next):
    # Extract tenant from JWT or header
    tenant_id = request.headers.get("X-Tenant-ID") or extract_from_jwt(request)
    current_tenant.set(tenant_id)
    
    # Set PostgreSQL session variable
    async with get_db_connection() as conn:
        await conn.execute(f"SET app.current_tenant = '{tenant_id}'")
    
    response = await call_next(request)
    return response
```

**Aufwand:** 2-3 Tage (inkl. Migration)

**QW-8: Geo-Fencing Config**

```python
# config.py
ALLOWED_DB_REGIONS = ["eu-central-1", "eu-west-1"]  # AWS Example

def validate_db_region(host: str):
    """Prüft ob DB in erlaubter Region"""
    # IP-Geolocation oder Cloud-Provider API
    region = get_region_for_host(host)
    if region not in ALLOWED_DB_REGIONS:
        raise ValueError(f"DB region {region} not allowed (GDPR)")
```

**Aufwand:** 1 Tag

---

## 6. Lösch-Workflows & Retention

### 6.1 Status

✅ **Delete API:** Implementiert
- `delete_document(document_id)` vorhanden
- Location: `uds3/database/database_api_postgresql_pooled.py`

❌ **Retention Policies:** Nicht implementiert
- Keine automatische Löschung nach Ablauf
- Keine Berücksichtigung von Legal Hold
- **Risiko:** Art. 5 Abs. 1 lit. e DSGVO (Speicherbegrenzung)

❌ **Löschkonzept:** Nicht dokumentiert
- Keine Definition von Löschfristen
- Keine Konfliktauflösung (Retention vs. Legal Hold)
- **Risiko:** Art. 17 DSGVO (Recht auf Löschung)

### 6.2 Empfohlene Implementierung

**QW-9: Retention Policy Engine**

```python
# Database Schema
CREATE TABLE retention_policies (
    id SERIAL PRIMARY KEY,
    document_type TEXT NOT NULL,  -- 'invoice', 'contract', 'hr_document'
    retention_years INTEGER NOT NULL,  -- HGB §257: 10 years
    legal_basis TEXT,  -- 'HGB_257', 'CUSTOM'
    created_at TIMESTAMP DEFAULT NOW()
);

CREATE TABLE legal_holds (
    id SERIAL PRIMARY KEY,
    document_id TEXT NOT NULL,
    reason TEXT NOT NULL,  -- 'litigation', 'audit', 'investigation'
    created_by TEXT NOT NULL,
    created_at TIMESTAMP DEFAULT NOW(),
    released_at TIMESTAMP
);

# Retention Check
def check_retention_expired(doc: Dict) -> bool:
    """Prüft ob Dokument gelöscht werden darf"""
    # 1. Check Legal Hold
    hold = db.execute(
        "SELECT id FROM legal_holds WHERE document_id = %s AND released_at IS NULL",
        (doc['document_id'],)
    )
    if hold:
        return False  # Legal Hold aktiv
    
    # 2. Check Retention Policy
    policy = db.execute(
        "SELECT retention_years FROM retention_policies WHERE document_type = %s",
        (doc['classification'],)
    )
    
    if not policy:
        return False  # Keine Policy = Safe Default (nicht löschen)
    
    retention_end = doc['created_at'] + timedelta(days=policy['retention_years'] * 365)
    return datetime.now() > retention_end

# Scheduled Deletion (Cron Job)
async def run_retention_cleanup():
    """Löscht abgelaufene Dokumente (täglich)"""
    docs = db.execute("SELECT document_id, classification, created_at FROM documents")
    
    for doc in docs:
        if check_retention_expired(doc):
            logger.info(f"[RETENTION] Deleting expired document {doc['document_id']}")
            delete_document(doc['document_id'])
```

**Aufwand:** 2 Tage

**QW-10: Art. 17 DSGVO - Löschanfrage API**

```python
@app.delete("/user/data")
async def request_deletion(
    user_id: str,
    _principal: Principal = Depends(get_current_user)
):
    """Recht auf Löschung (Art. 17 DSGVO)"""
    # Validate user owns data
    if _principal.username != user_id:
        raise HTTPException(403)
    
    # Check Legal Hold
    holds = db.execute(
        "SELECT document_id FROM legal_holds WHERE document_id IN (SELECT document_id FROM documents WHERE author_pseudo = %s) AND released_at IS NULL",
        (pseudonymizer.pseudonymize(user_id),)
    )
    
    if holds:
        return {
            "status": "pending",
            "reason": "Legal hold active",
            "documents_affected": len(holds)
        }
    
    # Delete all user documents
    deleted = db.execute(
        "DELETE FROM documents WHERE author_pseudo = %s RETURNING document_id",
        (pseudonymizer.pseudonymize(user_id),)
    )
    
    return {
        "status": "completed",
        "documents_deleted": len(deleted)
    }
```

**Aufwand:** 1 Tag

---

## 7. Backup/Restore & RPO/RTO

### 7.1 Status

❌ **Backup:** Nicht implementiert
- Keine automatischen Backups
- Keine Versionierung
- **Risiko:** Datenverlust, Art. 32 DSGVO (Verfügbarkeit)

❌ **RPO/RTO:** Nicht definiert
- Recovery Point Objective: Unklar
- Recovery Time Objective: Unklar
- **Risiko:** Keine SLA-Garantie

❌ **Disaster Recovery:** Nicht getestet
- Kein DR-Plan
- Keine Restore-Tests
- **Risiko:** Ungetestete Wiederherstellung

### 7.2 RPO/RTO Requirements

**Empfohlene Targets:**
- **RPO:** < 1 Stunde (max. 1h Datenverlust)
- **RTO:** < 4 Stunden (Wiederherstellung innerhalb 4h)

**Technische Umsetzung:**

| Datenbank | Backup-Methode | Frequenz | RPO | RTO |
|-----------|----------------|----------|-----|-----|
| PostgreSQL | pg_dump + WAL | Täglich + kontinuierlich | 15min | 2h |
| ChromaDB | Snapshot | Täglich | 24h | 1h |
| Neo4j | neo4j-admin backup | Täglich | 24h | 2h |
| CouchDB | Replication | Kontinuierlich | 1min | 30min |

### 7.3 Empfohlene Implementierung

**QW-11: PostgreSQL Backup Script**

```bash
#!/bin/bash
# File: scripts/backup_postgres.sh

BACKUP_DIR="/var/backups/covina/postgres"
TIMESTAMP=$(date +%Y%m%d_%H%M%S)
BACKUP_FILE="$BACKUP_DIR/covina_$TIMESTAMP.sql.gz"

# Full Backup
pg_dump -h 192.168.178.94 -U postgres -d postgres | gzip > "$BACKUP_FILE"

# Encrypt
gpg --encrypt --recipient backup@covina.local "$BACKUP_FILE"
rm "$BACKUP_FILE"  # Remove unencrypted

# Upload to S3 (optional)
# aws s3 cp "$BACKUP_FILE.gpg" s3://covina-backups/postgres/

# Retention (keep 30 days)
find "$BACKUP_DIR" -name "*.gpg" -mtime +30 -delete

# WAL Archiving (continuous)
# Edit postgresql.conf:
# wal_level = replica
# archive_mode = on
# archive_command = 'test ! -f /var/backups/wal/%f && cp %p /var/backups/wal/%f'
```

**Cron:** Täglich 2:00 Uhr
```cron
0 2 * * * /opt/covina/scripts/backup_postgres.sh
```

**QW-12: Restore Test (Quarterly)**

```bash
#!/bin/bash
# File: scripts/test_restore.sh

# 1. Restore to test DB
gunzip < "$BACKUP_FILE.gz" | gpg --decrypt | psql -h localhost -U postgres -d postgres_test

# 2. Validate
psql -h localhost -U postgres -d postgres_test -c "SELECT COUNT(*) FROM documents;"

# 3. Cleanup
dropdb postgres_test
```

**Aufwand:** 2 Tage (Setup + Testing)

---

## 8. Compliance-Checkliste

| Anforderung | Status | Priorität | Aufwand |
|-------------|--------|-----------|---------|
| DPIA durchführen | ❌ | P0 | 2d |
| Art. 30 Verzeichnis | ❌ | P0 | 4-8h |
| Rechtsgrundlagen dokumentieren | ❌ | P1 | 2-4h |
| Consent Management | ❌ | P2 | 1d |
| Pseudonymisierung | ❌ | P1 | 1d |
| Datenminimierung | ⚠️ | P1 | 4h |
| Tenant Isolation | ❌ | P1 | 2-3d |
| Geo-Fencing | ⚠️ | P2 | 1d |
| Retention Policies | ❌ | P1 | 2d |
| Art. 17 Lösch-API | ❌ | P1 | 1d |
| Backup/Restore | ❌ | P0 | 2d |
| DR-Plan & Tests | ❌ | P1 | 1d |

---

## 9. Quick Wins (Priorisiert)

### Top 5 Quick Wins (1 Woche):

1. **Art. 30 Verzeichnis** (4-8h, P0, Compliance-Pflicht)
2. **DPIA Template** (2d, P0, mit DSB-Konsultation)
3. **PostgreSQL Backup** (2d, P0, Datenverlust-Risiko)
4. **Rechtsgrundlagen-Doku** (2-4h, P1, Rechtfertigung)
5. **Pseudonymisierung** (1d, P1, Art. 32)

### Mittelfristig (2 Wochen):

6. **Retention Policies** (2d, P1)
7. **Art. 17 Lösch-API** (1d, P1)
8. **Datenminimierung** (4h, P1)

### Langfristig (1 Monat):

9. **Tenant Isolation** (2-3d, P1, Multi-Tenant)
10. **Consent Management** (1d, P2, falls Einwilligungen)
11. **DR-Plan & Quarterly Tests** (1d, P1)

---

## 10. Risiko-Bewertung

| Risiko | Wahrscheinlichkeit | Impact | Gesamt | Maßnahme |
|--------|-------------------|--------|--------|----------|
| DSGVO-Bußgeld (fehlende DPIA) | MITTEL | HOCH | 🔴 KRITISCH | QW-2 (2d) |
| Datenverlust (kein Backup) | NIEDRIG | HOCH | 🟡 HIGH | QW-11 (2d) |
| Ungültige Verarbeitung (keine Rechtsgrundlage) | MITTEL | HOCH | 🟡 HIGH | QW-4 (4h) |
| Art. 30 Verstoß | HOCH | MITTEL | 🟡 HIGH | QW-2 (8h) |
| Multi-Tenant Datenleck | NIEDRIG | HOCH | 🟡 MEDIUM | QW-7 (3d) |

---

## 11. Zusammenfassung

**Status:** 🟡 TEILWEISE IMPLEMENTIERT (25% Coverage)

**Stärken:**
- ✅ Compliance Service vorhanden
- ✅ Delete API implementiert
- ✅ DBs in Deutschland

**Schwächen:**
- ❌ Keine DPIA durchgeführt
- ❌ Kein Art. 30 Verzeichnis
- ❌ Kein Backup/Restore
- ❌ Keine Pseudonymisierung

**Empfehlung:** 5 Quick Wins (1 Woche) sofort umsetzen für Compliance.

**Nächster Audit:** Nach DPIA + Art. 30 (in 2 Wochen)

---

**Audit abgeschlossen:** 21. Oktober 2025  
**Nächste Review:** 4. November 2025  
**Verantwortlich:** Legal + Datenschutzbeauftragter
