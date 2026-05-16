"""
In-memory pub/sub per job_id.
Each subscriber gets an asyncio.Queue. Events are buffered (capped) for reconnect replay.
"""
import asyncio
from collections import defaultdict, deque
from typing import Any

from app.config import settings


class EventBus:
    def __init__(self) -> None:
        self._queues: dict[str, list[asyncio.Queue[dict[str, Any]]]] = defaultdict(list)
        self._buffers: dict[str, deque[dict[str, Any]]] = defaultdict(
            lambda: deque(maxlen=settings.max_event_buffer)
        )

    def subscribe(self, job_id: str, since_ts: int = 0) -> "asyncio.Queue[dict[str, Any]]":
        q: asyncio.Queue[dict[str, Any]] = asyncio.Queue()
        # replay buffered events the client missed
        for event in self._buffers[job_id]:
            if event.get("ts", 0) >= since_ts:
                q.put_nowait(event)
        self._queues[job_id].append(q)
        return q

    def unsubscribe(self, job_id: str, q: "asyncio.Queue[dict[str, Any]]") -> None:
        try:
            self._queues[job_id].remove(q)
        except ValueError:
            pass

    async def publish(self, job_id: str, event: dict[str, Any]) -> None:
        self._buffers[job_id].append(event)
        for q in list(self._queues[job_id]):
            await q.put(event)

    def clear(self, job_id: str) -> None:
        self._queues.pop(job_id, None)
        self._buffers.pop(job_id, None)


# Singleton shared across all routers
event_bus = EventBus()
