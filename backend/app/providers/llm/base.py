"""
LLM adapter protocol. Switch provider via LLM_PROVIDER=gemini|openai|claude|mock env.
All adapters must implement this interface.
"""
from typing import Protocol, runtime_checkable
from dataclasses import dataclass


@dataclass
class LLMResponse:
    content: str
    model: str
    usage: dict


@runtime_checkable
class LLMAdapter(Protocol):
    async def generate(
        self,
        *,
        system: str,
        prompt: str,
        json_schema: dict | None = None,
    ) -> LLMResponse: ...


class MockLLMAdapter:
    """Phase 1 mock — returns fixture responses."""

    async def generate(
        self,
        *,
        system: str,
        prompt: str,
        json_schema: dict | None = None,
    ) -> LLMResponse:
        return LLMResponse(
            content='{"mock": true, "result": "Phase 1 mock response"}',
            model="mock",
            usage={"input_tokens": 0, "output_tokens": 0},
        )
