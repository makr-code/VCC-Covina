# UDS3 Package Installation & Import-Fix

## Problem

Namespace-Konflikt zwischen Covina `database/` und UDS3 `database/` Packages.

## Lösung: UDS3 als Python Package installieren

### Schritt 1: UDS3 Package installieren ✅

```powershell
& "C:/Program Files/Python313/python.exe" -m pip install -e C:\VCC\uds3
```

**Ergebnis:**
```
Successfully installed uds3-1.0.0
```

### Schritt 2: sitecustomize.py aktualisieren ✅

**Datei:** `c:\VCC\Covina\sitecustomize.py`

**Änderung:**
```python
UDS3_ROOT = VCC_ROOT / "uds3"  # C:\VCC\uds3

EXTRA_PATHS = [
    PROJECT_ROOT,        # C:\VCC\Covina (für Covina-Module)
    VCC_ROOT,           # C:\VCC (für "import uds3")
    UDS3_ROOT,          # C:\VCC\uds3 (für "from database import")  ← NEU!
]
```

**Zweck:** Ermöglicht `from database.xxx import` Imports, die auf UDS3 verweisen.

### Schritt 3: Imports zurück auf Standard-Form ✅

Alle vorherigen `from uds3.database.xxx` Imports wurden zurück auf `from database.xxx` geändert:

**Geänderte Dateien:**
1. `management_core/vector_management.py`
2. `management_core/graph_management.py`
3. `management_core/relational_management.py`
4. `management_core/filesystem_management.py`
5. `tests/test_vector_management_service.py`
6. `tests/test_saga_crud.py`

**Beispiel:**
```python
# JETZT (Standard-Form):
from database.database_api_base import VectorDatabaseBackend

# NICHT MEHR (explizit):
from uds3.database.database_api_base import VectorDatabaseBackend
```

## Warum das funktioniert

1. **UDS3 ist installiert:** `pip install -e` macht es zu einem echten Python Package
2. **sys.path ist erweitert:** `C:\VCC\uds3` ist im PYTHONPATH
3. **sitecustomize.py lädt automatisch:** Bei jedem Python-Start in Covina
4. **Import-Resolution:**
   - `from database.xxx` → findet ZUERST Covina `database/` (leer außer PostgreSQL Adapter)
   - Wenn Modul fehlt → sucht in `C:\VCC\uds3\database\` (UDS3)
   - **Problem:** Python **stoppt** bei Package-Ebene, sucht nicht weiter!

## AKTUELLES PROBLEM ⚠️

**Import schlägt immer noch fehl:**
```
ModuleNotFoundError: No module named 'database.database_api_base'
```

**Root Cause:** Covina hat ein `database/` Package (mit PostgreSQL Adapter). Python findet das Package, stoppt die Suche, findet aber kein `database_api_base.py` Modul darin.

## FINALE LÖSUNG: Covina database/ Package umbenennen

Um den Konflikt zu vermeiden, müssen wir das Covina `database/` Package umbenennen:

```powershell
Rename-Item -Path "C:\VCC\Covina\database" -NewName "covina_database"
```

**Dann alle Covina-Imports aktualisieren:**
```python
# VORHER:
from database.database_api_postgresql import PostgreSQLRelationalBackend
from database.saga_crud import SagaDatabaseCRUD
from database.adapter_governance import AdapterGovernance

# NACHHER:
from covina_database.database_api_postgresql import PostgreSQLRelationalBackend
from covina_database.saga_crud import SagaDatabaseCRUD
from covina_database.adapter_governance import AdapterGovernance
```

**Betroffene Dateien:** ~15 Dateien (siehe grep-Suche oben)

## Status

✅ UDS3 Package installiert
✅ sitecustomize.py aktualisiert  
✅ Imports auf Standard-Form zurückgesetzt
⏸️ **Warte auf User-Bestätigung** für Package-Umbenennung

## Datum

11. Oktober 2025
