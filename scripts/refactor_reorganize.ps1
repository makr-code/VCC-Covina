# Covina Refactoring - Automated File Reorganization
# Generated: 2025-10-24
# Purpose: Execute all git mv commands from RENAME_MAPPING.csv

param(
    [switch]$DryRun = $false,
    [switch]$SkipDeletes = $false,
    [string]$Category = "ALL"
)

# Color output functions
function Write-Info { param($msg) Write-Host $msg -ForegroundColor Cyan }
function Write-Success { param($msg) Write-Host $msg -ForegroundColor Green }
function Write-Warning { param($msg) Write-Host $msg -ForegroundColor Yellow }
function Write-Error { param($msg) Write-Host $msg -ForegroundColor Red }

Write-Info "========================================="
Write-Info "Covina Refactoring - File Reorganization"
Write-Info "========================================="
Write-Info ""

# Check if git is available
if (-not (Get-Command git -ErrorAction SilentlyContinue)) {
    Write-Error "ERROR: git not found in PATH!"
    exit 1
}

# Check if in git repository
if (-not (Test-Path .git)) {
    Write-Error "ERROR: Not in a git repository!"
    exit 1
}

# Check for uncommitted changes
$gitStatus = git status --porcelain
if ($gitStatus) {
    Write-Warning "WARNING: You have uncommitted changes!"
    Write-Warning "Please commit or stash changes before running this script."
    $continue = Read-Host "Continue anyway? (yes/no)"
    if ($continue -ne "yes") {
        Write-Info "Aborted."
        exit 0
    }
}

# Load CSV
$csvPath = "docs\RENAME_MAPPING.csv"
if (-not (Test-Path $csvPath)) {
    Write-Error "ERROR: RENAME_MAPPING.csv not found!"
    exit 1
}

Write-Info "Loading rename mapping from: $csvPath"
$mappings = Import-Csv $csvPath

# Filter by category if specified
if ($Category -ne "ALL") {
    $mappings = $mappings | Where-Object { $_.category -eq $Category }
    Write-Info "Filtered to category: $Category"
}

Write-Info "Total operations: $($mappings.Count)"
Write-Info ""

if ($DryRun) {
    Write-Warning "DRY RUN MODE - No actual changes will be made"
    Write-Info ""
}

# Define category order
$categoryOrder = @(
    "Backend",
    "Config", 
    "Scripts",
    "Tests",
    "Docs",
    "Tools",
    "Archive",
    "Frontend",
    "Git Artifacts",
    "Duplicates"
)

$stats = @{
    Moved = 0
    Deleted = 0
    Skipped = 0
    Errors = 0
}

foreach ($cat in $categoryOrder) {
    $categoryMappings = $mappings | Where-Object { $_.category -eq $cat }
    
    if ($categoryMappings.Count -eq 0) {
        continue
    }
    
    Write-Info "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
    Write-Info "Category: $cat ($($categoryMappings.Count) files)"
    Write-Info "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
    Write-Info ""
    
    foreach ($mapping in $categoryMappings) {
        $oldPath = $mapping.old_path
        $newPath = $mapping.new_path
        $reason = $mapping.reason
        $priority = $mapping.priority
        
        # Check if DELETE operation
        if ($newPath -eq "DELETE") {
            if ($SkipDeletes) {
                Write-Warning "SKIP DELETE: $oldPath (--SkipDeletes flag)"
                $stats.Skipped++
                continue
            }
            
            if (-not (Test-Path $oldPath)) {
                Write-Warning "SKIP: $oldPath (already deleted)"
                $stats.Skipped++
                continue
            }
            
            Write-Info "DELETE: $oldPath"
            Write-Info "  Reason: $reason"
            
            if (-not $DryRun) {
                try {
                    Remove-Item $oldPath -Force
                    Write-Success "  ✓ Deleted"
                    $stats.Deleted++
                } catch {
                    Write-Error "  ✗ Error: $_"
                    $stats.Errors++
                }
            } else {
                Write-Warning "  [DRY RUN] Would delete"
            }
            Write-Info ""
            continue
        }
        
        # Check if file exists
        if (-not (Test-Path $oldPath)) {
            Write-Warning "SKIP: $oldPath → $newPath (source not found)"
            $stats.Skipped++
            continue
        }
        
        # Create target directory if needed
        $targetDir = Split-Path $newPath -Parent
        if ($targetDir -and -not (Test-Path $targetDir)) {
            Write-Info "CREATE DIR: $targetDir"
            if (-not $DryRun) {
                New-Item -ItemType Directory -Path $targetDir -Force | Out-Null
            }
        }
        
        # Execute git mv
        Write-Info "MOVE: $oldPath → $newPath"
        Write-Info "  Reason: $reason"
        Write-Info "  Priority: $priority"
        
        if (-not $DryRun) {
            try {
                git mv $oldPath $newPath 2>&1 | Out-Null
                if ($LASTEXITCODE -eq 0) {
                    Write-Success "  ✓ Moved"
                    $stats.Moved++
                } else {
                    Write-Error "  ✗ git mv failed (exit code: $LASTEXITCODE)"
                    $stats.Errors++
                }
            } catch {
                Write-Error "  ✗ Error: $_"
                $stats.Errors++
            }
        } else {
            Write-Warning "  [DRY RUN] Would execute: git mv $oldPath $newPath"
        }
        Write-Info ""
    }
    
    # Commit after each category (if not dry run and files were moved)
    if (-not $DryRun -and ($categoryMappings | Where-Object { $_.new_path -ne "DELETE" }).Count -gt 0) {
        $movedCount = ($categoryMappings | Where-Object { $_.new_path -ne "DELETE" }).Count
        $commitMsg = "refactor($($cat.ToLower().Replace(' ', '-'))): reorganize files

- Category: $cat
- Files moved: $movedCount
- See docs/RENAME_MAPPING.csv for details"
        
        Write-Info "COMMIT: $cat changes"
        git commit -m $commitMsg 2>&1 | Out-Null
        if ($LASTEXITCODE -eq 0) {
            Write-Success "✓ Committed"
        } else {
            Write-Warning "No changes to commit"
        }
        Write-Info ""
    }
}

# Summary
Write-Info "========================================="
Write-Info "Refactoring Complete!"
Write-Info "========================================="
Write-Info "Moved:   $($stats.Moved) files"
Write-Info "Deleted: $($stats.Deleted) files"
Write-Info "Skipped: $($stats.Skipped) files"
Write-Info "Errors:  $($stats.Errors) errors"
Write-Info ""

if ($DryRun) {
    Write-Warning "This was a DRY RUN - no actual changes were made"
    Write-Info "Run without -DryRun flag to execute changes"
} else {
    Write-Success "All changes have been committed!"
    Write-Info ""
    Write-Info "Next steps:"
    Write-Info "1. Review git log for commits"
    Write-Info "2. Run import statement updates (Task #13)"
    Write-Info "3. Run test suite (Task #15)"
    Write-Info "4. Update documentation (Task #16)"
}
