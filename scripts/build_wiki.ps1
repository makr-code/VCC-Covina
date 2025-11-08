# Build Covina Wiki locally
# - Copies Covina/docs to Covina/wiki via Python generator
# - Requires Python 3 on PATH

$ErrorActionPreference = 'Stop'

function Invoke-Python {
    param(
        [Parameter(ValueFromRemainingArguments=$true)]
        [string[]]$argv
    )
    try {
        # Prefer py launcher on Windows if available
        & py -3 @argv
        return $LASTEXITCODE
    } catch {
        # Fallback to python
        & python @argv
        return $LASTEXITCODE
    }
}

# Resolve repo root (this script is in Covina/scripts)
$scriptPath = Split-Path -Parent $MyInvocation.MyCommand.Path
$covinaRoot = Split-Path -Parent $scriptPath
$repoRoot = Split-Path -Parent $covinaRoot

Write-Host "Repo Root: $repoRoot"
Write-Host "Covina Root: $covinaRoot"

# Export COVINA_ROOT for generator (optional)
$env:COVINA_ROOT = $covinaRoot

# Run generator
$generator = Join-Path $covinaRoot 'tools/generate_wiki.py'
if (-not (Test-Path $generator)) {
    Write-Error "Generator not found: $generator"
    exit 1
}

Write-Host "Running: $generator"
Invoke-Python @($generator)
if ($LASTEXITCODE -ne 0) {
    Write-Error "Wiki generation failed with exit code $LASTEXITCODE"
    exit $LASTEXITCODE
}

Write-Host "Wiki generated at: $(Join-Path $covinaRoot 'wiki')"
