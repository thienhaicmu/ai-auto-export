"""
ASS subtitle generator from Timeline scene props.

Format: Advanced SubStation Alpha (ASS) v4+
Used by FFmpeg's libass filter to burn subtitles into video.

Phase 1: one dialogue line per scene (scene headline / subhead).
Phase 5A: improved styling — tighter wrap, stronger outline, better margins,
          optional emphasis style for subtitle_emphasis scenes.

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


def _wrap_subtitle(text: str, max_chars: int = 26) -> str:
    """
    Wrap subtitle text to max_chars per line using ASS line break \\N.

    26 chars per line works well for 9:16 1080px wide frames with the
    font size and margins defined below.
    """
    lines = textwrap.wrap(text, width=max_chars, break_long_words=False, break_on_hyphens=False)
    return "\\N".join(lines) if lines else text


def generate_ass_subtitles(timeline: Timeline, output_path: Path) -> None:
    """
    Write a .ass subtitle file for the timeline.

    Each scene contributes one dialogue line timed to its [start, end] window.
    Text: subhead if present (narrative), else headline.

    Scenes with visual_direction.subtitle_emphasis use the 'viral_emphasis' style
    (larger, bolder) for higher-impact readability.
    """
    # ── Style parameters (1080×1920 canonical resolution) ─────────────────────
    #
    # viral_bold   — standard lower-third subtitle
    #   Fontname: Arial   Fontsize: 54   PrimaryColour: white
    #   OutlineColour: black   Outline: 5   Shadow: 3
    #   Alignment: 2 (bottom-center)   MarginV: 240  (above progress bar)
    #
    # viral_emphasis — used when subtitle_emphasis=true
    #   Same but Fontsize: 64, Bold, letter-spacing wider
    #
    # ASS colour format: &H<AA><BB><GG><RR>  (alpha 00=opaque, FF=transparent)
    # Black outline:  &H00000000
    # White text:     &H00FFFFFF
    # BackColour (unused for BorderStyle 1): &HA0000000
    #
    # BorderStyle 1 = outline + shadow (no box fill)
    # Outline 5 = 5px wide black stroke for strong contrast on any background
    # Shadow 3 = drop shadow for depth
    header = """\
[Script Info]
ScriptType: v4.00+
PlayResX: 1080
PlayResY: 1920
ScaledBorderAndShadow: yes
YCbCr Matrix: TV.709

[V4+ Styles]
Format: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, OutlineColour, BackColour, Bold, Italic, Underline, StrikeOut, ScaleX, ScaleY, Spacing, Angle, BorderStyle, Outline, Shadow, Alignment, MarginL, MarginR, MarginV, Encoding
Style: viral_bold,Arial,54,&H00FFFFFF,&H000000FF,&H00000000,&HA0000000,-1,0,0,0,100,100,0.5,0,1,5,3,2,80,80,240,1
Style: viral_emphasis,Arial,66,&H00FFFFFF,&H000000FF,&H00000000,&HA0000000,-1,0,0,0,100,100,0.5,0,1,6,3,2,80,80,240,1

[Events]
Format: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text
"""

    dialogues: list[str] = []
    for scene in timeline.scenes:
        start = _ass_time(scene.start)
        end   = _ass_time(scene.end)

        # Prefer subhead (narrative) for subtitles; fall back to headline
        raw  = scene.props.subhead if scene.props.subhead else scene.props.headline
        text = _escape_ass(_wrap_subtitle(raw))

        # Use emphasis style when the scene director flagged subtitle_emphasis
        vd = scene.props.visual_direction
        emphasis = vd.subtitle_emphasis if vd is not None else False
        style = "viral_emphasis" if emphasis else "viral_bold"

        dialogues.append(
            f"Dialogue: 0,{start},{end},{style},,0,0,0,,{text}"
        )

    output_path.write_text(header + "\n".join(dialogues) + "\n", encoding="utf-8")
