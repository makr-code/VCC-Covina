# UDS3 Migration - Betroffene Dateien

**Generiert**: 6. Oktober 2025  
**Analyse-Basis**: grep_search für "from uds3|import uds3"

---

## 📊 Zusammenfassung

| Kategorie | Anzahl | Priorität | Änderungsbedarf |
|-----------|--------|-----------|-----------------|
| **Haupt-Adapter** | 1 | 🔴 KRITISCH | ✅ Keine (funktioniert automatisch) |
| **UDS3-Intern** | ~100+ | 🟡 INTERN | ✅ Keine (mit PYTHONPATH) |
| **Tests** | ~15 | 🟢 NIEDRIG | ⚠️ Zu prüfen |
| **Dokumentation** | ~5 | 🟢 NIEDRIG | 📝 Update nötig |

---

## 🔴 KRITISCH - Haupt-Adapter

### `C:\VCC\Covina\uds3_adapter.py`

**Zeile 24**:
```python
from uds3 import create_secure_document_light  # type: ignore
```
✅ **KEINE ÄNDERUNG NÖTIG** - Package-Import funktioniert automatisch

**Zeile 35**:
```python
from uds3.database.adapter_governance import (
    AdapterGovernance, GovernanceLevel, GovernanceMetric
)
```
✅ **KEINE ÄNDERUNG NÖTIG** - Absoluter Modul-Import funktioniert

**Zeile 384**:
```python
from uds3.uds3_security_quality import create_security_manager
```
✅ **KEINE ÄNDERUNG NÖTIG** - Absoluter Modul-Import funktioniert

**STATUS**: ✅ **READY** - Keine Änderungen erforderlich

---

## 🟡 UDS3-INTERN - Dateien innerhalb uds3/

Diese Dateien bleiben innerhalb des uds3-Packages und nutzen relative Imports:

### Häufige Import-Muster:

```python
# Pattern 1: Intra-Package Imports (AKTUELL)
from uds3_core import UnifiedDatabaseStrategy
from uds3_admin_types import AdminDocumentType
from uds3_security_quality import create_security_manager

# Pattern 2: Relative Imports (OPTIONAL - falls PYTHONPATH nicht gesetzt)
from .uds3_core import UnifiedDatabaseStrategy
from .uds3_admin_types import AdminDocumentType
from .uds3_security_quality import create_security_manager
```

### Betroffene Dateien (Auswahl):

| Datei | Imports | Strategie |
|-------|---------|-----------|
| `uds3_core.py` | 30+ imports | PYTHONPATH |
| `uds3_multi_db_distributor.py` | 10+ imports | PYTHONPATH |
| `uds3_saga_step_builders.py` | 5+ imports | PYTHONPATH |
| `uds3_document_classifier.py` | 5+ imports | PYTHONPATH |
| `uds3_polyglot_query.py` | 10+ imports | PYTHONPATH |
| `uds3_streaming_saga_integration.py` | 5+ imports | PYTHONPATH |
| ... | ... | PYTHONPATH |

**GESAMT**: ~100+ Python-Dateien

**STRATEGIE**: 
- ✅ **EMPFOHLEN**: PYTHONPATH auf `C:\VCC\uds3` setzen
- ⚠️ **ALTERNATIV**: Alle Imports zu relativen Imports umschreiben (100+ Dateien)

**STATUS**: ✅ **READY** - Keine Änderungen nötig mit PYTHONPATH

---

## 🟢 TESTS - Zu Prüfen

### Test-Dateien mit uds3-Imports:

#### `C:\VCC\Covina\test_uds3_dsgvo_database_api.py`
**MÖGLICHERWEISE** Import von:
```python
from uds3.uds3_dsgvo_core import UDS3DSGVOCore, PIIType, DSGVOProcessingBasis
```
⚠️ **ZU PRÜFEN** - Könnte Update benötigen

#### `C:\VCC\Covina\uds3\test_dsgvo_minimal.py`
**Zeile 9**:
```python
from uds3_dsgvo_core import UDS3DSGVOCore, PIIType, DSGVOProcessingBasis
```
⚠️ **ZU PRÜFEN** - Innerhalb uds3/, könnte relativen Import benötigen

#### `C:\VCC\Covina\uds3\test_naming_quick.py`
**Zeilen 14, 17**:
```python
from uds3_admin_types import AdminDocumentType, AdminLevel, AdminDomain
from uds3_naming_strategy import create_municipal_strategy, create_state_strategy
```
⚠️ **ZU PRÜFEN** - Innerhalb uds3/, PYTHONPATH-Strategie

#### Weitere Test-Dateien:
```
C:\VCC\Covina\tests\**\*.py
```
⚠️ **ZU ANALYSIEREN** - Vollständiger Scan erforderlich

**AKTION**: 
```powershell
# Finde alle Test-Dateien mit uds3-Imports
cd C:\VCC\Covina
Get-ChildItem -Path tests\ -Recurse -Include *.py | Select-String "from uds3|import uds3"
```

---

## 🟢 DOKUMENTATION - Update Erforderlich

### Markdown-Dateien mit uds3-Referenzen:

| Datei | Zeilen | Änderung |
|-------|--------|----------|
| `uds3\TODO15_FINAL_INTEGRATION_COMPLETE.md` | 310, 365, 372 | 📝 Beispiel-Code aktualisieren |
| `uds3\TODO14_COMPLETE_SUMMARY.md` | 233 | 📝 Import-Beispiel aktualisieren |
| `uds3\SESSION_COMPLETE_TODO9.md` | 341, 386 | 📝 Beispiel-Code aktualisieren |

**AKTION**: Beispiel-Code in Dokumentation aktualisieren:
```python
# ALT (in Docs):
from uds3_core import UnifiedDatabaseStrategy

# NEU (für externe Nutzung):
from uds3.uds3_core import UnifiedDatabaseStrategy
# ODER (Package-Import wenn in __init__.py exportiert):
from uds3 import UnifiedDatabaseStrategy
```

---

## 📋 Management Core - Zu Analysieren

**NOCH NICHT GEFUNDEN in grep_search**, aber sollten geprüft werden:

```powershell
# Manuelle Prüfung erforderlich:
cd C:\VCC\Covina\management_core
Select-String -Path *.py -Pattern "from uds3|import uds3"
```

### Vermutlich betroffene Dateien:
- `relational_management.py` - Könnte uds3_core nutzen
- `vector_management.py` - Könnte uds3-Vector-Module nutzen
- `graph_management.py` - Könnte uds3-Graph-Module nutzen
- `filesystem_management.py` - Könnte uds3-File-Storage nutzen

**STATUS**: ⚠️ **MANUELLE ANALYSE ERFORDERLICH**

---

## 📋 Ingestion - Zu Analysieren

**NOCH NICHT GEFUNDEN in grep_search**, aber sollten geprüft werden:

```powershell
cd C:\VCC\Covina\ingestion
Select-String -Path *.py -Pattern "from uds3|import uds3" -Recurse
```

### Vermutlich betroffene Dateien:
- `persistence.py` - Könnte uds3 für Speicherung nutzen
- `graph_persistence.py` - Könnte uds3-Graph nutzen

**STATUS**: ⚠️ **MANUELLE ANALYSE ERFORDERLICH**

---

## 🔧 Tools & Scripts für Migration

### 1. Vollständige Import-Analyse
```powershell
# Speichern als: analyze_uds3_imports.ps1
cd C:\VCC\Covina

Write-Host "🔍 Analysiere uds3-Imports..." -ForegroundColor Cyan

# Finde alle .py Dateien mit uds3-Imports
$results = Get-ChildItem -Recurse -Include *.py | 
    Select-String -Pattern "from uds3|import uds3" | 
    Select-Object Path, LineNumber, Line

# Gruppiere nach Datei
$grouped = $results | Group-Object Path | 
    Select-Object @{Name='Datei';Expression={$_.Name}}, 
                  @{Name='Anzahl';Expression={$_.Count}}

# Ausgabe
Write-Host "`nBetroffene Dateien: $($grouped.Count)" -ForegroundColor Yellow
$grouped | Format-Table -AutoSize

# Speichere Details
$results | Format-Table Path, LineNumber, Line -AutoSize | 
    Out-File -FilePath "uds3_imports_detailed.txt"

Write-Host "`n✅ Details gespeichert in: uds3_imports_detailed.txt" -ForegroundColor Green
```

### 2. Quick-Verifikation nach Migration
```powershell
# Speichern als: verify_uds3_migration.ps1
Write-Host "🧪 Verifiziere UDS3 Migration..." -ForegroundColor Cyan

# Test 1: Package verfügbar
Write-Host "`nTest 1: Package Import..." -NoNewline
$result = python -c "import uds3; print(uds3.__file__)" 2>&1
if ($LASTEXITCODE -eq 0) {
    Write-Host " ✅" -ForegroundColor Green
    Write-Host "  Location: $result"
} else {
    Write-Host " ❌" -ForegroundColor Red
    Write-Host "  Error: $result"
    exit 1
}

# Test 2: Core Import
Write-Host "Test 2: Core Import..." -NoNewline
$result = python -c "from uds3 import UnifiedDatabaseStrategy; print('OK')" 2>&1
if ($LASTEXITCODE -eq 0) {
    Write-Host " ✅" -ForegroundColor Green
} else {
    Write-Host " ❌" -ForegroundColor Red
    Write-Host "  Error: $result"
    exit 1
}

# Test 3: Adapter
Write-Host "Test 3: Adapter Import..." -NoNewline
$result = python -c "from uds3 import create_secure_document_light; print('OK')" 2>&1
if ($LASTEXITCODE -eq 0) {
    Write-Host " ✅" -ForegroundColor Green
} else {
    Write-Host " ❌" -ForegroundColor Red
    Write-Host "  Error: $result"
    exit 1
}

Write-Host "`n✅ Migration erfolgreich verifiziert!" -ForegroundColor Green
```

---

## 📝 Nächste Schritte

1. **Jetzt**: Vollständige Import-Analyse durchführen
   ```powershell
   PowerShell.exe -ExecutionPolicy Bypass -File analyze_uds3_imports.ps1
   ```

2. **Danach**: Management Core manuell prüfen
   ```powershell
   cd C:\VCC\Covina\management_core
   Select-String -Path *.py -Pattern "from uds3|import uds3"
   ```

3. **Dann**: Ingestion manuell prüfen
   ```powershell
   cd C:\VCC\Covina\ingestion
   Select-String -Path *.py -Pattern "from uds3|import uds3" -Recurse
   ```

4. **Schließlich**: Migration gemäß `UDS3_MIGRATION_PLAN.md` durchführen

---

**STATUS**: 📋 ANALYSE BEREIT  
**Konfidenz**: 🟢 HOCH - Hauptadapter benötigt KEINE Änderungen  
**Empfehlung**: PYTHONPATH-Strategie für minimale Code-Änderungen
