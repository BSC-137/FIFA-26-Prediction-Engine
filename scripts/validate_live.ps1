# Validate live provider configuration (Windows).
$ErrorActionPreference = "Stop"
$Root = Split-Path -Parent $PSScriptRoot
Set-Location $Root

$ArgsList = @()
if ($args -contains "--mock") { $ArgsList += "--mock" }
if ($args -contains "--json") { $ArgsList += "--json" }

python -m fifa26_engine.scripts.validate_live @ArgsList
exit $LASTEXITCODE
