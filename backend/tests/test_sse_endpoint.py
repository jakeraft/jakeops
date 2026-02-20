import asyncio

import httpx
import pytest
from fastapi import FastAPI

from app.adapters.inbound.deliveries import router
from app.domain.services.event_bus import EventBus


@pytest.fixture
def event_bus():
    return EventBus()


@pytest.fixture
def app(event_bus):
    test_app = FastAPI()
    test_app.include_router(router, prefix="/api")
    test_app.state.event_bus = event_bus
    test_app.state.delivery_usecases = None
    return test_app


class TestSSEStream:
    @pytest.mark.asyncio
    async def test_stream_returns_event_stream_content_type(self, app, event_bus):
        await event_bus.publish("d1", {"type": "system", "subtype": "init"})

        async def close_soon():
            await asyncio.sleep(0.05)
            await event_bus.close("d1")

        transport = httpx.ASGITransport(app=app)
        async with httpx.AsyncClient(transport=transport, base_url="http://test") as ac:
            close_task = asyncio.create_task(close_soon())
            response = await ac.get("/api/deliveries/d1/stream")
            await close_task
            assert response.status_code == 200
            assert "text/event-stream" in response.headers["content-type"]

    @pytest.mark.asyncio
    async def test_stream_sends_events_as_sse(self, app, event_bus):
        await event_bus.publish(
            "d1", {"type": "assistant", "message": {"role": "assistant"}}
        )

        async def close_soon():
            await asyncio.sleep(0.05)
            await event_bus.close("d1")

        transport = httpx.ASGITransport(app=app)
        async with httpx.AsyncClient(transport=transport, base_url="http://test") as ac:
            close_task = asyncio.create_task(close_soon())
            response = await ac.get("/api/deliveries/d1/stream")
            await close_task
            body = response.text
            assert "data:" in body
            assert "assistant" in body

    @pytest.mark.asyncio
    async def test_stream_sends_done_event_on_close(self, app, event_bus):
        async def close_soon():
            await asyncio.sleep(0.05)
            await event_bus.close("d1")

        transport = httpx.ASGITransport(app=app)
        async with httpx.AsyncClient(transport=transport, base_url="http://test") as ac:
            close_task = asyncio.create_task(close_soon())
            response = await ac.get("/api/deliveries/d1/stream")
            await close_task
            body = response.text
            assert "event: done" in body
