"""
Tests for AudioDirection and AudioConfig Pydantic models (Phase 4A).
Covers defaults, round-trips, and field constraints.
"""
from __future__ import annotations

import pytest
from pydantic import ValidationError
from app.models.job import AudioConfig, AudioDirection


# ── AudioDirection defaults ───────────────────────────────────────────────────

def test_audio_direction_defaults():
    d = AudioDirection()
    assert d.bpm == 128
    assert d.beat_markers == []
    assert d.intro_hit is None
    assert d.transition_hits == []
    assert d.outro_hit is None
    assert d.fade_in_ms == 500
    assert d.fade_out_ms == 1000
    assert d.duck_voice is True
    assert d.scene_energy == []


def test_audio_direction_accepts_beat_markers():
    d = AudioDirection(beat_markers=[0.0, 0.469, 0.938, 1.406])
    assert len(d.beat_markers) == 4
    assert d.beat_markers[0] == 0.0


def test_audio_direction_accepts_all_fields():
    d = AudioDirection(
        bpm=96,
        beat_markers=[0.0, 0.625, 1.25],
        intro_hit=0.625,
        transition_hits=[10.0, 20.0],
        outro_hit=29.0,
        fade_in_ms=300,
        fade_out_ms=800,
        duck_voice=False,
        scene_energy=[4, 3, 2, 3, 5],
    )
    assert d.bpm == 96
    assert d.intro_hit == 0.625
    assert d.outro_hit == 29.0
    assert d.duck_voice is False
    assert d.scene_energy == [4, 3, 2, 3, 5]


def test_audio_direction_json_roundtrip():
    d = AudioDirection(
        bpm=100,
        beat_markers=[0.0, 0.6, 1.2],
        intro_hit=0.6,
        transition_hits=[5.0, 10.0],
        outro_hit=29.4,
        scene_energy=[3, 4, 2],
    )
    restored = AudioDirection.model_validate_json(d.model_dump_json())
    assert restored == d


# ── AudioConfig with direction ────────────────────────────────────────────────

def test_audio_config_direction_none_by_default():
    cfg = AudioConfig()
    assert cfg.direction is None


def test_audio_config_accepts_direction():
    direction = AudioDirection(bpm=128, beat_markers=[0.0, 0.469])
    cfg = AudioConfig(direction=direction)
    assert cfg.direction is not None
    assert cfg.direction.bpm == 128


def test_audio_config_preserves_other_fields():
    cfg = AudioConfig(
        music_gain_db=-18.0,
        duck_voice=True,
        direction=AudioDirection(bpm=72),
    )
    assert cfg.music_gain_db == -18.0
    assert cfg.direction.bpm == 72


def test_audio_config_direction_optional_in_legacy_payload():
    """Existing timelines without direction must still parse correctly."""
    cfg = AudioConfig.model_validate({"voice_track": None, "music_bed": None, "music_gain_db": -22.0})
    assert cfg.direction is None


def test_audio_config_json_roundtrip_with_direction():
    cfg = AudioConfig(
        voice_track="/tmp/voice.wav",
        music_gain_db=-20.0,
        direction=AudioDirection(bpm=120, scene_energy=[3, 4, 5]),
    )
    restored = AudioConfig.model_validate_json(cfg.model_dump_json())
    assert restored.direction.bpm == 120
    assert restored.direction.scene_energy == [3, 4, 5]


# ── Edge cases ────────────────────────────────────────────────────────────────

def test_audio_direction_duck_voice_field_is_bool():
    d = AudioDirection(duck_voice=True)
    assert isinstance(d.duck_voice, bool)


def test_audio_direction_scene_energy_empty_list():
    d = AudioDirection(scene_energy=[])
    assert d.scene_energy == []


def test_audio_config_duck_voice_not_a_field():
    """duck_voice lives on AudioDirection, not AudioConfig — ensure no bleed-through."""
    cfg = AudioConfig()
    assert not hasattr(cfg, "duck_voice")
