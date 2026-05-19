<#
.SYNOPSIS
  Full build + packaging pipeline: Python sidecar + Electron NSIS installer.

.DESCRIPTION
  Orchestrates all Phase 4C build steps in order:
    1. Build Python backend sidecar (PyInstaller)
    2. Collect FFmpeg binaries
    3. Collect Playwright Chromium
    4. Build Electron renderer (Vite)
    5. Package with electron-builder -> release/<version>/

  Run from the repository root:
    .\build\package.ps1

  Skip individual steps with flags:
    .\build\package.ps1 -SkipBackend -SkipChromium

.PARAMETER SkipBackend
  Skip PyInstaller build (use existing backend/dist/sidecar/).

.PARAMETER SkipFFmpeg
  Skip FFmpeg collection (use existing build/ffmpeg/).

.PARAMETER SkipChromium
  Skip Chromium collection (use existing build/chromium/).

.PARAMETER SkipElectron
  Skip Electron build (run electron-builder only).
#>

[CmdletBinding()]
param(
    [switch] $SkipBackend,
    [switch] $SkipFFmpeg,
    [switch] $SkipChromium,
    [switch] $SkipElectron
)

Set-StrictMode -Version Latest
$ErrorActionPreference = 'Stop'

$repoRoot   = Split-Path $PSScriptRoot -Parent
$desktopDir = Join-Path $repoRoot 'apps\desktop'
$buildDir   = $PSScriptRoot

Write-Host "`n================================================" -ForegroundColor Magenta
Write-Host "  AI Keyword Video Factory — Full Package Build" -ForegroundColor Magenta
Write-Host "================================================`n" -ForegroundColor Magenta

$startTime = Get-Date

# ── Step 1: Python backend ─────────────────────────────────────────────────────
if (-not $SkipBackend) {
    Write-Host "STEP 1/5: Building Python backend sidecar..." -ForegroundColor Cyan
    & (Join-Path $buildDir 'build_backend.ps1')
} else {
    Write-Host "STEP 1/5: Skipping backend build." -ForegroundColor Gray
    $sidecarExe = Join-Path $repoRoot 'backend\dist\sidecar\sidecar.exe'
    if (-not (Test-Path $sidecarExe)) {
        Write-Error "backend/dist/sidecar/sidecar.exe not found. Run without -SkipBackend first."
        exit 1
    }
}

# ── Step 2: FFmpeg ─────────────────────────────────────────────────────────────
if (-not $SkipFFmpeg) {
    Write-Host "`nSTEP 2/5: Collecting FFmpeg binaries..." -ForegroundColor Cyan
    & (Join-Path $buildDir 'collect_ffmpeg.ps1')
} else {
    Write-Host "`nSTEP 2/5: Skipping FFmpeg collection." -ForegroundColor Gray
    if (-not (Test-Path (Join-Path $repoRoot 'build\ffmpeg\ffmpeg.exe'))) {
        Write-Error "build/ffmpeg/ffmpeg.exe not found. Run without -SkipFFmpeg first."
        exit 1
    }
}

# ── Step 3: Chromium ───────────────────────────────────────────────────────────
if (-not $SkipChromium) {
    Write-Host "`nSTEP 3/5: Collecting Playwright Chromium..." -ForegroundColor Cyan
    & (Join-Path $buildDir 'collect_chromium.ps1')
} else {
    Write-Host "`nSTEP 3/5: Skipping Chromium collection." -ForegroundColor Gray
    if (-not (Test-Path (Join-Path $repoRoot 'build\chromium'))) {
        Write-Error "build/chromium/ not found. Run without -SkipChromium first."
        exit 1
    }
}

# ── Step 4: Electron renderer (Vite) ──────────────────────────────────────────
if (-not $SkipElectron) {
    Write-Host "`nSTEP 4/5: Building Electron renderer..." -ForegroundColor Cyan
    Push-Location $desktopDir
    try {
        npm run build
    } finally {
        Pop-Location
    }
} else {
    Write-Host "`nSTEP 4/5: Skipping Electron renderer build." -ForegroundColor Gray
}

# ── Step 5: electron-builder ───────────────────────────────────────────────────
Write-Host "`nSTEP 5/5: Packaging with electron-builder..." -ForegroundColor Cyan
Push-Location $desktopDir
try {
    npx electron-builder --win --x64 --config electron-builder.yml
} finally {
    Pop-Location
}

# ── Summary ───────────────────────────────────────────────────────────────────
$elapsed = [math]::Round(((Get-Date) - $startTime).TotalMinutes, 1)
$releaseDir = Join-Path $desktopDir 'release'
$installer  = Get-ChildItem $releaseDir -Filter '*-setup.exe' -Recurse -ErrorAction SilentlyContinue |
              Sort-Object LastWriteTime -Descending | Select-Object -First 1

Write-Host "`n================================================" -ForegroundColor Magenta
Write-Host "  Package build complete ($elapsed min)" -ForegroundColor Green
if ($installer) {
    $sizeMB = [math]::Round($installer.Length / 1MB, 0)
    Write-Host "  Installer: $($installer.FullName)  ($sizeMB MB)" -ForegroundColor Green
}
Write-Host "================================================`n" -ForegroundColor Magenta
