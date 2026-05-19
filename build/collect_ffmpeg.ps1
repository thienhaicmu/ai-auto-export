<#
.SYNOPSIS
  Collect ffmpeg.exe and ffprobe.exe into build/ffmpeg/.

.DESCRIPTION
  Searches for ffmpeg/ffprobe in these locations (in order):
    1. $env:FFMPEG_BIN_DIR    — override via environment variable
    2. WinGet-installed path  — %LOCALAPPDATA%\Microsoft\WinGet\Packages\Gyan.FFmpeg*
    3. Chocolatey             — C:\ProgramData\chocolatey\bin\
    4. PATH                   — shutil.which equivalent (where.exe)

  Copies both binaries to <repo_root>/build/ffmpeg/.

  Run from the repository root:
    .\build\collect_ffmpeg.ps1

.NOTES
  FFmpeg version 6+ recommended for AV1/H.265 support.
  Only ffmpeg.exe and ffprobe.exe are copied — not the full share/doc tree.
#>

Set-StrictMode -Version Latest
$ErrorActionPreference = 'Stop'

$repoRoot  = Split-Path $PSScriptRoot -Parent
$outputDir = Join-Path $repoRoot 'build\ffmpeg'

Write-Host "`n=== Phase 4C: Collecting FFmpeg binaries ===" -ForegroundColor Cyan

# --- Locate ffmpeg.exe ----------------------------------------------------------

function Find-Binary([string]$name) {
    # 1. Explicit override
    if ($env:FFMPEG_BIN_DIR) {
        $p = Join-Path $env:FFMPEG_BIN_DIR $name
        if (Test-Path $p) { return $p }
    }

    # 2. WinGet packages (Gyan.FFmpeg or BtbN.FFmpeg-Builds)
    $wingetBase = Join-Path $env:LOCALAPPDATA 'Microsoft\WinGet\Packages'
    if (Test-Path $wingetBase) {
        $found = Get-ChildItem $wingetBase -Filter $name -Recurse -ErrorAction SilentlyContinue |
                 Select-Object -First 1
        if ($found) { return $found.FullName }
    }

    # 3. Chocolatey
    $choco = "C:\ProgramData\chocolatey\bin\$name"
    if (Test-Path $choco) { return $choco }

    # 4. PATH
    $fromPath = (Get-Command $name -ErrorAction SilentlyContinue)?.Source
    if ($fromPath) { return $fromPath }

    return $null
}

$ffmpegSrc  = Find-Binary 'ffmpeg.exe'
$ffprobeSrc = Find-Binary 'ffprobe.exe'

if (-not $ffmpegSrc) {
    Write-Error @"
ffmpeg.exe not found.
Install FFmpeg via WinGet:   winget install Gyan.FFmpeg
Or set FFMPEG_BIN_DIR to the directory containing ffmpeg.exe.
"@
    exit 1
}

if (-not $ffprobeSrc) {
    Write-Warning "ffprobe.exe not found — output QA checks will be skipped at runtime."
}

Write-Host "  ffmpeg  : $ffmpegSrc" -ForegroundColor Green
if ($ffprobeSrc) {
    Write-Host "  ffprobe : $ffprobeSrc" -ForegroundColor Green
}

# --- Copy to output directory ---------------------------------------------------

if (-not (Test-Path $outputDir)) {
    New-Item -ItemType Directory -Path $outputDir -Force | Out-Null
}

Copy-Item $ffmpegSrc -Destination (Join-Path $outputDir 'ffmpeg.exe') -Force
if ($ffprobeSrc) {
    Copy-Item $ffprobeSrc -Destination (Join-Path $outputDir 'ffprobe.exe') -Force
}

Write-Host "`n=== FFmpeg collection complete ===" -ForegroundColor Green
Write-Host "  Output dir: $outputDir" -ForegroundColor Green
Get-ChildItem $outputDir | ForEach-Object {
    $mb = [math]::Round($_.Length / 1MB, 1)
    Write-Host "    $($_.Name)  ($mb MB)" -ForegroundColor Gray
}
