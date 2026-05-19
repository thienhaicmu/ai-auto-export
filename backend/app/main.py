import logging
import os
import shutil
import time
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.config import settings
from app.logging_setup import setup_logging
from app.api import health, ws, render, ideas

log = logging.getLogger(__name__)


def _resolve_temp_root() -> Path:
    # Packaged mode: APP_TEMP_DIR is set by Electron sidecar.ts
    env_val = os.environ.get("APP_TEMP_DIR", "")
    if env_val:
        return Path(env_val)
    return Path(__file__).parent.parent / "temp"   # backend/temp (dev mode)


_TEMP_ROOT = _resolve_temp_root()


def _cleanup_orphaned_temp(temp_root: Path, ttl_hours: int) -> None:
    """
    Delete job temp dirs that are older than ttl_hours.

    Called once on startup to reclaim disk from crashed/incomplete previous runs.
    Never touches the output/ directory.
    """
    if not temp_root.exists():
        return

    cutoff = time.time() - ttl_hours * 3600
    removed = 0
    for child in temp_root.iterdir():
        if not child.is_dir():
            continue
        try:
            mtime = child.stat().st_mtime
        except OSError:
            continue
        if mtime < cutoff:
            shutil.rmtree(child, ignore_errors=True)
            log.info("Cleaned orphaned temp dir (age > %dh): %s", ttl_hours, child.name)
            removed += 1

    if removed:
        log.info("Startup cleanup: removed %d orphaned temp dir(s)", removed)


@asynccontextmanager
async def lifespan(app: FastAPI):
    setup_logging(settings.log_level)
    _cleanup_orphaned_temp(_TEMP_ROOT, settings.temp_cleanup_ttl_hours)
    yield


app = FastAPI(
    title="AI Keyword Video Factory",
    version=settings.version,
    lifespan=lifespan,
    docs_url="/docs",
    redoc_url=None,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:5173",
        "http://localhost:3000",
        "http://127.0.0.1:5173",
        # Electron file:// renderer
        "null",
    ],
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(health.router, prefix="/api", tags=["health"])
app.include_router(render.router, prefix="/api", tags=["render"])
app.include_router(ideas.router, prefix="/api", tags=["ideas"])
app.include_router(ws.router, tags=["ws"])
