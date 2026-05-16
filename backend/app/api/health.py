import shutil
from fastapi import APIRouter
from pydantic import BaseModel

from app.config import settings

router = APIRouter()


class ProviderStatus(BaseModel):
    llm: str
    tts: str


class HealthResponse(BaseModel):
    ok: bool
    version: str
    ffmpeg: bool
    chromium: bool
    providers: ProviderStatus


@router.get("/health", response_model=HealthResponse)
async def health() -> HealthResponse:
    return HealthResponse(
        ok=True,
        version=settings.version,
        ffmpeg=shutil.which("ffmpeg") is not None,
        chromium=True,  # Phase 1: lazy-install deferred
        providers=ProviderStatus(
            llm=settings.llm_provider,
            tts=settings.tts_provider,
        ),
    )
