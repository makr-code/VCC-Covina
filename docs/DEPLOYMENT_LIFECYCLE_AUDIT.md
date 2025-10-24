# Deployment & Lifecycle Audit Report
**Datum:** 21. Oktober 2025  
**System:** Covina (Main + Ingestion Backend, Windows Dev → Linux Prod geplant)  
**Auditor:** GitHub Copilot  
**Status:** 🟡 TEILWEISE IMPLEMENTIERT

---

## Executive Summary

Wir bewerten Release-Strategie, Feature Flags/Kill-Switches, Blue/Green/Canary, Rollbacks, DB-Migrationen, Container-Hardening und Betrieb (Start/Stop/Health, Probes).  
Aktuell sind Start-/Stop-Skripte und Health-/Ready-Probes vorhanden; moderne Release-Patterns (Blue/Green/Canary), Feature Flags und automatisierte Rollbacks fehlen. DB-Migrationen sind manuell; Container-Hardening nicht dokumentiert.

- ✅ Health-/Ready-Probes: vorhanden (beide Backends)
- ✅ Restart/Deploy-Skripte: vorhanden (PowerShell)
- ⚠️ Feature Flags/Kill-Switches: teilweise (ENV-Flags, keine zentrale Steuerung)
- ❌ Blue/Green/Canary: fehlt
- ⚠️ Rollback-Strategie: rudimentär (manuell)
- ⚠️ DB-Migrationen: Skripte vorhanden, kein Framework/Lifecycle
- ❌ Container-Hardening: nicht dokumentiert (User/Cap-Drops/Read-Only FS)

Risiko: 🟠 Mittel (Change-Risiko, Downtime).  
Empfehlung: 9 Quick Wins über 4–6 Tage.

---

## 1. Feature Flags & Kill-Switches

### 1.1 Status
- ENV-Toggles (z. B. `ENABLE_CHROMA_BATCH_INSERT`) vorhanden
- Keine zentrale Verwaltung/Telemetrie

### 1.2 Empfehlungen (Quick Win)
- Leichtgewichtiges Flag-System (Datei-/ENV-basiert + /admin-API)

```python
# flags.py
from typing import Dict
import os

FLAGS: Dict[str, bool] = {
    'ENABLE_CHROMA_BATCH_INSERT': os.getenv('ENABLE_CHROMA_BATCH_INSERT', 'true').lower() in ('1','true','yes'),
    'ENABLE_NEO4J_BATCHING': os.getenv('ENABLE_NEO4J_BATCHING', 'false').lower() in ('1','true','yes'),
}

def is_enabled(name: str) -> bool:
    return FLAGS.get(name, False)

# admin
@app.post('/admin/flags/{name}/{value}')
async def set_flag(name: str, value: bool, _principal: Principal = Depends(get_admin)):
    FLAGS[name] = bool(value)
    return {'flag': name, 'value': FLAGS[name]}
```

- Kill-Switch für kritische Integrationen (z. B. ChromaDB): hartes Abschalten ohne Deploy

---

## 2. Blue/Green & Canary Releases

### 2.1 Status
- Single-Instance-Deploys; keine Traffic-Shifts

### 2.2 Empfehlungen
- NGINX/HAProxy als Router: Green (neu) hochfahren, Health prüfen, Traffic switchen
- Canary: 5% Traffic → 50% → 100% mit automatischem Abort bei Error-Rate > X%

```nginx
# Beispiel (vereinfachtes Blue/Green)
upstream main_backend {
    server 10.0.0.11:45678;  # blue
    server 10.0.0.12:45678;  # green
}
server {
  listen 80;
  location / {
    proxy_pass http://main_backend;
  }
}
```

---

## 3. Rollback-Strategie

### 3.1 Status
- Manuell per Skript; kein automatisches Rollback bei Health-Fail

### 3.2 Empfehlungen (Quick Win)
- Deploy-Pipeline mit Health-Gate und Auto-Rollback
- Versionierte Artefakte (Image mit SHA)

```powershell
# Pseudo: deploy_with_health.ps1
param(
  [string]$ImageTag
)

# 1) Start New
Start-Service -Name "covina-main-$ImageTag"

# 2) Wait Ready
if (-not (Invoke-RestMethod "http://127.0.0.1:45678/ready")) {
  # Rollback
  Stop-Service -Name "covina-main-$ImageTag"
  Start-Service -Name "covina-main-previous"
  throw "Deploy failed: readiness"
}

# 3) Switch Traffic (Blue→Green)
# ...
```

---

## 4. DB-Migrationen

### 4.1 Status
- SQL-Migrationen vorhanden (z. B. `2025_10_21_add_indexes.sql`)
- Kein Framework (z. B. Alembic) oder Versionierungs-Workflow

### 4.2 Empfehlungen
- Alembic (PostgreSQL) für versionsbasierte Migrations
- Pre-Deploy Checks + Online Migrations

```bash
alembic init db
alembic revision -m "add retention tables"
alembic upgrade head
```

- Migrations-Policy: backward-compatible, additive-first; destructive Steps separat

---

## 5. Container-Hardening

### 5.1 Status
- Dockerfiles vorhanden (Argus), Covina in lokalen Skripten; Hardening nicht dokumentiert

### 5.2 Empfehlungen (Quick Win)
- Nicht-root-User, read-only rootfs, drop capabilities, seccomp/apparmor Profile, minimal base image

```Dockerfile
FROM python:3.11-slim
# add non-root user
RUN useradd -m appuser
WORKDIR /app
COPY . /app
RUN pip install --no-cache-dir -r requirements.txt
USER appuser
# optional: read-only FS + writable tmp via mount
```

- Trivy config scan gegen Dockerfile-Misskonfigurationen

---

## 6. Start/Stop/Health & Graceful Shutdown

### 6.1 Status
- Probes (`/live`, `/ready`, `/health`) vorhanden
- Frühere Fehler (Logger vor basicConfig, Decorators vor app) behoben

### 6.2 Empfehlungen
- SIGTERM-Handler validieren (Shutdown Hooks: Worker Pools beenden, WS schließen)
- Max. Shutdown Dauer definieren (z. B. 30s)

---

## 7. Observability in Releases

### 7.1 Status
- Observability-Audit erstellt; OpenTelemetry/Prometheus pending

### 7.2 Empfehlungen
- Release-Canary mit Metriken-Gates (error_rate, p95_latency)
- Dashboards „Release Health“ (vor/nach Deploy Vergleich)

---

## 8. Infrastructure as Code (IaC) & Environment Parity

### 8.1 Status
- PowerShell-Skripte, keine deklarative IaC (Terraform/Ansible)

### 8.2 Empfehlungen
- Terraform für Netz/VM/SG/WAF
- Ansible für Provisioning (pgBouncer, NGINX, Services)
- Dev/Stage/Prod Parity: identische Konfig mit Variablen

---

## 9. Konfigurations- & Geheimnis-Management

### 9.1 Status
- `.env.production` im Einsatz; Secrets nicht zentral verwaltet

### 9.2 Empfehlungen
- zentraler Secret Store (Vault/Azure Key Vault)
- getrennte Config per Environment; kein Secret im Image

---

## 10. Quick Wins (Priorisiert)

1. Feature-Flag Endpoint + Kill-Switch (P0, 0.5–1d)
2. Deploy mit Health-Gate + Auto-Rollback (P0, 1d)
3. Alembic für DB-Migrationen (P1, 1–2d)
4. Container-Hardening (non-root, caps drop) (P1, 1d)
5. Canary via NGINX Traffic-Split (P1, 1–2d)
6. SIGTERM Cleanup Validierung (P1, 0.5d)
7. Observability Gates (p95/error_rate) (P2, 1d)
8. Terraform/Ansible Skeleton (P2, 2–3d)
9. Secret Store Einbindung (P2, 2–3d)

---

## 11. Risiko-Matrix

| Risiko | W’keit | Impact | Gesamt | Maßnahme |
|---|---|---|---|---|
| Fehlgeschlagenes Deploy ohne Rollback | Mittel | Hoch | 🔴 | Health-Gates + Auto-Rollback (P0) |
| Schema-Drift/Migrationsfehler | Mittel | Mittel | 🟠 | Alembic + Tests (P1) |
| Container-Privilegien-Missbrauch | Niedrig | Hoch | 🟠 | Non-root + Caps Drop (P1) |
| Downtime bei Release | Mittel | Mittel | 🟠 | Blue/Green/Canary (P1) |

---

## 12. Zusammenfassung

Status: 🟡 Teilweise. Mit 9 Quick Wins über ca. 4–6 Tage steigt Deployment-Sicherheit und -Stabilität deutlich. Priorität: Kill-Switch + Auto-Rollback (P0), dann Alembic + Hardening + Canary (P1).
