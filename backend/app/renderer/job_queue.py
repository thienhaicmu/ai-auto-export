"""
Bounded concurrent render queue.
MAX_CONCURRENT_VARIANTS variants render in parallel (default 2).
"""
import asyncio
import logging
from app.config import settings

log = logging.getLogger(__name__)

_semaphore: asyncio.Semaphore | None = None


def get_semaphore() -> asyncio.Semaphore:
    global _semaphore
    if _semaphore is None:
        _semaphore = asyncio.Semaphore(settings.max_concurrent_variants)
    return _semaphore


async def acquire_render_slot() -> None:
    await get_semaphore().acquire()
    log.debug("Render slot acquired")


def release_render_slot() -> None:
    get_semaphore().release()
    log.debug("Render slot released")
