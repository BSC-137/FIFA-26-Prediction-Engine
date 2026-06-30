# Run from the project root to create a local .env for API keys (Windows).
$ErrorActionPreference = "Stop"
$Root = Split-Path -Parent $PSScriptRoot
Set-Location $Root

$EnvFile = Join-Path $Root ".env"
$ExampleFile = Join-Path $Root ".env.example"

if (Test-Path $EnvFile) {
    Write-Host ".env already exists at: $EnvFile"
} elseif (Test-Path $ExampleFile) {
    Copy-Item $ExampleFile $EnvFile
    Write-Host "Created .env from .env.example at: $EnvFile"
} else {
    Write-Error ".env.example not found in $Root"
    exit 1
}

Write-Host ""
Write-Host "Next steps:"
Write-Host "  1. Open $EnvFile"
Write-Host "  2. Paste your API-Football key:"
Write-Host "       API_FOOTBALL_KEY=your_key_here"
Write-Host "  3. Get a key at https://www.api-football.com/"
Write-Host "  4. Set USE_MOCK_DATA=false to use live fixture data"
Write-Host ""
Write-Host "Verify after starting the API:"
Write-Host "  GET http://localhost:8000/health   -> source should be api-football"
Write-Host "  GET http://localhost:8000/status   -> provider_mode should be api"
Write-Host ""
Write-Host "Never commit .env — it is listed in .gitignore."
