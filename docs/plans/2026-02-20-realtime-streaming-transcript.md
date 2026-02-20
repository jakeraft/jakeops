# Real-time Streaming Transcript Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Stream Claude CLI events to the frontend in real-time via SSE so users see live transcript on the delivery show page during agent execution.

**Architecture:** Claude CLI `--output-format stream-json` produces NDJSON events on stdout. A new `run_stream()` method on the CLI adapter yields these as `StreamEvent`. An in-memory `EventBus` broadcasts events per delivery. A new SSE endpoint streams them to the frontend. A `useEventStream` hook + `LiveTranscript` component render events inline on the show page.

**Tech Stack:** FastAPI StreamingResponse (SSE), asyncio.Queue, React EventSource API, existing StreamEvent/MessageRenderer components.

---

### Task 1: EventBus — in-memory pub/sub service

**Files:**
- Create: `backend/app/domain/services/event_bus.py`
- Test: `backend/tests/test_event_bus.py`

**Step 1: Write the failing test**

```python
# backend/tests/test_event_bus.py
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
```

**Step 2: Run test to verify it fails**

Run: `cd backend && python -m pytest tests/test_event_bus.py -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'app.domain.services.event_bus'`

**Step 3: Write minimal implementation**

```python
# backend/app/domain/services/event_bus.py
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
```

**Step 4: Run test to verify it passes**

Run: `cd backend && python -m pytest tests/test_event_bus.py -v`
Expected: All 5 tests PASS

**Step 5: Commit**

```
git add backend/app/domain/services/event_bus.py backend/tests/test_event_bus.py
git commit -m "feat: add EventBus in-memory pub/sub for delivery streaming"
```

---

### Task 2: ClaudeCliAdapter.run_stream() method

**Files:**
- Modify: `backend/app/adapters/outbound/claude_cli.py:11-67`
- Modify: `backend/app/ports/outbound/subprocess_runner.py:6-25`
- Test: `backend/tests/test_claude_cli_stream.py` (add new class)

**Step 1: Write the failing test**

Add to `backend/tests/test_claude_cli_stream.py`:

```python
class TestRunStream:
    @pytest.fixture
    def adapter(self):
        return ClaudeCliAdapter()

    def test_yields_stream_events(self, adapter, monkeypatch):
        lines = [
            json.dumps({"type": "system", "subtype": "init", "message": {"model": "opus"}}),
            json.dumps({"type": "assistant", "message": {"role": "assistant", "content": [{"type": "text", "text": "hi"}]}}),
            json.dumps({"type": "result", "subtype": "success", "message": {"result": "done", "is_error": False, "cost_usd": 0.01, "input_tokens": 10, "output_tokens": 5, "duration_ms": 100}}),
        ]

        async def fake_create_subprocess_exec(*args, **kwargs):
            class FakeStdout:
                def __init__(self):
                    self._lines = iter([line.encode() + b"\n" for line in lines])
                async def readline(self):
                    try:
                        return next(self._lines)
                    except StopIteration:
                        return b""
            class FakeProc:
                returncode = 0
                stdout = FakeStdout()
                stderr = None
                async def wait(self):
                    pass
            return FakeProc()

        monkeypatch.setattr("asyncio.create_subprocess_exec", fake_create_subprocess_exec)

        events = []
        async def run():
            async for ev in adapter.run_stream("prompt", "/tmp"):
                events.append(ev)

        asyncio.run(run())
        assert len(events) == 3
        assert events[0]["type"] == "system"
        assert events[2]["type"] == "result"

    def test_uses_stream_json_format(self, adapter, monkeypatch):
        captured_args = []

        async def fake_create_subprocess_exec(*args, **kwargs):
            captured_args.extend(args)
            class FakeStdout:
                async def readline(self):
                    return b""
            class FakeProc:
                returncode = 0
                stdout = FakeStdout()
                stderr = None
                async def wait(self):
                    pass
            return FakeProc()

        monkeypatch.setattr("asyncio.create_subprocess_exec", fake_create_subprocess_exec)
        asyncio.run(async_exhaust(adapter.run_stream("p", "/tmp")))
        assert "--output-format" in captured_args
        idx = captured_args.index("--output-format")
        assert captured_args[idx + 1] == "stream-json"


async def async_exhaust(agen):
    async for _ in agen:
        pass
```

**Step 2: Run test to verify it fails**

Run: `cd backend && python -m pytest tests/test_claude_cli_stream.py::TestRunStream -v`
Expected: FAIL — `AttributeError: 'ClaudeCliAdapter' object has no attribute 'run_stream'`

**Step 3: Update Protocol and implement run_stream**

Add to `backend/app/ports/outbound/subprocess_runner.py`:

```python
from typing import Protocol, AsyncGenerator, Any

class SubprocessRunner(Protocol):
    # ... existing run() and kill() ...

    async def run_stream(
        self,
        prompt: str,
        cwd: str,
        allowed_tools: list[str] | None = None,
        append_system_prompt: str | None = None,
        delivery_id: str | None = None,
    ) -> AsyncGenerator[dict[str, Any], None]:
        """Run `claude -p --output-format stream-json`.
        Yields parsed JSON events line by line.
        """
        ...
        yield  # type: ignore[misc]
```

Add to `backend/app/adapters/outbound/claude_cli.py`:

```python
from typing import Any, AsyncGenerator

class ClaudeCliAdapter:
    # ... existing run() and kill() ...

    async def run_stream(
        self,
        prompt: str,
        cwd: str,
        allowed_tools: list[str] | None = None,
        append_system_prompt: str | None = None,
        delivery_id: str | None = None,
    ) -> AsyncGenerator[dict[str, Any], None]:
        cmd = ["claude", "-p", prompt, "--output-format", "stream-json"]
        if allowed_tools:
            cmd += ["--allowedTools", ",".join(allowed_tools)]
        if append_system_prompt:
            cmd += ["--append-system-prompt", append_system_prompt]

        proc = await asyncio.create_subprocess_exec(
            *cmd,
            cwd=cwd,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )

        if delivery_id:
            self._processes[delivery_id] = proc

        try:
            while True:
                line = await proc.stdout.readline()
                if not line:
                    break
                line_str = line.decode().strip()
                if not line_str:
                    continue
                try:
                    event = json.loads(line_str)
                    yield event
                except json.JSONDecodeError:
                    logger.warning("stream-json parse failed", content=line_str[:200])
            await proc.wait()
        finally:
            if delivery_id:
                self._processes.pop(delivery_id, None)
```

**Step 4: Run test to verify it passes**

Run: `cd backend && python -m pytest tests/test_claude_cli_stream.py -v`
Expected: All tests PASS (both TestRun and TestRunStream)

**Step 5: Commit**

```
git add backend/app/adapters/outbound/claude_cli.py backend/app/ports/outbound/subprocess_runner.py backend/tests/test_claude_cli_stream.py
git commit -m "feat: add run_stream() to ClaudeCliAdapter for stream-json output"
```

---

### Task 3: Wire EventBus into UseCase + _run_agent_phase

**Files:**
- Modify: `backend/app/usecases/delivery_usecases.py:116-128` (constructor)
- Modify: `backend/app/usecases/delivery_usecases.py:340-441` (_run_agent_phase)
- Modify: `backend/app/main.py:56-60` (DI assembly)
- Test: `backend/tests/test_agent_execution.py` (update MockSubprocessRunner + add stream test)

**Step 1: Write the failing test**

Add to `backend/tests/test_agent_execution.py`:

```python
from app.domain.services.event_bus import EventBus

class MockStreamingRunner:
    """Mock that supports both run() and run_stream()."""

    def __init__(self, result_text: str = "Generated plan content"):
        self.result_text = result_text
        self.calls: list[dict] = []

    async def run(self, prompt, cwd, allowed_tools=None, append_system_prompt=None, delivery_id=None):
        self.calls.append({"prompt": prompt, "cwd": cwd})
        return (self.result_text, None)

    async def run_stream(self, prompt, cwd, allowed_tools=None, append_system_prompt=None, delivery_id=None):
        self.calls.append({"prompt": prompt, "cwd": cwd})
        events = [
            {"type": "system", "subtype": "init", "message": {"model": "test-model", "cwd": cwd}},
            {"type": "assistant", "message": {"role": "assistant", "content": [{"type": "text", "text": self.result_text}], "usage": {"input_tokens": 10, "output_tokens": 5}}},
            {"type": "result", "subtype": "success", "message": {"result": self.result_text, "is_error": False, "cost_usd": 0.01, "input_tokens": 10, "output_tokens": 5, "duration_ms": 100}},
        ]
        for event in events:
            yield event

    def kill(self, delivery_id):
        return False


class TestStreamingExecution:
    @pytest.fixture
    def event_bus(self):
        return EventBus()

    @pytest.fixture
    def streaming_runner(self):
        return MockStreamingRunner()

    @pytest.fixture
    def uc(self, repos, streaming_runner, git_ops, event_bus):
        delivery_repo, source_repo = repos
        return DeliveryUseCasesImpl(delivery_repo, streaming_runner, git_ops, source_repo, event_bus=event_bus)

    @pytest.mark.asyncio
    async def test_generate_plan_publishes_events(self, uc, event_bus):
        result = _create_delivery(uc)
        delivery_id = result["id"]

        collected = []
        async def collect():
            async for event in event_bus.subscribe(delivery_id):
                collected.append(event)

        import asyncio
        task = asyncio.create_task(collect())
        await asyncio.sleep(0.01)

        await uc.generate_plan(delivery_id)

        # EventBus should be closed after run completes
        await asyncio.sleep(0.05)
        task.cancel()
        try:
            await task
        except asyncio.CancelledError:
            pass

        assert len(collected) >= 2  # at least system + assistant events

    @pytest.mark.asyncio
    async def test_stream_extracts_metadata_from_events(self, uc, streaming_runner):
        result = _create_delivery(uc)
        plan_result = await uc.generate_plan(result["id"])
        assert plan_result["run_status"] == "succeeded"

        delivery = uc.get_delivery(result["id"])
        run = delivery["runs"][-1]
        assert run["stats"]["cost_usd"] == 0.01
        assert run["session"]["model"] == "test-model"
```

**Step 2: Run test to verify it fails**

Run: `cd backend && python -m pytest tests/test_agent_execution.py::TestStreamingExecution -v`
Expected: FAIL — `TypeError: DeliveryUseCasesImpl.__init__() got an unexpected keyword argument 'event_bus'`

**Step 3: Implement the changes**

1. Add `event_bus` parameter to `DeliveryUseCasesImpl.__init__()` (optional, default `None`)
2. In `_run_agent_phase()`:
   - Check if runner has `run_stream` method (hasattr)
   - If yes: iterate with `async for`, collect events, publish to event_bus
   - If no: fallback to existing `run()` + session file parsing
   - Close event_bus on completion
3. In `main.py`: create `EventBus()` instance and pass to `DeliveryUseCasesImpl`, store on `app.state`

**Step 4: Run test to verify it passes**

Run: `cd backend && python -m pytest tests/test_agent_execution.py -v`
Expected: All tests PASS (existing + new)

**Step 5: Commit**

```
git add backend/app/usecases/delivery_usecases.py backend/app/main.py backend/tests/test_agent_execution.py
git commit -m "feat: wire EventBus into agent execution for live event broadcasting"
```

---

### Task 4: SSE endpoint — GET /api/deliveries/{id}/stream

**Files:**
- Modify: `backend/app/adapters/inbound/deliveries.py` (add SSE endpoint)
- Test: `backend/tests/test_sse_endpoint.py`

**Step 1: Write the failing test**

```python
# backend/tests/test_sse_endpoint.py
import asyncio
import pytest
from fastapi.testclient import TestClient
from app.domain.services.event_bus import EventBus


@pytest.fixture
def event_bus():
    return EventBus()


@pytest.fixture
def app(event_bus):
    from fastapi import FastAPI
    from app.adapters.inbound.deliveries import router

    test_app = FastAPI()
    test_app.include_router(router, prefix="/api")
    test_app.state.event_bus = event_bus
    # Minimal mock for delivery_usecases
    test_app.state.delivery_usecases = None
    return test_app


@pytest.fixture
def client(app):
    return TestClient(app)


class TestSSEStream:
    def test_stream_returns_event_stream_content_type(self, client, event_bus):
        # Pre-publish events and close so the stream terminates
        asyncio.run(event_bus.publish("d1", {"type": "system", "subtype": "init"}))
        asyncio.run(event_bus.close("d1"))

        response = client.get("/api/deliveries/d1/stream", stream=True)
        assert response.status_code == 200
        assert "text/event-stream" in response.headers["content-type"]

    def test_stream_sends_events_as_sse(self, client, event_bus):
        asyncio.run(event_bus.publish("d1", {"type": "assistant", "message": {"role": "assistant"}}))
        asyncio.run(event_bus.close("d1"))

        response = client.get("/api/deliveries/d1/stream", stream=True)
        body = response.text
        assert "data:" in body
        assert '"type": "assistant"' in body or '"type":"assistant"' in body

    def test_stream_sends_done_event_on_close(self, client, event_bus):
        asyncio.run(event_bus.close("d1"))

        response = client.get("/api/deliveries/d1/stream", stream=True)
        body = response.text
        assert "event: done" in body
```

**Step 2: Run test to verify it fails**

Run: `cd backend && python -m pytest tests/test_sse_endpoint.py -v`
Expected: FAIL — 404 (endpoint doesn't exist)

**Step 3: Implement SSE endpoint**

Add to `backend/app/adapters/inbound/deliveries.py`:

```python
import json
from fastapi import Request
from fastapi.responses import StreamingResponse

def get_event_bus(request: Request):
    return request.app.state.event_bus

@router.get("/deliveries/{delivery_id}/stream")
async def stream_delivery(delivery_id: str, request: Request):
    event_bus = get_event_bus(request)

    async def event_generator():
        async for event in event_bus.subscribe(delivery_id):
            if await request.is_disconnected():
                break
            yield f"data: {json.dumps(event)}\n\n"
        yield "event: done\ndata: {}\n\n"

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )
```

**Step 4: Run test to verify it passes**

Run: `cd backend && python -m pytest tests/test_sse_endpoint.py -v`
Expected: All 3 tests PASS

**Step 5: Commit**

```
git add backend/app/adapters/inbound/deliveries.py backend/tests/test_sse_endpoint.py
git commit -m "feat: add SSE endpoint for real-time delivery event streaming"
```

---

### Task 5: Frontend — useEventStream hook

**Files:**
- Create: `frontend/src/hooks/use-event-stream.ts`
- Test: `frontend/src/hooks/__tests__/use-event-stream.test.ts`

**Step 1: Write the failing test**

```typescript
// frontend/src/hooks/__tests__/use-event-stream.test.ts
import { renderHook, act } from "@testing-library/react"
import { describe, it, expect, vi, beforeEach, afterEach } from "vitest"
import { useEventStream } from "../use-event-stream"

class MockEventSource {
  url: string
  onmessage: ((event: MessageEvent) => void) | null = null
  onerror: ((event: Event) => void) | null = null
  listeners: Record<string, ((event: Event) => void)[]> = {}
  readyState = 0

  constructor(url: string) {
    this.url = url
    MockEventSource.instances.push(this)
  }

  addEventListener(event: string, handler: (event: Event) => void) {
    if (!this.listeners[event]) this.listeners[event] = []
    this.listeners[event].push(handler)
  }

  removeEventListener(event: string, handler: (event: Event) => void) {
    if (this.listeners[event]) {
      this.listeners[event] = this.listeners[event].filter((h) => h !== handler)
    }
  }

  close() {
    this.readyState = 2
  }

  // Test helpers
  simulateMessage(data: string) {
    if (this.onmessage) {
      this.onmessage(new MessageEvent("message", { data }))
    }
  }

  simulateDone() {
    for (const handler of this.listeners["done"] ?? []) {
      handler(new Event("done"))
    }
  }

  static instances: MockEventSource[] = []
  static reset() {
    MockEventSource.instances = []
  }
}

describe("useEventStream", () => {
  beforeEach(() => {
    MockEventSource.reset()
    vi.stubGlobal("EventSource", MockEventSource)
  })

  afterEach(() => {
    vi.unstubAllGlobals()
  })

  it("connects when active is true", () => {
    renderHook(() => useEventStream("d1", true))
    expect(MockEventSource.instances).toHaveLength(1)
    expect(MockEventSource.instances[0].url).toBe("/api/deliveries/d1/stream")
  })

  it("does not connect when active is false", () => {
    renderHook(() => useEventStream("d1", false))
    expect(MockEventSource.instances).toHaveLength(0)
  })

  it("accumulates events from messages", () => {
    const { result } = renderHook(() => useEventStream("d1", true))
    const es = MockEventSource.instances[0]

    act(() => {
      es.simulateMessage(JSON.stringify({ type: "assistant", message: { role: "assistant" } }))
    })

    expect(result.current.events).toHaveLength(1)
    expect(result.current.events[0].type).toBe("assistant")
  })

  it("closes on done event", () => {
    const { result } = renderHook(() => useEventStream("d1", true))
    const es = MockEventSource.instances[0]

    act(() => {
      es.simulateDone()
    })

    expect(es.readyState).toBe(2)
    expect(result.current.done).toBe(true)
  })
})
```

**Step 2: Run test to verify it fails**

Run: `cd frontend && npx vitest run src/hooks/__tests__/use-event-stream.test.ts`
Expected: FAIL — module not found

**Step 3: Implement the hook**

```typescript
// frontend/src/hooks/use-event-stream.ts
import { useEffect, useRef, useState } from "react"

export interface StreamEvent {
  type: string
  subtype?: string
  parent_tool_use_id?: string
  message?: Record<string, unknown>
  session_id?: string
}

export function useEventStream(deliveryId: string, active: boolean) {
  const [events, setEvents] = useState<StreamEvent[]>([])
  const [done, setDone] = useState(false)
  const esRef = useRef<EventSource | null>(null)

  useEffect(() => {
    if (!active) {
      return
    }

    setEvents([])
    setDone(false)

    const es = new EventSource(`/api/deliveries/${deliveryId}/stream`)
    esRef.current = es

    es.onmessage = (event) => {
      try {
        const data = JSON.parse(event.data) as StreamEvent
        setEvents((prev) => [...prev, data])
      } catch {
        // skip malformed events
      }
    }

    const handleDone = () => {
      setDone(true)
      es.close()
    }

    es.addEventListener("done", handleDone)

    es.onerror = () => {
      es.close()
      setDone(true)
    }

    return () => {
      es.removeEventListener("done", handleDone)
      es.close()
      esRef.current = null
    }
  }, [deliveryId, active])

  return { events, done }
}
```

**Step 4: Run test to verify it passes**

Run: `cd frontend && npx vitest run src/hooks/__tests__/use-event-stream.test.ts`
Expected: All 4 tests PASS

**Step 5: Commit**

```
git add frontend/src/hooks/use-event-stream.ts frontend/src/hooks/__tests__/use-event-stream.test.ts
git commit -m "feat: add useEventStream hook for SSE-based live transcript"
```

---

### Task 6: Frontend — LiveTranscript component on show page

**Files:**
- Modify: `frontend/src/pages/deliveries/show.tsx` (add LiveTranscript section)
- Modify: `frontend/src/pages/deliveries/transcript.tsx` (export MessageRenderer)

**Step 1: Export MessageRenderer from transcript.tsx**

In `frontend/src/pages/deliveries/transcript.tsx`, change `MessageRenderer` from a file-private function to a named export:

```typescript
// Change this:
function MessageRenderer({ message }: { message: TranscriptMessage }) {
// To this:
export function MessageRenderer({ message }: { message: TranscriptMessage }) {
```

Also export `ContentBlockRenderer` similarly.

**Step 2: Add LiveTranscript to show.tsx**

Add a `LiveTranscript` component that:
- Takes `deliveryId` and `runStatus` props
- Uses `useEventStream(deliveryId, runStatus === "running")`
- Converts `StreamEvent[]` to `TranscriptMessage[]` for rendering
- Shows a "Streaming..." indicator with animation
- Auto-scrolls to bottom on new events
- Renders below the Agent Runs section

```typescript
import { useEventStream } from "@/hooks/use-event-stream"
import type { StreamEvent } from "@/hooks/use-event-stream"
import { MessageRenderer } from "@/pages/deliveries/transcript"
import type { TranscriptMessage } from "@/types"

function streamEventsToMessages(events: StreamEvent[]): TranscriptMessage[] {
  const messages: TranscriptMessage[] = []
  for (const event of events) {
    if (event.type === "system" || event.type === "result") continue
    if (!event.message) continue
    const role = (event.message.role as string) || event.type
    const content = event.message.content as TranscriptMessage["content"]
    messages.push({ role, content })
  }
  return messages
}

function LiveTranscript({ deliveryId, runStatus }: { deliveryId: string; runStatus: string }) {
  const { events, done } = useEventStream(deliveryId, runStatus === "running")
  const bottomRef = useRef<HTMLDivElement>(null)

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: "smooth" })
  }, [events.length])

  if (events.length === 0 && !done) return null

  const messages = streamEventsToMessages(events)

  return (
    <Card>
      <CardHeader>
        <CardTitle className="flex items-center gap-2">
          Live Transcript
          {!done && (
            <span className="inline-block h-2 w-2 rounded-full bg-green-500 animate-pulse" />
          )}
        </CardTitle>
      </CardHeader>
      <CardContent>
        <div className="space-y-1 max-h-[600px] overflow-y-auto">
          {messages.map((msg, i) => (
            <MessageRenderer key={i} message={msg} />
          ))}
          <div ref={bottomRef} />
        </div>
      </CardContent>
    </Card>
  )
}
```

Place it in the show page JSX right after `<AgentRunsSection>`:

```tsx
{/* Live Transcript (during running) */}
<LiveTranscript deliveryId={delivery.id} runStatus={delivery.run_status} />
```

**Step 3: Run lint and verify**

Run: `cd frontend && npm run lint`
Expected: No errors

Run: `cd frontend && npm run build`
Expected: Build succeeds

**Step 4: Commit**

```
git add frontend/src/pages/deliveries/show.tsx frontend/src/pages/deliveries/transcript.tsx
git commit -m "feat: add LiveTranscript panel to delivery show page"
```

---

### Task 7: Integration — polling refresh during running state

**Files:**
- Modify: `frontend/src/hooks/use-delivery.ts` (add polling when running)

**Step 1: Add polling to useDelivery**

The delivery show page needs to poll for status updates during `running` so that when the agent finishes, the page reflects the new `run_status` and updated `runs` list. Add a polling interval (3s) when `run_status === "running"`.

```typescript
// Add to useDelivery hook after the initial useEffect:
useEffect(() => {
  if (delivery?.run_status !== "running") return
  const interval = setInterval(() => {
    refresh()
  }, 3000)
  return () => clearInterval(interval)
}, [delivery?.run_status, refresh])
```

**Step 2: Verify manually + run existing tests**

Run: `cd frontend && npx vitest run`
Expected: All existing tests pass

**Step 3: Commit**

```
git add frontend/src/hooks/use-delivery.ts
git commit -m "feat: add polling refresh during running state for live status updates"
```

---

### Task 8: Backend integration test — full flow

**Files:**
- Create: `backend/tests/test_streaming_integration.py`

**Step 1: Write integration test**

Test the full flow: streaming runner → event_bus → events collected → transcript saved.

```python
# backend/tests/test_streaming_integration.py
import pytest
from app.adapters.outbound.filesystem_delivery import FileSystemDeliveryRepository
from app.adapters.outbound.filesystem_source import FileSystemSourceRepository
from app.domain.models.delivery import DeliveryCreate
from app.domain.services.event_bus import EventBus
from app.usecases.delivery_usecases import DeliveryUseCasesImpl
from tests.test_agent_execution import MockStreamingRunner, MockGitOperations


@pytest.fixture
def full_uc(tmp_path):
    delivery_repo = FileSystemDeliveryRepository(tmp_path / "deliveries")
    source_repo = FileSystemSourceRepository(tmp_path / "sources")
    runner = MockStreamingRunner()
    git_ops = MockGitOperations()
    event_bus = EventBus()
    uc = DeliveryUseCasesImpl(delivery_repo, runner, git_ops, source_repo, event_bus=event_bus)
    return uc, event_bus


class TestStreamingIntegration:
    @pytest.mark.asyncio
    async def test_plan_streams_events_and_saves_transcript(self, full_uc):
        uc, event_bus = full_uc
        body = DeliveryCreate(
            phase="plan", run_status="pending",
            summary="Test", repository="owner/repo",
            refs=[{"role": "trigger", "type": "github_issue", "label": "#1",
                   "url": "https://github.com/owner/repo/issues/1"}],
        )
        result = uc.create_delivery(body)
        delivery_id = result["id"]

        plan_result = await uc.generate_plan(delivery_id)
        assert plan_result["run_status"] == "succeeded"

        # Transcript should have been saved
        run_id = plan_result["run_id"]
        transcript = uc.get_run_transcript(delivery_id, run_id)
        assert transcript is not None
        assert "leader" in transcript

        # EventBus should be cleaned up
        assert not event_bus.is_active(delivery_id)
```

**Step 2: Run test**

Run: `cd backend && python -m pytest tests/test_streaming_integration.py -v`
Expected: PASS

**Step 3: Run full test suite**

Run: `cd backend && python -m pytest -v`
Expected: All tests pass

Run: `cd frontend && npx vitest run`
Expected: All tests pass

**Step 4: Commit**

```
git add backend/tests/test_streaming_integration.py
git commit -m "test: add streaming integration test for full plan execution flow"
```
