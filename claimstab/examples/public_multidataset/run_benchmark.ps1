param(
    [string]$Python = "python",
    [string]$Rscript = "Rscript"
)

$ErrorActionPreference = "Stop"
$output = Join-Path $PSScriptRoot "output"

& $Rscript (Join-Path $PSScriptRoot "build_public_multiverse.R") $output
& $Python (Join-Path $PSScriptRoot "summarize_public_benchmark.py") `
    --benchmark-root $output `
    --claimstab-root (Resolve-Path (Join-Path $PSScriptRoot "..\..")).Path `
    --output-dir (Join-Path $output "summary")
