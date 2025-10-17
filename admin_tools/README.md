# Covina Admin Tools

**Version:** 1.0.0  
**Datum:** 17. Oktober 2025  
**Status:** ✅ PRODUCTION READY

---

## 📋 Übersicht

Die Covina Admin Tools sind eine Suite von Tkinter-basierten GUI-Applikationen zur Verwaltung von:

1. **Golden Datasets** (Relational) - PostgreSQL
2. **Graph Patterns** (Neo4j Hybrid) - PostgreSQL + Neo4j
3. **Governance Policies** - PostgreSQL

Alle Tools bieten CRUD-Operationen mit benutzerfreundlicher Oberfläche.

---

## 🚀 Quick Start

### Option 1: Launcher verwenden (Empfohlen)

```bash
python admin_tools/launcher.py
```

Der Launcher zeigt alle verfügbaren Tools und ermöglicht einfaches Starten.

### Option 2: Einzelne Tools direkt starten

```bash
# Golden Dataset Manager
python admin_tools/golden_dataset_manager.py

# Graph Pattern Manager
python admin_tools/graph_pattern_manager.py

# Governance Policy Manager
python admin_tools/governance_policy_manager.py
```

---

## 📦 Requirements

```bash
# Python Packages
pip install requests tkinter

# Backend (muss laufen!)
python main_backend.py         # Port 45678 (Main Backend)
python ingestion_backend.py    # Port 45679 (Ingestion)
```

**Wichtig:** Die Admin-Tools benötigen einen laufenden Covina Backend!

---

## 🛠️ Tools im Detail

### 1. Golden Dataset Manager

**Zweck:** Verwaltung von relational gespeicherten Golden Datasets

**Features:**
- ✅ CRUD Operations (Create, Read, Update, Delete)
- ✅ Filter nach Klassifikation, Qualitätsscore, Reviewer
- ✅ Pagination & Search
- ✅ CSV Export
- ✅ Echtzeit-Aktualisierung
- ✅ Verbindungsstatus-Anzeige

**UI Components:**
- **Filter Panel:** Klassifikation, Min. Qualität, Geprüft von
- **Tabelle:** Übersicht aller Datasets mit 6 Spalten
- **Edit Dialog:** Vollständiger Editor mit allen Feldern
- **Toolbar:** Quick Actions für alle CRUD Operations

**API Endpoints:**
```
GET  /golden-dataset          # List datasets (with filters)
POST /golden-dataset          # Create/Update dataset (UPSERT)
```

**Beispiel Workflow:**
1. Tool starten
2. Filter setzen (z.B. nur "Rechnung", min. Qualität 0.8)
3. "Neu" klicken → Dialog öffnet sich
4. Daten eingeben → "Speichern"
5. Liste aktualisiert sich automatisch

---

### 2. Graph Pattern Manager

**Zweck:** Verwaltung von Neo4j Graph Patterns (Hybrid Storage)

**Features:**
- ✅ Pattern Definition (JSON-basiert)
- ✅ Node & Relationship Configuration
- ✅ Validation Rules Editor
- ✅ Pattern Visualization (Text-basiert)
- ✅ JSON Import/Export
- ✅ Usage Tracking

**UI Components:**
- **Pattern List:** Treeview mit Pattern-Übersicht
- **Details Panel:** Vollständige Pattern-Ansicht
- **Multi-Tab Editor:** 4 Tabs (Basic, Nodes, Relationships, Validation)
- **JSON Preview:** Live-Vorschau der Pattern-Struktur

**API Endpoints:**
```
GET  /graph-golden-dataset                # List patterns
POST /graph-golden-dataset                # Create/Update pattern
GET  /graph-golden-dataset/{pattern_id}   # Get pattern details
```

**Beispiel Pattern:**
```json
{
  "pattern_id": "invoice_workflow",
  "pattern_name": "Rechnung → Lieferschein → Vertrag Workflow",
  "category": "workflow",
  "nodes_definition": {
    "node_types": [
      {"type": "Invoice", "properties": ["invoice_id", "amount"]},
      {"type": "Delivery", "properties": ["delivery_id", "date"]},
      {"type": "Contract", "properties": ["contract_id"]}
    ]
  },
  "relationships_definition": {
    "relationship_types": [
      {"type": "REFERS_TO", "from_node": "Invoice", "to_node": "Delivery"},
      {"type": "BASED_ON", "from_node": "Delivery", "to_node": "Contract"}
    ]
  },
  "validation_rules": {
    "required_nodes": ["Invoice", "Contract"],
    "min_nodes": 2
  }
}
```

---

### 3. Governance Policy Manager

**Zweck:** Verwaltung von Governance Policies (Retention, Compliance, etc.)

**Features:**
- ✅ Policy Management (7 Policy Types)
- ✅ Approval Workflow
- ✅ Temporal Validity (effective_from/until)
- ✅ Priority-based Resolution
- ✅ Soft Delete (status: inactive)
- ✅ JSONB Rules Editor
- ✅ Active-Only Filter

**UI Components:**
- **Filter Panel:** Type, Scope, Status, Active-Only
- **Policy Table:** Übersicht mit Genehmigungsstatus
- **Details Panel:** Vollständige Policy-Ansicht
- **Multi-Tab Editor:** 3 Tabs (Basic, Rules, Validity)
- **Approval Button:** One-Click Genehmigung

**Policy Types:**
1. **retention** - Aufbewahrungsfristen
2. **access_control** - Zugriffskontrolle
3. **classification** - Klassifikationsregeln
4. **quality** - Qualitätsstandards
5. **audit** - Audit-Trail Anforderungen
6. **compliance** - Compliance-Regeln (DSGVO, etc.)
7. **custom** - Benutzerdefiniert

**API Endpoints:**
```
GET  /governance/policies     # List policies (with filters)
POST /governance/policies     # Create/Update policy (UPSERT)
```

**Beispiel Policy:**
```json
{
  "policy_id": "retention_invoices_10y",
  "name": "Rechnungsaufbewahrung 10 Jahre",
  "policy_type": "retention",
  "scope": "document_type",
  "status": "active",
  "priority": 1000,
  "rules": {
    "retention_days": 3650,
    "action": "archive",
    "applies_to": ["Rechnung"]
  },
  "effective_from": "2024-01-01",
  "effective_until": null,
  "approved_by": "admin",
  "approved_at": "2024-01-01T10:00:00"
}
```

---

## 🎨 UI/UX Design

### Design Principles

- **Dark Theme:** Angenehm für die Augen (#2b2b2b Hintergrund)
- **Color Coding:** 
  - Blau (#4a90e2): Primary Actions
  - Grün (#27ae60): Success/Approval
  - Rot (#e74c3c): Delete/Danger
  - Grau (#95a5a6): Secondary Actions
- **Icons:** Emoji-basiert für schnelle Erkennung
- **Responsive:** Alle Panels sind resizable
- **Real-Time:** Status-Updates alle 2 Sekunden

### Keyboard Shortcuts

- **Double-Click:** Eintrag bearbeiten
- **Enter:** In Formularen = Speichern
- **Escape:** Dialog schließen (in Zukunft)

---

## 🔧 Konfiguration

### Backend URL

Standardmäßig: `http://127.0.0.1:45678`

**Option 1:** Im Launcher konfigurieren (Footer)
**Option 2:** Environment Variable setzen:

```bash
export COVINA_BACKEND_URL=http://192.168.1.100:45678
```

**Option 3:** Direkt im Code ändern (nicht empfohlen):

```python
# In jedem Tool:
def __init__(self, root: tk.Tk, backend_url: str = "http://127.0.0.1:45678"):
```

---

## 📊 Datenbank-Schema

### Golden Dataset (PostgreSQL)

```sql
CREATE TABLE golden_dataset (
    id SERIAL PRIMARY KEY,
    document_id TEXT UNIQUE NOT NULL,
    classification TEXT NOT NULL,
    quality_score REAL,
    reviewed_by TEXT,
    review_date DATE,
    notes TEXT,
    metadata JSONB,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
```

### Graph Golden Dataset (PostgreSQL)

```sql
CREATE TABLE graph_golden_dataset (
    id SERIAL PRIMARY KEY,
    pattern_id TEXT UNIQUE NOT NULL,
    pattern_name TEXT NOT NULL,
    category TEXT,
    description TEXT,
    nodes_definition JSONB,
    relationships_definition JSONB,
    validation_rules JSONB,
    usage_count INTEGER DEFAULT 0,
    created_by TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
```

### Governance Policies (PostgreSQL)

```sql
CREATE TABLE governance_policies (
    id SERIAL PRIMARY KEY,
    policy_id TEXT UNIQUE NOT NULL,
    name TEXT NOT NULL,
    description TEXT,
    policy_type TEXT,
    scope TEXT,
    rules JSONB,
    status TEXT DEFAULT 'draft',
    priority INTEGER DEFAULT 100,
    effective_from TIMESTAMP,
    effective_until TIMESTAMP,
    created_by TEXT,
    approved_by TEXT,
    approved_at TIMESTAMP,
    metadata JSONB,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
```

---

## 🚨 Troubleshooting

### Problem: "Backend nicht erreichbar"

**Lösung:**
1. Backend starten: `python main_backend.py`
2. URL prüfen: `http://127.0.0.1:45678/health`
3. Firewall-Einstellungen prüfen

### Problem: "Tabelle existiert nicht"

**Lösung:**
1. Migrations ausführen:
   ```bash
   python migrations/create_golden_dataset_table.py
   python migrations/create_graph_golden_dataset.py
   python migrations/create_governance_policies_table.py
   ```

### Problem: "JSON Fehler beim Speichern"

**Lösung:**
- JSON-Syntax prüfen (valid JSON required!)
- Online Validator verwenden: https://jsonlint.com/

### Problem: "DELETE funktioniert nicht"

**Hinweis:** DELETE Endpoints sind noch nicht implementiert im Backend.
- Golden Dataset: Manuell in DB löschen
- Governance: Soft Delete (status: inactive) funktioniert!

---

## 📝 Development

### Code-Struktur

```
admin_tools/
├── launcher.py                      # Zentrale Launcher-App
├── golden_dataset_manager.py        # Golden Dataset CRUD
├── graph_pattern_manager.py         # Graph Pattern CRUD
├── governance_policy_manager.py     # Governance Policy CRUD
└── README.md                        # Diese Datei
```

### Klassen-Hierarchie

Alle Tools folgen dem gleichen Pattern:

```python
class XYZManager:
    def __init__(self, root, backend_url)
    def _create_menu()              # Menu Bar
    def _create_toolbar()           # Quick Actions
    def _create_main_layout()       # Main UI
    def _create_status_bar()        # Footer
    def refresh_list()              # Load data from API
    def show_create_dialog()        # Create new entry
    def show_edit_dialog()          # Edit existing entry
    def delete_entry()              # Delete entry

class XYZDialog:
    def __init__(self, parent, backend_url, mode, data)
    def save()                      # POST to API
```

### Erweiterungen

**Neue Features hinzufügen:**

1. **Neues Feld in Tabelle:**
   - Backend Migration erweitern
   - Pydantic Model updaten
   - UI Column hinzufügen
   - Edit Dialog erweitern

2. **Neuer Filter:**
   - ComboBox/Entry in Filter Panel
   - Query Parameter in `refresh_list()`
   - Filter-Reset erweitern

3. **Neue Export-Funktion:**
   - Button in Toolbar
   - Export-Logik implementieren
   - File Dialog integrieren

---

## 🎯 Roadmap

### Version 1.1 (Geplant)

- [ ] DELETE Endpoints im Backend implementieren
- [ ] Batch Operations (Multi-Select)
- [ ] Import von CSV/JSON
- [ ] Advanced Search (Full-Text)
- [ ] Keyboard Shortcuts
- [ ] Theme Switcher (Light/Dark)

### Version 2.0 (Zukunft)

- [ ] All-in-One Dashboard (Multi-Tab)
- [ ] Real-Time Updates (WebSocket)
- [ ] User Authentication
- [ ] Audit Log Viewer
- [ ] Report Generator
- [ ] Graph Visualization (Neo4j Cytoscape)

---

## 📞 Support

**Entwickler:** Covina Backend Team  
**Version:** 1.0.0  
**Datum:** 17. Oktober 2025

**Bekannte Issues:**
- DELETE Endpoints fehlen im Backend (geplant für v1.1)
- Font Warnings in Windows (cosmetic, harmless)

**Feature Requests:**
- GitHub Issues erstellen
- Entwickler kontaktieren

---

## 📄 Lizenz

Internal Tool - Covina Project  
© 2025 Covina Backend Team

---

## ✅ Checkliste für Deployment

**Vor dem ersten Start:**

- [ ] Python 3.9+ installiert
- [ ] `pip install requests` ausgeführt
- [ ] PostgreSQL läuft (192.168.178.94:5432)
- [ ] Migrations ausgeführt (3x create_*_table.py)
- [ ] Backend gestartet (main_backend.py auf Port 45678)
- [ ] Health-Check erfolgreich: `curl http://127.0.0.1:45678/health`

**Beim ersten Start:**

- [ ] Launcher starten: `python admin_tools/launcher.py`
- [ ] Backend URL prüfen (Footer)
- [ ] Verbindungsstatus prüfen (grüner Punkt)
- [ ] Beispieldaten vorhanden (3-5 Einträge pro Tool)

**Bei Problemen:**

- [ ] Logs prüfen (Backend Console)
- [ ] Troubleshooting-Sektion in README lesen
- [ ] Backend neu starten
- [ ] Tools einzeln starten (nicht über Launcher)

---

**Happy Admin-ing! 🎉**
