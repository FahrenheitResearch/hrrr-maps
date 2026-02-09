# start_windows.ps1 — wxsection.com Windows startup script
# Usage: cd C:\Users\drew\hrrr-maps; .\start_windows.ps1

$ErrorActionPreference = "Stop"
Set-Location $PSScriptRoot

Write-Host "=== wxsection.com (Windows) ===" -ForegroundColor Cyan

# --- Environment ---
$env:XSECT_GRIB_BACKEND = "auto"
$env:WXSECTION_KEY = "cwtc"
$env:XSECT_CACHE_DIR = "C:\Users\drew\hrrr-maps\cache\xsect"
$env:XSECT_OUTPUTS_DIR = "C:\Users\drew\hrrr-maps\outputs"
$env:XSECT_ARCHIVE_DIR = "E:\hrrr-archive"

$PYTHON = "C:\Users\drew\miniforge3\envs\wxsection\python.exe"
$PORT = 5565

# --- Ensure directories exist ---
New-Item -ItemType Directory -Force -Path $env:XSECT_CACHE_DIR | Out-Null
New-Item -ItemType Directory -Force -Path $env:XSECT_OUTPUTS_DIR | Out-Null
New-Item -ItemType Directory -Force -Path $env:XSECT_ARCHIVE_DIR | Out-Null

# --- Stop existing processes ---
Write-Host "Stopping existing processes..."
Get-Process python -ErrorAction SilentlyContinue | Where-Object {
    $_.Path -eq $PYTHON
} | Stop-Process -Force -ErrorAction SilentlyContinue
Start-Sleep -Seconds 2

# --- Start auto-update ---
Write-Host "Starting auto-update (HRRR+GFS+RRFS)..."
$autoUpdate = Start-Process -FilePath $PYTHON -ArgumentList @(
    "-u", "tools\auto_update.py",
    "--interval", "2",
    "--models", "hrrr,gfs,rrfs",
    "--hrrr-slots", "3",
    "--gfs-slots", "2",
    "--rrfs-slots", "1"
) -PassThru -NoNewWindow -RedirectStandardOutput "$env:TEMP\wxsection_auto_update.log" -RedirectStandardError "$env:TEMP\wxsection_auto_update_err.log"
Write-Host "  Auto-update PID: $($autoUpdate.Id)"

# --- Start dashboard ---
Write-Host "Starting dashboard on port $PORT..."
$dashboard = Start-Process -FilePath $PYTHON -ArgumentList @(
    "-u", "tools\unified_dashboard.py",
    "--port", "$PORT",
    "--models", "hrrr,gfs,rrfs",
    "--grib-workers", "4"
) -PassThru -NoNewWindow -RedirectStandardOutput "$env:TEMP\wxsection_dashboard.log" -RedirectStandardError "$env:TEMP\wxsection_dashboard_err.log"
Write-Host "  Dashboard PID: $($dashboard.Id)"

Start-Sleep -Seconds 5

# --- Status ---
Write-Host ""
Write-Host "=== Status ===" -ForegroundColor Green
Write-Host "Dashboard:   http://localhost:$PORT"
Write-Host "Auto-update: PID $($autoUpdate.Id)"
Write-Host ""
Write-Host "Storage layout:"
Write-Host "  NVMe cache:    $env:XSECT_CACHE_DIR"
Write-Host "  GRIB outputs:  $env:XSECT_OUTPUTS_DIR"
Write-Host "  Archive GRIBs: $env:XSECT_ARCHIVE_DIR"
Write-Host ""
Write-Host "Logs:"
Write-Host "  Dashboard:   $env:TEMP\wxsection_dashboard.log"
Write-Host "  Auto-update: $env:TEMP\wxsection_auto_update.log"
Write-Host ""

# Quick health check
try {
    $response = Invoke-RestMethod -Uri "http://localhost:$PORT/api/status" -TimeoutSec 10
    Write-Host "Dashboard: RESPONDING" -ForegroundColor Green
} catch {
    Write-Host "Dashboard: starting up (check log in a few seconds)" -ForegroundColor Yellow
}
