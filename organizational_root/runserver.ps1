$ProjectRoot = Split-Path -Parent $MyInvocation.MyCommand.Path
$Python = Join-Path $ProjectRoot '..\organizational_env\Scripts\python.exe'

if (-not (Test-Path $Python)) {
    Write-Error "Virtualenv Python was not found at $Python"
    exit 1
}

Set-Location $ProjectRoot
& $Python manage.py runserver @args
