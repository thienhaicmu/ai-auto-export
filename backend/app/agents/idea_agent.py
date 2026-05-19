"""
Idea generation agent.

Calls the LLM provider to generate 3 distinct video ideas for a given keyword.
Falls back to an empty list (caller must supply fallback ideas) on any error.
"""
from __future__ import annotations

import json
import logging
from typing import Optional

from pydantic import BaseModel, ValidationError

from app.models.job import Idea
from app.providers.llm.base import LLMAdapter

log = logging.getLogger(__name__)

_SYSTEM = """\
You are a viral short-form video strategist for TikTok, Instagram Reels, and YouTube Shorts.
Generate exactly 3 distinct video idea concepts for the given keyword.
Respond ONLY with valid JSON matching the schema exactly — no explanation, no markdown fences."""

_PROMPT_TMPL = """\
Keyword: "{keyword}"

Return this JSON structure exactly:
{{
  "language": "<BCP-47 code detected from the keyword, e.g. en, vi, zh, ja, ko>",
  "ideas": [
    {{
      "id": "idea_01",
      "title": "<compelling video title, max 70 chars>",
      "angle": "<one word: controversy | timeline | viral_hook | listicle | expose>",
      "hook": "<scroll-stopping first line, max 80 chars>",
      "estimated_views": "<view range e.g. 500K-2M>"
    }},
    {{
      "id": "idea_02",
      "title": "<genuinely different angle title>",
      "angle": "<different angle>",
      "hook": "<different hook>",
      "estimated_views": "<range>"
    }},
    {{
      "id": "idea_03",
      "title": "<third angle title>",
      "angle": "<different angle>",
      "hook": "<different hook>",
      "estimated_views": "<range>"
    }}
  ]
}}

Rules:
- Detect the keyword's language and set "language" to the correct BCP-47 code
- Each idea MUST use a genuinely different angle
- Write titles and hooks in the same language as the keyword
- Hooks must create immediate curiosity or controversy
- No copyrighted content. No dangerous misinformation. No unsafe advice."""


class _IdeasOutput(BaseModel):
    language: str = "en"
    ideas: list[Idea]


async def generate_ideas(keyword: str, provider: LLMAdapter) -> tuple[list[Idea], str]:
    """
    Generate video ideas for *keyword* using *provider*.

    Returns (ideas, language). Returns ([], "en") on any error so the caller
    can supply fallback mock ideas without crashing.
    """
    prompt = _PROMPT_TMPL.format(keyword=keyword)

    try:
        resp = await provider.generate(
            system=_SYSTEM,
            prompt=prompt,
            json_schema={"type": "object"},
        )
        data = json.loads(resp.content)
        output = _IdeasOutput.model_validate(data)

        if not output.ideas:
            raise ValueError("LLM returned empty ideas list")

        log.info("Idea generation OK: %d ideas (lang=%s)", len(output.ideas), output.language)
        return output.ideas, output.language

    except (json.JSONDecodeError, ValidationError, ValueError, KeyError) as exc:
        log.warning("Idea generation parse error (%s: %s)", type(exc).__name__, exc)
        return [], "en"
    except Exception as exc:
        log.warning("Idea generation failed (%s) — returning empty list", type(exc).__name__)
        return [], "en"
