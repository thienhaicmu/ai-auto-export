<#
.SYNOPSIS
  Collect the Playwright Chromium browser into build/chromium/.

.DESCRIPTION
  Playwright stores Chromium under:
    %LOCALAPPDATA%\ms-playwright\chromium-XXXX\chrome-win64\

  This script copies the entire chromium-XXXX directory into build/chromium/
  so that electron-builder can bundle it as an extraResource.

  At runtime, Electron sets PLAYWRIGHT_BROWSERS_PATH=resources/chromium
  before spawning the backend, and Playwright discovers the browser
  automatically without any code changes.

  Run from the repository root:
    .\build\collect_chromium.ps1

.NOTES
  Run  python -m playwright install chromium  in the backend venv first
  if Chromium has not been downloaded yet.
#>

Set-StrictMode -Version Latest
$ErrorActionPreference = 'Stop'

$repoRoot  = Split-Path $PSScriptRoot -Parent
$outputDir = Join-Path $repoRoot 'build\chromium'

Write-Host "`n=== Phase 4C: Collecting Playwright Chromium ===" -ForegroundColor Cyan

# --- Locate Playwright Chromium dir --------------------------------------------

function Find-PlaywrightChromium {
    # Check PLAYWRIGHT_BROWSERS_PATH override first
    if ($env:PLAYWRIGHT_BROWSERS_PATH -and (Test-Path $env:PLAYWRIGHT_BROWSERS_PATH)) {
        $dir = Get-ChildItem $env:PLAYWRIGHT_BROWSERS_PATH -Directory -Filter 'chromium-*' |
               Sort-Object Name -Descending | Select-Object -First 1
        if ($dir) { return $dir.FullName }
    }

    # Default ms-playwright location
    $msBase = Join-Path $env:LOCALAPPDATA 'ms-playwright'
    if (Test-Path $msBase) {
        $dir = Get-ChildItem $msBase -Directory -Filter 'chromium-*' |
               Sort-Object Name -Descending | Select-Object -First 1
        if ($dir) { return $dir.FullName }
    }

    return $null
}

$chromiumDir = Find-PlaywrightChromium
if (-not $chromiumDir) {
    Write-Error @"
Playwright Chromium not found.
Install it with:
  cd backend
  python -m playwright install chromium
Then re-run this script.
"@
    exit 1
}

$dirName = Split-Path $chromiumDir -Leaf   # e.g. chromium-1217
Write-Host "  Source: $chromiumDir" -ForegroundColor Green
Write-Host "  Dir   : $dirName" -ForegroundColor Green

# --- Copy to output directory ---------------------------------------------------

$destDir = Join-Path $outputDir $dirName

if (Test-Path $outputDir) {
    Write-Host "  Removing old build/chromium/ ..." -ForegroundColor Gray
    Remove-Item $outputDir -Recurse -Force
}
New-Item -ItemType Directory -Path $outputDir -Force | Out-Null

Write-Host "  Copying Chromium (this may take a minute)..." -ForegroundColor Yellow
Copy-Item $chromiumDir -Destination $destDir -Recurse -Force

$sizeGB = [math]::Round(
    (Get-ChildItem $outputDir -Recurse -File | Measure-Object -Property Length -Sum).Sum / 1GB,
    2
)

Write-Host "`n=== Chromium collection complete ===" -ForegroundColor Green
Write-Host "  Output dir : $outputDir" -ForegroundColor Green
Write-Host "  Total size : ~$sizeGB GB" -ForegroundColor Green
Write-Host "  Electron will bundle this under resources/chromium/$dirName/" -ForegroundColor Gray
