"""
Asset provider protocol and shared types.

All asset adapters must implement AssetProvider.
AssetCandidate is the normalized representation returned by every provider.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Protocol, runtime_checkable


@dataclass
class AssetCandidate:
    url: str              # full-resolution download URL
    thumb_url: str        # smaller version — used in preview quality mode
    width: int
    height: int
    description: str      # alt text / tags (used for keyword scoring)
    source: str           # "pexels" | "pixabay" | "unsplash" | "mock"
    score: float = 0.0    # filled in by scoring logic


@runtime_checkable
class AssetProvider(Protocol):
    async def search(self, query: str, per_page: int = 10) -> list[AssetCandidate]: ...


def score_candidate(
    c: AssetCandidate,
    visual_keywords: list[str],
    target_width: int,
    target_height: int,
) -> float:
    """
    Score an asset candidate 0..∞ (higher = better fit).

    Components:
      aspect_ratio   — most important; 9:16 portrait is critical
      resolution     — enough pixels to fill the frame
      keyword_match  — description contains visual search terms
    """
    # Aspect ratio (target is typically 9:16 = 0.5625)
    target_ar = target_width / max(target_height, 1)
    actual_ar = c.width / max(c.height, 1)
    ar_diff = abs(actual_ar - target_ar)
    # 1.0 at perfect match; drops to 0 when diff ≥ 0.25 (e.g. landscape)
    ar_score = max(0.0, 1.0 - ar_diff * 4.0)

    # Resolution — penalty if image is smaller than the target
    res_score = min(1.0, c.width / max(target_width, 1)) * 0.5

    # Keyword match in description / tags
    desc = c.description.lower()
    hits = sum(1 for kw in visual_keywords if kw.lower() in desc)
    kw_score = min(hits * 0.15, 0.45)  # cap so this can't dominate alone

    return ar_score + res_score + kw_score


# Minimum score to use an asset; below this → gradient / text-only background
SCORE_THRESHOLD = 0.35
