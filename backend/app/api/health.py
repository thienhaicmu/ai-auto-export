import shutil
from fastapi import APIRouter
from pydantic import BaseModel

from app.config import settings

router = APIRouter()


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
        ffmpeg=shutil.which("ffmpeg") is not None,
        chromium=True,  # lazy-install deferred
        providers=ProviderStatus(
            llm=llm_name,
            llm_ready=llm_ready,
            tts=settings.tts_provider,
        ),
    )
