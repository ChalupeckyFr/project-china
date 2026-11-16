$ErrorActionPreference = 'Stop'
$root = $PSScriptRoot
$python = Join-Path $root '.venv\Scripts\python.exe'
$csv = Join-Path $root 'examples\moving_object.csv'

Push-Location (Join-Path $root 'src')
try {
    & $python -m project_china.demo $csv
    if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }
}
finally {
    Pop-Location
}
