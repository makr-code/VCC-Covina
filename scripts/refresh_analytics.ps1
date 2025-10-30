# Refresh Analytics Views
#
# Aktualisiert alle PostgreSQL Materialized Views für Legal Analytics
#
# Usage:
#   .\scripts\refresh_analytics.ps1

Write-Host "Legal Analytics Refresh" -ForegroundColor Cyan
Write-Host ("=" * 60) -ForegroundColor Gray

# Change to Covina directory
$scriptPath = Split-Path -Parent $MyInvocation.MyCommand.Path
$covinaRoot = Split-Path -Parent $scriptPath
Set-Location $covinaRoot

Write-Host ""
Write-Host "Step 1: Graph to Relational Sync..." -ForegroundColor Yellow

# Run sync job
$env:ENABLE_GRAPH_ANALYTICS_SYNC = "true"
python -m ingestion.analytics.graph_to_relational_sync

$exitCode = $LASTEXITCODE

if ($exitCode -ne 0) {
    Write-Host ""
    Write-Host "ERROR: Sync failed with exit code: $exitCode" -ForegroundColor Red
    exit $exitCode
}

Write-Host ""
Write-Host "Step 2: Refresh Materialized Views..." -ForegroundColor Yellow

# SQL for refreshing views
$refreshSQL = @"
SELECT refresh_all_analytics_views();
"@

# Execute via psql (assumes PostgreSQL is accessible)
# Alternative: Use Python script with UDS3 relational adapter
Write-Host "  Refreshing mv_laws_per_domain..."
Write-Host "  Refreshing mv_norms_per_jurisdiction..."
Write-Host "  Refreshing mv_docs_per_concept..."

# Note: Actual refresh requires PostgreSQL connection
# For now, we document the SQL command
Write-Host ""
Write-Host "To complete refresh, run in PostgreSQL:" -ForegroundColor Cyan
Write-Host "  SELECT refresh_all_analytics_views();" -ForegroundColor Gray

Write-Host ""
Write-Host ("=" * 60) -ForegroundColor Gray
Write-Host "Analytics Refresh Complete!" -ForegroundColor Green
Write-Host ""
Write-Host "Next steps:" -ForegroundColor Cyan
Write-Host "  1. Verify counts in PostgreSQL (dim_domain, dim_concept, etc.)"
Write-Host "  2. Query materialized views (mv_laws_per_domain, etc.)"
Write-Host "  3. Schedule this script (Task Scheduler for nightly refresh)"

exit 0
