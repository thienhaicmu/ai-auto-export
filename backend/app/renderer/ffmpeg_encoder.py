"""
FFmpeg encoder: frames + voice + music + subtitles → MP4.
Phase 1 stub — full implementation in Phase 2.

Stages:
  1. Per-scene: ffmpeg -framerate 30 -i frames/%04d.png -c:v libx264 scene_N.mp4
  2. Concat clips.txt → combined video
  3. Mix voice + music, burn subtitles
  4. Atomic move to output_path
"""
import logging
from pathlib import Path
from app.models.job import Timeline

log = logging.getLogger(__name__)


async def encode(timeline: Timeline, frame_dirs: list[Path]) -> Path:
    log.info("FFmpeg encode stub: %s", timeline.output_path)
    # Phase 2: subprocess ffmpeg with full filter_complex
    raise NotImplementedError("FFmpeg encoder not yet implemented — Phase 2")
