import os
import shutil
from pathlib import Path
from fastapi import APIRouter
from pydantic import BaseModel

from app.config import settings

router = APIRouter()


def _ffmpeg_available() -> bool:
    if settings.ffmpeg_dir:
        exe = "ffmpeg.exe" if os.name == "nt" else "ffmpeg"
        if (Path(settings.ffmpeg_dir) / exe).exists():
            return True
    return shutil.which("ffmpeg") is not None


def _chromium_available() -> bool:
    browsers_path = os.environ.get("PLAYWRIGHT_BROWSERS_PATH", "")
    if browsers_path:
        # Playwright stores chromium under chromium-XXXX/chrome-win64/chrome.exe
        p = Path(browsers_path)
        if p.exists():
            for entry in p.iterdir():
                if entry.is_dir() and entry.name.startswith("chromium-"):
                    return True
    return True  # in dev mode, Playwright manages its own browser path


class ProviderStatus(BaseModel):
    llm: str          # "gemini", "mock", etc.
    llm_ready: bool   # True if provider has credentials / no missing deps
    tts: str


class HealthResponse(BaseModel):
    ok: bool
    version: str
    ffmpeg: bool
    chromium: bool
    providers: ProviderStatus


@router.get("/health", response_model=HealthResponse)
async def health() -> HealthResponse:
    # LLM readiness: gemini requires API key; mock is always ready
    llm_name = settings.llm_provider.lower()
    if llm_name == "gemini":
        llm_ready = bool(settings.gemini_api_key)
    else:
        llm_ready = True  # mock never fails

    return HealthResponse(
        ok=True,
        version=settings.version,
        ffmpeg=_ffmpeg_available(),
        chromium=_chromium_available(),
        providers=ProviderStatus(
            llm=llm_name,
            llm_ready=llm_ready,
            tts=settings.tts_provider,
        ),
    )
