"""
HTML Scene → Playwright frame capture.

Architecture (ARCHITECTURE.md §7):
  - One Chromium browser instance per render job.
  - Each scene is a fresh BrowserContext at the target resolution.
  - Props injected via page.add_init_script() before navigation.
  - Template signals ready via window.__SCENE_READY__ = true.
  - Frames captured by stepping CSS Web Animations currentTime deterministically.
  - Frames saved as PNG to temp/<job>/<variant>/scene_<i>/frames/.
  - Progress emitted as html.capture.progress WS events.

Serving strategy: Playwright page.route() intercepts HTTP requests to
http://local/ and maps them to local file paths — no external server needed.

  http://local/templates/<style>/...  →  backend/app/templates/<style>/...
  http://local/assets/...             →  <project_root>/assets/...
  http://local/temp/...               →  <project_root>/temp/...
"""
from __future__ import annotations

import json
import logging
import mimetypes
import shutil
from pathlib import Path
from typing import Awaitable, Callable

from app.models.job import Timeline

log = logging.getLogger(__name__)

# Derive paths relative to this file
_RENDERER_DIR = Path(__file__).parent           # backend/app/renderer/
_BACKEND_APP_DIR = _RENDERER_DIR.parent         # backend/app/
_BACKEND_DIR = _BACKEND_APP_DIR.parent          # backend/
_PROJECT_ROOT = _BACKEND_DIR.parent             # d:\ai-auto-export\

_TEMPLATES_DIR = _BACKEND_APP_DIR / "templates"
_ASSETS_DIR = _PROJECT_ROOT / "assets"
# temp/ lives inside backend/ so that http://local/temp/... maps to the same
# directory used by render.py (backend/temp/{job_id}/...)
_TEMP_ROOT = _BACKEND_DIR / "temp"

# Fake origin used for routing; Playwright intercepts all requests to it
_BASE_URL = "http://local"

# Extra content-type mappings not in Python's mimetypes DB
_EXTRA_TYPES: dict[str, str] = {
    ".ttf": "font/truetype",
    ".otf": "font/opentype",
    ".woff": "font/woff",
    ".woff2": "font/woff2",
}


def _url_to_local(url: str) -> Path | None:
    """Map http://local/<path> to a local filesystem Path, or None if unknown."""
    if not url.startswith(_BASE_URL + "/"):
        return None
    rel = url[len(_BASE_URL) + 1:]  # strip leading 'http://local/'

    if rel.startswith("templates/"):
        return _TEMPLATES_DIR / rel[len("templates/"):]
    if rel.startswith("assets/"):
        return _ASSETS_DIR / rel[len("assets/"):]
    if rel.startswith("temp/"):
        return _TEMP_ROOT / rel[len("temp/"):]
    return None


async def render_html_scenes(
    timeline: Timeline,
    temp_dir: Path,
    emit: Callable[[str, dict], Awaitable[None]],
    variant_id: str,
) -> list[Path]:
    """
    Capture PNG frames for every scene in *timeline*.

    Returns a list of frame directories (one per scene, in scene order).
    Frame dirs live at: temp_dir/scene_<NN>/frames/
    """
    try:
        from playwright.async_api import async_playwright, Route
    except ImportError as exc:
        raise RuntimeError(
            "playwright is not installed. Run: pip install playwright && playwright install chromium"
        ) from exc

    fps = timeline.fps
    width, height = timeline.resolution
    frame_dirs: list[Path] = []

    async def _route_handler(route: Route) -> None:
        local = _url_to_local(route.request.url)
        if local is None or not local.exists():
            log.debug("404 for: %s", route.request.url)
            await route.fulfill(status=404, body=b"Not Found")
            return
        body = local.read_bytes()
        suffix = local.suffix.lower()
        ct = _EXTRA_TYPES.get(suffix) or mimetypes.guess_type(str(local))[0] or "application/octet-stream"
        await route.fulfill(body=body, content_type=ct)

    async with async_playwright() as pw:
        browser = await pw.chromium.launch(
            headless=True,
            args=[
                "--no-sandbox",
                "--disable-setuid-sandbox",
                "--disable-dev-shm-usage",
            ],
        )

        try:
            for scene in timeline.scenes:
                n_frames = max(1, round((scene.end - scene.start) * fps))
                scene_dir = temp_dir / f"scene_{scene.index:02d}"
                frames_dir = scene_dir / "frames"
                frames_dir.mkdir(parents=True, exist_ok=True)

                log.info(
                    "Capturing scene %d/%d: %d frames @ %dx%d (%.2fs–%.2fs)",
                    scene.index + 1,
                    len(timeline.scenes),
                    n_frames,
                    width,
                    height,
                    scene.start,
                    scene.end,
                )

                context = await browser.new_context(
                    viewport={"width": width, "height": height},
                    device_scale_factor=1,
                )
                page = await context.new_page()

                # Intercept all requests to http://local/* and serve local files
                await page.route(f"{_BASE_URL}/**", _route_handler)

                # Inject scene data BEFORE the page loads (add_init_script runs first)
                scene_payload = {
                    "index": scene.index,
                    "start": scene.start,
                    "end": scene.end,
                    "template": scene.template,
                    "role": scene.role,
                    "props": scene.props.model_dump(),
                }
                await page.add_init_script(
                    f"window.__SCENE__ = {json.dumps(scene_payload, ensure_ascii=False)};"
                )

                # Navigate — template URL: http://local/templates/viral/index.html
                template_url = f"{_BASE_URL}/templates/{scene.template}/index.html"
                await page.goto(template_url, wait_until="domcontentloaded", timeout=30_000)

                # Wait for scene.js to signal SCENE_READY
                try:
                    await page.wait_for_function(
                        "() => window.__SCENE_READY__ === true",
                        timeout=15_000,
                    )
                except Exception:
                    log.warning(
                        "Scene %d: __SCENE_READY__ timeout — proceeding anyway",
                        scene.index,
                    )

                # Pause all CSS animations at t=0 before stepping
                await page.evaluate("""() => {
                    document.getAnimations().forEach(a => {
                        a.pause();
                        a.currentTime = 0;
                    });
                }""")

                # Step through every frame deterministically
                for f in range(n_frames):
                    t_ms = (f / fps) * 1000.0

                    # Advance all animations to this exact moment
                    await page.evaluate(
                        f"(t) => {{ document.getAnimations().forEach(a => {{ a.currentTime = t; }}); }}",
                        t_ms,
                    )

                    frame_path = frames_dir / f"{f:04d}.png"
                    await page.screenshot(
                        path=str(frame_path),
                        clip={"x": 0, "y": 0, "width": width, "height": height},
                        type="png",
                    )

                    # Emit progress every 15 frames and on the last frame
                    if f % 15 == 0 or f == n_frames - 1:
                        await emit(
                            "html.capture.progress",
                            {
                                "variant_id": variant_id,
                                "scene_index": scene.index,
                                "frames_done": f + 1,
                                "frames_total": n_frames,
                            },
                        )

                await page.close()
                await context.close()

                frame_dirs.append(frames_dir)
                log.info("Scene %d: %d frames captured -> %s", scene.index, n_frames, frames_dir)

        finally:
            await browser.close()

    return frame_dirs
