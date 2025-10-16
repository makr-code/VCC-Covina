# UDS3 Covina Backend - Port-√úbersicht

**Erstellt:** 3. Oktober 2025  
**Version:** UDS3 Covina Backend v2.0.0  
**Autor:** GitHub Copilot

## √úbersicht aller Ports

Diese Dokumentation listet alle verwendeten Ports im UDS3 Covina Backend System auf.

---

## üèõÔ∏è **Hauptsystem (Core Services)**

### **FastAPI Backend Server**
- **Port:** `8001`
- **Protokoll:** HTTP
- **Host:** `127.0.0.1` (localhost)
- **Service:** Covina Backend API (FastAPI/Uvicorn)
- **Zweck:** 
  - Hauptwebserver f√ºr alle API-Endpunkte
  - Dokumenten-Upload und -Verarbeitung
  - UDS3 Framework Integration
  - Management Core API
- **Konfiguration:** `covina_backend.py:2595`
- **Status:** ‚úÖ Aktiv

### **GUI Client**
- **Port:** `8001` (Client)
- **Protokoll:** HTTP
- **Host:** `127.0.0.1`
- **Service:** Covina GUI API-Client
- **Zweck:** Desktop-GUI verbindet sich mit Backend
- **Konfiguration:** `covina_gui.py:36`
- **Status:** ‚úÖ Aktiv
- **Hinweis:** GUI zeigt falsch Port 8000 in API-Docs Link (`covina_gui.py:914`)

---

## üóÑÔ∏è **Datenbank-Services**

### **Neo4j Graph Database**
- **Port:** `7687`
- **Protokoll:** Bolt (Neo4j)
- **Host:** `127.0.0.1`
- **Service:** Neo4j Knowledge Graph
- **Zweck:**
  - UDS3 Relations Framework
  - Document Relations & Knowledge Graphs
  - Semantic Relationships
- **Auth:** `neo4j` / `v3f3b1d7`
- **Konfiguration:** `covina_backend.py:402-403`
- **Status:** ‚ö†Ô∏è Optional (Python 3.13 Kompatibilit√§tsprobleme)

### **SQLite Database**
- **Port:** N/A (File-based)
- **Protokoll:** File System
- **Service:** Relationale Datenbank
- **Zweck:**
  - Prim√§re Dokumenten-Metadaten
  - DSGVO Compliance Daten
  - UDS3 Core Storage
- **Dateien:**
  - `data/sqlite_relational.db`
  - `dsgvo_fallback.db`
  - `temp_*.db` (Test-Datenbanken)
- **Status:** ‚úÖ Aktiv

### **ChromaDB Vector Database**
- **Port:** `32768` (Produktiv) / `8000` (Fallback)
- **Protokoll:** HTTP/REST API
- **Host:** `192.168.178.94`
- **Service:** ChromaDB Vector Database Server
- **Zweck:**
  - Semantic Search
  - Document Embeddings  
  - AI-Enhanced Content Processing
- **Collection:** `covina_documents`
- **URL:** `http://192.168.178.94:32768`
- **Konfiguration:** 
  - `uds3/database/config.py:152-153` (Host/Port)
  - Env: `CHROMA_CLIENT_HOST`, `CHROMA_CLIENT_PORT`
- **Status:** ‚úÖ Aktiv (Externer Server)

### **PostgreSQL Database**
- **Port:** `5432`
- **Protokoll:** PostgreSQL/TCP
- **Host:** `192.168.178.94`
- **Service:** PostgreSQL Relational Database
- **Zweck:**
  - Relational Data Storage
  - Key-Value Store (via PostgreSQL)
  - Structured Metadata
- **Auth:** `postgres` / `postgres`
- **Database:** `vcc_relational_prod`
- **Konfiguration:** `uds3/database/config.py:185-190`
- **Env:** `POSTGRES_HOST`, `POSTGRES_PORT`, `POSTGRES_USER`
- **Status:** ‚úÖ Aktiv

### **CouchDB Document Database**  
- **Port:** `32931`
- **Protokoll:** HTTP/REST API
- **Host:** `192.168.178.94`
- **Service:** CouchDB Document Database
- **Zweck:**
  - Document Storage
  - File-based Backend
  - JSON Document Management
- **Auth:** `couchdb` / `couchdb`
- **Database:** `vcc_couch_prod`
- **Konfiguration:** `uds3/database/config.py:259-264`
- **Env:** `COUCHDB_HOST`, `COUCHDB_PORT`
- **Status:** ‚úÖ Aktiv

### **Redis Key-Value Store**
- **Port:** `6379`
- **Protokoll:** Redis/TCP
- **Host:** `localhost`
- **Service:** Redis In-Memory Database
- **Zweck:**
  - Caching
  - Session Storage
  - Key-Value Operations
- **Konfiguration:** `uds3/database/config.py:205-213`
- **Env:** `REDIS_HOST`, `REDIS_PORT`, `REDIS_PASSWORD`
- **Status:** ‚ùå Deaktiviert (nicht installiert)

### **Alternative Databases (Deaktiviert)**
- **ArangoDB:** Port `8529` (Graph Database Alternative)
- **HugeGraph:** Port `8080` (Enterprise Graph Database)
- **Active Directory:** Port `389` (LDAP Authentication)

---

## üìß **Mail-Services**

### **SMTP Server**
- **Port:** `25`
- **Protokoll:** SMTP
- **Host:** `192.168.178.94` (Fritz!Box)
- **Service:** E-Mail-Versand
- **Zweck:**
  - System-Benachrichtigungen
  - Compliance-Reports
  - Fehler-Meldungen
- **Auth:** `system@fritz.box` / `v3f3b1d7`
- **TLS:** Deaktiviert
- **Konfiguration:** 
  - `covina_backend.py:636` (Port)
  - Umgebungsvariablen: `SMTP_SERVER`, `SMTP_PORT`, `SMTP_USER`, `SMTP_PASSWORD`
- **Status:** ‚úÖ Konfiguriert

---

## üîß **Management & Monitoring**

### **Compliance Dashboard API**
- **Port:** `8080`
- **Protokoll:** HTTP
- **Host:** `localhost`
- **Service:** Compliance Dashboard HTTP-Server
- **Zweck:**
  - DSGVO Compliance Monitoring
  - Dashboard Web-Interface
  - Management Reports
- **Konfiguration:** `compliance_dashboard_api.py:732`
- **Status:** üîÑ Optional (bei Bedarf)

---

## ‚öôÔ∏è **Entwicklung & Testing**

### **ChromaDB Development Server**
- **Port:** `8000` (Standard/Fallback)
- **Protokoll:** HTTP
- **Service:** Lokaler ChromaDB Development Server
- **Zweck:** Entwicklung und Testing (Alternative)
- **Script:** `scripts/start_chromadb_server.py`
- **Konfiguration:** `uds3/database/config.py:153` (Fallback Port)
- **Status:** üí§ Nicht aktiv (Produktiver Server auf 32768 verwendet)

---

## üõ°Ô∏è **Sicherheit & Konfiguration**

### **Umgebungsvariablen (Ports)**

```bash
# E-Mail Konfiguration
SMTP_SERVER=192.168.178.94
SMTP_PORT=25
SMTP_USER=system@fritz.box
SMTP_PASSWORD=v3f3b1d7
SMTP_USE_TLS=false

# ChromaDB Server Konfiguration
CHROMA_CLIENT_HOST=192.168.178.94
CHROMA_CLIENT_PORT=32768
CHROMA_SERVER_URL=http://192.168.178.94:32768

# PostgreSQL Konfiguration
POSTGRES_HOST=192.168.178.94
POSTGRES_PORT=5432
POSTGRES_USER=postgres
POSTGRES_PASSWORD=postgres
POSTGRES_DB=vcc_relational_prod

# CouchDB Konfiguration
COUCHDB_HOST=192.168.178.94
COUCHDB_PORT=32931
COUCHDB_USER=couchdb
COUCHDB_PASSWORD=couchdb
COUCHDB_DB=vcc_couch_prod

# Redis Konfiguration (deaktiviert)
REDIS_HOST=localhost
REDIS_PORT=6379
REDIS_DB=0

# Neo4j Konfiguration (optional)
NEO4J_HOST=192.168.178.94
NEO4J_URI=neo4j://127.0.0.1:7687
NEO4J_USER=neo4j
NEO4J_PASSWORD=v3f3b1d7
```

---

## üìä **Port-Zuordnungstabelle**

| Port | Service | Protokoll | Host | Status | Zweck |
|------|---------|-----------|------|---------|--------|
| `25` | SMTP Server | SMTP | `192.168.178.94` | ‚úÖ Aktiv | E-Mail-Versand |
| `389` | Active Directory | LDAP | `192.168.178.94` | ‚ùå Deaktiviert | Authentication |
| `5432` | PostgreSQL | PostgreSQL | `192.168.178.94` | ‚úÖ Aktiv | Relational DB |
| `6379` | Redis | Redis | `127.0.0.1` | ‚ùå Deaktiviert | Key-Value Store |
| `7687` | Neo4j | Bolt | `127.0.0.1` | ‚ö†Ô∏è Optional | Knowledge Graph |
| `8000` | ChromaDB Dev | HTTP | `127.0.0.1` | üí§ Fallback | Entwicklung |
| `8001` | Covina Backend | HTTP | `127.0.0.1` | ‚úÖ Aktiv | Haupt-API |
| `8080` | Compliance API | HTTP | `127.0.0.1` | üîÑ Optional | Dashboard |
| `8080` | HugeGraph | HTTP | `127.0.0.1` | ‚ùå Deaktiviert | Enterprise Graph |
| `8529` | ArangoDB | HTTP | `127.0.0.1` | ‚ùå Deaktiviert | Graph Alternative |
| `32768` | ChromaDB Server | HTTP | `192.168.178.94` | ‚úÖ Aktiv | Vector Database |
| `32931` | CouchDB | HTTP | `192.168.178.94` | ‚úÖ Aktiv | Document Database |

---

## üîç **Problemdiagnose**

### **Port-Konflikte pr√ºfen**
```powershell
# Lokale Ports pr√ºfen
netstat -ano | findstr ":8001"    # Covina Backend
netstat -ano | findstr ":7687"    # Neo4j
netstat -ano | findstr ":6379"    # Redis

# Externe Server auf 192.168.178.94 testen
Test-NetConnection -ComputerName 192.168.178.94 -Port 32768  # ChromaDB
Test-NetConnection -ComputerName 192.168.178.94 -Port 5432   # PostgreSQL
Test-NetConnection -ComputerName 192.168.178.94 -Port 32931  # CouchDB
Test-NetConnection -ComputerName 192.168.178.94 -Port 25     # SMTP

# HTTP Services testen
curl -I "http://192.168.178.94:32768"     # ChromaDB
curl -I "http://192.168.178.94:32931"     # CouchDB

# Prozess zu Port finden
tasklist /FI "PID eq [PID]"
```

### **H√§ufige Probleme**

1. **Port 8001 ß±Ä   ò   0 P  ∑SPõp	>‹hê"l  $¨!D	(   ê
 ™ e 
Ë 2f8N +ó"°'L¡c£}ôû0#  Pxf  NNÙö~
'ˇˇ ˇÄ ˇ??ˇ????????ˇ????????ˇ????????ˇ???ˇˇˇˇˇˇˇˇˇˇˇˇˇ∞ˇ¸∞ˇ¸∞ˇ¸∞ˇ¸∞ˇ¸∞ˇ¸∞ˇ¸∞ˇ¸∞ˇ¸∞ˇ¸∞ˇ¸∞ˇ¸∞ˇ¸∞ˇ¸∞ˇ¸                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                