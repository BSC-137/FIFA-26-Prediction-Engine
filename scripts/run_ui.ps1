# Run the prediction pitch UI (dev mode: Vite + API)

$ErrorActionPreference = "Stop"
$Root = Split-Path -Parent $PSScriptRoot
Set-Location $Root

# Start API in background if not already listening
$apiRunning = $false
try {
    $null = Invoke-WebRequest -Uri "http://127.0.0.1:8000/health" -UseBasicParsing -TimeoutSec 2
    $apiRunning = $true
    Write-Host "API already running on :8000"
} catch {
    Write-Host "Starting API on :8000..."
    Start-Process powershell -ArgumentList "-NoExit", "-Command", "cd '$Root'; .\scripts\run_api.ps1" -WindowStyle Minimized
    Start-Sleep -Seconds 4
}

# Install frontend deps if needed
if (-not (Test-Path "frontend\node_modules")) {
    Write-Host "Installing frontend dependencies..."
    Push-Location frontend
    npm install
    Pop-Location
}

Write-Host ""
Write-Host "Pitch UI: http://localhost:5173  (proxied API -> :8000)"
Write-Host "Or build + serve from API: npm run build in frontend/, then http://localhost:8000"
Write-Host ""

Push-Location frontend
npm run dev
Pop-Location
