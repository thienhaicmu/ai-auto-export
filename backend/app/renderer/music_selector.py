"""
Style-to-music-bed mapping.

Music files live in <project_root>/assets/music/.  If the mapped file does not
exist on disk, the selector returns None and logs a WARNING — the render
pipeline continues without music rather than failing.

Style → filename:
  viral        viral_pulse.mp3
  story        story_ambient.mp3
  explainer    explainer_upbeat.mp3
  documentary  documentary_tension.mp3
  news         news_driving.mp3
  cinematic    cinematic_epic.mp3

All other styles fall back to viral_pulse.mp3.
"""
from __future__ import annotations

import logging
from pathlib import Path

log = logging.getLogger(__name__)

_MUSIC_DIR = Path(__file__).parent.parent.parent.parent / "assets" / "music"

_STYLE_TRACK: dict[str, str] = {
    "viral":        "viral_pulse.mp3",
    "story":        "story_ambient.mp3",
    "explainer":    "explainer_upbeat.mp3",
    "documentary":  "documentary_tension.mp3",
    "news":         "news_driving.mp3",
    "cinematic":    "cinematic_epic.mp3",
}

_DEFAULT_TRACK = "viral_pulse.mp3"


def select_music(style: str, music_dir: Path | None = None) -> Path | None:
    """
    Return the Path to the music bed for *style*, or None if the file is absent.

    Never raises — a missing file is a WARNING, not an error.
    """
    base = music_dir or _MUSIC_DIR
    filename = _STYLE_TRACK.get(style, _DEFAULT_TRACK)
    path = base / filename
    if not path.exists():
        log.warning(
            "Music file not found for style '%s': %s — rendering without music bed",
            style, path,
        )
        return None
    return path
