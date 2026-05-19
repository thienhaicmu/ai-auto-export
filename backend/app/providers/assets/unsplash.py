"""
Unsplash photo search adapter.

API docs: https://unsplash.com/documentation
Auth:     Authorization: Client-ID <ACCESS_KEY>  (header)
Env:      UNSPLASH_ACCESS_KEY

Returns portrait photos for 9:16 short-form video.
"""
from __future__ import annotations

import logging

import httpx

from app.providers.assets.base import AssetCandidate

log = logging.getLogger(__name__)

_BASE = "https://api.unsplash.com"
_TIMEOUT = 10.0


class UnsplashProvider:
    def __init__(self, access_key: str) -> None:
        self._headers = {"Authorization": f"Client-ID {access_key}"}

    async def search(self, query: str, per_page: int = 10) -> list[AssetCandidate]:
        params = {
            "query": query,
            "per_page": min(per_page, 30),
            "orientation": "portrait",
        }
        try:
            async with httpx.AsyncClient(timeout=_TIMEOUT) as client:
                r = await client.get(
                    f"{_BASE}/search/photos",
                    headers=self._headers,
                    params=params,
                )
                r.raise_for_status()
                data = r.json()
        except Exception as exc:
            log.warning("Unsplash search failed (%s): %s", type(exc).__name__, exc)
            return []

        candidates: list[AssetCandidate] = []
        for photo in data.get("results", []):
            urls = photo.get("urls", {})
            url = urls.get("regular") or urls.get("full") or ""
            thumb = urls.get("small") or urls.get("thumb") or url
            if not url:
                continue
            w = photo.get("width", 0)
            h = photo.get("height", 0)
            desc = photo.get("alt_description") or photo.get("description") or ""
            candidates.append(AssetCandidate(
                url=url,
                thumb_url=thumb,
                width=w,
                height=h,
                description=desc,
                source="unsplash",
            ))

        log.debug("Unsplash: %d candidates for %r", len(candidates), query)
        return candidates
