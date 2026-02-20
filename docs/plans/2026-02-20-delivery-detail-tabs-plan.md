# Delivery Detail Tabs + Agents Log Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Split the delivery detail page into Overview + Agents Log tabs, persist stream events to disk, remove transcript page and plan section.

**Architecture:** Backend saves stream events as JSON file per run (alongside existing transcript). Frontend uses shadcn Tabs for two-tab layout. Agents Log tab uses a Select dropdown to pick runs, shows SSE stream for running state or loads persisted log for completed runs.

**Tech Stack:** React 19, shadcn/ui (Tabs, Select), FastAPI, file-based JSON persistence

---

### Task 1: Backend — Add stream log persistence to repository layer

**Files:**
- Modify: `backend/app/ports/outbound/delivery_repository.py:4-10`
- Modify: `backend/app/adapters/outbound/filesystem_delivery.py:50-54`
- Test: `backend/tests/test_filesystem_delivery.py`

**Step 1: Write the failing test**

```python
# In backend/tests/test_filesystem_delivery.py — add test
def test_save_and_get_stream_log(tmp_path):
    repo = FileSystemDeliveryRepository(tmp_path)
    log_data = {
        "run_id": "run001",
        "started_at": "2026-02-20T10:00:00",
        "completed_at": "2026-02-20T10:05:00",
        "events": [{"type": "assistant", "message": {"role": "assistant"}}],
    }
    repo.save_stream_log("dlv00001", "run001", log_data)
    result = repo.get_stream_log("dlv00001", "run001")
    assert result == log_data


def test_get_stream_log_not_found(tmp_path):
    repo = FileSystemDeliveryRepository(tmp_path)
    assert repo.get_stream_log("dlv00001", "run999") is None
```

**Step 2: Run test to verify it fails**

Run: `cd backend && python -m pytest tests/test_filesystem_delivery.py::test_save_and_get_stream_log -v`
Expected: FAIL with "AttributeError: 'FileSystemDeliveryRepository' has no attribute 'save_stream_log'"

**Step 3: Add methods to Protocol and implementation**

Add to `DeliveryRepository` Protocol (`backend/app/ports/outbound/delivery_repository.py`):
```python
def get_stream_log(self, delivery_id: str, run_id: str) -> dict | None: ...
def save_stream_log(self, delivery_id: str, run_id: str, data: dict) -> None: ...
```

Add to `FileSystemDeliveryRepository` (`backend/app/adapters/outbound/filesystem_delivery.py`):
```python
def get_stream_log(self, delivery_id: str, run_id: str) -> dict | None:
    file = self._dir / delivery_id / f"run-{run_id}.stream_log.json"
    if not file.exists():
        return None
    return json.loads(file.read_text(encoding="utf-8"))

def save_stream_log(self, delivery_id: str, run_id: str, data: dict) -> None:
    delivery_dir = self._dir / delivery_id
    delivery_dir.mkdir(parents=True, exist_ok=True)
    file = delivery_dir / f"run-{run_id}.stream_log.json"
    self._atomic_write(file, data)
```

**Step 4: Run test to verify it passes**

Run: `cd backend && python -m pytest tests/test_filesystem_delivery.py -v`
Expected: ALL PASS

**Step 5: Commit**

```bash
git add backend/app/ports/outbound/delivery_repository.py backend/app/adapters/outbound/filesystem_delivery.py backend/tests/test_filesystem_delivery.py
git commit -m "feat: add stream log persistence to repository layer"
```

---

### Task 2: Backend — Save stream events during execution (success + error)

**Files:**
- Modify: `backend/app/usecases/delivery_usecases.py:370-466`
- Modify: `backend/app/ports/inbound/delivery_usecases.py`

**Step 1: Add `save_stream_log` and `get_stream_log` to inbound Protocol**

In `backend/app/ports/inbound/delivery_usecases.py`, add:
```python
def get_stream_log(self, delivery_id: str, run_id: str) -> dict | None: ...
```

**Step 2: Add `get_stream_log` pass-through in usecase class**

In `backend/app/usecases/delivery_usecases.py`, add method:
```python
def get_stream_log(self, delivery_id: str, run_id: str) -> dict | None:
    return self._repo.get_stream_log(delivery_id, run_id)
```

**Step 3: Persist stream events on success**

In `_run_agent_impl()` (around line 420-442), after building the `run` dict and before `self._repo.save_delivery()`:
```python
stream_log = {
    "run_id": run_id,
    "started_at": run["created_at"],
    "completed_at": datetime.now(KST).isoformat(),
    "events": collected_events,
}
self._repo.save_stream_log(delivery_id, run_id, stream_log)
```

**Step 4: Persist partial stream events on error**

In the `except` block (around line 451-462), save what was collected. We need `collected_events` and `run_id` to be available in the except scope. Move `run_id = uuid.uuid4().hex[:8]` and `collected_events: list[dict] = []` before the try/if blocks:
```python
run_id = uuid.uuid4().hex[:8]
collected_events: list[dict] = []
# ... existing try block ...
# In except:
if collected_events:
    stream_log = {
        "run_id": run_id,
        "started_at": datetime.now(KST).isoformat(),
        "completed_at": datetime.now(KST).isoformat(),
        "events": collected_events,
    }
    self._repo.save_stream_log(delivery_id, run_id, stream_log)
```

Note: `run_id` is currently generated at line 420 inside the success path. Move it before the `try` block so it's available in `except` too.

**Step 5: Run tests**

Run: `cd backend && python -m pytest -v`
Expected: ALL PASS

**Step 6: Commit**

```bash
git add backend/app/usecases/delivery_usecases.py backend/app/ports/inbound/delivery_usecases.py
git commit -m "feat: persist stream events to JSON on run completion and error"
```

---

### Task 3: Backend — Add stream log API endpoint

**Files:**
- Modify: `backend/app/adapters/inbound/deliveries.py`
- Test: `backend/tests/test_api_deliveries.py` (if exists) or new test

**Step 1: Add endpoint**

In `backend/app/adapters/inbound/deliveries.py`, add after the existing transcript endpoint (line 187):
```python
@router.get("/deliveries/{delivery_id}/runs/{run_id}/stream_log")
def get_stream_log(delivery_id: str, run_id: str, uc=Depends(get_usecases)):
    log = uc.get_stream_log(delivery_id, run_id)
    if log is None:
        raise HTTPException(status_code=404, detail="Stream log not found")
    return log
```

**Step 2: Run tests**

Run: `cd backend && python -m pytest -v`
Expected: ALL PASS

**Step 3: Commit**

```bash
git add backend/app/adapters/inbound/deliveries.py
git commit -m "feat: add GET stream_log API endpoint"
```

---

### Task 4: Frontend — Remove transcript page, route, hook, and plan section

**Files:**
- Delete content from: `frontend/src/pages/deliveries/transcript.tsx` (keep MessageRenderer export only)
- Modify: `frontend/src/App.tsx:5,17`
- Delete: `frontend/src/hooks/use-transcript.ts`
- Modify: `frontend/src/pages/deliveries/show.tsx`

**Step 1: Refactor transcript.tsx — keep only MessageRenderer and its dependencies**

Rewrite `frontend/src/pages/deliveries/transcript.tsx` to contain only the block renderers and `MessageRenderer`. Remove `TranscriptViewer`, `AgentList`, and the `useTranscript` import. Remove `useParams`, `Link`, `Badge` imports that are only used by `TranscriptViewer`.

The file should export: `MessageRenderer` (and its internal block renderer helpers).

**Step 2: Remove transcript route from App.tsx**

Remove line 5 (`import { TranscriptViewer }`) and line 17 (the transcript Route).

**Step 3: Delete use-transcript.ts**

Delete `frontend/src/hooks/use-transcript.ts` entirely.

**Step 4: Remove PlanSection and transcript links from show.tsx**

In `show.tsx`:
- Remove `PlanSection` component (lines 220-241)
- Remove `{delivery.plan && <PlanSection plan={delivery.plan} />}` (line 516)
- Remove the "View Transcript" `<Link>` column from `AgentRunsSection` (lines 358-365 and the empty `<TableHead>` at line 320)

**Step 5: Verify build**

Run: `cd frontend && npm run build`
Expected: Build succeeds with no errors

**Step 6: Commit**

```bash
git add -A frontend/src/
git commit -m "refactor: remove transcript page, use-transcript hook, and plan section"
```

---

### Task 5: Frontend — Add useStreamLog hook

**Files:**
- Create: `frontend/src/hooks/use-stream-log.ts`

**Step 1: Create the hook**

```typescript
import { useCallback, useEffect, useState } from "react"
import { apiFetch } from "@/utils/api"
import type { StreamEvent } from "@/hooks/use-event-stream"

export interface StreamLog {
  run_id: string
  started_at: string
  completed_at: string
  events: StreamEvent[]
}

export function useStreamLog(deliveryId: string, runId: string | null) {
  const [log, setLog] = useState<StreamLog | null>(null)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)

  const refresh = useCallback(async () => {
    if (!runId) return
    setLoading(true)
    setError(null)
    try {
      const data = await apiFetch<StreamLog>(
        `/deliveries/${deliveryId}/runs/${runId}/stream_log`,
      )
      setLog(data)
    } catch (e) {
      setError(e instanceof Error ? e.message : "Unknown error")
    } finally {
      setLoading(false)
    }
  }, [deliveryId, runId])

  useEffect(() => {
    refresh()
  }, [refresh])

  return { log, loading, error, refresh }
}
```

**Step 2: Verify build**

Run: `cd frontend && npm run build`
Expected: Build succeeds

**Step 3: Commit**

```bash
git add frontend/src/hooks/use-stream-log.ts
git commit -m "feat: add useStreamLog hook for fetching persisted stream logs"
```

---

### Task 6: Frontend — Implement two-tab layout with Agents Log tab

**Files:**
- Modify: `frontend/src/pages/deliveries/show.tsx`

**Step 1: Add imports**

Add to show.tsx imports:
```typescript
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs"
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select"
import { useStreamLog } from "@/hooks/use-stream-log"
```

**Step 2: Create AgentsLogTab component**

Add new component in show.tsx:
```typescript
function AgentsLogTab({ deliveryId, runs, runStatus }: {
  deliveryId: string
  runs: AgentRun[]
  runStatus: RunStatus
}) {
  const [selectedRunId, setSelectedRunId] = useState<string | null>(
    runs.length > 0 ? runs[runs.length - 1].id : null,
  )

  const isLatestRun = selectedRunId === (runs.length > 0 ? runs[runs.length - 1].id : null)
  const isLive = runStatus === "running" && isLatestRun

  const { log, loading: logLoading } = useStreamLog(
    deliveryId,
    isLive ? null : selectedRunId,
  )

  return (
    <div className="space-y-4">
      {runs.length > 0 && (
        <Select value={selectedRunId ?? ""} onValueChange={setSelectedRunId}>
          <SelectTrigger className="w-80">
            <SelectValue placeholder="Select a run..." />
          </SelectTrigger>
          <SelectContent>
            {runs.map((run) => (
              <SelectItem key={run.id} value={run.id}>
                {run.mode} — {run.status} — {run.session.model}
              </SelectItem>
            ))}
          </SelectContent>
        </Select>
      )}

      {isLive ? (
        <LiveTranscript deliveryId={deliveryId} runStatus={runStatus} />
      ) : logLoading ? (
        <p className="text-sm text-muted-foreground">Loading log...</p>
      ) : log ? (
        <Card>
          <CardHeader>
            <CardTitle className="flex items-center gap-2">
              Run Log
              <span className="text-xs font-normal text-muted-foreground">
                {log.started_at} → {log.completed_at}
              </span>
            </CardTitle>
          </CardHeader>
          <CardContent>
            <div className="space-y-1 max-h-[600px] overflow-y-auto">
              {streamEventsToMessages(log.events).map((msg, i) => (
                <MessageRenderer key={i} message={msg} />
              ))}
            </div>
          </CardContent>
        </Card>
      ) : selectedRunId ? (
        <p className="text-sm text-muted-foreground">No log available for this run.</p>
      ) : (
        <p className="text-sm text-muted-foreground">No agent runs yet.</p>
      )}
    </div>
  )
}
```

**Step 3: Wrap DeliveryShow body in Tabs**

Replace the content of `DeliveryShow`'s return (the `<div className="space-y-6">` block) with:
```tsx
<div className="space-y-6">
  {/* Header */}
  <div className="space-y-2">
    <h1 className="text-2xl font-bold">{delivery.summary}</h1>
    <div className="flex items-center gap-2 text-sm">
      <Badge variant="secondary" className={PHASE_CLASSES[delivery.phase]}>
        {delivery.phase}
      </Badge>
      <RunStatusBadge status={delivery.run_status} animate />
    </div>
  </div>

  {/* Action Error */}
  {actionError && (
    <div className="flex items-center justify-between rounded-md border border-red-200 bg-red-50 p-3 text-sm text-red-800">
      <span>{actionError}</span>
      <Button variant="ghost" size="sm" onClick={clearActionError}
        className="h-auto p-1 text-red-800 hover:text-red-900">
        Dismiss
      </Button>
    </div>
  )}

  {/* Actions */}
  <ActionButtons
    phase={delivery.phase}
    runStatus={delivery.run_status}
    onApprove={approve}
    onReject={reject}
    onCancel={cancel}
    onRunAgent={runAgent}
  />

  <Separator />

  {/* Tabs */}
  <Tabs defaultValue="overview">
    <TabsList>
      <TabsTrigger value="overview">Overview</TabsTrigger>
      <TabsTrigger value="agents-log">Agents Log</TabsTrigger>
    </TabsList>

    <TabsContent value="overview" className="space-y-6 mt-4">
      {delivery.error && delivery.run_status !== "running" && (
        <ErrorBox message={delivery.error} />
      )}
      <RefsList refs={delivery.refs} />
      <PhaseRunsTable phaseRuns={delivery.phase_runs} />
      <AgentRunsSection deliveryId={delivery.id} runs={delivery.runs} />
    </TabsContent>

    <TabsContent value="agents-log" className="mt-4">
      <AgentsLogTab
        deliveryId={delivery.id}
        runs={delivery.runs}
        runStatus={delivery.run_status}
      />
    </TabsContent>
  </Tabs>
</div>
```

**Step 4: Verify build**

Run: `cd frontend && npm run build`
Expected: Build succeeds

**Step 5: Run lint**

Run: `cd frontend && npm run lint`
Expected: No errors

**Step 6: Commit**

```bash
git add frontend/src/pages/deliveries/show.tsx
git commit -m "feat: split delivery detail into Overview + Agents Log tabs"
```

---

### Task 7: Cleanup — Remove unused imports and dead code

**Files:**
- Modify: `frontend/src/pages/deliveries/show.tsx` (remove unused Link import if no longer needed)
- Modify: `frontend/src/types.ts` (TranscriptData can stay — still used by MessageRenderer indirectly)

**Step 1: Check for unused imports**

Run: `cd frontend && npm run lint`
Fix any unused import warnings.

**Step 2: Verify everything builds and tests pass**

Run: `cd frontend && npm run build && npm run lint`
Run: `cd backend && python -m pytest -v`

**Step 3: Commit**

```bash
git add -A
git commit -m "chore: remove unused imports and dead code"
```
