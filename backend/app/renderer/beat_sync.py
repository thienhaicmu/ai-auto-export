"""
Deterministic beat marker generation and scene boundary alignment.

No external audio analysis required — beats are computed from BPM presets
per template style. All functions are pure (no IO, no randomness).

Usage:
  from app.renderer.beat_sync import build_audio_direction

  direction = build_audio_direction(timeline)
  timeline.audio.direction = direction
"""
from __future__ import annotations

from app.models.job import AudioDirection, Scene, Timeline

# ── BPM presets by style ──────────────────────────────────────────────────────

_STYLE_BPM: dict[str, int] = {
    "viral":       128,
    "story":        96,
    "explainer":   100,
    "documentary":  80,
    "news":        120,
    "cinematic":    72,
}

_DEFAULT_BPM = 128
_MIN_SCENE_DURATION = 1.5   # seconds — never compress a scene below this
_DEFAULT_FADE_IN_MS  = 500
_DEFAULT_FADE_OUT_MS = 1000


# ── Core math ─────────────────────────────────────────────────────────────────

def get_bpm(style: str) -> int:
    """Return BPM for the given style, falling back to the default."""
    return _STYLE_BPM.get(style, _DEFAULT_BPM)


def generate_beat_markers(duration_seconds: float, bpm: int) -> list[float]:
    """
    Generate beat timestamps (seconds from start) for the given duration and BPM.

    Beat 0 is at t=0.  All markers are rounded to 4 decimal places.
    Returns an ascending list; the last marker is <= duration_seconds.
    """
    if bpm <= 0 or duration_seconds <= 0:
        return []
    beat_interval = 60.0 / bpm
    markers: list[float] = []
    t = 0.0
    while t <= duration_seconds + 1e-9:
        markers.append(round(t, 4))
        t += beat_interval
    # Drop any marker that exceeds duration (floating-point overshoot)
    return [m for m in markers if m <= duration_seconds + 1e-6]


def nearest_beat(t: float, markers: list[float]) -> float:
    """Return the marker timestamp closest to *t*. Returns *t* if markers is empty."""
    if not markers:
        return t
    return min(markers, key=lambda b: abs(b - t))


# ── Scene alignment ───────────────────────────────────────────────────────────

def align_scenes_to_beats(
    scenes: list[Scene],
    beat_markers: list[float],
    total_duration: float,
    min_scene_duration: float = _MIN_SCENE_DURATION,
) -> list[Scene]:
    """
    Snap interior scene boundaries to the nearest beat while preserving total duration.

    Guarantees:
    - First scene starts at 0.0.
    - Last scene ends at total_duration.
    - No scene is shorter than min_scene_duration.
    - Scene indices and template/props data are unchanged.

    Returns a new list of Scene objects (inputs are not mutated).
    """
    if not scenes or not beat_markers:
        return list(scenes)

    n = len(scenes)
    if n == 1:
        s = scenes[0]
        return [s.model_copy(update={"start": 0.0, "end": round(total_duration, 3)})]

    # Compute interior boundary timestamps (between scenes[i] and scenes[i+1])
    # boundaries[0] = 0.0, boundaries[n] = total_duration
    # boundaries[1..n-1] = interior boundaries snapped to nearest beat
    boundaries: list[float] = [0.0]
    for i in range(1, n):
        original = scenes[i].start
        snapped  = nearest_beat(original, beat_markers)
        boundaries.append(snapped)
    boundaries.append(total_duration)

    # Forward pass: push a boundary forward if the scene before it would be too short
    for i in range(1, n):
        if boundaries[i] - boundaries[i - 1] < min_scene_duration:
            boundaries[i] = boundaries[i - 1] + min_scene_duration

    # Backward pass: pull a boundary back if the scene after it would be too short
    for i in range(n - 1, 0, -1):
        if boundaries[i + 1] - boundaries[i] < min_scene_duration:
            boundaries[i] = boundaries[i + 1] - min_scene_duration

    # Clamp all boundaries to [0, total_duration]
    boundaries = [max(0.0, min(total_duration, b)) for b in boundaries]

    return [
        scene.model_copy(update={
            "start": round(boundaries[i], 3),
            "end":   round(boundaries[i + 1], 3),
        })
        for i, scene in enumerate(scenes)
    ]


# ── High-level builder ────────────────────────────────────────────────────────

def build_audio_direction(timeline: Timeline) -> AudioDirection:
    """
    Derive an AudioDirection from a Timeline's style, duration, and scenes.

    Generates beat markers, computes transition hit times, and reads per-scene
    energy from VisualDirection if present.

    This is the single call-site used by the render pipeline.
    """
    style            = timeline.style
    duration         = float(timeline.duration_seconds)
    scenes           = timeline.scenes
    bpm              = get_bpm(style)
    beat_markers     = generate_beat_markers(duration, bpm)

    # Transition hits: start of every scene except the first
    transition_hits  = [round(s.start, 3) for s in scenes[1:]]

    # Intro hit: first beat slightly after the very start (beat index 1, or t≈beat_interval)
    intro_hit: float | None = beat_markers[1] if len(beat_markers) > 1 else None

    # Outro hit: last beat that is >= 1.0s before the end
    candidates = [b for b in beat_markers if b <= duration - 1.0]
    outro_hit: float | None = candidates[-1] if candidates else None

    # Per-scene energy from VisualDirection (fallback: 3)
    scene_energy = [
        (s.props.visual_direction.energy_level
         if s.props.visual_direction else 3)
        for s in scenes
    ]

    return AudioDirection(
        bpm=bpm,
        beat_markers=beat_markers,
        intro_hit=round(intro_hit, 4) if intro_hit is not None else None,
        transition_hits=transition_hits,
        outro_hit=round(outro_hit, 4) if outro_hit is not None else None,
        fade_in_ms=_DEFAULT_FADE_IN_MS,
        fade_out_ms=_DEFAULT_FADE_OUT_MS,
        duck_voice=True,
        scene_energy=scene_energy,
    )


def apply_beat_sync(timeline: Timeline) -> Timeline:
    """
    Return a new Timeline with:
    1. audio.direction populated from BPM presets.
    2. Scene boundaries snapped to the nearest beat (preserving total duration).

    The input Timeline is NOT mutated.
    """
    bpm          = get_bpm(timeline.style)
    duration     = float(timeline.duration_seconds)
    beat_markers = generate_beat_markers(duration, bpm)

    # Align scenes
    aligned_scenes = align_scenes_to_beats(
        timeline.scenes, beat_markers, duration
    )

    # Build direction using the aligned scenes
    direction = build_audio_direction(
        timeline.model_copy(update={"scenes": aligned_scenes})
    )

    # Update audio config (preserve all other audio fields)
    new_audio = timeline.audio.model_copy(update={"direction": direction})

    return timeline.model_copy(update={
        "scenes": aligned_scenes,
        "audio":  new_audio,
    })
