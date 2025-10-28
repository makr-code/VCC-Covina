# Ingestion GUI - Quick Start Guide

## 🚀 Schnellstart

### 1. Backend starten
```powershell
cd C:\VCC\Covina
.\scripts\start_services.ps1
```

**Warten auf:**
```
✅ Backend: Online (Main Backend: 45678, Ingestion Backend: 45679)
```

### 2. GUI starten
```powershell
python tools\ingestion_gui.py
```

### 3. Dateien hochladen

#### Option A: Einzelne Dateien
1. Klick auf **"📁 Select Files"**
2. Dateien auswählen (Ctrl+Click für mehrere)
3. Klick auf **"🚀 Start Upload"**

#### Option B: Ganzer Ordner
1. Klick auf **"📂 Select Folder"**
2. Ordner auswählen
3. **Overlay erscheint:**
   - Echtzeit-Counter: "Files found: X"
   - Aktueller Ordner sichtbar
   - ❌ Cancel bei Bedarf
4. Warten auf Scan-Complete
5. Klick auf **"🚀 Start Upload"**

#### Option C: Drag & Drop
1. Dateien/Ordner ins GUI ziehen
2. **Bei Ordnern:** Overlay mit Echtzeit-Scan
3. Klick auf **"🚀 Start Upload"**

---

## 📊 UI-Elemente erklärt

### Backend-Status (unten links)
```
✅ Backend: Online     → Alles OK
⚠️ Backend: Unhealthy → Backend läuft, aber Probleme
❌ Backend: Offline    → Backend nicht erreichbar
⚪ Backend: Checking... → Initializing
```

### File Count Label
```
"42 files selected (12.5 MB)"
```
- Zeigt Anzahl + Gesamtgröße
- Aktualisiert sich automatisch

### Progress Bar
- **Leer:** Bereit zum Upload
- **Grün:** Upload läuft (0-100%)
- **100%:** Verarbeitung abgeschlossen

### Progress Label
```
"Ready to upload"           → Bereit
"Uploading 42 files..."     → Upload läuft
"Processing: 10/42 (24%)"   → Verarbeitung läuft
"Upload complete!"          → Fertig
```

### Status Label (blau/grün/rot)
```
"Upload successful! Job ID: abc123"  → Erfolg (grün)
"Processing files..."                → Info (blau)
"Upload failed: 500 - Error"         → Fehler (rot)
```

---

## 🎯 Folder Scan Overlay (NEU!)

### Was passiert beim Ordner-Scan?

1. **Overlay-Fenster öffnet sich**
2. **Live-Updates:**
   - "Scanning: C:\Documents\ProjectX..."
   - "(143 folders scanned)"
   - "Files found: 856" ← Wächst in Echtzeit!
3. **Progressbar:** Animierte Anzeige
4. **Cancel-Button:** Scan abbrechen möglich
5. **Fertig:** MessageBox mit Zusammenfassung

### Beispiel-Ablauf (großer Ordner)
```
[0s]   Overlay erscheint
[0s]   Files found: 0
[1s]   Files found: 42
[2s]   Scanning: Subfolder1... (15 folders scanned)
[3s]   Files found: 127
[5s]   Scanning: Subfolder2... (43 folders scanned)
[7s]   Files found: 234
...
[30s]  Files found: 856
[30s]  Scan complete! MessageBox
[31s]  Overlay schließt
```

### Cancel während Scan
```
1. ❌ Cancel klicken
2. Label: "Cancelling scan..."
3. MessageBox: "Scan cancelled. Found 234 files before cancellation."
4. Bereits gefundene Dateien bleiben in Liste!
```

---

## 🔧 Fehlerbehebung

### Problem: "Backend: Offline"
**Lösung:**
```powershell
# Backend prüfen
curl http://127.0.0.1:45679/health

# Backend neu starten
.\scripts\stop_services.ps1
.\scripts\start_services.ps1
```

### Problem: Upload schlägt fehl
**Mögliche Ursachen:**
1. **Backend nicht erreichbar** → Backend-Status prüfen
2. **Timeout (große Dateien)** → Timeout erhöhen (aktuell: 5 Min)
3. **Keine Berechtigung** → Als Admin starten

**Debug:**
```python
# Log-Datei prüfen
Get-Content logs\ingestion_backend.log -Tail 50
Get-Content logs\ingestion_backend_error.log
```

### Problem: Scan dauert ewig
**Workaround:**
1. **❌ Cancel klicken**
2. **Kleinere Ordner** auswählen
3. **Oder:** Dateien direkt auswählen (📁 Select Files)

### Problem: GUI friert ein
**Ursache:** Wahrscheinlich Netzwerk-Share mit langsamer Verbindung

**Workaround:**
1. **Ordner lokal kopieren**
2. **Scan abbrechen** und neu starten
3. **Task Manager:** Python-Prozess beenden

---

## 📁 Unterstützte Dateitypen

```
✅ PDF:   .pdf
✅ Text:  .txt, .md, .rtf
✅ Word:  .docx, .doc
✅ Excel: .xlsx, .xls
✅ Data:  .csv, .json, .xml
✅ Web:   .html
```

**Hinweis:** Andere Dateitypen werden automatisch gefiltert (ignoriert)

---

## 🎯 Best Practices

### 1. Große Uploads (1000+ Dateien)
```
✅ Ordner-Scan nutzen (automatisch)
✅ Geduld: Scan kann 1-2 Minuten dauern
✅ Cancel-Option bei Bedarf
❌ Nicht: Einzeln auswählen (zu langsam)
```

### 2. Kleine Uploads (< 50 Dateien)
```
✅ Select Files nutzen (schneller)
✅ Ctrl+Click für mehrere Dateien
✅ Drag & Drop (bequem)
```

### 3. Netzwerk-Shares
```
⚠️  Langsame Scans möglich
✅ Lokal kopieren (schneller)
✅ Cancel-Option nutzen
```

### 4. Monitoring
```
✅ Progress Label beobachten
✅ Status Label für Fehler prüfen
✅ Job ID notieren (für Support)
```

---

## 🔄 Workflow-Beispiele

### Beispiel 1: Projekt-Dokumentation hochladen
```
1. Backend-Status: ✅ Online prüfen
2. "📂 Select Folder" klicken
3. C:\Projects\Documentation auswählen
4. Overlay: "Files found: 42" (2 Sekunden)
5. Scan complete: "Found 42 files in 8 folders"
6. Liste prüfen (alle 42 Dateien sichtbar)
7. "🚀 Start Upload" klicken
8. Progress: "Uploading 42 files..."
9. WebSocket: "Processing: 10/42 (24%)"
10. Status: "✅ Job completed! All 42 files processed."
11. MessageBox: "Successfully processed 42 files!"
```

### Beispiel 2: Einzelne Verträge hochladen
```
1. "📁 Select Files" klicken
2. Verträge auswählen (Ctrl+Click):
   - Vertrag_2024_001.pdf
   - Vertrag_2024_002.pdf
   - Vertrag_2024_003.pdf
3. "3 files selected (2.4 MB)" angezeigt
4. "🚀 Start Upload" klicken
5. Progress: "Processing: 3/3 (100%)"
6. Fertig in 5-10 Sekunden
```

### Beispiel 3: Großer Ordner mit Cancel
```
1. "📂 Select Folder" klicken
2. C:\Archive (10,000+ Dateien)
3. Overlay erscheint
4. Nach 30 Sekunden: "Files found: 2,341"
5. ❌ Cancel klicken (genug für Test)
6. "Scan cancelled. Found 2,341 files..."
7. Liste zeigt 2,341 Dateien
8. Upload wie gewohnt
```

---

## 📊 Performance-Erwartungen

### Scan-Zeiten (typisch)
| Dateien | Ordner | Zeit        |
|---------|--------|-------------|
| 100     | 10     | < 1 Sekunde |
| 1,000   | 50     | 2-5 Sekunden|
| 5,000   | 200    | 10-30 Sek   |
| 10,000  | 500    | 30-60 Sek   |

### Upload-Zeiten (typisch)
| Dateien | Größe | Upload | Verarbeitung | Total     |
|---------|-------|--------|--------------|-----------|
| 10      | 5 MB  | 2s     | 10-30s       | 12-32s    |
| 100     | 50 MB | 10s    | 1-3 Min      | 1-3.5 Min |
| 1,000   | 500MB | 60s    | 10-30 Min    | 11-31 Min |

**Hinweis:** Verarbeitung hängt von Backend-Workern ab (aktuell: 36 I/O + 8 CPU)

---

## 🆘 Support

### Logs prüfen
```powershell
# GUI-Output (falls gestartet via Terminal)
# Siehe Konsole

# Backend-Logs
Get-Content logs\ingestion_backend.log -Tail 100
Get-Content logs\ingestion_backend_error.log
```

### Häufige Fehler
```
"No module named 'tkinterdnd2'" 
→ Drag & Drop deaktiviert (funktioniert trotzdem)

"Backend: Offline"
→ Backend starten: .\scripts\start_services.ps1

"Upload failed: 413 Request Entity Too Large"
→ Datei zu groß (aktuelles Limit prüfen)
```

### Job-Status prüfen (manuell)
```powershell
# Job-Liste abrufen
Invoke-RestMethod http://127.0.0.1:45679/jobs

# Spezifischer Job
Invoke-RestMethod http://127.0.0.1:45679/jobs/abc123
```

---

**Letzte Aktualisierung:** 28. Oktober 2025  
**Version:** 1.1.0  
**Support:** Siehe Logs + Backend-Dokumentation
