"""
Timeline validation tests.

Checks that fixture_timeline() produces a structurally valid Timeline,
and that the Timeline model enforces its invariants.
"""
import pytest
from pydantic import ValidationError

from app.renderer.timeline import fixture_timeline
from app.models.job import (
    Timeline, Scene, SceneProps, AudioConfig, SubtitleConfig, VisualDirection,
)


# ── fixture_timeline() structural checks ─────────────────────────────────────

def test_fixture_timeline_has_five_scenes():
    tl = fixture_timeline(job_id="t1", keyword="karen", output_path="/tmp/out.mp4")
    assert len(tl.scenes) == 5


def test_fixture_timeline_scene_indices_are_sequential():
    tl = fixture_timeline(job_id="t2", keyword="bitcoin", output_path="/tmp/out.mp4")
    for i, scene in enumerate(tl.scenes):
        assert scene.index == i, f"Scene index mismatch at position {i}"


def test_fixture_timeline_scene_times_are_ordered():
    tl = fixture_timeline(job_id="t3", keyword="ai", output_path="/tmp/out.mp4")
    for scene in tl.scenes:
        assert scene.start < scene.end, f"Scene {scene.index}: start >= end"


def test_fixture_timeline_scenes_are_contiguous():
    tl = fixture_timeline(job_id="t4", keyword="test", output_path="/tmp/out.mp4")
    for prev, curr in zip(tl.scenes, tl.scenes[1:]):
        assert abs(prev.end - curr.start) < 0.01, (
            f"Gap between scene {prev.index} end ({prev.end}) "
            f"and scene {curr.index} start ({curr.start})"
        )


def test_fixture_timeline_duration_matches_scenes():
    tl = fixture_timeline(
        job_id="t5", keyword="test", output_path="/tmp/out.mp4", duration_seconds=30
    )
    total = sum(s.end - s.start for s in tl.scenes)
    assert abs(total - tl.duration_seconds) < 0.1


def test_fixture_timeline_quality_preview():
    tl = fixture_timeline(
        job_id="t6", keyword="test", output_path="/tmp/out.mp4",
        quality_mode="preview",
    )
    assert tl.resolution == (480, 854)
    assert tl.fps == 24
    assert tl.quality_mode == "preview"


def test_fixture_timeline_quality_final():
    tl = fixture_timeline(
        job_id="t7", keyword="test", output_path="/tmp/out.mp4",
        quality_mode="final",
    )
    assert tl.resolution == (1080, 1920)
    assert tl.fps == 30
    assert tl.quality_mode == "final"


# ── Timeline model invariants ─────────────────────────────────────────────────

def test_timeline_requires_output_path():
    with pytest.raises((ValidationError, TypeError)):
        Timeline(
            job_id="t8",
            variant_id="v01",
            duration_seconds=30,
            # output_path omitted — should fail
        )


def test_timeline_quality_mode_literal():
    with pytest.raises(ValidationError):
        Timeline(
            job_id="t9",
            variant_id="v01",
            duration_seconds=30,
            output_path="/tmp/out.mp4",
            quality_mode="ultra",   # not a valid Literal
        )


def test_scene_props_visual_direction_optional():
    """SceneProps.visual_direction defaults to None (backward compat)."""
    props = SceneProps(headline="TEST")
    assert props.visual_direction is None


def test_scene_props_visual_direction_roundtrip():
    """VisualDirection survives model_dump/model_validate."""
    import json
    vd = VisualDirection(
        energy_level=4,
        motion_intensity="high",
        layout_mode="split",
        transition_style="zoom",
        emphasis_words=["word"],
        background_treatment="dark_image",
        subtitle_emphasis=True,
        pacing_note="test note",
    )
    props = SceneProps(headline="TEST", visual_direction=vd)
    props2 = SceneProps.model_validate(json.loads(props.model_dump_json()))
    assert props2.visual_direction is not None
    assert props2.visual_direction.energy_level == 4
    assert props2.visual_direction.motion_intensity == "high"
    assert props2.visual_direction.layout_mode == "split"


def test_visual_direction_energy_clamp():
    """energy_level must be stored as-is (clamping is done in scene_agent, not model)."""
    vd = VisualDirection(energy_level=3)
    assert vd.energy_level == 3


def test_scene_model_requires_props():
    with pytest.raises((ValidationError, TypeError)):
        Scene(index=0, start=0.0, end=5.0, template="viral")
