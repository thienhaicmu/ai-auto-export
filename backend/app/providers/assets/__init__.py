"""
Asset provider factory.

Resolution order for ASSET_PROVIDER=pexels|pixabay|unsplash:
  - Corresponding API key set  → real provider
  - Key missing                → MockAssetProvider (warning logged)
  - Import error               → MockAssetProvider (warning logged)

ASSET_PROVIDER=mock (or any other value) → MockAssetProvider
Results in gradient / text-only backgrounds for all scenes.

The resolved adapter is cached as a module-level singleton.
"""
import logging
from typing import cast

from app.providers.assets.base import AssetProvider

log = logging.getLogger(__name__)

_provider: AssetProvider | None = None


def get_asset_provider() -> AssetProvider:
    global _provider
    if _provider is not None:
        return _provider

    from app.config import settings

    name = settings.asset_provider.lower()

    if name == "pexels":
        if not settings.pexels_api_key:
            log.warning("ASSET_PROVIDER=pexels but PEXELS_API_KEY is not set — using mock")
            _provider = _make_mock()
        else:
            from app.providers.assets.pexels import PexelsProvider
            _provider = cast(AssetProvider, PexelsProvider(api_key=settings.pexels_api_key))
            log.info("Pexels asset provider ready")

    elif name == "pixabay":
        if not settings.pixabay_api_key:
            log.warning("ASSET_PROVIDER=pixabay but PIXABAY_API_KEY is not set — using mock")
            _provider = _make_mock()
        else:
            from app.providers.assets.pixabay import PixabayProvider
            _provider = cast(AssetProvider, PixabayProvider(api_key=settings.pixabay_api_key))
            log.info("Pixabay asset provider ready")

    elif name == "unsplash":
        if not settings.unsplash_access_key:
            log.warning("ASSET_PROVIDER=unsplash but UNSPLASH_ACCESS_KEY is not set — using mock")
            _provider = _make_mock()
        else:
            from app.providers.assets.unsplash import UnsplashProvider
            _provider = cast(AssetProvider, UnsplashProvider(access_key=settings.unsplash_access_key))
            log.info("Unsplash asset provider ready")

    else:
        _provider = _make_mock()

    return _provider


def reset_provider() -> None:
    """Force re-initialisation on next call (useful in tests)."""
    global _provider
    _provider = None


def _make_mock() -> AssetProvider:
    from app.providers.assets.mock import MockAssetProvider
    log.info("Mock asset provider active — scenes will use gradient backgrounds")
    return cast(AssetProvider, MockAssetProvider())
