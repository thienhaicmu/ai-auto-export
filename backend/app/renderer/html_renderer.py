"""
HTML Scene → Playwright frame capture.
Phase 1 stub — full implementation in Phase 2.

Contract:
  - Each scene is a self-contained HTML page under backend/app/templates/<style>/
  - Props injected via window.__SCENE__ before page load
  - Template signals ready via window.__SCENE_READY__ = true
  - Frames captured by stepping CSS animation currentTime deterministically
  - Frames saved as PNG to temp/<job_id>/<variant_id>/scene_<i>/frames/
"""
import logging
from pathlib import Path
from app.models.job import Timeline

log = logging.getLogger(__name__)


async def render_html_scenes(timeline: Timeline, temp_dir: Path) -> list[Path]:
    """Capture frames for each scene in the timeline. Returns list of frame dirs."""
    log.info(
        "HTML render stub: job=%s variant=%s scenes=%d",
        timeline.job_id,
        timeline.variant_id,
        len(timeline.scenes),
    )
    # Phase 2: spawn Playwright Chromium, inject props, step CSS animations, capture PNGs
    raise NotImplementedError("HTML renderer not yet implemented — Phase 2")
