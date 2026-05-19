"""
Tests for beat_sync.py — BPM presets, marker generation, scene alignment,
AudioDirection derivation, and apply_beat_sync round-trips.
"""
from __future__ import annotations

import pytest
from app.renderer.beat_sync import (
    get_bpm,
    generate_beat_markers,
    nearest_beat,
    align_scenes_to_beats,
    build_audio_direction,
    apply_beat_sync,
)
from app.models.job import Scene, SceneProps, Timeline, AudioConfig


# ── Fixtures ──────────────────────────────────────────────────────────────────

def _props() -> SceneProps:
    return SceneProps(headline="TEST")


def _timeline(n_scenes: int = 3, duration: int = 30, style: str = "viral") -> Timeline:
    scene_dur = duration / n_scenes
    scenes = [
        Scene(
            index=i,
            start=round(i * scene_dur, 3),
            end=round((i + 1) * scene_dur, 3),
            template="viral",
            role="hook" if i == 0 else "context",
            props=_props(),
        )
        for i in range(n_scenes)
    ]
    return Timeline(
        job_id="test_job",
        variant_id="v01",
        style=style,
        duration_seconds=duration,
        scenes=scenes,
        output_path="/tmp/out.mp4",
    )


# ── get_bpm ───────────────────────────────────────────────────────────────────

def test_bpm_known_styles():
    assert get_bpm("viral") == 128
    assert get_bpm("story") == 96
    assert get_bpm("explainer") == 100
    assert get_bpm("documentary") == 80
    assert get_bpm("news") == 120
    assert get_bpm("cinematic") == 72


def test_bpm_unknown_style_fallback():
    assert get_bpm("unknown_style") == 128
    assert get_bpm("") == 128


# ── generate_beat_markers ─────────────────────────────────────────────────────

def test_beat_markers_start_at_zero():
    markers = generate_beat_markers(10.0, 120)
    assert markers[0] == 0.0


def test_beat_markers_interval():
    bpm = 120
    markers = generate_beat_markers(10.0, bpm)
    expected_interval = 60.0 / bpm   # 0.5s
    for a, b in zip(markers, markers[1:]):
        assert abs((b - a) - expected_interval) < 1e-3


def test_beat_markers_none_exceeds_duration():
    duration = 15.0
    markers = generate_beat_markers(duration, 128)
    assert all(m <= duration + 1e-6 for m in markers)


def test_beat_markers_ascending():
    markers = generate_beat_markers(20.0, 100)
    assert markers == sorted(markers)


def test_beat_markers_empty_for_zero_duration():
    assert generate_beat_markers(0.0, 128) == []


def test_beat_markers_empty_for_zero_bpm():
    assert generate_beat_markers(30.0, 0) == []


def test_beat_markers_rounded_to_4dp():
    markers = generate_beat_markers(5.0, 100)
    for m in markers:
        assert round(m, 4) == m


# ── nearest_beat ──────────────────────────────────────────────────────────────

def test_nearest_beat_exact_match():
    markers = [0.0, 0.5, 1.0, 1.5, 2.0]
    assert nearest_beat(1.0, markers) == 1.0


def test_nearest_beat_rounds_down():
    markers = [0.0, 0.5, 1.0]
    assert nearest_beat(0.7, markers) == 0.5


def test_nearest_beat_rounds_up():
    markers = [0.0, 0.5, 1.0]
    assert nearest_beat(0.85, markers) == 1.0


def test_nearest_beat_empty_markers_returns_t():
    assert nearest_beat(3.7, []) == 3.7


# ── align_scenes_to_beats ─────────────────────────────────────────────────────

def test_align_preserves_total_duration():
    tl = _timeline(5, 30)
    markers = generate_beat_markers(30.0, 128)
    aligned = align_scenes_to_beats(tl.scenes, markers, 30.0)
    assert abs(aligned[-1].end - 30.0) < 1e-6


def test_align_first_scene_starts_at_zero():
    tl = _timeline(5, 30)
    markers = generate_beat_markers(30.0, 128)
    aligned = align_scenes_to_beats(tl.scenes, markers, 30.0)
    assert aligned[0].start == 0.0


def test_align_scenes_contiguous():
    tl = _timeline(5, 30)
    markers = generate_beat_markers(30.0, 128)
    aligned = align_scenes_to_beats(tl.scenes, markers, 30.0)
    for a, b in zip(aligned, aligned[1:]):
        assert abs(a.end - b.start) < 1e-6


def test_align_min_scene_duration_enforced():
    tl = _timeline(5, 30)
    markers = generate_beat_markers(30.0, 128)
    aligned = align_scenes_to_beats(tl.scenes, markers, 30.0, min_scene_duration=1.5)
    for s in aligned:
        assert (s.end - s.start) >= 1.5 - 1e-6


def test_align_single_scene():
    tl = _timeline(1, 30)
    markers = generate_beat_markers(30.0, 128)
    aligned = align_scenes_to_beats(tl.scenes, markers, 30.0)
    assert len(aligned) == 1
    assert aligned[0].start == 0.0
    assert abs(aligned[0].end - 30.0) < 1e-6


def test_align_empty_scenes():
    aligned = align_scenes_to_beats([], [0.0, 0.5, 1.0], 30.0)
    assert aligned == []


def test_align_no_mutation():
    tl = _timeline(3, 30)
    original_starts = [s.start for s in tl.scenes]
    markers = generate_beat_markers(30.0, 128)
    align_scenes_to_beats(tl.scenes, markers, 30.0)
    assert [s.start for s in tl.scenes] == original_starts


# ── build_audio_direction ─────────────────────────────────────────────────────

def test_build_audio_direction_bpm_matches_style():
    tl = _timeline(style="documentary")
    direction = build_audio_direction(tl)
    assert direction.bpm == 80


def test_build_audio_direction_has_beat_markers():
    tl = _timeline()
    direction = build_audio_direction(tl)
    assert len(direction.beat_markers) > 0
    assert direction.beat_markers[0] == 0.0


def test_build_audio_direction_transition_hits():
    tl = _timeline(3, 30)
    direction = build_audio_direction(tl)
    # transition hits = starts of scenes[1:]
    assert len(direction.transition_hits) == 2


def test_build_audio_direction_fade_defaults():
    tl = _timeline()
    direction = build_audio_direction(tl)
    assert direction.fade_in_ms == 500
    assert direction.fade_out_ms == 1000


def test_build_audio_direction_duck_voice_true():
    tl = _timeline()
    direction = build_audio_direction(tl)
    assert direction.duck_voice is True


# ── apply_beat_sync ───────────────────────────────────────────────────────────

def test_apply_beat_sync_returns_new_timeline():
    tl = _timeline()
    synced = apply_beat_sync(tl)
    assert synced is not tl


def test_apply_beat_sync_populates_audio_direction():
    tl = _timeline()
    synced = apply_beat_sync(tl)
    assert synced.audio.direction is not None
    assert synced.audio.direction.bpm == 128


def test_apply_beat_sync_preserves_duration():
    tl = _timeline(5, 30)
    synced = apply_beat_sync(tl)
    assert abs(synced.scenes[-1].end - 30.0) < 1e-6


def test_apply_beat_sync_no_mutation():
    tl = _timeline(5, 30)
    original_duration = tl.duration_seconds
    apply_beat_sync(tl)
    assert tl.duration_seconds == original_duration
    assert tl.audio.direction is None
