# setup_dev.ps1 - Create venv, install dev dependencies and set PYTHONPATH for session
param(
    [string]$venvName = '.venv'
)

python -m venv $venvName
Write-Host "Created virtual environment: $venvName"

# Activate venv for this script run (affects current process)
$venvPath = Join-Path -Path (Get-Location).Path -ChildPath $venvName
$activateScript = Join-Path $venvPath 'Scripts\Activate.ps1'
if (Test-Path $activateScript) {
    Write-Host "Activating venv..."
    & $activateScript
} else {
    Write-Host "Activation script not found at $activateScript"
}

python -m pip install --upgrade pip
if (Test-Path 'requirements.txt') {
    pip install -r requirements.txt
} else {
    Write-Host "requirements.txt not found; skipping dependency install."
}

# Set PYTHONPATH for the session to include repo root and third_party_stubs
$currentPath = (Get-Location).Path
$env:PYTHONPATH = "$currentPath;$currentPath\third_party_stubs"
Write-Host "PYTHONPATH set for this session: $env:PYTHONPATH"
Write-Host "Development environment ready. To activate the venv in a new shell run:"
Write-Host ".\$venvName\Scripts\Activate.ps1"
