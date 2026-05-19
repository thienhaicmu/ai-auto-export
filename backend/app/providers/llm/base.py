"""
LLM adapter protocol. Switch provider via LLM_PROVIDER=gemini|mock env.
All adapters must implement LLMAdapter.
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
