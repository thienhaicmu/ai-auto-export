"""
Tests for music_selector.py — style mapping and graceful fallback when
music files are absent (as in the current repo where assets/music/ only
has .gitkeep).
"""
from __future__ import annotations

from pathlib import Path
import tempfile

from app.renderer.music_selector import select_music, _STYLE_TRACK, _DEFAULT_TRACK


# ── Fallback when files are missing ──────────────────────────────────────────

def test_missing_file_returns_none(tmp_path: Path):
    result = select_music("viral", music_dir=tmp_path)
    assert result is None


def test_unknown_style_returns_none_when_missing(tmp_path: Path):
    result = select_music("nonexistent_style", music_dir=tmp_path)
    assert result is None


def test_all_known_styles_return_none_when_missing(tmp_path: Path):
    for style in ["viral", "story", "explainer", "documentary", "news", "cinematic"]:
        assert select_music(style, music_dir=tmp_path) is None


# ── Returns path when file exists ─────────────────────────────────────────────

def test_returns_path_when_file_exists(tmp_path: Path):
    (tmp_path / "viral_pulse.mp3").write_bytes(b"\x00" * 16)
    result = select_music("viral", music_dir=tmp_path)
    assert result is not None
    assert result.name == "viral_pulse.mp3"


def test_returns_correct_track_per_style(tmp_path: Path):
    for style, filename in _STYLE_TRACK.items():
        (tmp_path / filename).write_bytes(b"\x00" * 16)
        result = select_music(style, music_dir=tmp_path)
        assert result is not None
        assert result.name == filename


def test_unknown_style_falls_back_to_default_track(tmp_path: Path):
    (tmp_path / _DEFAULT_TRACK).write_bytes(b"\x00" * 16)
    result = select_music("mystery_style", music_dir=tmp_path)
    assert result is not None
    assert result.name == _DEFAULT_TRACK


# ── Does not raise ────────────────────────────────────────────────────────────

def test_select_music_never_raises(tmp_path: Path):
    for style in ["viral", "story", "", "🎵", "x" * 200]:
        try:
            select_music(style, music_dir=tmp_path)
        except Exception as exc:
            pytest.fail(f"select_music raised for style {style!r}: {exc}")


import pytest  # noqa: E402 (moved up for clarity in last test)
