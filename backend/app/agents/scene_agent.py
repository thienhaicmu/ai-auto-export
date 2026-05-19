"""
Scene generation agent.

Calls the LLM provider to build 5 viral scenes from a keyword/language/duration,
then maps the result into a validated Timeline Pydantic model.

Fallback: any parse or API error returns fixture_timeline() so the render job
never fails due to LLM issues.
"""
from __future__ import annotations

import json
import logging
import random
from typing import Optional

from pydantic import BaseModel, ValidationError, field_validator

from app.models.job import (
    AudioConfig, Idea, Scene, SceneProps, SubtitleConfig, Timeline,
)
from app.providers.llm.base import LLMAdapter

log = logging.getLogger(__name__)

# Mirror of QUALITY_PRESETS in renderer/timeline.py (avoids circular import)
_QUALITY_PRESETS: dict[str, dict] = {
    "preview": {"resolution": (480, 854),  "fps": 24},
    "final":   {"resolution": (1080, 1920), "fps": 30},
}

# ── Pydantic schema for Gemini scene output ───────────────────────────────────

class _GeminiScene(BaseModel):
    index: int
    duration_seconds: float
    headline: str
    subhead: str = ""
    highlight_word_indices: list[int] = []
    animation_seed: int = 0

    @field_validator("headline", mode="before")
    @classmethod
    def _clean_headline(cls, v: str) -> str:
        # Enforce ALL CAPS and trim; never let it be blank
        cleaned = str(v).strip().upper()[:30]
        return cleaned or "UNTITLED"

    @field_validator("duration_seconds", mode="before")
    @classmethod
    def _positive_duration(cls, v: float) -> float:
        return max(0.5, float(v))


class _GeminiSceneOutput(BaseModel):
    hook: str = ""
    scenes: list[_GeminiScene]


# ── Prompt templates ──────────────────────────────────────────────────────────

_SYSTEM = """\
You are a viral short-form video script writer for TikTok, Instagram Reels, and YouTube Shorts.
Create exactly 5 scenes for a vertical 9:16 video using kinetic bold typography on a dark background.
Respond ONLY with valid JSON matching the schema exactly — no explanation, no markdown fences."""

_PROMPT_TMPL = """\
Keyword: "{keyword}"
Language: {language}
Total video duration: {duration} seconds
Style: viral (bold kinetic text, dark cinematic background)
{idea_context}
Create exactly 5 scenes. Duration of all scenes must sum to exactly {duration} seconds ({scene_dur} s each).

Return this JSON structure exactly:
{{
  "hook": "<overall video hook, SHORT ALL CAPS, max 40 chars>",
  "scenes": [
    {{
      "index": 0,
      "duration_seconds": {scene_dur},
      "headline": "<SHORT BOLD ALL-CAPS HEADLINE, max 4 words, max 20 chars — the hook>",
      "subhead": "<supporting text, sentence case, max 50 chars>",
      "highlight_word_indices": [0],
      "animation_seed": {seed0}
    }},
    {{
      "index": 1,
      "duration_seconds": {scene_dur},
      "headline": "<scene 2 headline, max 4 words>",
      "subhead": "<scene 2 subhead, max 50 chars>",
      "highlight_word_indices": [],
      "animation_seed": {seed1}
    }},
    {{
      "index": 2,
      "duration_seconds": {scene_dur},
      "headline": "<scene 3 headline, max 4 words>",
      "subhead": "<scene 3 subhead, max 50 chars>",
      "highlight_word_indices": [],
      "animation_seed": {seed2}
    }},
    {{
      "index": 3,
      "duration_seconds": {scene_dur},
      "headline": "<scene 4 headline, max 4 words>",
      "subhead": "<scene 4 subhead, max 50 chars>",
      "highlight_word_indices": [],
      "animation_seed": {seed3}
    }},
    {{
      "index": 4,
      "duration_seconds": {scene_dur},
      "headline": "<CALL TO ACTION, max 4 words>",
      "subhead": "<follow for more / link in bio / watch next>",
      "highlight_word_indices": [],
      "animation_seed": {seed4}
    }}
  ]
}}

Rules:
- Write ALL headlines and subheads in the keyword's language ({language})
- Headlines: ALL CAPS, max 4 words, max 20 characters (like a movie title or news ticker)
- Subheads: sentence case, conversational, max 50 characters
- Scene 0: stop-the-scroll hook / title
- Scenes 1-3: build tension, reveal facts, maintain curiosity
- Scene 4: call to action
- Keep animation_seed values exactly as I provided (do not change them)
- No copyrighted long quotes. No dangerous claims. No unsafe advice."""


def _build_prompt(
    keyword: str,
    language: str,
    duration_seconds: int,
    chosen_idea: Optional[Idea],
) -> str:
    scene_dur = round(duration_seconds / 5, 1)
    seeds = [random.randint(1000, 9999) for _ in range(5)]
    idea_context = ""
    if chosen_idea:
        idea_context = (
            f"Chosen angle: {chosen_idea.angle}\n"
            f"Hook concept: {chosen_idea.hook}\n"
        )
    return _PROMPT_TMPL.format(
        keyword=keyword,
        language=language,
        duration=duration_seconds,
        scene_dur=scene_dur,
        idea_context=idea_context,
        seed0=seeds[0], seed1=seeds[1], seed2=seeds[2],
        seed3=seeds[3], seed4=seeds[4],
    )


# ── Public API ────────────────────────────────────────────────────────────────

async def generate_scene_timeline(
    job_id: str,
    keyword: str,
    language: str,
    duration_seconds: int,
    output_path: str,
    chosen_idea: Optional[Idea],
    provider: LLMAdapter,
    quality_mode: str = "final",
) -> Timeline:
    """
    Build a Timeline using the LLM provider.

    On any parse, validation, or API error: logs a warning and returns
    fixture_timeline() so the render job always continues.
    """
    prompt = _build_prompt(keyword, language, duration_seconds, chosen_idea)

    try:
        resp = await provider.generate(
            system=_SYSTEM,
            prompt=prompt,
            json_schema={"type": "object"},
        )
        data = json.loads(resp.content)
        scene_output = _GeminiSceneOutput.model_validate(data)

        if len(scene_output.scenes) != 5:
            raise ValueError(
                f"Expected 5 scenes, got {len(scene_output.scenes)}"
            )

        timeline = _map_to_timeline(
            job_id=job_id,
            keyword=keyword,
            language=language,
            output_path=output_path,
            scene_output=scene_output,
            quality_mode=quality_mode,
            duration_seconds=duration_seconds,
        )
        log.info(
            "LLM scene generation OK for job %s: %d scenes (provider=%s)",
            job_id, len(timeline.scenes), resp.model,
        )
        return timeline

    except (json.JSONDecodeError, ValidationError, ValueError) as exc:
        log.warning(
            "LLM scene output invalid for job %s (%s: %s) — using fixture fallback",
            job_id, type(exc).__name__, exc,
        )
    except Exception as exc:
        log.warning(
            "LLM scene generation error for job %s (%s) — using fixture fallback",
            job_id, type(exc).__name__,
        )

    from app.renderer.timeline import fixture_timeline
    return fixture_timeline(
        job_id=job_id,
        keyword=keyword,
        output_path=output_path,
        duration_seconds=duration_seconds,
        quality_mode=quality_mode,
    )


# ── Mapping ───────────────────────────────────────────────────────────────────

def _map_to_timeline(
    job_id: str,
    keyword: str,
    language: str,
    output_path: str,
    scene_output: _GeminiSceneOutput,
    quality_mode: str,
    duration_seconds: int,
) -> Timeline:
    preset = _QUALITY_PRESETS.get(quality_mode, _QUALITY_PRESETS["final"])
    resolution: tuple[int, int] = preset["resolution"]
    fps: int = preset["fps"]

    # Normalise durations: clamp negatives, rescale sum to duration_seconds
    raw = [max(0.5, s.duration_seconds) for s in scene_output.scenes]
    scale = duration_seconds / sum(raw)
    durations = [d * scale for d in raw]

    scenes: list[Scene] = []
    t = 0.0
    for i, (gs, dur) in enumerate(zip(scene_output.scenes, durations)):
        end = t + dur
        scenes.append(Scene(
            index=i,
            start=round(t, 3),
            end=round(end, 3),
            template="viral",
            props=SceneProps(
                headline=gs.headline[:30].upper(),
                subhead=gs.subhead[:60],
                highlight_word_indices=gs.highlight_word_indices,
                animation_seed=gs.animation_seed or (1000 + i * 37),
            ),
        ))
        t = end

    return Timeline(
        job_id=job_id,
        variant_id="v01",
        language=language,
        style="viral",
        format="9:16",
        quality_mode=quality_mode,
        resolution=resolution,
        fps=fps,
        duration_seconds=duration_seconds,
        audio=AudioConfig(music_bed=None, music_gain_db=-22.0),
        subtitles=SubtitleConfig(style="viral_bold"),
        scenes=scenes,
        output_path=output_path,
    )
