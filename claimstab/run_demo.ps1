param(
    [string]$Python = "python"
)

$ErrorActionPreference = "Stop"
$env:PYTHONPATH = Join-Path $PSScriptRoot "src"
$base = Join-Path $PSScriptRoot "examples\minimal"

& $Python -m unittest discover -s (Join-Path $PSScriptRoot "tests") -v
& $Python -m claimstab build `
    --claims (Join-Path $base "claims.csv") `
    --reconstruction (Join-Path $base "reconstruction.csv") `
    --endpoints (Join-Path $base "endpoints.csv") `
    --output-dir (Join-Path $base "output") `
    --alpha 0.05
& $Python -m claimstab compare `
    --claims (Join-Path $base "claims.csv") `
    --reconstruction (Join-Path $base "reconstruction.csv") `
    --endpoints (Join-Path $base "endpoints.csv") `
    --output-dir (Join-Path $base "comparison") `
    --alpha 0.05
