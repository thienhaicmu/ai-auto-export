"""
Filesystem-safe output filename slugifier.
Handles: Latin, Vietnamese (diacritics), CJK (romanized), mixed.

Rules (from ARCHITECTURE.md §7):
  1. Unicode NFKD → strip combining marks (Vietnamese diacritics removed)
  2. CJK / non-Latin: try unidecode for romanization; fallback to lang-<sha1[:8]>
  3. Lowercase, whitespace → underscore, strip outside [a-z0-9_-], collapse _, max 40 chars
  4. If file exists → suffix with timestamp. Never overwrite.

Examples:
  karen            → karen
  tổng thống biden → tong_thong_biden
  韓国大統領         → hangug-daetonglyeong  (unidecode)
"""
import hashlib
import unicodedata
from pathlib import Path

try:
    from unidecode import unidecode as _unidecode
    HAS_UNIDECODE = True
except ImportError:
    HAS_UNIDECODE = False

import re


def slugify(text: str, max_len: int = 40) -> str:
    """Convert arbitrary unicode text to a filesystem-safe ASCII slug."""
    # Step 1: NFKD decompose → strip combining marks
    normalized = unicodedata.normalize("NFKD", text)
    stripped = "".join(c for c in normalized if not unicodedata.combining(c))

    # Step 2: romanize remaining non-ASCII via unidecode
    if HAS_UNIDECODE:
        romanized = _unidecode(stripped).strip()
    else:
        # fallback: sha1-based stable identifier for non-ASCII content
        sha = hashlib.sha1(text.encode()).hexdigest()[:8]
        romanized = stripped if stripped.isascii() else f"kw-{sha}"

    # Step 3: normalize to clean slug
    result = romanized.lower()
    result = re.sub(r"[\s\-]+", "_", result)         # spaces/hyphens → underscore
    result = re.sub(r"[^a-z0-9_]", "", result)        # strip illegal chars
    result = re.sub(r"_+", "_", result)               # collapse multiple underscores
    result = result.strip("_")
    result = result[:max_len]

    return result or "video"


def output_filename(keyword: str, style: str, index: int, output_dir: str) -> Path:
    """
    Build output path: <output_dir>/<slug>_<style>_<NN>.mp4
    Never overwrites an existing file — appends timestamp suffix.
    """
    import time

    slug = slugify(keyword)
    nn = str(index).zfill(2)
    base = Path(output_dir) / f"{slug}_{style}_{nn}.mp4"

    if not base.exists():
        return base

    # Suffix with unix timestamp to avoid collision
    ts = int(time.time())
    return Path(output_dir) / f"{slug}_{style}_{nn}_{ts}.mp4"
