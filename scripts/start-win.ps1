$ErrorActionPreference = "Stop"

docker compose up --build -d
Write-Host "App started at http://localhost:8000"
