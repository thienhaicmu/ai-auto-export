"""
Story rhythm planner — pure algorithmic, no LLM call.

Assigns the 5-scene short-form structure before Gemini generates specific content:
  0. hook        — stop-the-scroll opener
  1. context     — what is this and why does it matter
  2. escalation  — raise stakes, build tension
  3. twist       — unexpected truth / key insight
  4. payoff      — call to action / conclusion

Outputs a StoryPlan that is injected into the Gemini scene-generation prompt so
every scene knows its narrative role, ideal duration, and visual search keywords.
"""
from __future__ import annotations

from dataclasses import dataclass, field

# Ordered list of roles — index = scene index
ROLES: list[str] = ["hook", "context", "escalation", "twist", "payoff"]

# Per-role profile: duration weight, emotional tone, base visual keywords
_ROLE_PROFILES: dict[str, dict] = {
    "hook": {
        "weight": 0.9,             # slightly shorter — snap hook
        "emotional_tone": "shocking",
        "visual_keywords": ["dramatic", "bold", "intense", "eye-catching"],
        "guidance": "Stop-the-scroll opening. ONE punchy statement that creates immediate curiosity.",
    },
    "context": {
        "weight": 1.0,
        "emotional_tone": "curious",
        "visual_keywords": ["background", "documentary", "serious", "reveal"],
        "guidance": "Establish the stakes. What is this, and why should the viewer care?",
    },
    "escalation": {
        "weight": 1.1,
        "emotional_tone": "tense",
        "visual_keywords": ["conflict", "tension", "dramatic", "crisis"],
        "guidance": "Build tension. Things get worse before they get better.",
    },
    "twist": {
        "weight": 1.2,             # longest — give the insight room to land
        "emotional_tone": "revelatory",
        "visual_keywords": ["truth", "revelation", "surprise", "exposed"],
        "guidance": "The unexpected truth or key insight that reframes everything.",
    },
    "payoff": {
        "weight": 0.8,             # short CTA
        "emotional_tone": "triumphant",
        "visual_keywords": ["action", "follow", "conclusion", "impact"],
        "guidance": "Call to action. Subscribe / share / comment — keep it tight.",
    },
}


@dataclass
class ScenePace:
    index: int
    role: str
    duration_seconds: float
    emotional_tone: str
    visual_keywords: list[str]    # base keywords from role + keyword-derived terms
    guidance: str                 # short directive fed into the LLM prompt


@dataclass
class StoryPlan:
    keyword: str
    language: str
    total_duration: int
    scenes: list[ScenePace]       # always 5 entries


def plan_story(keyword: str, language: str, duration_seconds: int) -> StoryPlan:
    """
    Build a 5-scene rhythm plan for *keyword*.

    Durations are weighted so the twist scene gets the most time and the
    hook/payoff are snappy. The last scene absorbs any rounding remainder.
    """
    weights = [_ROLE_PROFILES[r]["weight"] for r in ROLES]
    total_w = sum(weights)

    # Compute durations; round to 1 decimal, fix remainder on last scene
    durations: list[float] = []
    for w in weights[:-1]:
        durations.append(round(w / total_w * duration_seconds, 1))
    durations.append(round(duration_seconds - sum(durations), 1))

    # Derive keyword-contextual terms (simple: keyword words + role keywords)
    kw_words = [w.lower() for w in keyword.split() if len(w) > 2]

    scenes: list[ScenePace] = []
    for i, (role, dur) in enumerate(zip(ROLES, durations)):
        profile = _ROLE_PROFILES[role]
        # Blend keyword words with role-specific visual keywords (dedup, cap at 6)
        vk = list(dict.fromkeys(kw_words + profile["visual_keywords"]))[:6]
        scenes.append(ScenePace(
            index=i,
            role=role,
            duration_seconds=dur,
            emotional_tone=profile["emotional_tone"],
            visual_keywords=vk,
            guidance=profile["guidance"],
        ))

    return StoryPlan(
        keyword=keyword,
        language=language,
        total_duration=duration_seconds,
        scenes=scenes,
    )
