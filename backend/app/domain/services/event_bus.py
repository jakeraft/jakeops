from __future__ import annotations

import asyncio
from collections import defaultdict
from typing import Any, AsyncGenerator

_SENTINEL = object()


class EventBus:
    """In-memory pub/sub per delivery_id with replay buffer."""

    def __init__(self) -> None:
        self._buffers: dict[str, list[dict]] = defaultdict(list)
        self._subscribers: dict[str, list[asyncio.Queue]] = defaultdict(list)

    async def publish(self, delivery_id: str, event: dict[str, Any]) -> None:
        self._buffers[delivery_id].append(event)
        for queue in self._subscribers[delivery_id]:
            queue.put_nowait(event)

    async def subscribe(self, delivery_id: str) -> AsyncGenerator[dict[str, Any], None]:
        queue: asyncio.Queue = asyncio.Queue()
        # Replay buffered events
        for event in list(self._buffers.get(delivery_id, [])):
            queue.put_nowait(event)
        self._subscribers[delivery_id].append(queue)
        try:
            while True:
                item = await queue.get()
                if item is _SENTINEL:
                    break
                yield item
        finally:
            self._subscribers[delivery_id].remove(queue)

    async def close(self, delivery_id: str) -> None:
        for queue in self._subscribers.get(delivery_id, []):
            queue.put_nowait(_SENTINEL)
        self._buffers.pop(delivery_id, None)
        # subscribers clean themselves up in subscribe()

    def is_active(self, delivery_id: str) -> bool:
        return delivery_id in self._buffers
