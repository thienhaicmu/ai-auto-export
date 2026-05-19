"""
Mock asset provider — always returns an empty candidate list.

Signals to the asset agent to use a gradient / text-only background for every
scene. Safe to use without any external API keys.
"""
from app.providers.assets.base import AssetCandidate


class MockAssetProvider:
    async def search(self, query: str, per_page: int = 10) -> list[AssetCandidate]:
        return []
