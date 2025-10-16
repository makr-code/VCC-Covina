# VERITAS DATA STATUS JSON CLEANER

## ÜBERSICHT

Der Data Status JSON Cleaner ist ein atomarer, sicherer Cleaner zum Löschen aller `success.json` und `failure.json` Dateien im `data`-Verzeichnis und allen Unterverzeichnissen.

## FUNKTIONEN

### ✅ **SICHERHEITSFEATURES**
- **Dry-Run-Modus** (Standard): Zeigt nur an, was gelöscht werden würde
- **Atomare Löschung**: Jede Datei wird einzeln und sicher gelöscht
- **Backup-Option**: Erstellt ZIP-Backup vor Löschung
- **Thread-Safe**: Parallele Verarbeitung ohne Race-Conditions
- **Detailliertes Logging**: Vollständige Nachverfolgung aller Operationen

### 🚀 **PERFORMANCE**
- **Rekursiver Scan**: Durchsucht alle Unterverzeichnisse
- **Parallele Löschung**: Bis zu 4 parallele Threads
- **Progress-Tracking**: Echtzeit-Status-Updates
- **Statistiken**: Detaillierte Erfolgs- und Fehlermetriken

### 📊 **REPORTING**
- Anzahl gescannte Verzeichnisse
- Gefundene success.json/failure.json Dateien
- Gelöschte Dateien und Fehler
- Freigegebener Speicherplatz
- Verarbeitungszeiten

## VERWENDUNG

### **Command Line**

#### Dry-Run (Empfohlen für ersten Lauf)
```bash
python data_status_json_cleaner.py
```

#### Nur Statistiken anzeigen
```bash
python data_status_json_cleaner.py --stats-only
```

#### Tatsächliche Löschung
```bash
python data_status_json_cleaner.py --execute
```

#### Löschung mit Backup
```bash
python data_status_json_cleaner.py --execute --backup
```

#### Erweiterte Optionen
```bash
# Custom Data-Verzeichnis
python data_status_json_cleaner.py --execute --data-dir "/custom/path/data"

# Mit Backup in custom Verzeichnis
python data_status_json_cleaner.py --execute --backup --backup-dir "/custom/backups"

# Mehr parallele Threads
python data_status_json_cleaner.py --execute --max-workers 8

# Verbose Logging
python data_status_json_cleaner.py --execute --backup --verbose
```

### **Windows Batch-Script**
```cmd
run_data_cleaner.bat
```

Das Batch-Script bietet ein interaktives Menü:
1. Dry Run (Voranzeige)
2. Nur Statistiken
3. Ausführung (mit Bestätigung)
4. Ausführung mit Backup
5. Custom Options
6. Exit

## SICHERHEITSMECHANISMEN

### **1. Dry-Run-Standard**
- Standard-Modus löscht KEINE Dateien
- Zeigt nur Voranzeige der Löschkandidaten
- Muss explizit mit `--execute` aktiviert werden

### **2. Bestätigungen**
```python
# Im Batch-Script
set /p confirm="Are you sure? Type 'DELETE' to confirm: "
if not "%confirm%"=="DELETE" (
    echo Cleanup cancelled.
)
```

### **3. Backup-System**
- ZIP-Backup mit Timestamp
- Erhält Original-Verzeichnisstruktur
- Backup-Verifikation vor Löschung

### **4. Atomare Operationen**
```python
def delete_file_atomic(self, file_path: Path) -> bool:
    try:
        if not file_path.exists():
            return True  # Bereits gelöscht
        
        file_path.unlink()  # Atomare Löschung
        return True
    except Exception as e:
        # Fehlerbehandlung ohne Datenverlust
        return False
```

### **5. Thread-Safety**
```python
# Thread-sichere Statistiken
with self.lock:
    self.stats['files_deleted'] += 1
```

## BEISPIEL-OUTPUT

### Dry-Run
```
🔍 Scanning directory: Y:\veritas\data
📂 Scanned 150 directories, found 23 target files
✅ Scan complete: 23 target files found in 0.45s

📁 FOUND FILES (23 total):
------------------------------------------------------------

✅ SUCCESS.JSON FILES (15):
  scraper_results/bw_results/success.json
  scraper_results/bayern_results/success.json
  downloads/completed/success.json
  ... and 12 more

❌ FAILURE.JSON FILES (8):
  scraper_results/failed_attempts/failure.json
  temp_downloads/errors/failure.json
  ... and 6 more

⚠️ DRY RUN: 23 files would be deleted

================================================================================
DATA STATUS JSON CLEANER - STATISTICS
================================================================================

📊 SCAN RESULTS:
  Directories scanned: 150
  Success files found: 15
  Failure files found: 8
  Total files found:   23
  Scan duration:       0.45s

💾 STORAGE:
  Space freed:         2.3 MB
```

### Erfolgreiche Löschung
```
🚀 Starting cleanup operation...
📦 Creating backup of 23 files...
✅ Backup created: ./backups/status_json_backup_20250902_143022.zip (2.3 MB)
🗑️ Deleting 23 files using 4 threads...
🗑️ Progress: 20/23 files processed
✅ Deletion complete: 23 deleted, 0 errors in 0.12s

📊 CLEANUP RESULTS:
  Files deleted:       23
  Deletion errors:     0
  Files backed up:     23
  Cleanup duration:    0.12s
  
✅ Cleanup completed successfully
```

## LOGGING

Automatisches Logging in Datei:
```
data_cleaner_20250902_143022.log
```

Enthält:
- Detaillierte Scan-Informationen
- Alle Löschoperationen
- Fehler und Warnungen
- Performance-Metriken
- Timestamp für jeden Schritt

## FEHLERBEHANDLUNG

### **Robuste Fehlerbehandlung**
- Einzelne Dateifehler stoppen nicht den gesamten Prozess
- Detaillierte Fehlerprotokollierung
- Weiterverarbeitung trotz einzelner Fehler
- Exit-Codes für Automatisierung

### **Häufige Szenarien**
- **Datei bereits gelöscht**: Wird als Erfolg gewertet
- **Keine Berechtigung**: Fehler wird protokolliert, andere Dateien weiter verarbeitet
- **Datei in Verwendung**: Fehler wird protokolliert, Retry-Mechanismus
- **Verzeichnis nicht gefunden**: Warnung, keine Fehlerbeendigung

## INTEGRATION

### **In VERITAS Pipeline**
```python
from data_status_json_cleaner import DataStatusJSONCleaner

# Periodische Bereinigung
cleaner = DataStatusJSONCleaner(data_dir="./data")
cleaner.run_cleanup(create_backup=True)
```

### **Automatisierung**
```bash
# Cron-Job (Linux/Mac)
0 2 * * 0 cd /path/to/veritas && python data_status_json_cleaner.py --execute

# Task Scheduler (Windows)
# Täglich um 02:00: data_status_json_cleaner.py --execute --backup
```

## SICHERHEITSHINWEISE

### ⚠️ **WICHTIGE WARNUNGEN**
1. **Immer erst Dry-Run**: Prüfen Sie die Ausgabe vor der Ausführung
2. **Backup empfohlen**: Verwenden Sie `--backup` bei kritischen Daten
3. **Berechtigungen prüfen**: Stellen Sie sicher, dass der Benutzer Schreibrechte hat
4. **Verzeichnis-Check**: Prüfen Sie den `--data-dir` Parameter

### ✅ **BEST PRACTICES**
1. **Erst testen**: Immer mit Dry-Run beginnen
2. **Backup erstellen**: Bei wichtigen Daten `--backup` verwenden
3. **Logging prüfen**: Log-Dateien auf Fehler kontrollieren
4. **Regelmäßig ausführen**: Automatisierte Bereinigung einrichten

---

*Der Data Status JSON Cleaner ist Teil des VERITAS-Systems und folgt allen Sicherheits- und Qualitätsstandards.*
