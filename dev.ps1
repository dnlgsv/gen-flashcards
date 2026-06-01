#!/usr/bin/env pwsh
# Start both backend and frontend dev servers for frontend development.
# Usage: .\dev.ps1

$ErrorActionPreference = "Stop"
$root = $PSScriptRoot

Write-Host "Starting backend (port 8000) and frontend (port 3000)..." -ForegroundColor Cyan

$backend = Start-Process -NoNewWindow -PassThru -FilePath "cmd.exe" `
    -ArgumentList "/c", "uv run uvicorn src.api.run:app --host 0.0.0.0 --port 8000 --reload" `
    -WorkingDirectory $root

$frontend = Start-Process -NoNewWindow -PassThru -FilePath "cmd.exe" `
    -ArgumentList "/c", "npm run dev" `
    -WorkingDirectory (Join-Path $root "frontend")

Write-Host ""
Write-Host "  Backend  -> http://localhost:8000" -ForegroundColor Green
Write-Host "  Frontend -> http://localhost:3000" -ForegroundColor Green
Write-Host "  Press Ctrl+C to stop both." -ForegroundColor Yellow
Write-Host ""

try {
    # Wait for either process to exit
    while (!$backend.HasExited -and !$frontend.HasExited) {
        Start-Sleep -Milliseconds 500
    }
} finally {
    # Clean up both processes
    if (!$backend.HasExited) { Stop-Process -Id $backend.Id -Force -ErrorAction SilentlyContinue }
    if (!$frontend.HasExited) { Stop-Process -Id $frontend.Id -Force -ErrorAction SilentlyContinue }
    Write-Host "Dev servers stopped." -ForegroundColor Cyan
}
