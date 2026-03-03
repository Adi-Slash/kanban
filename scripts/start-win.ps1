$ErrorActionPreference = "Stop"

function Exit-WithMessage {
    param(
        [string]$Message
    )

    Write-Host "ERROR: $Message" -ForegroundColor Red
    exit 1
}

if (-not (Get-Command docker -ErrorAction SilentlyContinue)) {
    Exit-WithMessage "Docker CLI is not installed or not in PATH."
}

cmd /c "docker info >nul 2>&1"
if ($LASTEXITCODE -ne 0) {
    Exit-WithMessage "Docker engine is not running. Start Docker Desktop and retry."
}

cmd /c "docker compose up --build -d"
if ($LASTEXITCODE -ne 0) {
    Exit-WithMessage "Docker compose failed to start the backend container."
}

Write-Host "App started at http://localhost:8000"
