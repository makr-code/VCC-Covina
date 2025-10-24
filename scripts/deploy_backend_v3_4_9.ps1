# Deploy Covina Microservices v3.4.9
# Quick deployment script for production (Main + Ingestion Backend)

Write-Host "=" * 70 -ForegroundColor Cyan
Write-Host "🚀 Deploying Covina Microservices v3.4.9 (Dual Backend)" -ForegroundColor Cyan
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

# Step 3: Validate code (both backends)
Write-Host ""
Write-Host "3️⃣  Validating code..." -ForegroundColor Yellow
python -m py_compile backend\main.py 2>$null
if ($LASTEXITCODE -eq 0) {
    Write-Host "   ✅ Main Backend validation passed" -ForegroundColor Green
} else {
    Write-Host "   ❌ Main Backend validation failed - aborting deployment!" -ForegroundColor Red
    exit 1
}

python -m py_compile backend\ingestion.py 2>$null
if ($LASTEXITCODE -eq 0) {
    Write-Host "   ✅ Ingestion Backend validation passed" -ForegroundColor Green
} else {
    Write-Host "   ❌ Ingestion Backend validation failed - aborting deployment!" -ForegroundColor Red
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

# Step 5: Start backends (Microservices Architecture)
Write-Host ""
Write-Host "5️⃣  Starting Backends..." -ForegroundColor Yellow
Write-Host "   🔄 Starting Main Backend (Port 45678)..." -NoNewline

Start-Process powershell -ArgumentList "-NoExit", "-Command", "python backend\main.py" -WindowStyle Minimized
Start-Sleep -Seconds 2
Write-Host " ✅" -ForegroundColor Green

Write-Host "   🔄 Starting Ingestion Backend (Port 45679)..." -NoNewline
Start-Process powershell -ArgumentList "-NoExit", "-Command", "python backend\ingestion.py" -WindowStyle Minimized
Start-Sleep -Seconds 3

Write-Host " ✅" -ForegroundColor Green

# Step 6: Wait for backends to be ready
Write-Host ""
Write-Host "6️⃣  Waiting for backends to be ready..." -ForegroundColor Yellow
$maxWait = 30
$waited = 0
$mainReady = $false
$ingestionReady = $false

while ($waited -lt $maxWait -and (-not $mainReady -or -not $ingestionReady)) {
    # Check Main Backend
    if (-not $mainReady) {
        try {
            $mainHealth = curl http://127.0.0.1:45678/health 2>$null | ConvertFrom-Json
            if ($mainHealth.status -eq "healthy") {
                $mainReady = $true
                Write-Host "   ✅ Main Backend ready after $waited seconds" -ForegroundColor Green
            }
        } catch {
            # Still waiting
        }
    }
    
    # Check Ingestion Backend
    if (-not $ingestionReady) {
        try {
            $ingestionHealth = curl http://127.0.0.1:45679/health 2>$null | ConvertFrom-Json
            if ($ingestionHealth.status -eq "healthy") {
                $ingestionReady = $true
                Write-Host "   ✅ Ingestion Backend ready after $waited seconds" -ForegroundColor Green
            }
        } catch {
            # Still waiting
        }
    }
    
    if (-not $mainReady -or -not $ingestionReady) {
        Write-Host "   ⏳ Waiting... ($waited/$maxWait seconds)" -ForegroundColor Gray
        Start-Sleep -Seconds 2
        $waited += 2
    }
}

if (-not $mainReady) {
    Write-Host "   ❌ Main Backend failed to start after $maxWait seconds!" -ForegroundColor Red
    exit 1
}

if (-not $ingestionReady) {
    Write-Host "   ❌ Ingestion Backend failed to start after $maxWait seconds!" -ForegroundColor Red
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
Write-Host "✅ Covina Microservices v3.4.9 deployed successfully!" -ForegroundColor Green
Write-Host ""
Write-Host "🔍 Next Steps:" -ForegroundColor Cyan
Write-Host "   1. Monitor logs:     tail -f logs/main_backend.log" -ForegroundColor Gray
Write-Host "   2. Monitor logs:     tail -f logs/ingestion_backend.log" -ForegroundColor Gray
Write-Host "   3. Test auto-resume: python tests\test_auto_resume.py" -ForegroundColor Gray
Write-Host "   4. Check job status: curl http://127.0.0.1:45679/jobs" -ForegroundColor Gray
Write-Host ""
Write-Host "📝 Microservices Architecture:" -ForegroundColor Cyan
Write-Host "   • Main Backend:      Port 45678 (Queries, DSGVO, Review)" -ForegroundColor White
Write-Host "   • Ingestion Backend: Port 45679 (Upload, Processing)" -ForegroundColor White
Write-Host "   • Worker pool:       36 I/O + 36 CPU processes" -ForegroundColor White
Write-Host "   • Auto-Resume:       Enabled (pending jobs recovered)" -ForegroundColor White
Write-Host ""
Write-Host "🎉 Deployment complete!" -ForegroundColor Green
Write-Host ""
