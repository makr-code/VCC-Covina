# Setup Legal Domain Taxonomy in Neo4j
# 
# Requirements:
#   - Neo4j running and configured in UDS3
#   - Python environment with dependencies installed
#
# Usage:
#   .\scripts\setup_legal_taxonomy.ps1

Write-Host "Legal Domain Taxonomy Setup" -ForegroundColor Cyan
Write-Host ("=" * 60) -ForegroundColor Gray

# Change to Covina directory
$scriptPath = Split-Path -Parent $MyInvocation.MyCommand.Path
$covinaRoot = Split-Path -Parent $scriptPath
Set-Location $covinaRoot

Write-Host ""
Write-Host "Checking prerequisites..." -ForegroundColor Yellow

# Check Python
$pythonCmd = Get-Command python -ErrorAction SilentlyContinue
if (-not $pythonCmd) {
    Write-Host "ERROR: Python not found in PATH" -ForegroundColor Red
    exit 1
}
Write-Host "Python found: $($pythonCmd.Source)" -ForegroundColor Green

# Check if script exists
$setupScript = "ingestion\scripts\setup_legal_taxonomy.py"
if (-not (Test-Path $setupScript)) {
    Write-Host "ERROR: Setup script not found: $setupScript" -ForegroundColor Red
    exit 1
}
Write-Host "Setup script found" -ForegroundColor Green

# Run setup
Write-Host ""
Write-Host "Running setup..." -ForegroundColor Yellow
Write-Host ""

python -m ingestion.scripts.setup_legal_taxonomy

$exitCode = $LASTEXITCODE

if ($exitCode -eq 0) {
    Write-Host ""
    Write-Host "Setup completed successfully!" -ForegroundColor Green
    Write-Host ""
    Write-Host "Recommended next steps:" -ForegroundColor Cyan
    Write-Host "  1. Verify in Neo4j Browser: http://localhost:7474" -ForegroundColor Gray
    Write-Host "  2. Query: MATCH (d:LegalDomain {tier: 1}) RETURN d" -ForegroundColor Gray
    Write-Host "  3. Check hierarchy with MATCH query" -ForegroundColor Gray
    Write-Host "  4. Continue with Phase L2: Legal Entity Extraction" -ForegroundColor Gray
} else {
    Write-Host ""
    Write-Host "Setup failed with exit code: $exitCode" -ForegroundColor Red
    Write-Host ""
    Write-Host "Troubleshooting:" -ForegroundColor Yellow
    Write-Host "  - Check Neo4j is running" -ForegroundColor Gray
    Write-Host "  - Verify UDS3 config in config.py" -ForegroundColor Gray
    Write-Host "  - Check logs for errors" -ForegroundColor Gray
}

exit $exitCode

exit $exitCode
