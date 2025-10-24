# Supply Chain Security Audit Report
**Datum:** 21. Oktober 2025  
**System:** Covina (Main + Ingestion Backend, UDS3 Polyglot DBs)  
**Auditor:** GitHub Copilot  
**Status:** 🟡 TEILWEISE IMPLEMENTIERT

---

## Executive Summary

Ziel ist die Bewertung der Software-Lieferkette (Dependencies, Build, CI/CD, Artefakt-Sicherheit, Laufzeit-Schutz).  
Aktueller Stand: Dependency Management ist teilweise vorhanden, formale SBOM-Erzeugung, Signierung und automatisches Vulnerability-Scanning fehlen. CI/CD-Hardening und Secret Management sind verbesserungsfähig.

- ✅ Versions-Pinning: teilweise (requirements.txt vorhanden, nicht überall strikt gepinnt)
- ⚠️ SBOM (Software Bill of Materials): fehlt
- ⚠️ Vulnerability Scanning: punktuell (nicht automatisiert; pip-audit/Trivy fehlen)
- ❌ Artefakt-Signierung/Verifikation: fehlt
- ⚠️ CI/CD Hardening: teilweise (Skripte vorhanden, Policies fehlen)
- ⚠️ Secret Management: ENV-Dateien, kein zentrales Secret-Backend
- ⚠️ Netzwerk-Segmentierung/WAF: geplant (keine Doku/Regeln)

Risiko: 🟠 Mittel bis 🔴 Hoch bei fehlender Signierung/Scanning.  
Empfehlung: 8 Quick Wins innerhalb 3–5 Tagen implementieren.

---

## 1. Dependency Management

### 1.1 Status
- Python: `requirements.txt`/`requirements-dev.txt` vorhanden (mehrere Repos), aber nicht überall strikt gepinnt (`package==x.y.z`)
- Keine automatische Renovation (z. B. Dependabot/Renovate)

### 1.2 Empfehlungen
- Striktes Pinning überall: `==` statt `>=`
- Hash-Pinning für Pip (pip-tools) oder Poetry Lockfiles
- Automatische Update-PRs via Dependabot/Renovate (mit CI-Tests)

```bash
# Beispiel: pip-tools
pip-compile --generate-hashes -o requirements.lock.txt requirements.in
pip-sync requirements.lock.txt
```

---

## 2. SBOM (Software Bill of Materials)

### 2.1 Status
- Keine SBOM-Generierung (CycloneDX/Syft) dokumentiert

### 2.2 Empfehlungen (Quick Win)
- CycloneDX für Python-Requirements und Docker-Images

```bash
# Python SBOM
pip install cyclonedx-bom
cyclonedx-py -r -o sbom_python_covina.json

# Container SBOM (Syft)
syft packages docker:covina-main:latest -o cyclonedx-json > sbom_container_main.json
```

- Ablage unter `docs/sbom/` und CI-Artefakte

---

## 3. Vulnerability Scanning

### 3.1 Status
- Kein automatisiertes Scanning in CI (pip-audit, Trivy, Grype)

### 3.2 Empfehlungen (Quick Win)
- Python-Pakete: `pip-audit` im Build-Break-Modus
- Container: `trivy` Scan (OS/Packages/Misconfig)

```bash
# Python
pip install pip-audit
pip-audit --strict  # Exit-Code != 0 bei kritischen CVEs

# Container (lokal/CI)
trivy image --severity HIGH,CRITICAL --exit-code 1 covina-main:latest
```

- Wöchentliche geplante Scans + PR-Checks

---

## 4. Artefakt-Signierung & Verifikation

### 4.1 Status
- Keine Signierung von Container-Images/Release-Artefakten

### 4.2 Empfehlungen (Quick Win)
- Sigstore Cosign zur Image-Signierung + Admission Policy (in Prod)

```bash
# Signieren (CI)
cosign sign --key env://COSIGN_KEY quay.io/org/covina-main:$(git rev-parse --short HEAD)

# Verifizieren (Deploy)
cosign verify quay.io/org/covina-main:$(git rev-parse --short HEAD)
```

- Optional: SLSA Provenance (gha-attestations)

---

## 5. CI/CD Hardening

### 5.1 Status
- PowerShell-Deploy-Skripte vorhanden, aber:
  - Kein Least-Privilege auf Token/Einstellungen dokumentiert
  - Keine Immutable Build-Artefakte (Reproducible Builds nicht gesichert)

### 5.2 Empfehlungen
- Principle of Least Privilege (Tokens/Secrets nur lesend, getrennte Rollen Build/Deploy)
- Reproducible Builds (pinned base images, pinned packages)
- Mandatory Scans (pip-audit, trivy) vor Release
- PR-Checks mit Tests + Lint + SAST (Bandit)

```bash
# Bandit (Python SAST)
pip install bandit
bandit -r covina -x tests
```

---

## 6. Secret Management

### 6.1 Status
- ENV-Files (`.env.production`) im Einsatz
- Keine zentrale Secret Vault (z. B. HashiCorp Vault/Azure Key Vault)

### 6.2 Empfehlungen
- Secrets in Vault, CI holt Short-Lived Tokens
- Kein Secret im Log/Artefakt
- Secret Scanning (Gitleaks) in CI

```bash
# Gitleaks
choco install gitleaks -y
gitleaks detect --source . --no-git --verbose --redact
```

---

## 7. Netzwerk-Segmentierung & WAF/API-Gateway

### 7.1 Status
- Interne IPs (192.168.178.94) für DBs → gut
- Keine dokumentierte WAF/API-Gateway-Policy

### 7.2 Empfehlungen
- API-Gateway (Rate-Limits, AuthN, Schema-Validation, mTLS intern)
- WAF-Regeln (OWASP CRS), z. B. NGINX + ModSecurity
- Netzwerk-Policies: Main ↔ Ingestion ↔ DBs minimal

---

## 8. Third-Party & Lizenz-Compliance

### 8.1 Status
- Kein lizenzrechtliches Review dokumentiert (GPL/AGPL-Risiken)

### 8.2 Empfehlungen
- Lizenz-Scanner (FOSSology, ORT) auf SBOM
- Policy: verbotene Lizenzen (AGPL) blockieren

---

## 9. Quick Wins (Priorisiert)

1. pip-audit + trivy in CI (P0, 0.5–1d)
2. SBOM (CycloneDX) erzeugen und versionieren (P0, 0.5d)
3. Cosign-Signierung von Images (P1, 1d)
4. Dependabot/Renovate aktivieren (P1, 0.5d)
5. Gitleaks Secret Scan (P1, 0.5d)
6. Bandit SAST (P1, 0.5d)
7. WAF-Basisregeln (P2, 1–2d)
8. Vault-Einführung (P2, 2–3d)

---

## 10. Risiko-Matrix

| Risiko | W’keit | Impact | Gesamt | Maßnahme |
|---|---|---|---|---|
| Kritische CVE in Runtime | Mittel | Hoch | 🔴 | pip-audit + trivy (P0) |
| Supply-Chain-Angriff (kompromittiertes Image) | Niedrig | Hoch | 🟠 | Cosign + Policy (P1) |
| Secret-Leak im Repo/Logs | Mittel | Hoch | 🔴 | Gitleaks + Vault (P1) |
| Lizenzverletzung | Niedrig | Mittel | 🟡 | SBOM + Lizenz-Scan (P1) |

---

## 11. Zusammenfassung

Status: 🟡 Teilweise umgesetzt. Mit 8 Quick Wins in 3–5 Tagen lässt sich das Risiko signifikant senken. Zuerst Scans & SBOM (P0), dann Signierung & Secret-Scans (P1), mittelfristig WAF/Vault (P2).
