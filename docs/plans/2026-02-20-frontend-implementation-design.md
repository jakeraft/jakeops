# Frontend Full Implementation Design

## Context

Backend is fully implemented (FastAPI + hexagonal architecture). Frontend src/ is empty.
This design covers the complete frontend build using shadcn/ui + TailwindCSS.

Priority: Shell-First approach, building outward-in from layout to pages.
Differentiator pages (Delivery Detail with actor tracking, Transcript Viewer) are core.

## Constraints (from .claude/rules/frontend.md)

- Never modify components/ui/ (shadcn originals)
- Never create custom CSS files — TailwindCSS utility classes only
- Never implement components from scratch — use shadcn if available
- Never call fetch() directly — use utils/api.ts wrappers
- State management: React hooks only (no global state library)
- Transcript rendering: plain text (`pre`) based

## File Structure

```
frontend/src/
├── main.tsx
├── App.tsx                    # Route definitions
├── types.ts                   # Backend domain type mirrors
├── utils/
│   ├── api.ts                 # apiFetch, apiPost, apiPatch, apiDelete
│   └── format.ts              # formatDateTime, etc.
├── components/
│   ├── ui/                    # shadcn components (read-only)
│   ├── app-sidebar.tsx        # Sidebar navigation
│   └── app-layout.tsx         # SidebarProvider + SidebarInset wrapper
├── hooks/
│   ├── use-deliveries.ts      # Delivery list/detail fetch
│   ├── use-sources.ts         # Source CRUD fetch
│   └── use-worker.ts          # Worker status fetch
└── pages/
    ├── deliveries/
    │   ├── list.tsx            # Delivery table
    │   ├── show.tsx            # Delivery detail + actions + phase runs
    │   └── transcript.tsx      # Transcript viewer (pre-based)
    ├── sources/
    │   └── list.tsx            # Source CRUD table
    └── worker/
        └── status.tsx          # Worker health cards
```

## Routing

```
/                                              → redirect /deliveries
/deliveries                                    → DeliveryList
/deliveries/:id                                → DeliveryShow
/deliveries/:id/runs/:runId/transcript         → TranscriptViewer
/sources                                       → SourceList
/worker                                        → WorkerStatus
```

All routes wrapped in AppLayout (Sidebar + main content area).

## Types (types.ts)

Mirror backend domain models exactly:

- Phase: "intake" | "plan" | "implement" | "review" | "verify" | "deploy" | "observe" | "close"
- RunStatus: "pending" | "running" | "succeeded" | "failed" | "blocked" | "canceled"
- ExecutorKind: "system" | "agent" | "human"
- Delivery: id, schema_version, created_at, updated_at, phase, run_status, exit_phase, summary, repository, refs, runs, phase_runs, plan?, error?
- PhaseRun: phase, run_status, executor, started_at?, ended_at?
- AgentRun: id, mode, status, created_at, session, stats, error?, summary?, session_id?
- Ref: role, type, label, url?
- Source: id, type, owner, repo, created_at, token, active, default_exit_phase
- WorkerStatus: name, label, enabled, interval_sec, last_poll_at?, last_result?, last_error?

## API Layer (utils/api.ts)

Thin wrappers around fetch with /api prefix (Vite proxy):

- apiFetch<T>(path) → GET
- apiPost<T>(path, body?) → POST
- apiPatch<T>(path, body) → PATCH
- apiDelete(path) → DELETE

## Page Designs

### Delivery List

shadcn Table. Columns:

| Column | Field | Display |
|--------|-------|---------|
| Summary | summary | Link to /deliveries/:id |
| Phase | phase | shadcn Badge |
| Status | run_status | shadcn Badge (color-coded via Tailwind) |
| Repository | repository | Text |
| Updated | updated_at | Relative time |

### Delivery Detail

Sections:

1. **Header** — summary, phase + run_status badges, repository
2. **Actions** — conditional buttons using shadcn Button:
   - Gate phase + succeeded → Approve / Reject
   - failed → Retry
   - intake → Generate Plan
   - Any non-terminal → Cancel
3. **Refs** — list of reference links (trigger/output/parent)
4. **Plan** — if exists, render content in `pre` block
5. **Phase Runs** — timeline/table of phase_runs with executor badge (system/agent/human)
6. **Agent Runs** — cards showing mode, status, model, cost/tokens/duration, link to transcript

### Transcript Viewer

Pre-based rendering per frontend-conventions.md.

- Left: agent list (leader + subagent_* from transcript keys), click to switch
- Right: selected agent's messages in `pre` blocks
- Content blocks rendered as plain text:
  - text: as-is
  - thinking: labeled section, collapsible via shadcn Collapsible
  - tool_use: tool name + JSON input in `pre`
  - tool_result: result content in `pre`
- Top bar: metadata (model, cost, tokens, duration)

### Sources List

shadcn Table + Dialog for create/edit.

| Column | Field |
|--------|-------|
| Type | type |
| Repository | owner/repo |
| Active | active (shadcn Switch or Badge) |
| Exit Phase | default_exit_phase |
| Created | created_at |

Actions: Create (Dialog), Edit (Dialog), Delete (confirmation), Sync Now button.

### Worker Status

Card per worker using shadcn Card:
- name, label, enabled status
- interval, last poll time
- last result or error (color-coded)

## Implementation Order

1. shadcn/ui + TailwindCSS initialization
2. types.ts + utils/api.ts + utils/format.ts
3. App layout (Sidebar + routing)
4. Delivery List page
5. Delivery Detail page
6. Transcript Viewer page
7. Sources page
8. Worker Status page
9. Lint + test + build verification
