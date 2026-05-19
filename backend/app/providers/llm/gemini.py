"""
Gemini LLM adapter using google-genai SDK (v1+).

Features:
  - Async via client.aio.models.generate_content()
  - JSON mode via response_mime_type="application/json"
  - System instruction set at request level
  - One automatic retry on invalid JSON or transient errors
  - API key NEVER logged or exposed
"""
from __future__ import annotations

import json
import logging

from app.providers.llm.base import LLMResponse

log = logging.getLogger(__name__)


class GeminiAdapter:
    def __init__(self, api_key: str, model: str = "gemini-2.0-flash") -> None:
        try:
            from google import genai
            from google.genai import types as genai_types
        except ImportError as exc:
            raise RuntimeError(
                "google-genai is not installed. Run: pip install google-genai"
            ) from exc

        self._client = genai.Client(api_key=api_key)
        self._types = genai_types
        self._model = model

    async def generate(
        self,
        *,
        system: str,
        prompt: str,
        json_schema: dict | None = None,
    ) -> LLMResponse:
        types = self._types

        cfg_kwargs: dict = {}
        if system:
            cfg_kwargs["system_instruction"] = system
        if json_schema is not None:
            cfg_kwargs["response_mime_type"] = "application/json"

        config = types.GenerateContentConfig(**cfg_kwargs) if cfg_kwargs else None

        last_exc: Exception | None = None
        for attempt in range(2):
            try:
                response = await self._client.aio.models.generate_content(
                    model=self._model,
                    contents=prompt,
                    config=config,
                )
                content = response.text

                # Validate JSON parsability when schema was requested
                if json_schema is not None:
                    json.loads(content)

                usage: dict = {}
                if hasattr(response, "usage_metadata") and response.usage_metadata:
                    meta = response.usage_metadata
                    usage = {
                        "input_tokens": getattr(meta, "prompt_token_count", 0),
                        "output_tokens": getattr(meta, "candidates_token_count", 0),
                    }

                log.info(
                    "Gemini %s responded (%d chars, attempt %d)",
                    self._model, len(content), attempt + 1,
                )
                return LLMResponse(content=content, model=self._model, usage=usage)

            except json.JSONDecodeError as exc:
                last_exc = exc
                if attempt == 0:
                    log.warning("Gemini returned invalid JSON on attempt 1 — retrying")
                    continue
                log.error("Gemini returned invalid JSON after retry")
                raise

            except Exception as exc:
                # Do NOT log exc message verbatim (may contain key fragment in HTTP trace)
                last_exc = exc
                if attempt == 0:
                    log.warning("Gemini API error on attempt 1 (%s) — retrying", type(exc).__name__)
                    continue
                log.error("Gemini API error after retry (%s)", type(exc).__name__)
                raise

        raise RuntimeError("Gemini generate failed") from last_exc
