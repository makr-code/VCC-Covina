# Deploy Backend v3.4.9 with Auto-Resume
# Quick deployment script for production

Write-Host "=" * 70 -ForegroundColor Cyan
Write-Host "🚀 Deploying Covina Backend v3.4.9 (Auto-Resume Mechanism)" -ForegroundColor Cyan
Write-Host "=" * 70 -ForegroundColor Cyan
Write-Host ""

# Step 1: Backup database
Write-Host "1️⃣  Backing up database..." -ForegroundColor Yellow
if (Test-Path "data\ingestion_jobs.db") {
    $timestamp = Get-Date -Format "yyyyMMdd_HHmmss"
    Copy-Item "data\ingestion_jobs.db" "data\ingestion_jobs.db.backup_$timestamp"
    Write-Host "   ✅ Database backed up to: ingestion_jobs.db.backup_$timestamp" -ForegroundColor Green
} else {
    Write-Host "   ⚠️  No database file found - skipping backup" -ForegroundColor Yellow
}

# Step 2: Stop existing services
Write-Host ""
Write-Host "2️⃣  Stopping existing services..." -ForegroundColor Yellow
& .\scripts\stop_services.ps1
Start-Sleep -Seconds 2

# Step 3: Validate code
Write-Host ""
Write-Host "3️⃣  Validating code..." -ForegroundColor Yellow
python -m py_compile ingestion_backend.py 2>$null
if ($LASTEXITCODE -eq 0) {
    Write-Host "   ✅ Code validation passed" -ForegroundColor Green
} else {
    Write-Host "   ❌ Code validation failed - aborting deployment!" -ForegroundColor Red
    exit 1
}

# Step 4: Check pending jobs BEFORE restart
Write-Host ""
Write-Host "4️⃣  Checking pending jobs (before restart)..." -ForegroundColor Yellow
try {
    # This will fail if backend is not running, which is expected
    $jobsBefore = curl http://127.0.0.1:45679/jobs?limit=1000 2>$null | ConvertFrom-Json
    $pendingBefore = ($jobsBefore | Where-Object { $_.status -eq "pending" -and $_.processed_files -eq 0 }).Count
    Write-Host "   📊 Pending jobs (0 progress): $pendingBefore" -ForegroundColor Cyan
} catch {
    Write-Host "   ⚠️  Backend not running - cannot check current state" -ForegroundColor Yellow
    $pendingBefore = "N/A"
}

# Step 5: Start backend
Write-Host ""
Write-Host "5️⃣  Starting Ingestion Backend..." -ForegroundColor Yellow
Write-Host "   🔄 Starting backend process..." -NoNewline

Start-Process powershell -ArgumentList "-NoExit", "-Command", "python ingestion_backend.py" -WindowStyle Minimized
Start-Sleep -Seconds 5

Write-Host " ✅" -ForegroundColor Green

# Step 6: Wait for backend to be ready
Write-Host ""
Write-Host "6️⃣  Waiting for backend to be ready..." -ForegroundColor Yellow
$maxWait = 30
$waited = 0
$ready = $false

while ($waited -lt $maxWait -and -not $ready) {
    try {
        $health = curl http://127.0.0.1:45679/health 2>$null | ConvertFrom-Json
        if ($health.status -eq "healthy") {
            $ready = $true
            Write-Host "   ✅ Backend ready after $waited seconds" -ForegroundColor Green
        }
    } catch {
        Write-Host "   ⏳ Waiting... ($waited/$maxWait seconds)" -ForegroundColor Gray
        Start-Sleep -Seconds 2
        $waited += 2
    }
}

if (-not $ready) {
    Write-Host "   ❌ Backend failed to start after $maxWait seconds!" -ForegroundColor Red
    exit 1
}

# Step 7: Check auto-resume results
Write-Host ""
Write-Host "7️⃣  Checking auto-resume results..." -ForegroundColor Yellow
Start-Sleep -Seconds 2

try {
    $jobsAfter = curl http://127.0.0.1:45679/jobs?limit=1000 2>$null | ConvertFrom-Json
    $pendingAfter = ($jobsAfter | Where-Object { $_.status -eq "pending" -and $_.processed_files -eq 0 }).Count
    $processingAfter = ($jobsAfter | Where-Object { $_.status -eq "processing" }).Count
    $failedAfter = ($jobsAfter | Where-Object { $_.status -eq "failed" }).Count
    
    Write-Host "   📊 Jobs Status (after auto-resume):" -ForegroundColor Cyan
    Write-Host "      • Pending (0 progress):  $pendingAfter" -ForegroundColor White
    Write-Host "      • Processing:            $processingAfter" -ForegroundColor White
    Write-Host "      • Failed (ghost jobs):   $failedAfter" -ForegroundColor White
    
    if ($pendingBefore -ne "N/A") {
        $ghostCleaned = [int]$pendingBefore - [int]$pendingAfter
        if ($ghostCleaned -gt 0) {
            Write-Host ""
            Write-Host "   🧹 Ghost jobs cleaned: $ghostCleaned" -ForegroundColor Green
        }
    }
} catch {
    Write-Host "   ⚠️  Could not fetch job status" -ForegroundColor Yellow
}

# Step 8: Worker pool check
Write-Host ""
Write-Host "8️⃣  Checking worker pool..." -ForegroundColor Yellow
$pythonProcesses = (Get-Process python -ErrorAction SilentlyContinue | Where-Object { $_.StartTime -gt (Get-Date).AddMinutes(-1) }).Count
Write-Host "   📊 Python processes (last 1 min): $pythonProcesses" -ForegroundColor Cyan

if ($pythonProcesses -ge 10) {
    Write-Host "   ✅ Worker pool active (expected: 36+)" -ForegroundColor Green
} else {
    Write-Host "   ⚠️  Worker pool not fully active yet (give it 30 seconds)" -ForegroundColor Yellow
}

# Summary
Write-Host ""
Write-Host "=" * 70 -ForegroundColor Cyan
Write-Host "📊 Deployment Summary" -ForegroundColor Cyan
Write-Host "=" * 70 -ForegroundColor Cyan
Write-Host ""
Write-Host "✅ Backend v3.4.9 deployed successfully!" -ForegroundColor Green
Write-Host ""
Write-Host "🔍 Next Steps:" -ForegroundColor Cyan
Write-Host "   1. Monitor logs:     tail -f logs/ingestion_backend.log" -ForegroundColor Gray
Write-Host "   2. Test auto-resume: python tests\test_auto_resume.py" -ForegroundColor Gray
Write-Host "   3. Check job status: curl http://127.0.0.1:45679/jobs" -ForegroundColor Gray
Write-Host ""
Write-Host "📝 Auto-Resume Features:" -ForegroundColor Cyan
Write-Host "   • Pending jobs automatically resumed" -ForegroundColor White
Write-Host "   • Ghost jobs automatically cleaned" -ForegroundColor White
Write-Host "   • Worker pool started immediately" -ForegroundColor White
Write-Host "   • Zero manual intervention required" -ForegroundColor White
Write-Host ""
Write-Host "🎉 Deployment complete!" -ForegroundColor Green
Write-Host ""
