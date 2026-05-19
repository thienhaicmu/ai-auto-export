"""
LLM provider factory.

Resolution order for LLM_PROVIDER=gemini:
  1. GEMINI_API_KEY set  → GeminiAdapter
  2. GEMINI_API_KEY missing → MockLLMAdapter (warning logged)
  3. google-generativeai not installed → MockLLMAdapter (warning logged)

LLM_PROVIDER=mock (or any other value) → MockLLMAdapter

The resolved adapter is cached as a module-level singleton.
"""
import logging
from typing import cast

from app.providers.llm.base import LLMAdapter

log = logging.getLogger(__name__)

_provider: LLMAdapter | None = None


def get_llm_provider() -> LLMAdapter:
    global _provider
    if _provider is not None:
        return _provider

    from app.config import settings

    name = settings.llm_provider.lower()

    if name == "gemini":
        if not settings.gemini_api_key:
            log.warning(
                "LLM_PROVIDER=gemini but GEMINI_API_KEY is not set — falling back to mock provider"
            )
            _provider = _make_mock()
        else:
            try:
                from app.providers.llm.gemini import GeminiAdapter
                _provider = GeminiAdapter(
                    api_key=settings.gemini_api_key,
                    model=settings.gemini_model,
                )
                log.info("Gemini LLM provider ready (model=%s)", settings.gemini_model)
            except (ImportError, RuntimeError) as exc:
                log.warning(
                    "Gemini provider unavailable (%s: %s) — falling back to mock",
                    type(exc).__name__, exc,
                )
                _provider = _make_mock()
    else:
        _provider = _make_mock()

    return _provider


def reset_provider() -> None:
    """Force re-initialisation on next call (useful in tests)."""
    global _provider
    _provider = None


def _make_mock() -> LLMAdapter:
    from app.providers.llm.mock import MockLLMAdapter
    log.info("Mock LLM provider active")
    return cast(LLMAdapter, MockLLMAdapter())
