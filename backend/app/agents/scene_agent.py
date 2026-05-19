"""
Scene generation agent.

Flow:
  1. story_planner.plan_story() assigns roles, durations, visual keywords (no LLM)
  2. LLM generates specific headlines/subheads/etc. guided by the story plan
  3. Pydantic validates the full response; retry once on failure
  4. Maps to Timeline; falls back to fixture_timeline() on any error

The 5-scene narrative structure is:
  hook → context → escalation → twist → payoff/CTA
"""
from __future__ import annotations

import json
import logging
import random
from typing import Optional

from pydantic import BaseModel, ValidationError, field_validator

from app.agents.story_planner import StoryPlan, plan_story
from app.models.job import (
    AudioConfig, Idea, Scene, SceneProps, SubtitleConfig, Timeline,
)
from app.providers.llm.base import LLMAdapter

log = logging.getLogger(__name__)

_QUALITY_PRESETS: dict[str, dict] = {
    "preview": {"resolution": (480, 854),  "fps": 24},
    "final":   {"resolution": (1080, 1920), "fps": 30},
}

# ── Pydantic schema for Gemini output ────────────────────────────────────────

class _GeminiScene(BaseModel):
    index: int
    role: str                            # hook|context|escalation|twist|payoff
    duration_seconds: float
    headline: str                        # ALL CAPS, max 4 words / 20 chars
    subhead: str = ""                    # sentence case, max 50 chars
    highlight_word_indices: list[int] = []
    animation_seed: int = 0
    visual_keywords: list[str] = []     # 2-4 keywords for background image search
    emotional_tone: str = "energetic"

    @field_validator("headline", mode="before")
    @classmethod
    def _clean_headline(cls, v: str) -> str:
        return str(v).strip().upper()[:30] or "UNTITLED"

    @field_validator("duration_seconds", mode="before")
    @classmethod
    def _positive_dur(cls, v: float) -> float:
        return max(0.5, float(v))

    @field_validator("subhead", mode="before")
    @classmethod
    def _clean_subhead(cls, v: str) -> str:
        return str(v).strip()[:60]


class _GeminiSceneOutput(BaseModel):
    hook: str = ""
    scenes: list[_GeminiScene]


# ── Prompt templates ──────────────────────────────────────────────────────────

_SYSTEM = """\
You are a viral short-form video script writer for TikTok, Instagram Reels, and YouTube Shorts.
Create exactly 5 scenes that follow the provided narrative structure.
Respond ONLY with valid JSON — no explanation, no markdown fences, no comments."""


def _build_prompt(
    keyword: str,
    language: str,
    duration_seconds: int,
    plan: StoryPlan,
    chosen_idea: Optional[Idea],
) -> str:
    # Describe each planned scene with its role, duration and guidance
    scenes_spec = ""
    for sp in plan.scenes:
        vk_str = ", ".join(sp.visual_keywords[:4])
        scenes_spec += (
            f"  Scene {sp.index} — role: {sp.role} | "
            f"duration: {sp.duration_seconds}s | "
            f"tone: {sp.emotional_tone} | "
            f"visual keywords: {vk_str}\n"
            f"  Guidance: {sp.guidance}\n"
        )

    idea_ctx = ""
    if chosen_idea:
        idea_ctx = f"Chosen angle: {chosen_idea.angle}\nHook concept: {chosen_idea.hook}\n"

    # Build the example scene block for the JSON template
    def _example_scene(sp) -> str:
        seed = random.randint(1000, 9999)
        vk_example = json.dumps(sp.visual_keywords[:3])
        return (
            f"    {{\n"
            f'      "index": {sp.index},\n'
            f'      "role": "{sp.role}",\n'
            f'      "duration_seconds": {sp.duration_seconds},\n'
            f'      "headline": "<ALL CAPS, max 4 words, max 20 chars>",\n'
            f'      "subhead": "<sentence case, max 50 chars>",\n'
            f'      "highlight_word_indices": [{",".join(str(i) for i in ([0] if sp.index == 0 else []))}],\n'
            f'      "animation_seed": {seed},\n'
            f'      "visual_keywords": {vk_example},\n'
            f'      "emotional_tone": "{sp.emotional_tone}"\n'
            f"    }}"
        )

    scenes_json = ",\n".join(_example_scene(sp) for sp in plan.scenes)

    return f"""\
Keyword: "{keyword}"
Language: {language}
Total video duration: {duration_seconds} seconds
{idea_ctx}
Narrative structure to follow:
{scenes_spec}
CRITICAL RULES:
- Write ALL text in the keyword's language ({language})
- Headlines: ALL CAPS, max 4 words, max 20 characters (news-ticker style)
- Subheads: sentence case, conversational, max 50 characters
- Scene 0 (hook): single shocking statement that stops the scroll instantly
- Scene 4 (payoff): short CTA (follow / share / comment)
- visual_keywords: 2-4 English words for background image search regardless of video language
- animation_seed: unique random integer, keep the example values as-is
- No copyrighted long quotes. No dangerous claims.

Return this JSON structure exactly (replace angle-bracket placeholders with real content):
{{
  "hook": "<overall video hook, ALL CAPS, max 40 chars>",
  "scenes": [
{scenes_json}
  ]
}}"""


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
    Build a Timeline via the story planner + LLM.

    Fallback chain on any error: fixture_timeline().
    """
    # Step 1 — story plan (pure algorithm, no LLM)
    plan = plan_story(keyword=keyword, language=language, duration_seconds=duration_seconds)
    log.info("Story plan for job %s: roles=%s", job_id, [s.role for s in plan.scenes])

    # Step 2 — LLM scene generation guided by the plan
    prompt = _build_prompt(keyword, language, duration_seconds, plan, chosen_idea)

    try:
        resp = await provider.generate(
            system=_SYSTEM,
            prompt=prompt,
            json_schema={"type": "object"},
        )
        data = json.loads(resp.content)
        scene_output = _GeminiSceneOutput.model_validate(data)

        if len(scene_output.scenes) != 5:
            raise ValueError(f"Expected 5 scenes, got {len(scene_output.scenes)}")

        # Step 3 — map to Timeline (with normalised durations)
        timeline = _map_to_timeline(
            job_id=job_id,
            keyword=keyword,
            language=language,
            output_path=output_path,
            scene_output=scene_output,
            plan=plan,
            quality_mode=quality_mode,
            duration_seconds=duration_seconds,
        )
        log.info(
            "LLM scene generation OK for job %s (%d scenes via %s)",
            job_id, len(timeline.scenes), resp.model,
        )
        return timeline

    except (json.JSONDecodeError, ValidationError, ValueError) as exc:
        log.warning(
            "LLM scene output invalid for job %s (%s: %s) — fixture fallback",
            job_id, type(exc).__name__, exc,
        )
    except Exception as exc:
        log.warning(
            "LLM scene generation error for job %s (%s) — fixture fallback",
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
    plan: StoryPlan,
    quality_mode: str,
    duration_seconds: int,
) -> Timeline:
    preset = _QUALITY_PRESETS.get(quality_mode, _QUALITY_PRESETS["final"])
    resolution: tuple[int, int] = preset["resolution"]
    fps: int = preset["fps"]

    # Normalise durations so they sum exactly to duration_seconds
    raw = [max(0.5, s.duration_seconds) for s in scene_output.scenes]
    scale = duration_seconds / sum(raw)
    durations = [d * scale for d in raw]

    scenes: list[Scene] = []
    t = 0.0
    for i, (gs, dur, sp) in enumerate(zip(scene_output.scenes, durations, plan.scenes)):
        end = t + dur
        # visual_keywords are stored as a custom attribute (not in SceneProps Pydantic model)
        # so we propagate them through props using a workaround via __dict__
        props = SceneProps(
            headline=gs.headline[:30].upper(),
            subhead=gs.subhead[:60],
            highlight_word_indices=gs.highlight_word_indices,
            animation_seed=gs.animation_seed or (1000 + i * 37),
        )
        # Attach visual_keywords as an extra attr so asset_agent can read it
        # (Pydantic v2 model_config extra="allow" would be needed; instead we
        #  stash it in a simple list the asset_agent reads via getattr)
        object.__setattr__(props, "visual_keywords",
                           gs.visual_keywords or sp.visual_keywords)

        scenes.append(Scene(
            index=i,
            start=round(t, 3),
            end=round(end, 3),
            template="viral",
            role=gs.role,
            props=props,
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
