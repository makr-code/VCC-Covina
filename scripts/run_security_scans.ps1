<#
.SYNOPSIS
  Führt Security-Scans aus: pip-audit (Python Dependencies), Bandit (SAST), Trivy (Filesystem/Container).
.DESCRIPTION
  - Windows PowerShell Skript für lokale Scans und CI-Integration
  - Exit-Code 0: Keine kritischen Funde oder Tools nicht installiert (siehe Hinweise)
  - Exit-Code 1: Mindestens ein Scanner meldet HIGH/CRITICAL bzw. Issues
.NOTES
  Voraussetzungen: Python/Pip, optional Bandit, pip-audit, Trivy im PATH
#>

[CmdletBinding()]
param(
  [switch]$SkipPipAudit,
  [switch]$SkipBandit,
  [switch]$SkipTrivy,
  [string]$TargetPath = "."
)

function Test-Command {
  param([string]$Name)
  $old = $ErrorActionPreference; $ErrorActionPreference = 'SilentlyContinue'
  $cmd = Get-Command $Name
  $ErrorActionPreference = $old
  return $null -ne $cmd
}

$ErrorCount = 0
Write-Host "==> Security Scans starten (Target: $TargetPath)" -ForegroundColor Cyan

# 1) pip-audit (Python Dependencies)
if (-not $SkipPipAudit) {
  # Versuche pip-audit direkt im PATH oder als Python-Modul
  if (Test-Command "pip-audit") {
    Write-Host "[pip-audit] Scanne Python-Dependencies ..." -ForegroundColor Yellow
    pip-audit --strict
    if ($LASTEXITCODE -ne 0) {
      Write-Host "[pip-audit] 🛑 Vulnerabilities gefunden (strict)" -ForegroundColor Red
      $ErrorCount++
    } else {
      Write-Host "[pip-audit] ✅ Keine kritischen Findings" -ForegroundColor Green
    }
  } else {
    # Fallback: Als Python-Modul ausführen
    Write-Host "[pip-audit] Tool nicht im PATH, versuche python -m pip_audit ..." -ForegroundColor Yellow
    & python -m pip_audit --strict 2>&1 | Out-Null
    if ($LASTEXITCODE -eq 0 -or $LASTEXITCODE -eq $null) {
      Write-Host "[pip-audit] Scanne Python-Dependencies (via python -m) ..." -ForegroundColor Yellow
      & python -m pip_audit --strict
      if ($LASTEXITCODE -ne 0) {
        Write-Host "[pip-audit] 🛑 Vulnerabilities gefunden (strict)" -ForegroundColor Red
        $ErrorCount++
      } else {
        Write-Host "[pip-audit] ✅ Keine kritischen Findings" -ForegroundColor Green
      }
    } else {
      Write-Host "[pip-audit] ⚠️ Tool nicht gefunden. Installieren mit: python -m pip install pip-audit" -ForegroundColor DarkYellow
    }
  }
}

# 2) Bandit (SAST für Python)
if (-not $SkipBandit) {
  # Versuche bandit direkt im PATH oder als Python-Modul
  if (Test-Command "bandit") {
    Write-Host "[bandit] Führe statische Codeanalyse durch ..." -ForegroundColor Yellow
    bandit -r $TargetPath -x tests -q
    if ($LASTEXITCODE -ne 0) {
      Write-Host "[bandit] 🛑 Issues gefunden" -ForegroundColor Red
      $ErrorCount++
    } else {
      Write-Host "[bandit] ✅ Keine Findings" -ForegroundColor Green
    }
  } else {
    # Fallback: Als Python-Modul ausführen
    Write-Host "[bandit] Tool nicht im PATH, versuche python -m bandit ..." -ForegroundColor Yellow
    & python -m bandit --version 2>&1 | Out-Null
    if ($LASTEXITCODE -eq 0 -or $LASTEXITCODE -eq $null) {
      Write-Host "[bandit] Führe statische Codeanalyse durch (via python -m) ..." -ForegroundColor Yellow
      & python -m bandit -r $TargetPath -x tests -q
      if ($LASTEXITCODE -ne 0) {
        Write-Host "[bandit] 🛑 Issues gefunden" -ForegroundColor Red
        $ErrorCount++
      } else {
        Write-Host "[bandit] ✅ Keine Findings" -ForegroundColor Green
      }
    } else {
      Write-Host "[bandit] ⚠️ Tool nicht gefunden. Installieren mit: python -m pip install bandit" -ForegroundColor DarkYellow
    }
  }
}

# 3) Trivy (Filesystem Scan für High/Critical)
if (-not $SkipTrivy) {
  if (Test-Command "trivy") {
    Write-Host "[trivy] Scanne Filesystem (HIGH/CRITICAL) ..." -ForegroundColor Yellow
    trivy fs --severity HIGH,CRITICAL --exit-code 1 --no-progress $TargetPath
    if ($LASTEXITCODE -ne 0) {
      Write-Host "[trivy] 🛑 HIGH/CRITICAL Findings vorhanden" -ForegroundColor Red
      $ErrorCount++
    } else {
      Write-Host "[trivy] ✅ Keine HIGH/CRITICAL Findings" -ForegroundColor Green
    }
  } else {
    Write-Host "[trivy] ⚠️ Tool nicht gefunden. Installation: https://aquasecurity.github.io/trivy/v0.55/getting-started/installation/" -ForegroundColor DarkYellow
  }
}

if ($ErrorCount -gt 0) {
  Write-Host "==> Scans abgeschlossen mit Findings (Count=$ErrorCount)" -ForegroundColor Red
  exit 1
} else {
  Write-Host "==> Scans abgeschlossen (keine kritischen Findings oder Tools fehlten)" -ForegroundColor Green
  exit 0
}
