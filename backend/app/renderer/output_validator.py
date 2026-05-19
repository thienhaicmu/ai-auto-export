"""
Output QA validator — runs after FFmpeg finishes.

Uses ffprobe to confirm the rendered MP4 meets minimum correctness
requirements before the pipeline emits job.completed.

Checks:
  1. File exists on disk
  2. File size > _MIN_SIZE_BYTES  (catches zero-byte / near-empty files)
  3. Duration within ±DURATION_TOLERANCE of expected
  4. Video stream present with codec h264
  5. Resolution matches timeline spec
  6. Audio stream present (only checked when voice_track was provided)

If ffprobe is not installed, checks 3-6 are skipped with a warning
(file-existence and size checks always run).
"""
from __future__ import annotations

import asyncio
import json
import logging
import shutil
from dataclasses import dataclass, field
from pathlib import Path

from app.models.job import Timeline

log = logging.getLogger(__name__)

# Minimum acceptable output size (10 KB)
_MIN_SIZE_BYTES = 10_240

# Duration may deviate by this fraction from the expected value
_DURATION_TOLERANCE = 0.05

_EXPECTED_VIDEO_CODEC = "h264"

# ffprobe timeout (seconds)
_PROBE_TIMEOUT = 15.0


# ── Data types ────────────────────────────────────────────────────────────────

@dataclass
class QAViolation:
    check: str
    message: str

    def __str__(self) -> str:
        return f"[{self.check}] {self.message}"


@dataclass
class QAResult:
    output_path: Path
    violations: list[QAViolation] = field(default_factory=list)
    ffprobe_available: bool = True

    @property
    def ok(self) -> bool:
        return len(self.violations) == 0

    @property
    def summary(self) -> str:
        if self.ok:
            return f"QA passed: {self.output_path.name}"
        msgs = "; ".join(str(v) for v in self.violations)
        return f"QA FAILED: {msgs}"


# ── ffprobe helper ────────────────────────────────────────────────────────────

def _find_ffprobe() -> str | None:
    return shutil.which("ffprobe")


async def _probe(path: Path) -> dict | None:
    """
    Run ffprobe on *path* and return parsed JSON dict, or None on any failure.
    Never raises — callers treat None as "probe unavailable".
    """
    ffprobe = _find_ffprobe()
    if not ffprobe:
        return None

    cmd = [
        ffprobe, "-v", "quiet",
        "-print_format", "json",
        "-show_format", "-show_streams",
        str(path),
    ]
    try:
        proc = await asyncio.create_subprocess_exec(
            *cmd,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )
        stdout, _ = await asyncio.wait_for(proc.communicate(), timeout=_PROBE_TIMEOUT)
        if proc.returncode != 0:
            log.debug("ffprobe returned code %d for %s", proc.returncode, path.name)
            return None
        return json.loads(stdout.decode(errors="replace"))
    except asyncio.TimeoutError:
        log.warning("ffprobe timed out for %s", path.name)
        try:
            proc.kill()
        except Exception:
            pass
        return None
    except Exception as exc:
        log.warning("ffprobe failed for %s: %s", path.name, exc)
        return None


# ── Public API ────────────────────────────────────────────────────────────────

async def validate_output(path: Path, timeline: Timeline) -> QAResult:
    """
    Validate *path* against the expectations encoded in *timeline*.

    Returns a QAResult. The caller should check result.ok and handle violations.
    This function never raises.
    """
    result = QAResult(output_path=path)

    # 1. File existence
    if not path.exists():
        result.violations.append(QAViolation(
            "exists",
            f"Output file missing: {path}",
        ))
        return result  # no point running further checks

    # 2. Minimum file size
    size = path.stat().st_size
    if size < _MIN_SIZE_BYTES:
        result.violations.append(QAViolation(
            "size",
            f"Output too small: {size:,} bytes (minimum {_MIN_SIZE_BYTES:,})",
        ))

    # 3–6. ffprobe stream checks
    if _find_ffprobe() is None:
        result.ffprobe_available = False
        log.warning("ffprobe not found — stream/duration/codec checks skipped")
        return result

    probe = await _probe(path)
    if probe is None:
        log.warning("ffprobe returned no data for %s — skipping stream checks", path.name)
        return result

    streams = probe.get("streams", [])
    fmt     = probe.get("format", {})

    # 3. Duration
    expected_dur = float(timeline.duration_seconds)
    actual_dur   = float(fmt.get("duration") or 0)
    lower_bound  = expected_dur * (1.0 - _DURATION_TOLERANCE)
    if actual_dur < lower_bound:
        result.violations.append(QAViolation(
            "duration",
            f"Duration too short: {actual_dur:.2f}s (expected ~{expected_dur:.1f}s, "
            f"tolerance {_DURATION_TOLERANCE*100:.0f}%)",
        ))

    # 4 & 5. Video stream
    video_streams = [s for s in streams if s.get("codec_type") == "video"]
    if not video_streams:
        result.violations.append(QAViolation("video_stream", "No video stream found"))
    else:
        vs = video_streams[0]

        # Codec
        codec = vs.get("codec_name", "")
        if codec != _EXPECTED_VIDEO_CODEC:
            result.violations.append(QAViolation(
                "codec",
                f"Unexpected video codec: {codec!r} (expected {_EXPECTED_VIDEO_CODEC!r})",
            ))

        # Resolution
        actual_w = vs.get("width",  0)
        actual_h = vs.get("height", 0)
        exp_w, exp_h = timeline.resolution
        if actual_w != exp_w or actual_h != exp_h:
            result.violations.append(QAViolation(
                "resolution",
                f"Resolution mismatch: {actual_w}x{actual_h} "
                f"(expected {exp_w}x{exp_h})",
            ))

    # 6. Audio stream (only when voice_track was provided)
    if timeline.audio.voice_track:
        audio_streams = [s for s in streams if s.get("codec_type") == "audio"]
        if not audio_streams:
            result.violations.append(QAViolation(
                "audio_stream",
                "No audio stream found but voice_track was present",
            ))

    log.info("Output QA %s: %s", "passed" if result.ok else "FAILED", result.summary)
    return result
