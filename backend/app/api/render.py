"""
Render API — POST /api/render/start triggers the pipeline:
  LLM scene generation (Gemini or mock fallback)
  + real Playwright frame capture
  + real FFmpeg encode.

WS event order (ARCHITECTURE.md §8):
  job.started -> language.detected -> research.completed -> scripts.generated
  -> scenes.generated -> voice.generated -> html.capture.progress (xN)
  -> render.progress (xN) -> video.ready -> job.completed
"""
from __future__ import annotations

import asyncio
import logging
import shutil
import time
import uuid
import wave
from pathlib import Path
from typing import Literal

from fastapi import APIRouter, BackgroundTasks
from pydantic import BaseModel

from app.services.event_bus import event_bus
from app.utils.lang import detect_language
from app.utils.slug import output_filename
from app.providers.llm import get_llm_provider
from app.providers.assets import get_asset_provider
from app.agents.scene_agent import generate_scene_timeline
from app.agents.asset_agent import fetch_scene_assets
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
        wf.writeframes(b"\x00" * n_samples * 4)


# ── Real pipeline ─────────────────────────────────────────────────────────────

async def _run_pipeline(job_id: str, req: RenderRequest) -> None:
    """
    Phase 2B pipeline:
      - Language detection (heuristic)
      - LLM scene generation via Gemini (falls back to mock on error)
      - Playwright HTML frame capture
      - FFmpeg encode with quality mode
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

        # 2. Language detection (heuristic — LLM-backed in Phase 3)
        language = detect_language(req.keyword)
        await emit("language.detected", {"language": language, "confidence": 0.9})

        # 3. Research context (quick emit — LLM research baked into scene prompt)
        await asyncio.sleep(0.15)
        await emit("research.completed", {
            "summary": f"Analyzing '{req.keyword}' for viral content angles",
            "angles": ["controversy", "timeline", "viral hook"],
        })

        # 4. Build output path before LLM call so it's available for fallback
        output_folder = req.output_folder or str(_BACKEND_DIR / "output")
        final_output_path = output_filename(
            keyword=req.keyword,
            style="viral",
            index=1,
            output_dir=output_folder,
        )

        # 5. LLM scene generation (Gemini or mock; fixture fallback on error)
        provider = get_llm_provider()
        log.info(
            "Generating scenes for job %s via provider=%s quality=%s",
            job_id, type(provider).__name__, req.quality_mode,
        )
        timeline = await generate_scene_timeline(
            job_id=job_id,
            keyword=req.keyword,
            language=language,
            duration_seconds=req.duration_seconds,
            output_path=str(final_output_path),
            chosen_idea=None,   # Phase 2B: idea lookup not yet implemented
            provider=provider,
            quality_mode=req.quality_mode,
        )

        # Emit scripts.generated using scene 0 headline as the hook
        hook = timeline.scenes[0].props.headline if timeline.scenes else req.keyword.upper()
        word_count = sum(
            len(s.props.headline.split()) + len(s.props.subhead.split())
            for s in timeline.scenes
        )
        await emit("scripts.generated", {
            "variant_id": variant_id,
            "word_count": word_count,
            "hook": hook,
        })

        vd_summary = [
            {
                "role": s.role,
                "energy": s.props.visual_direction.energy_level if s.props.visual_direction else 3,
                "motion": s.props.visual_direction.motion_intensity if s.props.visual_direction else "medium",
                "layout": s.props.visual_direction.layout_mode if s.props.visual_direction else "center",
            }
            for s in timeline.scenes
        ]
        await emit("scenes.generated", {
            "variant_id": variant_id,
            "scene_count": len(timeline.scenes),
            "visual_direction": vd_summary,
        })

        # 6. Asset fetch — background images for each scene
        asset_provider = get_asset_provider()
        log.info(
            "Fetching scene assets for job %s via %s",
            job_id, type(asset_provider).__name__,
        )
        asset_results = await fetch_scene_assets(
            timeline=timeline,
            job_id=job_id,
            job_temp=job_temp,
            provider=asset_provider,
            keyword=req.keyword,
        )
        assets_found = sum(1 for v in asset_results.values() if v)
        await emit("assets.selected", {
            "variant_id": variant_id,
            "assets_found": assets_found,
            "total_scenes": len(timeline.scenes),
        })

        # 8. Generate silent voice placeholder (edge-tts wired in Phase 3)
        voice_path = job_temp / "voice.wav"
        _generate_silent_wav(voice_path, req.duration_seconds)
        timeline.audio.voice_track = str(voice_path)
        await emit("voice.generated", {
            "variant_id": variant_id,
            "duration_seconds": req.duration_seconds,
        })

        # 9. Generate ASS subtitles
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
        shutil.rmtree(job_temp, ignore_errors=True)
        log.debug("Cleaned up temp dir: %s", job_temp)


# ── Routes ────────────────────────────────────────────────────────────────────

@router.post("/render/start", response_model=RenderResponse)
async def start_render(
    req: RenderRequest, background_tasks: BackgroundTasks
) -> RenderResponse:
    job_id = f"job_{uuid.uuid4().hex[:8]}"
    log.info(
        "Render job %s: keyword='%s' dur=%ds quality=%s",
        job_id, req.keyword, req.duration_seconds, req.quality_mode,
    )
    background_tasks.add_task(_run_pipeline, job_id, req)
    return RenderResponse(job_id=job_id)


@router.get("/render/jobs/{job_id}", response_model=JobSnapshot)
async def get_job(job_id: str) -> JobSnapshot:
    return JobSnapshot(job_id=job_id, status="running", keyword="")


@router.post("/render/jobs/{job_id}/cancel")
async def cancel_job(job_id: str) -> dict:
    return {"cancelled": True, "job_id": job_id}
