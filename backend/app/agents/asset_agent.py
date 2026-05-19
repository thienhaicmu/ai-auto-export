"""
Asset agent — fetches, scores, and caches one background image per scene.

Flow per scene:
  1. Build search query from keyword + scene visual_keywords
  2. Call asset provider.search()
  3. Score all candidates (aspect ratio, resolution, keyword match)
  4. If best score >= SCORE_THRESHOLD: download image to temp/assets/
  5. Return http://local/temp/{job_id}/assets/scene_N_bg.jpg URL
     (None signals "use gradient background — no image")

All failures are soft: on any error the scene gets None (gradient fallback).
Asset files are cleaned up with the rest of job_temp after render.
"""
from __future__ import annotations

import asyncio
import logging
from pathlib import Path

import httpx

from app.models.job import Timeline
from app.providers.assets.base import AssetCandidate, AssetProvider, score_candidate, SCORE_THRESHOLD

log = logging.getLogger(__name__)

_DOWNLOAD_TIMEOUT = 12.0   # seconds per image download
_MAX_DOWNLOAD_BYTES = 8 * 1024 * 1024   # 8 MB hard cap per image


def _build_query(keyword: str, visual_keywords: list[str]) -> str:
    """Combine keyword with top visual keywords for the search query."""
    kw_words = keyword.strip().split()[:3]          # max 3 words from keyword
    vk_words = [v for v in visual_keywords if v not in kw_words][:3]  # top 3 visual kw
    parts = kw_words + vk_words
    return " ".join(parts)


async def _download(url: str, dest: Path) -> bool:
    """Download *url* to *dest*. Returns True on success."""
    try:
        async with httpx.AsyncClient(timeout=_DOWNLOAD_TIMEOUT, follow_redirects=True) as client:
            async with client.stream("GET", url) as r:
                r.raise_for_status()
                total = 0
                chunks: list[bytes] = []
                async for chunk in r.aiter_bytes(chunk_size=65536):
                    total += len(chunk)
                    if total > _MAX_DOWNLOAD_BYTES:
                        log.warning("Asset download aborted: too large (>%d B) for %s", _MAX_DOWNLOAD_BYTES, url)
                        return False
                    chunks.append(chunk)
        dest.write_bytes(b"".join(chunks))
        return True
    except Exception as exc:
        log.warning("Asset download failed (%s): %s", type(exc).__name__, exc)
        return False


async def _fetch_one(
    scene_index: int,
    keyword: str,
    visual_keywords: list[str],
    provider: AssetProvider,
    assets_dir: Path,
    target_width: int,
    target_height: int,
    preview_mode: bool,
) -> str | None:
    """
    Fetch and cache one background image for a scene.

    Returns:
        http://local/temp/{job_id}/assets/scene_NN_bg.jpg  — on success
        None  — on failure or score too low (use gradient background)
    """
    query = _build_query(keyword, visual_keywords)

    try:
        candidates = await provider.search(query, per_page=15)
    except Exception as exc:
        log.warning("Asset search error (scene %d): %s", scene_index, exc)
        return None

    if not candidates:
        log.debug("No asset candidates for scene %d (query=%r)", scene_index, query)
        return None

    # Score all and pick the best
    scored = sorted(
        candidates,
        key=lambda c: score_candidate(c, visual_keywords, target_width, target_height),
        reverse=True,
    )
    best = scored[0]
    best_score = score_candidate(best, visual_keywords, target_width, target_height)

    if best_score < SCORE_THRESHOLD:
        log.debug(
            "Scene %d: best asset score %.2f < %.2f (query=%r) — gradient fallback",
            scene_index, best_score, SCORE_THRESHOLD, query,
        )
        return None

    # Download — use thumbnail for preview mode (smaller, faster)
    download_url = best.thumb_url if (preview_mode and best.thumb_url) else best.url
    dest = assets_dir / f"scene_{scene_index:02d}_bg.jpg"

    ok = await _download(download_url, dest)
    if not ok:
        return None

    log.info(
        "Scene %d: asset fetched (score=%.2f src=%s query=%r)",
        scene_index, best_score, best.source, query,
    )
    return dest.name  # just the filename — caller constructs the full URL


async def fetch_scene_assets(
    timeline: Timeline,
    job_id: str,
    job_temp: Path,
    provider: AssetProvider,
    keyword: str,
) -> dict[int, str | None]:
    """
    Fetch one background image per scene in *timeline* (sequentially — no flood).

    Returns a dict mapping scene_index → http://local/... URL (or None).
    Also mutates timeline.scenes[i].props.background_image in place.
    """
    preview_mode = timeline.quality_mode == "preview"
    target_w, target_h = timeline.resolution

    assets_dir = job_temp / "assets"
    assets_dir.mkdir(exist_ok=True)

    results: dict[int, str | None] = {}

    for scene in timeline.scenes:
        # Visual keywords come from scene.props or we fall back to the keyword
        vk: list[str] = getattr(scene.props, "visual_keywords", None) or [keyword]

        filename = await _fetch_one(
            scene_index=scene.index,
            keyword=keyword,
            visual_keywords=vk,
            provider=provider,
            assets_dir=assets_dir,
            target_width=target_w,
            target_height=target_h,
            preview_mode=preview_mode,
        )

        if filename:
            # Construct http://local/temp/{job_id}/assets/{filename}
            url = f"http://local/temp/{job_id}/assets/{filename}"
            scene.props.background_image = url
            results[scene.index] = url
        else:
            scene.props.background_image = None
            results[scene.index] = None

        # Small pause between requests — don't flood the API
        await asyncio.sleep(0.1)

    found = sum(1 for v in results.values() if v)
    log.info(
        "Asset fetch complete: %d/%d scenes have background images",
        found, len(timeline.scenes),
    )
    return results
