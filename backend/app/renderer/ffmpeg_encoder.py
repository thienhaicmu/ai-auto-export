"""
FFmpeg encoder: frames + voice + music + subtitles → final MP4.

Pipeline (ARCHITECTURE.md §7):
  Stage 1 — per-scene: ffmpeg -framerate 30 -i frames/%04d.png … scene_N.mp4
             Delete frame folder immediately after encode to free disk.
  Stage 2 — concat all scene clips via concat demuxer → combined.mp4
  Stage 3 — mix voice + music, burn subtitles → <output_path>
  Stage 4 — clean up intermediate clips

Progress events:
  render.progress  { variant_id, percent, fps, eta_seconds }

ASS path escaping (Windows + FFmpeg libass):
  - Backslashes → forward slashes
  - Drive-letter colon escaped: C:/ → C\:/
"""
from __future__ import annotations

import asyncio
import logging
import shutil
from pathlib import Path
from typing import Awaitable, Callable

from app.models.job import Timeline

log = logging.getLogger(__name__)


def _find_ffmpeg() -> str:
    ffmpeg = shutil.which("ffmpeg")
    if not ffmpeg:
        raise RuntimeError(
            "ffmpeg not found in PATH. Install FFmpeg and ensure it is on PATH."
        )
    return ffmpeg


async def _run(cmd: list[str]) -> None:
    """Run FFmpeg subprocess, raise on non-zero exit."""
    proc = await asyncio.create_subprocess_exec(
        *cmd,
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE,
    )
    _, stderr = await proc.communicate()
    if proc.returncode != 0:
        snippet = stderr.decode(errors="replace")[-600:]
        log.error("FFmpeg failed (code %d):\n%s", proc.returncode, snippet)
        raise RuntimeError(f"FFmpeg error (code {proc.returncode}): {snippet}")


def _ass_filter_path(path: Path) -> str:
    """
    Convert an absolute path to the escaping required inside FFmpeg
    filter_complex for the ass= filter on Windows.

    Windows:  D:\\a\\b\\c.ass  →  D\\:/a/b/c.ass
    Linux:    /a/b/c.ass       →  /a/b/c.ass
    """
    p = str(path).replace("\\", "/")
    # Escape drive-letter colon so FFmpeg filter parser doesn't treat it as option separator
    if len(p) >= 2 and p[1] == ":":
        p = p[0] + "\\:" + p[2:]
    return p


async def encode(
    timeline: Timeline,
    frame_dirs: list[Path],
    emit: Callable[[str, dict], Awaitable[None]],
    variant_id: str,
) -> Path:
    """
    Encode a complete MP4 from captured frame directories.

    *frame_dirs* must match the order of *timeline.scenes*.
    Returns the final output Path.
    """
    ffmpeg = _find_ffmpeg()
    fps = timeline.fps
    output_path = Path(timeline.output_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)

    # job_temp is the common ancestor of all frame_dirs
    job_temp = frame_dirs[0].parent.parent  # scene_NN/frames/../.. = job_temp

    total_frames = sum(
        max(1, round((s.end - s.start) * fps)) for s in timeline.scenes
    )
    encoded_frames = 0
    scene_clips: list[Path] = []

    # ── Stage 1: per-scene frame sequence → clip ─────────────────────────────

    for i, (scene, frames_dir) in enumerate(zip(timeline.scenes, frame_dirs)):
        clip_path = job_temp / f"scene_{i:02d}.mp4"
        n_frames = max(1, round((scene.end - scene.start) * fps))

        cmd = [
            ffmpeg, "-y",
            "-framerate", str(fps),
            "-i", str(frames_dir / "%04d.png"),
            "-c:v", "libx264",
            "-pix_fmt", "yuv420p",
            "-preset", "fast",
            "-crf", "18",
            "-r", str(fps),          # output framerate = input framerate
            str(clip_path),
        ]
        log.info("Encoding scene %d → %s", i, clip_path.name)
        await _run(cmd)

        # Free disk: delete frames immediately
        shutil.rmtree(frames_dir, ignore_errors=True)
        try:
            frames_dir.parent.rmdir()  # scene_NN/ if now empty
        except OSError:
            pass

        scene_clips.append(clip_path)
        encoded_frames += n_frames

        pct = int(encoded_frames / total_frames * 50)  # 0–50 % for stage 1
        await emit(
            "render.progress",
            {"variant_id": variant_id, "percent": pct, "fps": fps, "eta_seconds": 0},
        )

    # ── Stage 2: concat scene clips ──────────────────────────────────────────

    await emit("render.progress", {"variant_id": variant_id, "percent": 55, "fps": fps, "eta_seconds": 0})

    clips_txt = job_temp / "clips.txt"
    # Use POSIX paths (forward slashes) in the concat manifest — required on all platforms
    clips_txt.write_text(
        "\n".join(f"file '{clip.as_posix()}'" for clip in scene_clips),
        encoding="utf-8",
    )

    combined_path = job_temp / "combined.mp4"
    cmd = [
        ffmpeg, "-y",
        "-f", "concat",
        "-safe", "0",
        "-i", str(clips_txt),
        "-c", "copy",
        str(combined_path),
    ]
    log.info("Concatenating %d clips → %s", len(scene_clips), combined_path.name)
    await _run(cmd)

    for clip in scene_clips:
        clip.unlink(missing_ok=True)
    clips_txt.unlink(missing_ok=True)

    # ── Stage 3: mix audio + burn subtitles ──────────────────────────────────

    await emit("render.progress", {"variant_id": variant_id, "percent": 65, "fps": fps, "eta_seconds": 0})

    voice_track = timeline.audio.voice_track
    music_bed = timeline.audio.music_bed
    subs_file = timeline.subtitles.path

    inputs: list[str] = [ffmpeg, "-y", "-i", str(combined_path)]
    next_idx = 1          # input 0 = combined video
    filter_parts: list[str] = []
    video_out = "0:v"
    audio_out: str | None = None

    # Voice (always present after Phase 1.5 — silent WAV if no real TTS)
    if voice_track and Path(voice_track).exists():
        inputs += ["-i", str(voice_track)]
        vi = next_idx
        next_idx += 1

        if music_bed and Path(music_bed).exists():
            inputs += ["-i", str(music_bed)]
            mi = next_idx
            next_idx += 1
            music_vol = 10 ** (timeline.audio.music_gain_db / 20.0)
            filter_parts += [
                f"[{vi}:a]volume=1.0[v_a]",
                f"[{mi}:a]volume={music_vol:.6f}[m_a]",
                "[v_a][m_a]amix=inputs=2:normalize=0[audio_out]",
            ]
            audio_out = "[audio_out]"
        else:
            filter_parts.append(f"[{vi}:a]volume=1.0[audio_out]")
            audio_out = "[audio_out]"

    # Subtitle burn (libass)
    if subs_file and Path(subs_file).exists():
        ass_path = _ass_filter_path(Path(subs_file))
        filter_parts.insert(0, f"[0:v]ass='{ass_path}'[video_out]")
        video_out = "[video_out]"

    cmd = inputs[:]
    if filter_parts:
        cmd += ["-filter_complex", ";".join(filter_parts)]

    cmd += ["-map", video_out]
    if audio_out:
        cmd += ["-map", audio_out, "-c:a", "aac", "-b:a", "192k", "-shortest"]
    else:
        cmd += ["-an"]

    cmd += [
        "-c:v", "libx264",
        "-pix_fmt", "yuv420p",
        "-preset", "fast",
        "-crf", "18",
        "-movflags", "+faststart",
        str(output_path),
    ]

    log.info("Final encode → %s", output_path)
    await _run(cmd)

    combined_path.unlink(missing_ok=True)

    await emit(
        "render.progress",
        {"variant_id": variant_id, "percent": 100, "fps": fps, "eta_seconds": 0},
    )

    return output_path
