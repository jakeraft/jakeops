import asyncio
import pytest
from app.domain.services.event_bus import EventBus


class TestEventBus:
    @pytest.fixture
    def bus(self):
        return EventBus()

    @pytest.mark.asyncio
    async def test_subscriber_receives_published_event(self, bus):
        events = []

        async def collect():
            async for event in bus.subscribe("d1"):
                events.append(event)
                break  # exit after first event

        task = asyncio.create_task(collect())
        await asyncio.sleep(0.01)
        await bus.publish("d1", {"type": "assistant", "message": {"role": "assistant"}})
        await task
        assert len(events) == 1
        assert events[0]["type"] == "assistant"

    @pytest.mark.asyncio
    async def test_late_subscriber_receives_buffered_events(self, bus):
        await bus.publish("d1", {"type": "system", "subtype": "init"})
        await bus.publish("d1", {"type": "assistant"})

        events = []
        async for event in bus.subscribe("d1"):
            events.append(event)
            if len(events) == 2:
                break
        assert len(events) == 2

    @pytest.mark.asyncio
    async def test_close_sends_sentinel_and_cleans_up(self, bus):
        events = []

        async def collect():
            async for event in bus.subscribe("d1"):
                events.append(event)

        task = asyncio.create_task(collect())
        await asyncio.sleep(0.01)
        await bus.publish("d1", {"type": "assistant"})
        await asyncio.sleep(0.01)
        await bus.close("d1")
        await task
        assert len(events) == 1  # sentinel not included

    @pytest.mark.asyncio
    async def test_multiple_subscribers(self, bus):
        results_a, results_b = [], []

        async def collect(target):
            async for event in bus.subscribe("d1"):
                target.append(event)
                break

        task_a = asyncio.create_task(collect(results_a))
        task_b = asyncio.create_task(collect(results_b))
        await asyncio.sleep(0.01)
        await bus.publish("d1", {"type": "assistant"})
        await asyncio.gather(task_a, task_b)
        assert len(results_a) == 1
        assert len(results_b) == 1

    @pytest.mark.asyncio
    async def test_is_active(self, bus):
        assert not bus.is_active("d1")
        await bus.publish("d1", {"type": "system"})
        assert bus.is_active("d1")
        await bus.close("d1")
        assert not bus.is_active("d1")
