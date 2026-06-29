# Run the FIFA 26 Prediction Engine API (Windows)
$ErrorActionPreference = "Stop"
$Root = Split-Path -Parent $PSScriptRoot
Set-Location $Root

if (-not (Test-Path "venv\Scripts\Activate.ps1")) {
    Write-Host "Creating virtual environment..."
    python -m venv venv
}

& "venv\Scripts\Activate.ps1"
pip install -e . -q

Write-Host "Starting API on http://127.0.0.1:8000"
uvicorn fifa26_engine.api.main:app --reload --host 0.0.0.0 --port 8000
