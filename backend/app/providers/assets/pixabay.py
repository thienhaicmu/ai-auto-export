"""
Pixabay photo search adapter.

API docs: https://pixabay.com/api/docs/
Auth:     key= query param
Env:      PIXABAY_API_KEY

Returns vertical/portrait images for 9:16 short-form video.
"""
from __future__ import annotations

import logging

import httpx

from app.providers.assets.base import AssetCandidate

log = logging.getLogger(__name__)

_BASE = "https://pixabay.com/api/"
_TIMEOUT = 10.0


class PixabayProvider:
    def __init__(self, api_key: str) -> None:
        self._key = api_key

    async def search(self, query: str, per_page: int = 10) -> list[AssetCandidate]:
        params = {
            "key": self._key,
            "q": query,
            "image_type": "photo",
            "orientation": "vertical",
            "per_page": min(per_page, 200),
            "safesearch": "true",
        }
        try:
            async with httpx.AsyncClient(timeout=_TIMEOUT) as client:
                r = await client.get(_BASE, params=params)
                r.raise_for_status()
                data = r.json()
        except Exception as exc:
            log.warning("Pixabay search failed (%s): %s", type(exc).__name__, exc)
            return []

        candidates: list[AssetCandidate] = []
        for hit in data.get("hits", []):
            url = hit.get("largeImageURL") or hit.get("webformatURL", "")
            thumb = hit.get("previewURL") or hit.get("webformatURL", "") or url
            if not url:
                continue
            candidates.append(AssetCandidate(
                url=url,
                thumb_url=thumb,
                width=hit.get("imageWidth", hit.get("webformatWidth", 0)),
                height=hit.get("imageHeight", hit.get("webformatHeight", 0)),
                description=hit.get("tags", ""),
                source="pixabay",
            ))

        log.debug("Pixabay: %d candidates for %r", len(candidates), query)
        return candidates
