# Packaging Guide — AI Keyword Video Factory

Produces a single Windows NSIS installer that works on a clean machine
with no Node.js, Python, FFmpeg, or Playwright pre-installed.

---

## Prerequisites (build machine only)

| Tool | Version | Install |
|------|---------|---------|
| Python | 3.11+ | python.org (added to PATH) |
| Node.js | 18+ | nodejs.org |
| FFmpeg | 6+ | `winget install Gyan.FFmpeg` |
| Playwright Chromium | latest | `cd backend && python -m playwright install chromium` |
| PyInstaller | 6.11+ | auto-installed by `build_backend.ps1` |
| electron-builder | (in devDeps) | `cd apps/desktop && npm install` |

> **Note:** Python 3.14 users need PyInstaller 6.11+. The build script
> installs this automatically.

---

## Quick Start

```powershell
# From the repository root — builds everything in one command:
.\build\package.ps1
```

The NSIS installer will appear in `apps/desktop/release/<version>/`.

---

## Step-by-Step

### 1 — Backend: Python → sidecar.exe

```powershell
.\build\build_backend.ps1
```

- Installs PyInstaller if missing.
- Runs `backend/sidecar.spec` via PyInstaller `--onedir`.
- Output: `backend/dist/sidecar/sidecar.exe` + supporting DLLs/Python runtime.

The `backend/app/templates/` directory is bundled as `datas` in the spec
so `html_renderer.py` can find templates at `_MEIPASS/app/templates/`.

### 2 — FFmpeg: collect binaries

```powershell
.\build\collect_ffmpeg.ps1
```

- Searches: `$env:FFMPEG_BIN_DIR` → WinGet → Chocolatey → PATH.
- Copies `ffmpeg.exe` + `ffprobe.exe` to `build/ffmpeg/`.

Override search path:
```powershell
$env:FFMPEG_BIN_DIR = 'C:\ffmpeg\bin'
.\build\collect_ffmpeg.ps1
```

### 3 — Chromium: collect Playwright browser

```powershell
.\build\collect_chromium.ps1
```

- Finds Playwright Chromium under `%LOCALAPPDATA%\ms-playwright\chromium-XXXX\`.
- Copies the entire `chromium-XXXX/` directory to `build/chromium/`.
- At runtime Electron sets `PLAYWRIGHT_BROWSERS_PATH=resources/chromium`
  before spawning the backend — no code changes needed.

If Chromium is not yet installed:
```powershell
cd backend
python -m playwright install chromium
```

### 4 — Electron: build + package

```powershell
cd apps/desktop
npm run build                            # Vite + TypeScript compile
npx electron-builder --win --x64         # NSIS installer
```

Or use the orchestration script which does steps 1–4 automatically.

---

## Skip Flags (incremental builds)

```powershell
# Rebuild only Electron — skip the slow Python + Chromium steps:
.\build\package.ps1 -SkipBackend -SkipFFmpeg -SkipChromium

# Rebuild backend only:
.\build\build_backend.ps1
.\build\package.ps1 -SkipFFmpeg -SkipChromium
```

---

## Installed Layout

After the NSIS installer runs on the target machine:

```
%ProgramFiles%\AI Keyword Video Factory\
  AI Keyword Video Factory.exe          ← Electron host
  resources/
    backend/sidecar/
      sidecar.exe                       ← PyInstaller bundle entry
      _internal/                        ← Python runtime + packages
    ffmpeg/
      ffmpeg.exe
      ffprobe.exe
    chromium/
      chromium-XXXX/
        chrome-win64/
          chrome.exe                    ← Playwright Chromium
    assets/
      music/                            ← Background music tracks
      fonts/                            ← Fonts for templates
```

Writable runtime files go to the user profile (never Program Files):
```
%AppData%\AI Keyword Video Factory\
  temp/                                 ← Per-job render scratch space
  logs/
    app.log                             ← Backend log (rotated by size)
```

---

## Runtime Path Resolution

Electron `sidecar.ts` sets these env vars before spawning `sidecar.exe`:

| Env var | Value (packaged) | Fallback (dev) |
|---------|-----------------|----------------|
| `FFMPEG_DIR` | `resources/ffmpeg` | PATH lookup |
| `PLAYWRIGHT_BROWSERS_PATH` | `resources/chromium` | `%LOCALAPPDATA%\ms-playwright` |
| `ASSETS_DIR` | `resources/assets` | `../../assets` (repo root) |
| `APP_TEMP_DIR` | `%AppData%/<app>/temp` | `backend/temp` |
| `APP_LOG_DIR` | `%AppData%/<app>/logs` | `backend/logs` |

The backend reads each env var in its respective module and falls back to
the dev-mode relative path when the env var is empty or absent.

---

## Troubleshooting

### "Backend executable not found"
The installer is incomplete. Re-run `.\build\package.ps1` with all steps
enabled, or reinstall the application.

### "ffmpeg not found"
Run `.\build\collect_ffmpeg.ps1` or set `$env:FFMPEG_BIN_DIR`.

### "Playwright Chromium not found" (during build)
```powershell
cd backend
python -m playwright install chromium
.\build\collect_chromium.ps1
```

### Antivirus flags `sidecar.exe`
PyInstaller-built executables are commonly false-positived. Add an AV
exclusion for the install directory, or code-sign the exe with a trusted
certificate (see electron-builder `win.certificateFile` config).

### `ImportError` at runtime (missing Python module)
Add the missing module to `hiddenimports` in `backend/sidecar.spec` and
rebuild the backend.

### Build size too large
`upx` compression is disabled by default (can break some modules).
Enable it in `sidecar.spec` by setting `upx=True` on the `EXE`/`COLLECT`
calls, then test thoroughly before shipping.

---

## Security Notes

- `GEMINI_API_KEY` is **never** bundled in the installer.
  Users set it in `%AppData%\AI Keyword Video Factory\.env` or as a
  system environment variable. The backend reads it from the environment only.
- The key is **never** logged or sent over WebSocket.
- The sidecar binds to `127.0.0.1` only — not reachable from the network.
