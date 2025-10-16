# Resume All Incomplete Jobs
# Script: scripts/resume_all_jobs.ps1
# Purpose: Trigger recovery for all incomplete jobs in queue

Write-Host "🔄 Fetching incomplete jobs..." -ForegroundColor Cyan

# Get all jobs
$jobs = curl http://127.0.0.1:45679/jobs?limit=1000 2>$null | ConvertFrom-Json

# Filter pending/processing jobs with 0 progress
$incompleteJobs = $jobs | Where-Object { 
    ($_.status -eq "pending" -or $_.status -eq "processing") -and 
    $_.processed_files -eq 0 
}

Write-Host "✅ Found $($incompleteJobs.Count) incomplete jobs" -ForegroundColor Green
Write-Host ""

if ($incompleteJobs.Count -eq 0) {
    Write-Host "✅ No incomplete jobs to resume!" -ForegroundColor Green
    exit 0
}

Write-Host "🚀 Starting job recovery..." -ForegroundColor Yellow
Write-Host ""

$successCount = 0
$errorCount = 0

foreach ($job in $incompleteJobs) {
    $jobId = $job.job_id
    $fileCount = $job.file_count
    
    Write-Host "🔄 Recovering Job: $jobId ($fileCount files)..." -NoNewline
    
    try {
        $response = curl -Method POST "http://127.0.0.1:45679/jobs/$jobId/recover" 2>$null | ConvertFrom-Json
        
        if ($response.status -eq "success" -or $response.new_job_id) {
            Write-Host " ✅" -ForegroundColor Green
            $successCount++
        } else {
            Write-Host " ❌ $($response.message)" -ForegroundColor Red
            $errorCount++
        }
    } catch {
        Write-Host " ❌ Error: $_" -ForegroundColor Red
        $errorCount++
    }
    
    # Throttle to avoid overwhelming backend
    Start-Sleep -Milliseconds 100
}

Write-Host ""
Write-Host "=" * 60 -ForegroundColor Cyan
Write-Host "📊 Recovery Summary:" -ForegroundColor Cyan
Write-Host "   ✅ Success: $successCount" -ForegroundColor Green
Write-Host "   ❌ Errors:  $errorCount" -ForegroundColor Red
Write-Host "=" * 60 -ForegroundColor Cyan
Write-Host ""

if ($successCount -gt 0) {
    Write-Host "✅ Job recovery complete!" -ForegroundColor Green
    Write-Host "🔄 Jobs are now processing..." -ForegroundColor Yellow
    Write-Host ""
    Write-Host "Monitor progress:" -ForegroundColor Cyan
    Write-Host "   curl http://127.0.0.1:45679/jobs" -ForegroundColor Gray
} else {
    Write-Host "❌ No jobs recovered - check backend logs" -ForegroundColor Red
}
