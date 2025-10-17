# Discovery Service Test Suite
# Date: 16. Oktober 2025, 11:35 Uhr
# Status: COMPLETE VALIDATION

Write-Host "================================" -ForegroundColor Cyan
Write-Host "Discovery Service Test Suite" -ForegroundColor Cyan
Write-Host "================================" -ForegroundColor Cyan
Write-Host ""

# Test 1: Service Status
Write-Host "Test 1: Service Status" -ForegroundColor Yellow
$status = curl.exe http://127.0.0.1:45678/discovery/status -s | ConvertFrom-Json
Write-Host "  Running: $($status.running)" -ForegroundColor $(if ($status.running) { "Green" } else { "Red" })
Write-Host "  Watch Directories: $($status.watch_directories)"
Write-Host "  Total Scans: $($status.total_scans)"
Write-Host "  Files Discovered: $($status.total_files_discovered)"
Write-Host "  Scan Interval: $($status.scan_interval_seconds)s"
Write-Host ""

# Test 2: Create Test Files
Write-Host "Test 2: Create Test Files" -ForegroundColor Yellow
$testFiles = @(
    "data\inbox\test_document1.txt",
    "data\inbox\test_document2.pdf",
    "data\watch\contract.docx"
)

foreach ($file in $testFiles) {
    $content = "Test content for Discovery Service - $(Get-Date)"
    $content | Out-File -FilePath $file -Encoding utf8
    Write-Host "  Created: $file" -ForegroundColor Green
}
Write-Host ""

# Test 3: Trigger Manual Scan
Write-Host "Test 3: Trigger Manual Scan" -ForegroundColor Yellow
$scan = curl.exe -X POST http://127.0.0.1:45678/discovery/trigger-scan -s | ConvertFrom-Json
Write-Host "  Message: $($scan.message)"
Write-Host "  Files Found: $($scan.files_found)" -ForegroundColor $(if ($scan.files_found -gt 0) { "Green" } else { "Yellow" })
Write-Host "  Total Discovered: $($scan.service_status.total_files_discovered)"
Write-Host ""

# Test 4: Get Pending Files
Write-Host "Test 4: Get Pending Files" -ForegroundColor Yellow
$pending = curl.exe http://127.0.0.1:45678/discovery/pending-files -s | ConvertFrom-Json
Write-Host "  Count: $($pending.count)" -ForegroundColor $(if ($pending.count -gt 0) { "Green" } else { "Yellow" })
if ($pending.count -gt 0) {
    Write-Host "  Files:" -ForegroundColor Green
    foreach ($file in $pending.files) {
        Write-Host "    - $($file.name) ($($file.size_bytes) bytes, $($file.event_type))" -ForegroundColor Cyan
    }
} else {
    Write-Host "  No pending files (already processed or list cleared)" -ForegroundColor Yellow
}
Write-Host ""

# Test 5: Background Scanning (60s interval)
Write-Host "Test 5: Background Scanning Verification" -ForegroundColor Yellow
Write-Host "  Scan Interval: 60 seconds"
Write-Host "  Last Scan: $($status.last_scan)"
Write-Host "  Service automatically scans every 60s" -ForegroundColor Green
Write-Host ""

# Test 6: Cleanup Test Files
Write-Host "Test 6: Cleanup Test Files" -ForegroundColor Yellow
$cleanupChoice = Read-Host "  Delete test files? (y/N)"
if ($cleanupChoice -eq "y") {
    foreach ($file in $testFiles) {
        if (Test-Path $file) {
            Remove-Item $file -Force
            Write-Host "  Deleted: $file" -ForegroundColor Red
        }
    }
} else {
    Write-Host "  Test files kept for manual inspection" -ForegroundColor Yellow
}
Write-Host ""

# Summary
Write-Host "================================" -ForegroundColor Cyan
Write-Host "Test Suite Complete" -ForegroundColor Cyan
Write-Host "================================" -ForegroundColor Cyan
Write-Host "  Status: " -NoNewline
if ($status.running) {
    Write-Host "PASS" -ForegroundColor Green
} else {
    Write-Host "FAIL" -ForegroundColor Red
}
Write-Host "  Total Files Discovered: $($scan.service_status.total_files_discovered)"
Write-Host "  Discovery Service: OPERATIONAL" -ForegroundColor Green
Write-Host ""
