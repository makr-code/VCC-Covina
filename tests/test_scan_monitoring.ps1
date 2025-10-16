# Test Scan Monitoring Script
# Überwacht einen laufenden Directory-Scan

param(
    [string]$ScanJobId = $env:SCAN_JOB_ID,
    [int]$MaxIterations = 20,
    [int]$IntervalSeconds = 5
)

Write-Host "`n" -NoNewline
Write-Host "═══════════════════════════════════════════════════════════" -ForegroundColor Cyan
Write-Host "  📊 SCAN MONITORING: $ScanJobId" -ForegroundColor White
Write-Host "═══════════════════════════════════════════════════════════" -ForegroundColor Cyan
Write-Host ""

$startTime = Get-Date

for ($i = 1; $i -le $MaxIterations; $i++) {
    try {
        $status = Invoke-RestMethod -Uri "http://127.0.0.1:45679/scan/$ScanJobId" -ErrorAction Stop
        
        $elapsed = [math]::Round($status.elapsed_time, 1)
        $statusColor = switch ($status.status) {
            "scanning" { "Yellow" }
            "creating_jobs" { "Cyan" }
            "extracting" { "Magenta" }
            "completed" { "Green" }
            "error" { "Red" }
            default { "White" }
        }
        
        Write-Host "[$i/$MaxIterations] " -NoNewline -ForegroundColor Gray
        Write-Host "$($status.status.ToUpper())" -NoNewline -ForegroundColor $statusColor
        Write-Host " | " -NoNewline
        Write-Host "Files: $($status.files_found)" -NoNewline -ForegroundColor White
        Write-Host " | " -NoNewline
        Write-Host "Jobs: $($status.upload_jobs_created)" -NoNewline -ForegroundColor Cyan
        Write-Host " | " -NoNewline
        Write-Host "Zeit: ${elapsed}s" -ForegroundColor Gray
        
        # Check if completed or error
        if ($status.status -eq "completed") {
            Write-Host ""
            Write-Host "═══════════════════════════════════════════════════════════" -ForegroundColor Green
            Write-Host "  ✅ SCAN ERFOLGREICH ABGESCHLOSSEN!" -ForegroundColor Green
            Write-Host "═══════════════════════════════════════════════════════════" -ForegroundColor Green
            Write-Host ""
            Write-Host "📊 Ergebnis:" -ForegroundColor Cyan
            Write-Host "   • Files gefunden: $($status.files_found)" -ForegroundColor White
            Write-Host "   • Upload-Jobs erstellt: $($status.upload_jobs_created)" -ForegroundColor White
            Write-Host "   • Gesamt-Zeit: ${elapsed}s" -ForegroundColor White
            
            if ($status.upload_job_ids.Count -gt 0) {
                Write-Host ""
                Write-Host "🔧 Upload-Job-IDs:" -ForegroundColor Cyan
                foreach ($jobId in $status.upload_job_ids) {
                    Write-Host "   • $jobId" -ForegroundColor Gray
                }
            }
            
            Write-Host ""
            break
        }
        
        if ($status.status -eq "error") {
            Write-Host ""
            Write-Host "═══════════════════════════════════════════════════════════" -ForegroundColor Red
            Write-Host "  ❌ SCAN FEHLER!" -ForegroundColor Red
            Write-Host "═══════════════════════════════════════════════════════════" -ForegroundColor Red
            Write-Host ""
            Write-Host "Error: $($status.error)" -ForegroundColor Red
            Write-Host ""
            break
        }
        
    } catch {
        Write-Host "[$i/$MaxIterations] ⚠️  API-Fehler: $($_.Exception.Message)" -ForegroundColor Red
    }
    
    if ($i -lt $MaxIterations) {
        Start-Sleep -Seconds $IntervalSeconds
    }
}

# Final status check
if ($i -ge $MaxIterations -and $status.status -eq "scanning") {
    Write-Host ""
    Write-Host "═══════════════════════════════════════════════════════════" -ForegroundColor Yellow
    Write-Host "  ⏳ SCAN LÄUFT NOCH..." -ForegroundColor Yellow
    Write-Host "═══════════════════════════════════════════════════════════" -ForegroundColor Yellow
    Write-Host ""
    Write-Host "Der Scan ist noch nicht abgeschlossen." -ForegroundColor Yellow
    Write-Host "Netzwerk-Drives können sehr langsam sein (mehrere Minuten)." -ForegroundColor Gray
    Write-Host ""
    Write-Host "Prüfe Status manuell:" -ForegroundColor Cyan
    Write-Host "  Invoke-RestMethod -Uri http://127.0.0.1:45679/scan/$ScanJobId" -ForegroundColor Gray
    Write-Host ""
}

$totalElapsed = ((Get-Date) - $startTime).TotalSeconds
Write-Host "Monitoring-Zeit: $([math]::Round($totalElapsed, 1))s" -ForegroundColor Gray
Write-Host ""
