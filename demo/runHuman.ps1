$ErrorActionPreference = 'Stop'
$root = $PSScriptRoot
$python = Join-Path $root '.venv\Scripts\python.exe'
$csv = Join-Path $root 'examples\human_motion.csv'
$generator = Join-Path $root 'src\project_china\synthetic_human.py'

Push-Location (Join-Path $root 'src')
try {
    $fresh = (Test-Path -LiteralPath $csv) -and
        ((Get-Item -LiteralPath $csv).LastWriteTimeUtc -ge (Get-Item -LiteralPath $generator).LastWriteTimeUtc)
    if ($fresh) {
        Write-Host "Používám existující $csv"
    }
    else {
        # CSV is this script's own output; regenerate it when the generator is newer.
        # The generator never overwrites, so write a temporary file and swap it in.
        $temporary = "$csv.new"
        if (Test-Path -LiteralPath $temporary) { Remove-Item -LiteralPath $temporary }
        Write-Host "Generuji $csv (CSV chybí nebo je starší než generátor)..."
        & $python -m project_china.synthetic_human $temporary
        if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }
        Move-Item -LiteralPath $temporary -Destination $csv -Force
    }

    Write-Host 'Načítám demo, může to trvat přibližně 30 s...'
    & $python -m project_china.demo $csv --particles 360 --volume-particles 1500
    if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }
}
finally {
    Pop-Location
}