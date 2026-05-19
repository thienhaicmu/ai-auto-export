"""
Output QA validator tests.

Uses unittest.mock to avoid requiring a real video file or ffprobe binary
for the stream-check logic. File-existence and size checks use real temp files.
"""
import asyncio
import pytest
from pathlib import Path
from unittest.mock import AsyncMock, patch

from app.renderer.output_validator import validate_output, _MIN_SIZE_BYTES, QAViolation
from app.models.job import Timeline, AudioConfig, SubtitleConfig, Scene, SceneProps


# ── Fixture helpers ───────────────────────────────────────────────────────────

def _make_timeline(duration: int = 30, resolution: tuple = (480, 854)) -> Timeline:
    scenes = [
        Scene(
            index=0,
            start=0.0,
            end=float(duration),
            template="viral",
            props=SceneProps(headline="TEST"),
        )
    ]
    return Timeline(
        job_id="test-qa",
        variant_id="v01",
        resolution=resolution,
        fps=24,
        duration_seconds=duration,
        audio=AudioConfig(),
        subtitles=SubtitleConfig(),
        scenes=scenes,
        output_path="/tmp/test.mp4",
    )


def _good_probe(duration: float = 30.0, w: int = 480, h: int = 854) -> dict:
    return {
        "format": {"duration": str(duration)},
        "streams": [
            {
                "codec_type": "video",
                "codec_name": "h264",
                "width": w,
                "height": h,
            }
        ],
    }


# ── File-level checks (no ffprobe) ────────────────────────────────────────────

@pytest.mark.asyncio
async def test_missing_file_fails(tmp_path: Path):
    path = tmp_path / "nonexistent.mp4"
    tl = _make_timeline()
    result = await validate_output(path, tl)
    assert not result.ok
    assert any(v.check == "exists" for v in result.violations)


@pytest.mark.asyncio
async def test_too_small_fails(tmp_path: Path):
    path = tmp_path / "tiny.mp4"
    path.write_bytes(b"\x00" * 100)  # 100 bytes — well under minimum
    tl = _make_timeline()
    with patch("app.renderer.output_validator._probe", new_callable=AsyncMock) as mock_probe:
        mock_probe.return_value = None  # skip stream checks
        with patch("app.renderer.output_validator._find_ffprobe", return_value=None):
            result = await validate_output(path, tl)
    assert not result.ok
    assert any(v.check == "size" for v in result.violations)


# ── Stream-level checks (mocked ffprobe) ─────────────────────────────────────

@pytest.mark.asyncio
async def test_good_output_passes(tmp_path: Path):
    path = tmp_path / "good.mp4"
    path.write_bytes(b"\x00" * (_MIN_SIZE_BYTES + 1))
    tl = _make_timeline(duration=30, resolution=(480, 854))
    with patch("app.renderer.output_validator._probe", new_callable=AsyncMock) as mock_probe:
        mock_probe.return_value = _good_probe(duration=30.0, w=480, h=854)
        result = await validate_output(path, tl)
    assert result.ok, result.summary


@pytest.mark.asyncio
async def test_duration_too_short_fails(tmp_path: Path):
    path = tmp_path / "short.mp4"
    path.write_bytes(b"\x00" * (_MIN_SIZE_BYTES + 1))
    tl = _make_timeline(duration=30)
    with patch("app.renderer.output_validator._probe", new_callable=AsyncMock) as mock_probe:
        mock_probe.return_value = _good_probe(duration=10.0)  # 10s < 30*0.95=28.5s
        result = await validate_output(path, tl)
    assert not result.ok
    assert any(v.check == "duration" for v in result.violations)


@pytest.mark.asyncio
async def test_wrong_resolution_fails(tmp_path: Path):
    path = tmp_path / "wrongres.mp4"
    path.write_bytes(b"\x00" * (_MIN_SIZE_BYTES + 1))
    tl = _make_timeline(resolution=(1080, 1920))
    with patch("app.renderer.output_validator._probe", new_callable=AsyncMock) as mock_probe:
        mock_probe.return_value = _good_probe(w=480, h=854)  # wrong resolution
        result = await validate_output(path, tl)
    assert not result.ok
    assert any(v.check == "resolution" for v in result.violations)


@pytest.mark.asyncio
async def test_wrong_codec_fails(tmp_path: Path):
    path = tmp_path / "wrongcodec.mp4"
    path.write_bytes(b"\x00" * (_MIN_SIZE_BYTES + 1))
    tl = _make_timeline()
    probe = _good_probe()
    probe["streams"][0]["codec_name"] = "hevc"   # not h264
    with patch("app.renderer.output_validator._probe", new_callable=AsyncMock) as mock_probe:
        mock_probe.return_value = probe
        result = await validate_output(path, tl)
    assert not result.ok
    assert any(v.check == "codec" for v in result.violations)


@pytest.mark.asyncio
async def test_no_video_stream_fails(tmp_path: Path):
    path = tmp_path / "nostream.mp4"
    path.write_bytes(b"\x00" * (_MIN_SIZE_BYTES + 1))
    tl = _make_timeline()
    with patch("app.renderer.output_validator._probe", new_callable=AsyncMock) as mock_probe:
        mock_probe.return_value = {"format": {"duration": "30.0"}, "streams": []}
        result = await validate_output(path, tl)
    assert not result.ok
    assert any(v.check == "video_stream" for v in result.violations)


@pytest.mark.asyncio
async def test_missing_audio_stream_fails_when_voice_present(tmp_path: Path):
    path = tmp_path / "noaudio.mp4"
    path.write_bytes(b"\x00" * (_MIN_SIZE_BYTES + 1))
    tl = _make_timeline()
    tl.audio.voice_track = "/tmp/voice.wav"   # voice was expected
    probe = _good_probe(duration=30.0)
    # No audio stream in probe
    with patch("app.renderer.output_validator._probe", new_callable=AsyncMock) as mock_probe:
        mock_probe.return_value = probe
        result = await validate_output(path, tl)
    assert not result.ok
    assert any(v.check == "audio_stream" for v in result.violations)


@pytest.mark.asyncio
async def test_ffprobe_unavailable_skips_stream_checks(tmp_path: Path):
    """If ffprobe is not installed, file-level checks still run, streams are skipped."""
    path = tmp_path / "noprobe.mp4"
    path.write_bytes(b"\x00" * (_MIN_SIZE_BYTES + 1))
    tl = _make_timeline()
    with patch("app.renderer.output_validator._find_ffprobe", return_value=None):
        result = await validate_output(path, tl)
    # No size violation (file is large enough), no stream violations (skipped)
    assert result.ok
    assert not result.ffprobe_available
