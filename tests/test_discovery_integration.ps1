# Discovery Service → Ingestion Backend Integration Test
# Date: 16. Oktober 2025, 12:00 Uhr
# Purpose: Test automatic file upload from Discovery Service to Ingestion Backend

Write-Host "================================================================" -ForegroundColor Cyan
Write-Host "Discovery Service → Ingestion Backend Integration Test" -ForegroundColor Cyan
Write-Host "================================================================" -ForegroundColor Cyan
Write-Host ""

# Configuration
$testDir = "data\inbox"
$testFiles = @(
    @{name="test_auto_upload1.txt"; content="Test document 1 for automatic upload"},
    @{name="test_auto_upload2.pdf"; content="Test document 2 for automatic upload"},
    @{name="contract_auto.docx"; content="Test contract for automatic upload"}
)

# Pre-Test: Check services
Write-Host "Pre-Test: Checking Services..." -ForegroundColor Yellow
Write-Host ""

# Check Main Backend
try {
    $mainHealth = curl.exe http://127.0.0.1:45678/health -s | ConvertFrom-Json
    Write-Host "  Main Backend (45678): " -NoNewline
    Write-Host $mainHealth.status -ForegroundColor Green
} catch {
    Write-Host "  Main Backend (45678): " -NoNewline
    Write-Host "ERROR - Not Running!" -ForegroundColor Red
    exit 1
}

# Check Ingestion Backend
try {
    $ingestionHealth = curl.exe http://127.0.0.1:45679/health -s | ConvertFrom-Json
    Write-Host "  Ingestion Backend (45679): " -NoNewline
    Write-Host $ingestionHealth.status -ForegroundColor Green
} catch {
    Write-Host "  Ingestion Backend (45679): " -NoNewline
    Write-Host "ERROR - Not Running!" -ForegroundColor Red
    exit 1
}

# Check Discovery Service
try {
    $discoveryStatus = curl.exe http://127.0.0.1:45678/discovery/status -s | ConvertFrom-Json
    Write-Host "  Discovery Service: " -NoNewline
    if ($discoveryStatus.running) {
        Write-Host "Running (Scan Interval: $($discoveryStatus.scan_interval_seconds)s)" -ForegroundColor Green
    } else {
        Write-Host "Not Running!" -ForegroundColor Red
        exit 1
    }
} catch {
    Write-Host "  Discovery Service: " -NoNewline
    Write-Host "ERROR - Not Available!" -ForegroundColor Red
    exit 1
}

Write-Host ""
Write-Host "All services operational!" -ForegroundColor Green
Write-Host ""

# Test 1: Get initial job count
Write-Host "Test 1: Get Initial Job Count" -ForegroundColor Yellow
try {
    $initialJobs = curl.exe http://127.0.0.1:45679/jobs -s | ConvertFrom-Json
    $initialCount = $initialJobs.jobs.Count
    Write-Host "  Initial Jobs: $initialCount" -ForegroundColor Cyan
} catch {
    $initialCount = 0
    Write-Host "  Initial Jobs: 0 (or API error)" -ForegroundColor Yellow
}
Write-Host ""

# Test 2: Create test files
Write-Host "Test 2: Create Test Files in Watch Directory" -ForegroundColor Yellow
foreach ($file in $testFiles) {
    $filePath = Join-Path $testDir $file.name
    $file.content | Out-File -FilePath $filePath -Encoding utf8
    Write-Host "  Created: $($file.name)" -ForegroundColor Green
}
Write-Host ""

# Test 3: Trigger manual scan
Write-Host "Test 3: Trigger Discovery Service Scan" -ForegroundColor Yellow
try {
    $scanResult = curl.exe -X POST http://127.0.0.1:45678/discovery/trigger-scan -s | ConvertFrom-Json
    Write-Host "  Scan completed: $($scanResult.message)" -ForegroundColor Green
    Write-Host "  Files found: $($scanResult.files_found)" -ForegroundColor $(if ($scanResult.files_found -gt 0) { "Green" } else { "Yellow" })
} catch {
    Write-Host "  ERROR: Scan failed!" -ForegroundColor Red
    exit 1
}
Write-Host ""

# Test 4: Wait for auto-processing (async callback)
Write-Host "Test 4: Wait for Auto-Processing (5 seconds)..." -ForegroundColor Yellow
Start-Sleep -Seconds 5
Write-Host "  Processing window complete" -ForegroundColor Green
Write-Host ""

# Test 5: Check new job count
Write-Host "Test 5: Verify Job Creation" -ForegroundColor Yellow
try {
    $finalJobs = curl.exe http://127.0.0.1:45679/jobs -s | ConvertFrom-Json
    $finalCount = $finalJobs.jobs.Count
    $newJobs = $finalCount - $initialCount
    
    Write-Host "  Initial Jobs: $initialCount" -ForegroundColor Cyan
    Write-Host "  Final Jobs: $finalCount" -ForegroundColor Cyan
    Write-Host "  New Jobs Created: $newJobs" -ForegroundColor $(if ($newJobs -gt 0) { "Green" } else { "Red" })
    
    if ($newJobs -gt 0) {
        Write-Host ""
        Write-Host "  Recent Jobs:" -ForegroundColor Green
        $finalJobs.jobs | Select-Object -First $newJobs | ForEach-Object {
            Write-Host "    - Job $($_.job_id): $($_.file_count) file(s), Status: $($_.status)" -ForegroundColor Cyan
        }
    }
} catch {
    Write-Host "  ERROR: Could not verify jobs!" -ForegroundColor Red
}
Write-Host ""

# Test 6: Check backend logs
Write-Host "Test 6: Check Backend Logs (Last 30 Lines)" -ForegroundColor Yellow
$autoLogs = Get-Content logs\main_backend.log -Tail 30 | Select-String -Pattern "AUTO|UPLOAD|Discovery Service" | Select-Object -Last 10
if ($autoLogs) {
    Write-Host "  Recent Auto-Processing Logs:" -ForegroundColor Green
    foreach ($log in $autoLogs) {
        Write-Host "    $log" -ForegroundColor Cyan
    }
} else {
    Write-Host "  No auto-processing logs found (check if callback executed)" -ForegroundColor Yellow
}
Write-Host ""

# Test 7: Cleanup
Write-Host "Test 7: Cleanup Test Files" -ForegroundColor Yellow
$cleanupChoice = Read-Host "  Delete test files from $testDir? (y/N)"
if ($cleanupChoice -eq "y") {
    foreach ($file in $testFiles) {
        $filePath = Join-Path $testDir $file.name
        if (Test-Path $filePath) {
            Remove-Item $filePath -Force
            Write-Host "  Deleted: $($file.name)" -ForegroundColor Red
        }
    }
} else {
    Write-Host "  Test files kept for manual inspection" -ForegroundColor Yellow
}
Write-Host ""

# Summary
Write-Host "================================================================" -ForegroundColor Cyan
Write-Host "Integration Test Complete" -ForegroundColor Cyan
Write-Host "================================================================" -ForegroundColor Cyan
Write-Host "  Services Status: " -NoNewline
Write-Host "OPERATIONAL" -ForegroundColor Green
Write-Host "  Files Created: $($testFiles.Count)"
Write-Host "  Jobs Created: $newJobs"
Write-Host ""

if ($newJobs -ge $testFiles.Count) {
    Write-Host "  Result: " -NoNewline
    Write-Host "SUCCESS - All files auto-processed!" -ForegroundColor Green
    Write-Host "  Discovery Service → Ingestion Backend Integration: WORKING" -ForegroundColor Green
} elseif ($newJobs -gt 0) {
    Write-Host "  Result: " -NoNewline
    Write-Host "PARTIAL - Some files processed ($newJobs/$($testFiles.Count))" -ForegroundColor Yellow
    Write-Host "  Check logs for errors" -ForegroundColor Yellow
} else {
    Write-Host "  Result: " -NoNewline
    Write-Host "FAIL - No auto-processing detected" -ForegroundColor Red
    Write-Host "  Check:" -ForegroundColor Yellow
    Write-Host "    1. Discovery Service callback executed?" -ForegroundColor Yellow
    Write-Host "    2. Ingestion Backend accepting uploads?" -ForegroundColor Yellow
    Write-Host "    3. Backend logs for errors?" -ForegroundColor Yellow
}
Write-Host ""
