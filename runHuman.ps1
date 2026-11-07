$ErrorActionPreference = 'Stop'
$root = $PSScriptRoot
$python = Join-Path $root '.venv\Scripts\python.exe'
$csv = Join-Path $root 'examples\human_motion.csv'

Push-Location (Join-Path $root 'src')
try {
    if (Test-Path -LiteralPath $csv) {
        Write-Host "Používám existující $csv"
    }
    else {
        & $python -m project_china.synthetic_human $csv
        if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }
    }

    Write-Host 'Načítám demo, může to trvat přibližně 15 s...'
    & $python -m project_china.demo $csv --particles 360 --volume-particles 1500
    if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }
}
finally {
    Pop-Location
}
