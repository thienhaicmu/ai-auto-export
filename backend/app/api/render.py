import asyncio
import logging
import time
import uuid
from typing import Literal

from fastapi import APIRouter, BackgroundTasks
from pydantic import BaseModel

from app.services.event_bus import event_bus

router = APIRouter()
log = logging.getLogger(__name__)


class RenderRequest(BaseModel):
    keyword: str
    format: Literal["1:1", "3:4", "9:16", "16:9"] = "9:16"
    duration_seconds: int = 30
    output_count: int = 1
    styles: list[str] = ["viral"]
    output_folder: str = ""
    chosen_idea_id: str | None = None


class RenderResponse(BaseModel):
    job_id: str


class JobSnapshot(BaseModel):
    job_id: str
    status: str
    keyword: str


# ── Mock pipeline ────────────────────────────────────────────────────────────

async def _run_mock_pipeline(job_id: str, req: RenderRequest) -> None:
    async def emit(event_type: str, data: dict) -> None:
        event = {
            "type": event_type,
            "job_id": job_id,
            "ts": int(time.time()),
            "data": data,
        }
        log.debug("emit %s → %s", job_id, event_type)
        await event_bus.publish(job_id, event)

    try:
        await emit("job.started", {
            "output_count": req.output_count,
            "styles": req.styles,
            "language": "en",
        })
        await asyncio.sleep(0.4)

        await emit("language.detected", {"language": "en", "confidence": 0.98})
        await asyncio.sleep(0.7)

        await emit("research.completed", {
            "summary": f"Research complete for '{req.keyword}'",
            "angles": ["controversy", "timeline", "viral hook"],
        })
        await asyncio.sleep(0.8)

        variant_id = "v01"
        hook = f"{req.keyword.upper()} — the truth they don't want you to know"
        await emit("scripts.generated", {
            "variant_id": variant_id,
            "word_count": 120,
            "hook": hook,
        })
        await asyncio.sleep(0.7)

        await emit("scenes.generated", {"variant_id": variant_id, "scene_count": 5})
        await asyncio.sleep(0.5)

        await emit("voice.generated", {
            "variant_id": variant_id,
            "duration_seconds": req.duration_seconds,
        })

        # simulate per-scene frame capture
        total_frames = req.duration_seconds * 30
        for scene_idx in range(5):
            await asyncio.sleep(0.9)
            frames_done = (scene_idx + 1) * (total_frames // 5)
            await emit("html.capture.progress", {
                "variant_id": variant_id,
                "scene_index": scene_idx,
                "frames_done": frames_done,
                "frames_total": total_frames,
            })

        await asyncio.sleep(0.8)
        slug = req.keyword.lower().replace(" ", "_")[:20]
        output_path = f"{req.output_folder or 'output'}/{slug}_viral_01.mp4"
        await emit("video.ready", {
            "variant_id": variant_id,
            "output_path": output_path,
        })

        await asyncio.sleep(0.1)
        await emit("job.completed", {"outputs": [output_path]})

    except Exception as exc:
        log.error("mock pipeline error for %s: %s", job_id, exc)
        await emit("job.error", {"stage": "pipeline", "message": str(exc)})


# ── Routes ───────────────────────────────────────────────────────────────────

@router.post("/render/start", response_model=RenderResponse)
async def start_render(req: RenderRequest, background_tasks: BackgroundTasks) -> RenderResponse:
    job_id = f"job_{uuid.uuid4().hex[:8]}"
    log.info("Starting mock render job %s for keyword '%s'", job_id, req.keyword)
    background_tasks.add_task(_run_mock_pipeline, job_id, req)
    return RenderResponse(job_id=job_id)


@router.get("/render/jobs/{job_id}", response_model=JobSnapshot)
async def get_job(job_id: str) -> JobSnapshot:
    return JobSnapshot(job_id=job_id, status="running", keyword="")


@router.post("/render/jobs/{job_id}/cancel")
async def cancel_job(job_id: str) -> dict:
    return {"cancelled": True, "job_id": job_id}
