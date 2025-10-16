# Microservices Startup Script Improvements

**Datum:** 13. Oktober 2025  
**Version:** 2.0  
**Status:** ✅ PRODUCTION READY

---

## Übersicht

Die Startup-Scripts für die Covina Microservices wurden verbessert, um robustere Health-Checks und bessere Fehlerbehandlung zu bieten.

---

## Änderungen

### 1. Start Script (`scripts/start_services.ps1`)

#### **Problem:**
- Ingestion Backend brauchte länger zum Starten als erwartet
- Health-Check nach nur 3s schlug fehl
- Keine Retry-Logik bei temporären Verbindungsproblemen

#### **Lösung:**

**A) Erhöhte Initialisierungszeit:**
```powershell
# BEFORE:
Start-Sleep -Seconds 3

# AFTER:
Write-Host "  Waiting for backends to initialize (10s)..." -ForegroundColor Gray
Start-Sleep -Seconds 10
```

**Reason:** Ingestion Backend lädt:
- UDS3 SAGA Orchestrator (Database Backend)
- Sentence Transformers Model (384-dim embeddings)
- spaCy Model (de_core_news_sm)
- Whisper Model (base)
- 36 I/O Workers + 36 CPU Workers

**⏱️ Startup Time:** ~8-12 Sekunden

---

**B) Retry-Logik für Health-Checks:**

```powershell
function Test-BackendHealth {
    param(
        [string]$Name,
        [string]$Url,
        [int]$MaxRetries = 5,
        [int]$RetryDelay = 2
    )
    
    for ($i = 1; $i -le $MaxRetries; $i++) {
        try {
            $health = Invoke-RestMethod -Uri $Url -TimeoutSec 3 -ErrorAction Stop
            if ($health.status -eq "healthy") {
                Write-Host "  OK  $Name: healthy" -ForegroundColor Green
                return $health
            }
        } catch {
            if ($i -lt $MaxRetries) {
                Write-Host "  RETRY $Name: attempt $i/$MaxRetries..." -ForegroundColor Gray
                Start-Sleep -Seconds $RetryDelay
            }
        }
    }
    
    Write-Host "  FAIL $Name: not responding after $MaxRetries retries" -ForegroundColor Red
    return $null
}
```

**Features:**
- ✅ 5 Retry-Versuche mit 2s Delay
- ✅ Timeout pro Request: 3s
- ✅ Total Timeout: bis zu 15s (5 × 3s)
- ✅ Graceful Degradation: Script läuft weiter, auch wenn ein Backend fehlschlägt

---

**C) Erweiterte Ausgabe:**

```powershell
# BEFORE (Output):
OK  Main Backend: healthy
FAIL Ingestion Backend: not responding

# AFTER (Output):
OK  Main Backend: healthy
OK  Ingestion Backend: healthy
    Workers: 36 I/O, 36 CPU

Process IDs:
  Main Backend PID:      24056
  Ingestion Backend PID: 17880

Logs:
  Main:      logs\main_backend.log
  Ingestion: logs\ingestion_backend.log

Stop with: .\scripts\stop_services.ps1
```

**Benefits:**
- ✅ Klare Status-Anzeige
- ✅ Worker-Count sichtbar
- ✅ Process IDs für Debugging
- ✅ Log-Pfade dokumentiert
- ✅ Stop-Command bereitgestellt

---

### 2. Stop Script (`scripts/stop_services.ps1`)

#### **Problem:**
- Verwendete `CommandLine` Property (nicht auf allen Windows-Versionen verfügbar)
- Unreliable Process Detection

#### **Lösung:**

**Port-basierte Process Detection:**

```powershell
# BEFORE:
$mainBackend = Get-Process -Name python -ErrorAction SilentlyContinue | 
    Where-Object { $_.CommandLine -like "*backend.py*" }

# AFTER:
$mainConnection = Get-NetTCPConnection -LocalPort 45678 -State Listen -ErrorAction SilentlyContinue
if ($mainConnection) {
    $processId = $mainConnection.OwningProcess
    Stop-Process -Id $processId -Force
    Write-Host "  OK  Main Backend stopped (PID: $processId)" -ForegroundColor Green
}
```

**Benefits:**
- ✅ Funktioniert auf allen Windows-Versionen
- ✅ Eindeutige Process-Identifikation über Port
- ✅ Keine Abhängigkeit von CommandLine Property
- ✅ Bessere Fehlerbehandlung

---

## Performance-Vergleich

### Startup Time Analysis

| Phase | Before | After | Notes |
|-------|--------|-------|-------|
| Main Backend Start | 2s | 2s | Unchanged |
| Ingestion Backend Start | 0s (parallel) | 0s (parallel) | Unchanged |
| Wait Time | 3s | 10s | Increased for reliability |
| Health Check Timeout | 5s (single try) | 15s (5 retries) | More robust |
| **Total Worst Case** | **10s** | **27s** | Maximum time if retries needed |
| **Total Best Case** | **5s** | **12s** | When backends start quickly |

**Real-World Performance:**
```
Typical Startup: ~12-15 seconds
  - Main Backend:      ~3-5s  (PostgreSQL + SAGA + UDS3)
  - Ingestion Backend: ~8-12s (Models + Workers)
  - Health Checks:     ~1-2s  (both healthy)
```

---

## Usage

### Starting Services

```powershell
PS C:\VCC\Covina> .\scripts\start_services.ps1

============================================================
   Starting Covina Microservices
============================================================

Starting Main Backend on Port 45678...
Starting Ingestion Backend on Port 45679...
  Waiting for backends to initialize (10s)...

Running Health Checks...
  OK  Main Backend: healthy
  OK  Ingestion Backend: healthy
      Workers: 36 I/O, 36 CPU

============================================================
   Covina Microservices Running
============================================================

URLs:
  Main Backend:      http://127.0.0.1:45678
  Ingestion Backend: http://127.0.0.1:45679
```

### Stopping Services

```powershell
PS C:\VCC\Covina> .\scripts\stop_services.ps1

============================================================
   Stopping Covina Microservices
============================================================

Stopping Main Backend on Port 45678...
  OK  Main Backend stopped (PID: 24056)
Stopping Ingestion Backend on Port 45679...
  OK  Ingestion Backend stopped (PID: 17880)

============================================================
   All services stopped
============================================================
```

---

## Troubleshooting

### Problem: Health Check Timeout

**Symptom:**
```
RETRY Main Backend: attempt 1/5...
RETRY Main Backend: attempt 2/5...
FAIL Main Backend: not responding after 5 retries
```

**Solutions:**

1. **Check Logs:**
   ```powershell
   Get-Content logs\main_backend_error.log -Tail 50
   ```

2. **Verify Port Availability:**
   ```powershell
   Get-NetTCPConnection -LocalPort 45678 -ErrorAction SilentlyContinue
   ```

3. **Check Process Status:**
   ```powershell
   Get-Process python | Where-Object { $_.CPU -gt 1 }
   ```

4. **Increase Startup Delay:**
   - Edit `start_services.ps1`
   - Change `Start-Sleep -Seconds 10` zu `Start-Sleep -Seconds 15`

---

### Problem: Port Already in Use

**Symptom:**
```
ERROR: [Errno 10048] error while attempting to bind on address
```

**Solution:**

1. **Stop Old Processes:**
   ```powershell
   .\scripts\stop_services.ps1
   ```

2. **Force Kill (if needed):**
   ```powershell
   Get-NetTCPConnection -LocalPort 45678 | 
       ForEach-Object { Stop-Process -Id $_.OwningProcess -Force }
   ```

---

### Problem: Backend Crashes During Startup

**Symptom:**
```
FAIL Ingestion Backend: not responding after 5 retries
```

**Debug Steps:**

1. **Check Error Logs:**
   ```powershell
   Get-Content logs\ingestion_backend_error.log
   ```

2. **Common Issues:**
   - Missing Models (sentence-transformers, spaCy)
   - Database Connection Failed (PostgreSQL, Neo4j, ChromaDB, CouchDB)
   - CUDA/GPU Issues (wenn GPU aktiviert)
   - Insufficient Memory (Worker Pool zu groß)

3. **Manual Start for Debugging:**
   ```powershell
   python ingestion_backend.py
   ```

---

## Configuration

### Environment Variables

**Workers Configuration:**
```bash
# .env.production
WORKERS_IO=36      # I/O Thread Pool Size
WORKERS_CPU=36     # CPU Process Pool Size
```

**Startup Tuning:**
```powershell
# start_services.ps1 (Line 39)
Start-Sleep -Seconds 10  # Adjust based on hardware
```

**Health Check Tuning:**
```powershell
# start_services.ps1 (Test-BackendHealth function)
[int]$MaxRetries = 5     # Number of retry attempts
[int]$RetryDelay = 2     # Delay between retries (seconds)
```

---

## Architecture

### Service Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                    Covina Microservices                     │
├─────────────────────────────────────────────────────────────┤
│                                                             │
│  ┌──────────────────────┐    ┌──────────────────────┐     │
│  │   Main Backend       │    │  Ingestion Backend   │     │
│  │   Port: 45678        │    │  Port: 45679         │     │
│  ├──────────────────────┤    ├──────────────────────┤     │
│  │ • Queries            │    │ • Upload             │     │
│  │ • DSGVO              │    │ • Job Management     │     │
│  │ • Review Queue       │    │ • 36 I/O Workers     │     │
│  │ • Handelsregister    │    │ • 36 CPU Workers     │     │
│  │ • BM25 Search        │    │ • WebSocket /ws/jobs │     │
│  └──────────────────────┘    └──────────────────────┘     │
│           │                            │                   │
│           └────────────┬───────────────┘                   │
│                        ▼                                   │
│              ┌──────────────────┐                          │
│              │   UDS3 Backend   │                          │
│              ├──────────────────┤                          │
│              │ • PostgreSQL     │                          │
│              │ • ChromaDB       │                          │
│              │ • Neo4j          │                          │
│              │ • CouchDB        │                          │
│              │ • SAGA Pattern   │                          │
│              └──────────────────┘                          │
└─────────────────────────────────────────────────────────────┘
```

### Startup Sequence

```
1. Start Main Backend (Port 45678)
   ├─ Load UDS3 Core
   ├─ Initialize SAGA Orchestrator (PostgreSQL Backend)
   ├─ Connect to Neo4j (Graph DB)
   ├─ Connect to ChromaDB (Vector DB)
   └─ Ready (~3-5s)

2. Start Ingestion Backend (Port 45679)
   ├─ Load UDS3 Core
   ├─ Initialize Worker Pools (36 I/O + 36 CPU)
   ├─ Load AI Models:
   │  ├─ sentence-transformers (all-MiniLM-L6-v2)
   │  ├─ spaCy (de_core_news_sm)
   │  └─ Whisper (base)
   ├─ Connect to Databases
   └─ Ready (~8-12s)

3. Wait for Initialization (10s)

4. Health Checks (Retry: 5x, Delay: 2s)
   ├─ Check Main Backend (/health)
   └─ Check Ingestion Backend (/health)

5. Report Status & Process IDs
```

---

## Integration mit anderen Tools

### Docker Compose Integration (Planned)

```yaml
# docker-compose.yml (future)
services:
  main-backend:
    build: .
    ports:
      - "45678:45678"
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:45678/health"]
      interval: 5s
      timeout: 3s
      retries: 5
      start_period: 15s
  
  ingestion-backend:
    build: .
    ports:
      - "45679:45679"
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:45679/health"]
      interval: 5s
      timeout: 3s
      retries: 5
      start_period: 20s  # Längere start_period für Model Loading
```

### Systemd Service (Linux Deployment)

```ini
# /etc/systemd/system/covina-main.service
[Unit]
Description=Covina Main Backend
After=network.target postgresql.service

[Service]
Type=simple
User=covina
WorkingDirectory=/opt/covina
ExecStart=/usr/bin/python3 backend.py
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
```

---

## Testing

### Manual Health Check Tests

```powershell
# Test Main Backend
Invoke-RestMethod -Uri "http://127.0.0.1:45678/health"

# Expected Output:
# status          : healthy
# active_jobs     : 0
# mail_configured : True
# timestamp       : 13.10.2025 17:18:16

# Test Ingestion Backend
Invoke-RestMethod -Uri "http://127.0.0.1:45679/health"

# Expected Output:
# status      : healthy
# timestamp   : 13.10.2025 17:18:16
# components  : @{uds3=✅ ready; vector_db=✅; graph_db=✅; ...}
# worker_pool : @{io_workers=36; cpu_workers=36; total_cpus=20}
```

### Load Testing Integration

```powershell
# Start Services
.\scripts\start_services.ps1

# Run Load Tests
python tests\load_test_upload_simple.py
python tests\load_test_queries_simple.py

# Stop Services
.\scripts\stop_services.ps1
```

---

## Related Documentation

- `docs/LOAD_TEST_REPORT.md` - Performance Test Results
- `docs/MICROSERVICES_ARCHITECTURE.md` - Architecture Details
- `docs/WEBSOCKET_INTEGRATION.md` - Real-Time Updates
- `docs/SAGA_IMPORT_FIX.md` - SAGA Orchestrator Fix
- `docs/UDS3_FULL_INTEGRATION_COMPLETE.md` - UDS3 Multi-DB Setup

---

## Change Log

### Version 2.0 (13.10.2025)
- ✅ Erhöhte Startup Wartezeit (3s → 10s)
- ✅ Retry-Logik für Health-Checks (5 Versuche)
- ✅ Port-basierte Process Detection im Stop-Script
- ✅ Erweiterte Status-Ausgabe (PIDs, Logs, Workers)
- ✅ Verbesserte Fehlerbehandlung

### Version 1.0 (11.10.2025)
- Basic Startup/Stop Scripts
- Simple Health Checks
- CommandLine-basierte Process Detection

---

## Best Practices

### Development
1. **Always use scripts:** `start_services.ps1` / `stop_services.ps1`
2. **Check logs on failure:** `logs\*_backend_error.log`
3. **Monitor health endpoints:** `/health` endpoints für beide Services
4. **Use WebSocket for real-time updates:** `ws://127.0.0.1:45679/ws/jobs`

### Production
1. **Use systemd/Docker:** Für automatisches Restart
2. **Configure monitoring:** Prometheus + Grafana
3. **Set up alerting:** Notify bei Health-Check Failures
4. **Log aggregation:** ELK Stack oder ähnlich
5. **Load balancing:** NGINX für mehrere Backend-Instanzen

---

## Summary

**Status:** ✅ **PRODUCTION READY**

Die Startup-Scripts wurden signifikant verbessert:
- ✅ Robustere Health-Checks mit Retry-Logik
- ✅ Zuverlässige Process-Detection über Ports
- ✅ Bessere Fehlerbehandlung und Logging
- ✅ Klare Status-Ausgabe für Debugging

**Beide Microservices starten jetzt zuverlässig mit dem echten SAGA Orchestrator!** 🚀
