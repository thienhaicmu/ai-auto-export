"""
Render API — POST /api/render/start triggers the Phase 1.5 pipeline:
  mock LLM (research/scripts) + real Playwright frame capture + real FFmpeg encode.

WS event order (ARCHITECTURE.md §8):
  job.started → language.detected → research.completed → scripts.generated
  → scenes.generated → voice.generated → html.capture.progress (×N)
  → render.progress (×N) → video.ready → job.completed
"""
from __future__ import annotations

import asyncio
import logging
import shutil
import time
import uuid
import wave
from pathlib import Path
from typing import Awaitable, Callable, Literal

from fastapi import APIRouter, BackgroundTasks
from pydantic import BaseModel

from app.services.event_bus import event_bus
from app.utils.lang import detect_language
from app.utils.slug import output_filename
from app.renderer.timeline import fixture_timeline
from app.renderer.subtitle import generate_ass_subtitles
from app.renderer.html_renderer import render_html_scenes
from app.renderer.ffmpeg_encoder import encode

router = APIRouter()
log = logging.getLogger(__name__)

# Pipeline temp root lives inside the backend directory (cwd when uvicorn runs)
_BACKEND_DIR = Path(__file__).parent.parent.parent   # backend/
_TEMP_ROOT = _BACKEND_DIR / "temp"


# ── Request / Response schemas ───────────────────────────────────────────────

class RenderRequest(BaseModel):
    keyword: str
    format: Literal["1:1", "3:4", "9:16", "16:9"] = "9:16"
    duration_seconds: int = 30
    output_count: int = 1
    styles: list[str] = ["viral"]
    output_folder: str = ""
    chosen_idea_id: str | None = None
    quality_mode: Literal["preview", "final"] = "final"


class RenderResponse(BaseModel):
    job_id: str


class JobSnapshot(BaseModel):
    job_id: str
    status: str
    keyword: str


# ── Silent voice generator ────────────────────────────────────────────────────

def _generate_silent_wav(path: Path, duration_seconds: float, sample_rate: int = 44100) -> None:
    """Write a silent 16-bit stereo WAV file of the given duration."""
    n_samples = int(duration_seconds * sample_rate)
    with wave.open(str(path), "w") as wf:
        wf.setnchannels(2)
        wf.setsampwidth(2)
        wf.setframerate(sample_rate)
        # 2 channels × 2 bytes/sample = 4 bytes per frame, all zero (silence)
        wf.writeframes(b"\x00" * n_samples * 4)


# ── Real pipeline ─────────────────────────────────────────────────────────────

async def _run_pipeline(job_id: str, req: RenderRequest) -> None:
    """
    Phase 1.5 pipeline:
      - Mock AI (research, scripts) — no real LLM calls yet
      - Fixture timeline (5 scenes, viral template)
      - Silent voice placeholder (edge-tts wired in Phase 2)
      - ASS subtitle from scene text
      - Playwright HTML frame capture
      - FFmpeg encode per-scene + concat + audio mix + subtitle burn
    """
    variant_id = "v01"
    job_temp = _TEMP_ROOT / job_id
    job_temp.mkdir(parents=True, exist_ok=True)

    async def emit(event_type: str, data: dict) -> None:
        event = {
            "type": event_type,
            "job_id": job_id,
            "ts": int(time.time()),
            "data": data,
        }
        log.debug("emit %s -> %s  data=%s", job_id, event_type, data)
        await event_bus.publish(job_id, event)

    try:
        # 1. job.started
        await emit("job.started", {
            "output_count": req.output_count,
            "styles": req.styles,
            "language": "en",
            "quality_mode": req.quality_mode,
        })

        # 2. Language detection (heuristic — real LLM in Phase 2)
        language = detect_language(req.keyword)
        await asyncio.sleep(0.3)
        await emit("language.detected", {"language": language, "confidence": 0.95})

        # 3. Research (mock)
        await asyncio.sleep(0.4)
        await emit("research.completed", {
            "summary": f"Research complete for '{req.keyword}'",
            "angles": ["controversy", "timeline", "viral hook"],
        })

        # 4. Script generation (mock)
        await asyncio.sleep(0.3)
        hook = f"{req.keyword.upper()} — the truth they don't want you to know"
        await emit("scripts.generated", {
            "variant_id": variant_id,
            "word_count": 120,
            "hook": hook,
        })

        # 5. Build fixture timeline
        output_folder = req.output_folder or str(_BACKEND_DIR / "output")
        final_output_path = output_filename(
            keyword=req.keyword,
            style="viral",
            index=1,
            output_dir=output_folder,
        )
        timeline = fixture_timeline(
            job_id=job_id,
            keyword=req.keyword,
            output_path=str(final_output_path),
            duration_seconds=req.duration_seconds,
            quality_mode=req.quality_mode,
        )
        await emit("scenes.generated", {
            "variant_id": variant_id,
            "scene_count": len(timeline.scenes),
        })

        # 6. Generate silent voice placeholder
        voice_path = job_temp / "voice.wav"
        _generate_silent_wav(voice_path, req.duration_seconds)
        timeline.audio.voice_track = str(voice_path)
        await emit("voice.generated", {
            "variant_id": variant_id,
            "duration_seconds": req.duration_seconds,
        })

        # 7. Generate ASS subtitles
        sub_path = job_temp / "subs.ass"
        generate_ass_subtitles(timeline, sub_path)
        timeline.subtitles.path = str(sub_path)

        # 8. Playwright frame capture (emits html.capture.progress per scene)
        log.info("Starting HTML frame capture for job %s", job_id)
        frame_dirs = await render_html_scenes(
            timeline=timeline,
            temp_dir=job_temp,
            emit=emit,
            variant_id=variant_id,
        )

        # 9. FFmpeg encode (emits render.progress)
        log.info("Starting FFmpeg encode for job %s -> %s", job_id, final_output_path)
        output_path = await encode(
            timeline=timeline,
            frame_dirs=frame_dirs,
            emit=emit,
            variant_id=variant_id,
        )

        # 10. video.ready
        await emit("video.ready", {
            "variant_id": variant_id,
            "output_path": str(output_path),
        })

        # 11. job.completed
        await emit("job.completed", {"outputs": [str(output_path)]})
        log.info("Job %s complete [%s] -> %s", job_id, req.quality_mode, output_path)

    except Exception as exc:
        log.exception("Pipeline error for job %s", job_id)
        await emit("job.error", {
            "stage": "pipeline",
            "message": str(exc),
            "variant_id": variant_id,
        })
    finally:
        # Clean up scratch files (frame dirs already removed by encoder)
        shutil.rmtree(job_temp, ignore_errors=True)
        log.debug("Cleaned up temp dir: %s", job_temp)


# ── Routes ────────────────────────────────────────────────────────────────────

@router.post("/render/start", response_model=RenderResponse)
async def start_render(
    req: RenderRequest, background_tasks: BackgroundTasks
) -> RenderResponse:
    job_id = f"job_{uuid.uuid4().hex[:8]}"
    log.info("Render job %s: keyword='%s' dur=%ds", job_id, req.keyword, req.duration_seconds)
    background_tasks.add_task(_run_pipeline, job_id, req)
    return RenderResponse(job_id=job_id)


@router.get("/render/jobs/{job_id}", response_model=JobSnapshot)
async def get_job(job_id: str) -> JobSnapshot:
    return JobSnapshot(job_id=job_id, status="running", keyword="")


@router.post("/render/jobs/{job_id}/cancel")
async def cancel_job(job_id: str) -> dict:
    return {"cancelled": True, "job_id": job_id}
