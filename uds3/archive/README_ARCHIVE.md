# UDS3 Archivierte Dateien

**Datum der Archivierung:** 1. Oktober 2025  
**Optimierung:** -2,820 LOC, -127.7 KB (Phase 2: Todo #7, #4, #10)

## Schema-Dateien (Todo #7):

### 1. `uds3_schemas.py` (39.6 KB, 1,009 LOC)
- **Grund:** Nicht verwendet (keine aktiven Imports)
- **Alternative:** `uds3_database_schemas.py` (aktuell in Verwendung)

### 2. `uds3_enhanced_schema.py` (20.1 KB, 379 LOC)
- **Grund:** Nicht verwendet (keine aktiven Imports)
- **Notiz:** Potenziell nützlich für zukünftige Enhanced Metadata Integration

### 3. `uds3_vpb_schema.py` (16.3 KB, 343 LOC)
- **Grund:** Nicht verwendet (keine aktiven Imports)
- **Notiz:** Relevant für VPB-Integration, falls in Zukunft benötigt

**Subtotal:** -76 KB, -1,731 LOC

## Geo-Module (Todo #4):

### 4. `uds3_core_geo.py` (33.1 KB, 694 LOC)
- **Grund:** Konsolidierung, keine aktiven Imports (außer Dokumentation)
- **Features:** Geo-Extraktion, Räumliche Suche, Administrative Hierarchie
- **Notiz:** Verbleibende Geo-Module (`uds3_geo_extension.py`, `uds3_4d_geo_extension.py`) benötigen Wartung

**Subtotal:** -33.1 KB, -694 LOC

## API Backend (Todo #10):

### 5. `uds3_api_backend.py` (18.6 KB, 395 LOC)
- **Grund:** Minimal genutzt (nur in 1 Test), externe Dependency (Ollama LLM)
- **Features:** 
  - Semantische Prozessanalyse mit Ollama
  - Rechtliche Compliance-Prüfung
  - VPB Process Designer Integration
  - UDS3 Knowledge Base
- **Notiz:** Bei Bedarf reaktivierbar (benötigt Ollama Installation)

**Subtotal:** -18.6 KB, -395 LOC

---

**GESAMT ARCHIVIERT:** -127.7 KB, -2,820 LOC

## Wiederherstellung:

Falls eine der archivierten Dateien benötigt wird:

```powershell
# Beispiel: uds3_schemas.py wiederherstellen
Move-Item -Path "archive\uds3_schemas.py" -Destination ".\" -Force
```

## Optimierungs-Kontext:

Diese Archivierung ist Teil der **Phase 2: Code-Optimierung** des UDS3-Projekts:
- **Phase 1:** -113 KB, -2,556 LOC (Security/Quality/Saga/Relations)
- **Todo #6b:** -350 LOC (Schema Definitions → uds3_database_schemas.py)
- **Todo #6c:** -200 LOC (CRUD Strategies → uds3_crud_strategies.py)
- **Todo #7:** -1,731 LOC (Schema-Archivierung) ← **DIESER SCHRITT**

## Referenzen:

- **Aktive Schema-Datei:** `uds3_database_schemas.py` (384 LOC, in Verwendung)
- **CRUD Strategies:** `uds3_crud_strategies.py` (216 LOC, in Verwendung)
- **Dokumentation:** `docs/UDS3_OPTIMIZATION_PLAN.md`

## Backup-Sicherheit:

✅ Alle archivierten Dateien sind:
- Im Git-Repository versioniert
- Im Archiv-Verzeichnis gesichert
- Jederzeit wiederherstellbar
- Vollständig dokumentiert

---
**Autor:** UDS3 Optimization Team  
**Version:** Phase 2 - Todo #7
