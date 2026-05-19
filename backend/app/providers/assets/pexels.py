"""
Pexels photo search adapter.

API docs: https://www.pexels.com/api/documentation/
Auth:     Authorization: <API_KEY>  (header)
Env:      PEXELS_API_KEY

Returns portrait-oriented photos sized for 9:16 vertical video.
"""
from __future__ import annotations

import logging

import httpx

from app.providers.assets.base import AssetCandidate

log = logging.getLogger(__name__)

_BASE = "https://api.pexels.com/v1"
_TIMEOUT = 10.0


class PexelsProvider:
    def __init__(self, api_key: str) -> None:
        self._headers = {"Authorization": api_key}

    async def search(self, query: str, per_page: int = 10) -> list[AssetCandidate]:
        params = {
            "query": query,
            "per_page": min(per_page, 30),
            "orientation": "portrait",   # 9:16 candidates
        }
        try:
            async with httpx.AsyncClient(timeout=_TIMEOUT) as client:
                r = await client.get(f"{_BASE}/search", headers=self._headers, params=params)
                r.raise_for_status()
                data = r.json()
        except Exception as exc:
            log.warning("Pexels search failed (%s): %s", type(exc).__name__, exc)
            return []

        candidates: list[AssetCandidate] = []
        for photo in data.get("photos", []):
            src = photo.get("src", {})
            url = src.get("portrait") or src.get("large2x") or src.get("large") or ""
            thumb = src.get("small") or src.get("tiny") or url
            if not url:
                continue
            candidates.append(AssetCandidate(
                url=url,
                thumb_url=thumb,
                width=photo.get("width", 0),
                height=photo.get("height", 0),
                description=photo.get("alt", ""),
                source="pexels",
            ))

        log.debug("Pexels: %d candidates for %r", len(candidates), query)
        return candidates
