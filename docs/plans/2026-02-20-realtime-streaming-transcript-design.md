# Real-time Streaming Transcript

## Context

The current CLI adapter (`ClaudeCliAdapter`) runs `claude -p --output-format json`,
which blocks until completion and returns the full result at once. Transcripts are
collected post-hoc from local session `.jsonl` files under `~/.claude/projects/`.

Users want to see agent work in real-time on the delivery show page while a phase
(plan/implement/review) is running.

## Decision

Switch the agent execution path to `--output-format stream-json` and broadcast
events to the frontend via Server-Sent Events (SSE). The live transcript panel
renders inline on the delivery show page during `running` status.

## Architecture

```
Claude CLI (--output-format stream-json)
    | stdout line-by-line
    v
ClaudeCliAdapter.run_stream()   <- AsyncGenerator[StreamEvent]
    |
    v
_run_agent_phase()              <- collects events + publishes to EventBus
    |
    +---> EventBus (in-memory dict[delivery_id -> list[asyncio.Queue]])
    |         |
    |         v
    |     SSE endpoint: GET /api/deliveries/{id}/stream
    |         |
    |         v
    |     Frontend EventSource -> LiveTranscript component
    |
    +---> On completion: save transcript file (same as before)
```

## Component Changes

### 1. CLI Adapter — `run_stream()` method

- Add `run_stream()` as `AsyncGenerator[StreamEvent, None]`
- Uses `--output-format stream-json` instead of `json`
- Reads `proc.stdout` line-by-line via `async for`
- Parses each line into `StreamEvent` using existing `parse_stream_lines` logic
- Keeps existing `run()` method unchanged for backward compatibility

### 2. EventBus — in-memory pub/sub per delivery

- New module: `app/domain/services/event_bus.py`
- Structure: `dict[delivery_id -> EventBusEntry]`
  - `EventBusEntry`: buffer (list of past events) + subscribers (list of asyncio.Queue)
- `publish(delivery_id, event)`: append to buffer + put to all subscriber queues
- `subscribe(delivery_id) -> AsyncGenerator`: yields buffered events then waits on queue
- `close(delivery_id)`: sends sentinel, cleans up

### 3. SubprocessRunner Protocol — add `run_stream()`

- Add optional `run_stream()` to Protocol with default no-op
- Signature: `async def run_stream(...) -> AsyncGenerator[StreamEvent, None]`

### 4. UseCase — `_run_agent_phase()` uses streaming

- Replace `self._runner.run()` with `async for event in self._runner.run_stream()`
- Collect events into list for transcript extraction (same as before)
- Publish each event to EventBus as it arrives
- On completion: extract metadata from collected events, save transcript
- Session file parsing becomes fallback only

### 5. SSE Endpoint — `GET /api/deliveries/{id}/stream`

- FastAPI `StreamingResponse(media_type="text/event-stream")`
- Subscribes to EventBus for the delivery
- Sends each event as `data: {json}\n\n`
- Replays buffered events on connect (late joiners see full history)
- Sends `event: done\ndata: {}\n\n` on completion
- Handles client disconnect gracefully

### 6. Frontend — `useEventStream` hook + `LiveTranscript` component

- `useEventStream(deliveryId)`: connects EventSource when `run_status === "running"`
  - Accumulates `StreamEvent[]` in state
  - Auto-closes on `done` event or status change
- `LiveTranscript`: renders below Agent Runs on show page
  - Reuses existing `MessageRenderer` from transcript.tsx
  - Auto-scrolls to bottom as new events arrive
  - Shows "streaming..." indicator while active
  - Disappears when run completes (user can view full transcript via existing link)

## What Does NOT Change

- `SubprocessRunner.run()` — kept for backward compatibility
- Existing transcript page (`/deliveries/:id/runs/:runId/transcript`)
- `stream_parser.py` functions (`extract_metadata`, `extract_transcript`)
- `session_parser.py` — retained as fallback
- Delivery data model and phase state machine

## Alternatives Considered

1. **WebSocket**: More complex, requires WS infrastructure not present in the project.
   SSE is simpler, HTTP-based, proxy-friendly, and sufficient for server→client streaming.

2. **Polling**: Simplest but poor real-time experience. Would require intermediate
   storage and frequent API calls.

3. **Keep blocking + session file**: Current approach. Works but no real-time visibility.
