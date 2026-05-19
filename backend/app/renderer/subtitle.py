"""
ASS subtitle generator from Timeline scene props.

Format: Advanced SubStation Alpha (ASS) v4+
Used by FFmpeg's libass filter to burn subtitles into video.

Phase 1: one dialogue line per scene (scene headline / subhead).
Phase 2: word-level timing from edge-tts word boundaries.

PlayResX/Y are always set to the canonical 1080x1920 regardless of quality mode;
libass + FFmpeg scale automatically when the output video is a different size.
"""
import textwrap
from pathlib import Path

from app.models.job import Timeline


def _ass_time(seconds: float) -> str:
    """Convert seconds to ASS timestamp H:MM:SS.cc (centiseconds)."""
    h = int(seconds // 3600)
    m = int((seconds % 3600) // 60)
    s = seconds % 60
    cs = int(round((s - int(s)) * 100))
    return f"{h}:{m:02d}:{int(s):02d}.{cs:02d}"


def _escape_ass(text: str) -> str:
    """Escape ASS special characters."""
    return text.replace("{", "\\{").replace("}", "\\}").replace("\n", "\\N")


def _wrap_subtitle(text: str, max_chars: int = 32) -> str:
    """Wrap long subtitle text to max_chars per line using ASS line break \\N."""
    lines = textwrap.wrap(text, width=max_chars, break_long_words=False, break_on_hyphens=False)
    return "\\N".join(lines) if lines else text


def generate_ass_subtitles(timeline: Timeline, output_path: Path) -> None:
    """
    Write a .ass subtitle file for the timeline.

    Each scene contributes one dialogue line timed to its [start, end] window.
    Text: subhead if present (narrative), else headline.
    """
    # Style parameters tuned for 1080x1920 canonical resolution.
    # libass scales them proportionally for smaller output dimensions.
    #
    # Alignment 2  = bottom-center
    # MarginV 200  = 200px from bottom edge (above progress bar at very bottom)
    # Outline 4    = thick black outline for high-contrast readability on any background
    # Shadow 2     = drop shadow for depth
    header = """\
[Script Info]
ScriptType: v4.00+
PlayResX: 1080
PlayResY: 1920
ScaledBorderAndShadow: yes
YCbCr Matrix: TV.709

[V4+ Styles]
Format: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, OutlineColour, BackColour, Bold, Italic, Underline, StrikeOut, ScaleX, ScaleY, Spacing, Angle, BorderStyle, Outline, Shadow, Alignment, MarginL, MarginR, MarginV, Encoding
Style: viral_bold,Arial,56,&H00FFFFFF,&H000000FF,&H00000000,&H88000000,-1,0,0,0,100,100,1,0,1,4,2,2,80,80,200,1

[Events]
Format: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text
"""

    dialogues: list[str] = []
    for scene in timeline.scenes:
        start = _ass_time(scene.start)
        end = _ass_time(scene.end)
        # Prefer subhead (narrative) for subtitles; fall back to headline
        raw = scene.props.subhead if scene.props.subhead else scene.props.headline
        text = _escape_ass(_wrap_subtitle(raw))
        dialogues.append(
            f"Dialogue: 0,{start},{end},viral_bold,,0,0,0,,{text}"
        )

    output_path.write_text(header + "\n".join(dialogues) + "\n", encoding="utf-8")
