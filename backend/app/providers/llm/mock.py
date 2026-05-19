"""
Mock LLM adapter — returns fixture data that matches each pipeline node's expected JSON schema.
Used when LLM_PROVIDER=mock or when GEMINI_API_KEY is absent.
"""
import json
import re

from app.providers.llm.base import LLMResponse


def _extract_keyword(prompt: str) -> str:
    """Pull keyword from 'Keyword: "..."' or 'Keyword: ...' line."""
    m = re.search(r'[Kk]eyword[:\s]+["\']?([^"\'\n]+)["\']?', prompt)
    return m.group(1).strip() if m else "untitled"


class MockLLMAdapter:
    """Context-aware mock: inspects system prompt to return the right fixture JSON."""

    async def generate(
        self,
        *,
        system: str,
        prompt: str,
        json_schema: dict | None = None,
    ) -> LLMResponse:
        ctx = (system + " " + prompt).lower()

        if "scene" in ctx and "headline" in ctx:
            content = self._scenes(prompt)
        elif "idea" in ctx or "angle" in ctx:
            content = self._ideas(prompt)
        elif "research" in ctx:
            content = self._research(prompt)
        else:
            content = json.dumps({"mock": True, "result": "mock response"})

        return LLMResponse(content=content, model="mock", usage={"input_tokens": 0, "output_tokens": 0})

    # ── Fixture generators ────────────────────────────────────────────────────

    def _ideas(self, prompt: str) -> str:
        kw = _extract_keyword(prompt)
        return json.dumps({
            "language": "en",
            "ideas": [
                {
                    "id": "mock_01",
                    "title": f"{kw.title()} — The Untold Story",
                    "angle": "controversy",
                    "hook": f"What nobody tells you about {kw}",
                    "estimated_views": "500K-2M",
                },
                {
                    "id": "mock_02",
                    "title": f"The Rise of {kw.title()}",
                    "angle": "timeline",
                    "hook": f"How {kw} changed everything in 60 seconds",
                    "estimated_views": "200K-800K",
                },
                {
                    "id": "mock_03",
                    "title": f"{kw.title()} Exposed",
                    "angle": "viral_hook",
                    "hook": f"You won't believe what {kw} did next",
                    "estimated_views": "1M-5M",
                },
            ],
        })

    @staticmethod
    def _vd(role: str) -> dict:
        return {
            "hook":       {"energy_level": 5, "motion_intensity": "impact",  "layout_mode": "center",      "transition_style": "flash",  "emphasis_words": [],    "background_treatment": "dark_image",    "subtitle_emphasis": True,  "pacing_note": "Slam cut with white flash — stop the scroll."},
            "context":    {"energy_level": 2, "motion_intensity": "calm",    "layout_mode": "lower_third", "transition_style": "cut",    "emphasis_words": [],    "background_treatment": "blurred_image", "subtitle_emphasis": False, "pacing_note": "Slow reveal, let viewer absorb the context."},
            "escalation": {"energy_level": 4, "motion_intensity": "high",    "layout_mode": "split",       "transition_style": "zoom",   "emphasis_words": [],    "background_treatment": "dark_image",    "subtitle_emphasis": True,  "pacing_note": "Push zoom tightens tension to a breaking point."},
            "twist":      {"energy_level": 4, "motion_intensity": "high",    "layout_mode": "full_bleed",  "transition_style": "glitch", "emphasis_words": [],    "background_treatment": "abstract",      "subtitle_emphasis": True,  "pacing_note": "Glitch entry mirrors the mind-bending revelation."},
            "payoff":     {"energy_level": 3, "motion_intensity": "medium",  "layout_mode": "center",      "transition_style": "zoom",   "emphasis_words": [],    "background_treatment": "gradient",      "subtitle_emphasis": False, "pacing_note": "Confident close — drive the CTA home."},
        }.get(role, {"energy_level": 3, "motion_intensity": "medium", "layout_mode": "center", "transition_style": "cut", "emphasis_words": [], "background_treatment": "gradient", "subtitle_emphasis": False, "pacing_note": ""})

    def _scenes(self, prompt: str) -> str:
        kw = _extract_keyword(prompt)
        kw_up = kw.upper()[:20]

        # Try to extract duration from prompt
        m = re.search(r'duration[:\s]+(\d+)', prompt, re.I)
        total = int(m.group(1)) if m else 30
        scene_dur = round(total / 5, 1)

        kw_words = kw.lower().split()[:2]
        return json.dumps({
            "hook": f"{kw_up} — the truth they don't want you to know",
            "scenes": [
                {
                    "index": 0,
                    "role": "hook",
                    "duration_seconds": scene_dur,
                    "headline": kw_up,
                    "subhead": "The untold story",
                    "highlight_word_indices": [0],
                    "animation_seed": 1000,
                    "visual_keywords": kw_words + ["shocking", "breaking"],
                    "emotional_tone": "shocking",
                    "visual_direction": self._vd("hook"),
                },
                {
                    "index": 1,
                    "role": "context",
                    "duration_seconds": scene_dur,
                    "headline": "WHAT THEY",
                    "subhead": "Hidden for years",
                    "highlight_word_indices": [],
                    "animation_seed": 1037,
                    "visual_keywords": kw_words + ["background", "history"],
                    "emotional_tone": "curious",
                    "visual_direction": self._vd("context"),
                },
                {
                    "index": 2,
                    "role": "escalation",
                    "duration_seconds": scene_dur,
                    "headline": "DON'T WANT",
                    "subhead": "Exposed at last",
                    "highlight_word_indices": [],
                    "animation_seed": 1074,
                    "visual_keywords": kw_words + ["tension", "conflict"],
                    "emotional_tone": "tense",
                    "visual_direction": self._vd("escalation"),
                },
                {
                    "index": 3,
                    "role": "twist",
                    "duration_seconds": scene_dur,
                    "headline": "YOU TO KNOW",
                    "subhead": "The real truth",
                    "highlight_word_indices": [],
                    "animation_seed": 1111,
                    "visual_keywords": kw_words + ["reveal", "surprise"],
                    "emotional_tone": "revelatory",
                    "visual_direction": self._vd("twist"),
                },
                {
                    "index": 4,
                    "role": "payoff",
                    "duration_seconds": scene_dur,
                    "headline": "FIND OUT NOW",
                    "subhead": "Watch till the end",
                    "highlight_word_indices": [],
                    "animation_seed": 1148,
                    "visual_keywords": kw_words + ["success", "victory"],
                    "emotional_tone": "triumphant",
                    "visual_direction": self._vd("payoff"),
                },
            ],
        })

    def _research(self, prompt: str) -> str:
        kw = _extract_keyword(prompt)
        return json.dumps({
            "summary": f"High viral potential detected for '{kw}'",
            "angles": ["controversy", "timeline", "viral hook"],
            "context": f"Mock research context for {kw}",
        })
