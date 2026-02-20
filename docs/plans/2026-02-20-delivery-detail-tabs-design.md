# Delivery Detail Tabs + Agents Log Persistence

**Date**: 2026-02-20
**Status**: Approved

## Context

The delivery detail page currently displays everything in a single scrollable view:
Plan → Phase Runs → Agent Runs (with "View Transcript" links) → LiveTranscript.

Problems:
1. **"stream has no result event" error** — stream events are only held in-memory (EventBus buffer). When errors occur mid-stream, all rendered output is lost because nothing is persisted to disk.
2. **View Transcript** navigates to a separate page — no longer needed.
3. **Plan section** displayed inline — no longer needed.

## Decision

### 1. Two-Tab Layout

| Tab | Content |
|-----|---------|
| **Overview** | Delivery metadata: header (id, phase, status), action buttons, refs, phase runs table, agent runs table |
| **Agents Log** | Real-time stream during execution, persisted logs after completion, run history selector |

### 2. Removals

- `/deliveries/:id/runs/:runId/transcript` route and `transcript.tsx` page
- `useTranscript` hook
- Plan section (PlanSection component)
- "View Transcript" links in Agent Runs table

### 3. Stream Log Persistence (Backend)

**When**: Events buffered during stream execution, flushed to JSON file on completion (or error).
**Where**: `deliveries/<id>/runs/<runId>/stream_log.json`
**Format**:
```json
{
  "run_id": "...",
  "started_at": "...",
  "completed_at": "...",
  "events": [StreamEvent, ...]
}
```

On error, partial events are still saved — UI can recover and display what was captured.

### 4. New API Endpoint

- `GET /api/deliveries/{id}/runs/{runId}/stream_log` — returns persisted stream log JSON

Existing endpoints unchanged:
- `GET /api/deliveries/{id}/stream` — SSE real-time stream
- `GET /api/deliveries/{id}` — delivery metadata (already includes runs list)

### 5. Agents Log Tab UI Flow

```
[Run history dropdown]  ← select previous runs
        ↓
  run_status == 'running' && selected run is current
    → SSE real-time stream (LiveTranscript)
  otherwise
    → Load stream_log.json and render messages
```

## Alternatives Considered

1. **JSONL append format** — better for large streams but adds complexity for reading; JSON is simpler and sufficient for current scale.
2. **Keep EventBus memory-only, just fix error handling** — doesn't solve the persistence problem; logs lost on server restart.
3. **Keep transcript page as read-only viewer** — redundant with the new Agents Log tab.
