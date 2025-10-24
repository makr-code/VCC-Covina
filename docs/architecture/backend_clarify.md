# Covina Backend - KORRIGIERTE Analyse
**Datum:** 17. Oktober 2025, 19:00 Uhr  
**Status:** 🚨 KRITISCHE ERKENNTNIS - 3 Backend-Dateien gefunden!

---

## 🔍 Aktuelle Backend-Dateien

| Datei | Größe | Zeilen | Standard-Port | Rolle |
|-------|-------|--------|---------------|-------|
| `backend.py` | 400 KB | 9,181 | 45678 | **MONOLITH** (Upload + Query + ALLES!) |
| `ingestion_backend.py` | 129 KB | 3,182 | 45679 | **Ingestion Microservice** (Separat) |
| `covina_backend.py` | 66 KB | 1,735 | 45678 | **Main Backend** (Query, DSGVO, Review, Golden Datasets) |

---

## 🎯 Was ist was?

### 1. `backend.py` (MONOLITH)
**Größe:** 400 KB (9,181 Zeilen)  
**Port:** 45678 (default)  
**Rolle:** **VOLLSTÄNDIGES SYSTEM (Monolith)**

**Features:**
- ✅ File Upload (/upload/files)
- ✅ UDS3 Integration (4 Databases)
- ✅ Worker Pools (36 I/O, 36 CPU)
- ✅ Job Management
- ✅ WebSocket (/ws/jobs)
- ✅ SAGA Orchestrator
- ✅ Process Mining
- ✅ DSGVO
- ✅ Review Queue
- ✅ Compliance
- ✅ **ALLES!**

**Erkenntnis:** Dies ist das **ORIGINAL MONOLITH-Backend** mit ALLEN Features!

---

### 2. `ingestion_backend.py` (MICROSERVICE)
**Größe:** 129 KB (3,182 Zeilen)  
**Port:** 45679  
**Rolle:** **Ingestion Microservice** (Separierter Service)

**Features:**
- ✅ File Upload (spezialisiert)
- ✅ UDS3 Integration
- ✅ Worker Pools
- ✅ Job Management
- ✅ WebSocket
- ✅ SAGA Orchestrator

**Erkenntnis:** Dies ist eine **SEPARIERTE VERSION** nur für Ingestion (Microservice-Architektur).

---

### 3. `covina_backend.py` (MAIN BACKEND)
**Größe:** 66 KB (1,735 Zeilen)  
**Port:** 45678  
**Rolle:** **Main Backend** (Query & Management)

**Features:**
- ✅ Query APIs (Full-Text, Semantic)
- ✅ DSGVO
- ✅ Review Queue
- ✅ Gap Detection
- ✅ Compliance
- ✅ Golden Datasets
- ✅ Graph Patterns
- ✅ Governance Policies
- ❌ KEIN Upload
- ❌ KEINE Worker Pools

**Erkenntnis:** Dies ist das **NEUE MAIN BACKEND** ohne Upload (für Microservice-Architektur).

---

## 🏗️ Architektur-Strategien

### Strategie 1: MONOLITH (Aktuell in Produktion?)
```
backend.py (Port 45678)
└─ ALLES (Upload + Query + Management)
```

**Vorteile:**
- ✅ Einfach zu starten (1 Prozess)
- ✅ Keine Inter-Service-Kommunikation

**Nachteile:**
- ❌ 400 KB Code (schwer wartbar)
- ❌ Ein Fehler killt alles
- ❌ Schwer skalierbar

---

### Strategie 2: MICROSERVICES (Geplant?)
```
covina_backend.py (Port 45678 - Main Backend)
└─ Query, DSGVO, Review, Golden Datasets, Governance

ingestion_backend.py (Port 45679 - Ingestion Microservice)
└─ Upload, Processing, Worker Pools, UDS3, WebSocket
```

**Vorteile:**
- ✅ Separation of Concerns
- ✅ Getrennte Skalierung
- ✅ Kleinere Codebase pro Service

**Nachteile:**
- ❌ 2 Prozesse zu managen
- ❌ Inter-Service-Kommunikation

---

## 🔧 Empfohlene Umbenennung (KORRIGIERT)

### Option A: Monolith beibehalten
```
backend.py              → main_backend_monolith.py (oder einfach: main_backend.py)
ingestion_backend.py    → (bleibt, wird nicht genutzt)
covina_backend.py       → (archivieren oder löschen)
```

### Option B: Microservices aktivieren
```
backend.py              → (archivieren als backup_backend_monolith.py)
ingestion_backend.py    → (bleibt, Port 45679) ✅
covina_backend.py       → main_backend.py (Port 45678) ✅
```

### Option C: Klare Trennung mit Suffixes
```
backend.py              → backend_monolith.py
ingestion_backend.py    → backend_ingestion.py
covina_backend.py       → backend_main.py
```

---

## 🎯 Welche Architektur wird AKTUELL genutzt?

**Frage:** Welches Backend läuft in Produktion?

**Check in Scripts:**
```powershell
# scripts/start_services.ps1 prüfen
Get-Content scripts\start_services.ps1 | Select-String "python.*backend"
```

**Vermutung:**
- **Monolith** (`backend.py`) wird genutzt
- **Microservices** (`covina_backend.py` + `ingestion_backend.py`) sind vorbereitet aber inaktiv

---

## 📊 Empfehlung

**SCHRITT 1:** Klären welche Architektur aktiv ist

```powershell
# Welches Backend wird gestartet?
Get-Content scripts\start_services.ps1 | Select-String "ArgumentList"
```

**SCHRITT 2:** Basierend auf Antwort:

**Falls MONOLITH aktiv:**
- `backend.py` → `main_backend.py` (keep it simple)
- `ingestion_backend.py` → (löschen oder archivieren)
- `covina_backend.py` → (löschen oder archivieren)

**Falls MICROSERVICES aktiv:**
- `backend.py` → `backend_monolith_backup.py` (archivieren)
- `ingestion_backend.py` → (bleibt)
- `covina_backend.py` → `main_backend.py`

---

## 🔍 Nächster Schritt

**Bitte entscheiden:**

1. **Welche Architektur nutzen wir?**
   - [ ] Monolith (backend.py)
   - [ ] Microservices (covina_backend.py + ingestion_backend.py)

2. **Umbenennen zu:**
   - [ ] Option A (Monolith beibehalten)
   - [ ] Option B (Microservices aktivieren)
   - [ ] Option C (Klare Suffixes)

Ich warte auf Ihre Entscheidung! 🤔
