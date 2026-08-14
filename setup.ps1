param(
    [switch]$CacheDependencies,
    [switch]$Offline
)

$ErrorActionPreference = "Stop"
$RepoRoot = Split-Path -Parent $MyInvocation.MyCommand.Path
Set-Location $RepoRoot

if (-not (Test-Path ".venv")) {
    Write-Host "Creating .venv..."
    py -m venv .venv
}

$Python = Join-Path $RepoRoot ".venv\Scripts\python.exe"
if (-not (Test-Path $Python)) {
    throw "Virtual-environment Python was not found at $Python"
}

& $Python -m pip install --upgrade pip

if ($CacheDependencies) {
    New-Item -ItemType Directory -Force -Path "vendor" | Out-Null
    Write-Host "Downloading a LOCAL dependency cache into vendor/..."
    & $Python -m pip download -r requirements.txt -d vendor
    Write-Host "Dependency cache created. Do not commit Garmin SDK wheel/source archives to a public repository."
}

if ($Offline) {
    Write-Host "Installing dependencies from local vendor/ cache..."
    & $Python -m pip install --no-index --find-links vendor -r requirements.txt
} else {
    Write-Host "Installing dependencies from the configured Python package index..."
    & $Python -m pip install -r requirements.txt
}

Write-Host ""
Write-Host "Setup complete."
Write-Host "Python: $Python"
Write-Host "Run tests with: .\run_tests.ps1"
