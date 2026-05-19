# -*- mode: python ; coding: utf-8 -*-
"""
PyInstaller spec for the AI Keyword Video Factory backend sidecar.

Build:
  cd backend
  pyinstaller sidecar.spec

Output: backend/dist/sidecar/ (--onedir)

Requirements:
  pip install pyinstaller>=6.11
  Python 3.11+ (tested with 3.14.3 - use PyInstaller 6.11+)
"""
import sys
from pathlib import Path

block_cipher = None

# Collect the app/ package source
a = Analysis(
    ['sidecar_entry.py'],
    pathex=['.'],
    binaries=[],
    datas=[
        # Bundle HTML templates so html_renderer.py can find them at runtime
        ('app/templates', 'app/templates'),
    ],
    hiddenimports=[
        # FastAPI / Uvicorn internals that PyInstaller misses
        'uvicorn.logging',
        'uvicorn.loops',
        'uvicorn.loops.auto',
        'uvicorn.loops.asyncio',
        'uvicorn.protocols',
        'uvicorn.protocols.http',
        'uvicorn.protocols.http.auto',
        'uvicorn.protocols.http.h11_impl',
        'uvicorn.protocols.http.httptools_impl',
        'uvicorn.protocols.websockets',
        'uvicorn.protocols.websockets.auto',
        'uvicorn.protocols.websockets.websockets_impl',
        'uvicorn.protocols.websockets.wsproto_impl',
        'uvicorn.lifespan',
        'uvicorn.lifespan.on',
        # FastAPI / Starlette routing internals
        'fastapi',
        'fastapi.routing',
        'starlette.routing',
        'starlette.middleware',
        'starlette.middleware.cors',
        # Pydantic
        'pydantic',
        'pydantic.v1',
        'pydantic_settings',
        # Google Generative AI
        'google.genai',
        'google.auth',
        'google.auth.transport',
        # Playwright (Python bindings only — browser binary handled separately)
        'playwright',
        'playwright.async_api',
        'playwright._impl._api_types',
        # Other deps
        'websockets',
        'httpx',
        'unidecode',
        'slugify',
        # Our own packages
        'app',
        'app.main',
        'app.config',
        'app.logging_setup',
        'app.api.health',
        'app.api.render',
        'app.api.ws',
        'app.api.ideas',
        'app.agents.scene_agent',
        'app.agents.asset_agent',
        'app.models.job',
        'app.providers.llm',
        'app.providers.assets',
        'app.renderer.beat_sync',
        'app.renderer.music_selector',
        'app.renderer.ffmpeg_encoder',
        'app.renderer.html_renderer',
        'app.renderer.output_validator',
        'app.renderer.subtitle',
        'app.services.event_bus',
        'app.utils.lang',
        'app.utils.slug',
        # multiprocessing support (freeze_support)
        'multiprocessing.pool',
        'multiprocessing.managers',
    ],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[
        # Dev / test deps — keep binary small
        'pytest',
        'pytest_asyncio',
        'tkinter',
        'matplotlib',
        'numpy',
        'scipy',
        'PIL',
        'IPython',
        'jupyter',
    ],
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    cipher=block_cipher,
    noarchive=False,
)

pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)

exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name='sidecar',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=False,           # UPX can break some packages — disabled for reliability
    console=True,        # Must be True: Electron reads stdout/stderr via pipe
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
)

coll = COLLECT(
    exe,
    a.binaries,
    a.zipfiles,
    a.datas,
    strip=False,
    upx=False,
    upx_exclude=[],
    name='sidecar',
)
