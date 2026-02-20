from __future__ import annotations

import asyncio
from collections import defaultdict, deque
from typing import Any, AsyncGenerator

_SENTINEL = object()

MAX_BUFFER_SIZE = 2000


class EventBus:
    """In-memory pub/sub per delivery_id with replay buffer."""

    def __init__(self) -> None:
        self._buffers: dict[str, deque[dict]] = defaultdict(
            lambda: deque(maxlen=MAX_BUFFER_SIZE)
        )
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
        # Snapshot subscriber list to avoid mutation during iteration
        queues = list(self._subscribers.get(delivery_id, []))
        for queue in queues:
            queue.put_nowait(_SENTINEL)
        self._buffers.pop(delivery_id, None)

    def is_active(self, delivery_id: str) -> bool:
        return delivery_id in self._buffers
