"""
PyInstaller entry point for the backend sidecar.

Usage: sidecar.exe <port>
  Reads port from argv[1] (default 8765).
  All path env vars (FFMPEG_DIR, PLAYWRIGHT_BROWSERS_PATH, ASSETS_DIR,
  APP_TEMP_DIR, APP_LOG_DIR) are set by Electron sidecar.ts before spawn.
"""
import sys
import multiprocessing

# Required on Windows for PyInstaller frozen executables with uvicorn workers.
multiprocessing.freeze_support()

if __name__ == "__main__":
    port = int(sys.argv[1]) if len(sys.argv) > 1 else 8765

    import uvicorn
    uvicorn.run(
        "app.main:app",
        host="127.0.0.1",
        port=port,
        log_level="info",
    )
