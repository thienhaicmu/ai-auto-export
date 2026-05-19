<#
.SYNOPSIS
  Build the Python backend sidecar using PyInstaller.

.DESCRIPTION
  Installs PyInstaller into the active Python environment (if not present),
  then builds backend/sidecar.spec into backend/dist/sidecar/.

  Run from the repository root:
    .\build\build_backend.ps1

.NOTES
  Requires Python 3.11+ with backend dependencies already installed:
    cd backend && pip install -e .
  PyInstaller 6.11+ is required for Python 3.14 support.
#>

Set-StrictMode -Version Latest
$ErrorActionPreference = 'Stop'

$repoRoot  = Split-Path $PSScriptRoot -Parent
$backendDir = Join-Path $repoRoot 'backend'

Write-Host "`n=== Phase 4C: Building Python backend sidecar ===" -ForegroundColor Cyan

# --- 1. Ensure PyInstaller is available ----------------------------------------
Write-Host "`n[1/3] Checking PyInstaller..." -ForegroundColor Yellow

$pyinstallerVer = python -c "import PyInstaller; print(PyInstaller.__version__)" 2>$null
if (-not $pyinstallerVer) {
    Write-Host "  PyInstaller not found — installing..." -ForegroundColor Gray
    python -m pip install "pyinstaller>=6.11" --quiet
    $pyinstallerVer = python -c "import PyInstaller; print(PyInstaller.__version__)"
}
Write-Host "  PyInstaller $pyinstallerVer OK" -ForegroundColor Green

# --- 2. Clean previous build artifacts -----------------------------------------
Write-Host "`n[2/3] Cleaning previous build artifacts..." -ForegroundColor Yellow

$distDir  = Join-Path $backendDir 'dist'
$buildDir = Join-Path $backendDir 'build'   # PyInstaller work dir

if (Test-Path $distDir)  { Remove-Item $distDir  -Recurse -Force }
if (Test-Path $buildDir) { Remove-Item $buildDir -Recurse -Force }

Write-Host "  Cleaned." -ForegroundColor Green

# --- 3. Run PyInstaller ---------------------------------------------------------
Write-Host "`n[3/3] Running PyInstaller..." -ForegroundColor Yellow

Push-Location $backendDir
try {
    python -m PyInstaller sidecar.spec --noconfirm
} finally {
    Pop-Location
}

$sidecarExe = Join-Path $backendDir 'dist\sidecar\sidecar.exe'
if (-not (Test-Path $sidecarExe)) {
    Write-Error "Build failed — sidecar.exe not found at: $sidecarExe"
    exit 1
}

$sizeMB = [math]::Round((Get-Item $sidecarExe).Length / 1MB, 1)
Write-Host "`n=== Backend build complete ===" -ForegroundColor Green
Write-Host "  Output : $sidecarExe  ($sizeMB MB)" -ForegroundColor Green
Write-Host "  Dir    : $(Join-Path $backendDir 'dist\sidecar\')" -ForegroundColor Green
