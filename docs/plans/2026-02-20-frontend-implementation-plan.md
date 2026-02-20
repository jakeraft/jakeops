# Frontend Full Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Build the complete JakeOps frontend — layout, all pages, and the differentiator Transcript Viewer — using shadcn/ui + TailwindCSS on an empty src/ directory.

**Architecture:** Shell-First. Initialize shadcn, build app shell (sidebar + routing), then implement each page top-down. All styling via Tailwind utility classes. All API calls via utils/api.ts wrappers. State via React hooks only.

**Tech Stack:** React 19, TypeScript, shadcn/ui, TailwindCSS, React Router 7, Vite 7, Vitest + Testing Library

**Key conventions** (from `.claude/rules/frontend.md`):
- Never modify `components/ui/` — shadcn originals only
- Never create custom CSS files
- Never implement components from scratch if shadcn has one
- Never call `fetch()` directly — use `utils/api.ts`
- State: React hooks only, no global state library

---

### Task 1: Initialize shadcn/ui + TailwindCSS

**Files:**
- Modify: `frontend/package.json` (deps added by shadcn init)
- Modify: `frontend/tsconfig.app.json` (path aliases)
- Modify: `frontend/vite.config.ts` (path aliases)
- Create: `frontend/src/lib/utils.ts` (shadcn cn utility)
- Create: `frontend/src/main.tsx`
- Create: `frontend/src/App.tsx` (placeholder)
- Create: `frontend/src/index.css` (Tailwind directives + shadcn CSS variables — this is NOT custom CSS, it's the required shadcn/tailwind config)
- Create: `frontend/components.json`

**Step 1: Run shadcn init**

```bash
cd frontend && npx shadcn@latest init
```

Select: New York style, Zinc base color, CSS variables yes.

This creates `components.json`, `src/lib/utils.ts`, `src/index.css` with Tailwind directives and shadcn CSS variables.

**Step 2: Add path alias to tsconfig.app.json**

shadcn init should add `@/*` path alias. Verify it maps `@/*` to `./src/*`.

**Step 3: Add path alias to vite.config.ts**

shadcn init should add the resolve alias. Verify:

```typescript
resolve: {
  alias: {
    "@": path.resolve(__dirname, "./src"),
  },
},
```

**Step 4: Create minimal main.tsx and App.tsx**

`src/main.tsx`:
```tsx
import { StrictMode } from "react"
import { createRoot } from "react-dom/client"
import "./index.css"
import App from "./App"

createRoot(document.getElementById("root")!).render(
  <StrictMode>
    <App />
  </StrictMode>,
)
```

`src/App.tsx`:
```tsx
export default function App() {
  return <div className="p-4">JakeOps</div>
}
```

**Step 5: Create test setup file**

`src/test/setup.ts`:
```typescript
import "@testing-library/jest-dom/vitest"
```

**Step 6: Verify build**

```bash
cd frontend && npm run build
```

Expected: SUCCESS

**Step 7: Commit**

```bash
git add frontend/
git commit -m "chore: initialize shadcn/ui + TailwindCSS"
```

---

### Task 2: Install required shadcn components

**Files:**
- Create: `frontend/src/components/ui/*.tsx` (multiple shadcn components)

**Step 1: Install all needed shadcn components**

```bash
cd frontend
npx shadcn@latest add badge button card collapsible dialog input label separator sidebar switch table
```

These are all read-only after installation. Never modify.

**Step 2: Verify build**

```bash
cd frontend && npm run build
```

Expected: SUCCESS

**Step 3: Commit**

```bash
git add frontend/src/components/ui/
git commit -m "chore: install shadcn components (badge, button, card, collapsible, dialog, input, label, separator, sidebar, switch, table)"
```

---

### Task 3: Types + API utilities

**Files:**
- Create: `frontend/src/types.ts`
- Create: `frontend/src/utils/api.ts`
- Create: `frontend/src/utils/format.ts`
- Test: `frontend/src/utils/__tests__/api.test.ts`
- Test: `frontend/src/utils/__tests__/format.test.ts`

**Step 1: Write types.ts**

Mirror backend domain models exactly. See `backend/app/domain/models/delivery.py`, `agent_run.py`, `source.py`, `worker.py`.

```typescript
// Phase pipeline
export type Phase = "intake" | "plan" | "implement" | "review" | "verify" | "deploy" | "observe" | "close"
export type RunStatus = "pending" | "running" | "succeeded" | "failed" | "blocked" | "canceled"
export type ExecutorKind = "system" | "agent" | "human"

// Refs
export type RefRole = "trigger" | "output" | "parent"
export type RefType = "jira" | "verbal" | "pr" | "commit" | "repo" | "github_issue" | "pull_request" | "issue"

export interface Ref {
  role: RefRole
  type: RefType
  label: string
  url?: string
}

// Phase run history
export interface PhaseRun {
  phase: Phase
  run_status: RunStatus
  executor: ExecutorKind
  started_at?: string
  ended_at?: string
}

// Agent execution
export interface ExecutionStats {
  cost_usd: number
  input_tokens: number
  output_tokens: number
  duration_ms: number
}

export interface AgentRun {
  id: string
  mode: "plan" | "execution" | "fix"
  status: "success" | "failed"
  created_at: string
  session: { model: string }
  stats: ExecutionStats
  error?: string
  summary?: string
  session_id?: string
}

// Plan
export interface Plan {
  content: string
  generated_at: string
  model: string
  cwd: string
}

// Delivery
export interface Delivery {
  id: string
  schema_version: number
  created_at: string
  updated_at: string
  phase: Phase
  run_status: RunStatus
  exit_phase: Phase
  summary: string
  repository: string
  refs: Ref[]
  runs: AgentRun[]
  phase_runs: PhaseRun[]
  plan?: Plan
  error?: string
}

// Source
export type SourceType = "github"

export interface Source {
  id: string
  type: SourceType
  owner: string
  repo: string
  created_at: string
  token: string
  active: boolean
  default_exit_phase: string
}

export interface SourceCreate {
  type: SourceType
  owner: string
  repo: string
  token?: string
  default_exit_phase?: string
}

export interface SourceUpdate {
  token?: string
  active?: boolean
  default_exit_phase?: string
}

// Worker
export interface WorkerStatus {
  name: string
  label: string
  enabled: boolean
  interval_sec: number
  last_poll_at?: string
  last_result?: Record<string, unknown>
  last_error?: string
}

// Transcript
export interface TranscriptBlock {
  type: string
  text?: string
  thinking?: string
  name?: string
  input?: Record<string, unknown>
  content?: unknown
  tool_use_id?: string
}

export interface TranscriptMessage {
  role: string
  content: TranscriptBlock[] | string | null
}

export interface TranscriptData {
  meta: {
    agents: Record<string, { model: string }>
  }
  [agentKey: string]: TranscriptMessage[] | { agents: Record<string, { model: string }> }
}
```

**Step 2: Write failing tests for api.ts**

`src/utils/__tests__/api.test.ts`:

```typescript
import { describe, it, expect, vi, beforeEach } from "vitest"
import { apiFetch, apiPost, apiPatch, apiDelete } from "../api"

const mockFetch = vi.fn()
global.fetch = mockFetch

beforeEach(() => {
  mockFetch.mockReset()
})

describe("apiFetch", () => {
  it("sends GET request to /api + path", async () => {
    mockFetch.mockResolvedValue({ ok: true, json: () => Promise.resolve([]) })
    const result = await apiFetch<unknown[]>("/deliveries")
    expect(mockFetch).toHaveBeenCalledWith("/api/deliveries", { method: "GET" })
    expect(result).toEqual([])
  })

  it("throws on non-ok response", async () => {
    mockFetch.mockResolvedValue({ ok: false, status: 404, json: () => Promise.resolve({ detail: "Not found" }) })
    await expect(apiFetch("/deliveries/xxx")).rejects.toThrow("Not found")
  })
})

describe("apiPost", () => {
  it("sends POST with JSON body", async () => {
    mockFetch.mockResolvedValue({ ok: true, json: () => Promise.resolve({ id: "abc" }) })
    const result = await apiPost("/deliveries", { summary: "test" })
    expect(mockFetch).toHaveBeenCalledWith("/api/deliveries", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ summary: "test" }),
    })
    expect(result).toEqual({ id: "abc" })
  })
})

describe("apiPatch", () => {
  it("sends PATCH with JSON body", async () => {
    mockFetch.mockResolvedValue({ ok: true, json: () => Promise.resolve({ id: "abc" }) })
    await apiPatch("/deliveries/abc", { phase: "plan" })
    expect(mockFetch).toHaveBeenCalledWith("/api/deliveries/abc", {
      method: "PATCH",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ phase: "plan" }),
    })
  })
})

describe("apiDelete", () => {
  it("sends DELETE request", async () => {
    mockFetch.mockResolvedValue({ ok: true, json: () => Promise.resolve({ status: "deleted" }) })
    await apiDelete("/sources/abc")
    expect(mockFetch).toHaveBeenCalledWith("/api/sources/abc", { method: "DELETE" })
  })
})
```

**Step 3: Run tests — verify they fail**

```bash
cd frontend && npx vitest run src/utils/__tests__/api.test.ts
```

Expected: FAIL (module not found)

**Step 4: Implement api.ts**

`src/utils/api.ts`:

```typescript
class ApiError extends Error {
  constructor(public status: number, message: string) {
    super(message)
  }
}

async function handleResponse<T>(response: Response): Promise<T> {
  if (!response.ok) {
    const body = await response.json().catch(() => ({}))
    throw new ApiError(response.status, body.detail || `HTTP ${response.status}`)
  }
  return response.json()
}

export async function apiFetch<T>(path: string): Promise<T> {
  const response = await fetch(`/api${path}`, { method: "GET" })
  return handleResponse<T>(response)
}

export async function apiPost<T>(path: string, body?: unknown): Promise<T> {
  const response = await fetch(`/api${path}`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(body),
  })
  return handleResponse<T>(response)
}

export async function apiPatch<T>(path: string, body: unknown): Promise<T> {
  const response = await fetch(`/api${path}`, {
    method: "PATCH",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(body),
  })
  return handleResponse<T>(response)
}

export async function apiDelete<T>(path: string): Promise<T> {
  const response = await fetch(`/api${path}`, { method: "DELETE" })
  return handleResponse<T>(response)
}
```

**Step 5: Run tests — verify they pass**

```bash
cd frontend && npx vitest run src/utils/__tests__/api.test.ts
```

Expected: PASS (all 4 tests)

**Step 6: Write failing tests for format.ts**

`src/utils/__tests__/format.test.ts`:

```typescript
import { describe, it, expect } from "vitest"
import { formatRelativeTime, formatDateTime } from "../format"

describe("formatRelativeTime", () => {
  it("returns 'just now' for recent timestamps", () => {
    const now = new Date().toISOString()
    expect(formatRelativeTime(now)).toBe("just now")
  })

  it("returns '5m ago' for 5 minutes ago", () => {
    const date = new Date(Date.now() - 5 * 60 * 1000).toISOString()
    expect(formatRelativeTime(date)).toBe("5m ago")
  })

  it("returns '2h ago' for 2 hours ago", () => {
    const date = new Date(Date.now() - 2 * 60 * 60 * 1000).toISOString()
    expect(formatRelativeTime(date)).toBe("2h ago")
  })

  it("returns '3d ago' for 3 days ago", () => {
    const date = new Date(Date.now() - 3 * 24 * 60 * 60 * 1000).toISOString()
    expect(formatRelativeTime(date)).toBe("3d ago")
  })
})

describe("formatDateTime", () => {
  it("formats ISO string to readable date", () => {
    const result = formatDateTime("2026-02-20T10:30:00+09:00")
    expect(result).toMatch(/2026/)
  })
})
```

**Step 7: Run — verify fail**

```bash
cd frontend && npx vitest run src/utils/__tests__/format.test.ts
```

Expected: FAIL

**Step 8: Implement format.ts**

`src/utils/format.ts`:

```typescript
export function formatRelativeTime(isoString: string): string {
  const diff = Date.now() - new Date(isoString).getTime()
  const seconds = Math.floor(diff / 1000)

  if (seconds < 60) return "just now"

  const minutes = Math.floor(seconds / 60)
  if (minutes < 60) return `${minutes}m ago`

  const hours = Math.floor(minutes / 60)
  if (hours < 24) return `${hours}h ago`

  const days = Math.floor(hours / 24)
  return `${days}d ago`
}

export function formatDateTime(isoString: string): string {
  return new Date(isoString).toLocaleString()
}
```

**Step 9: Run — verify pass**

```bash
cd frontend && npx vitest run src/utils/__tests__/
```

Expected: PASS (all tests)

**Step 10: Commit**

```bash
git add frontend/src/types.ts frontend/src/utils/ frontend/src/test/
git commit -m "feat: add domain types, API client, and format utilities"
```

---

### Task 4: App Layout (Sidebar + Routing)

**Files:**
- Create: `frontend/src/components/app-sidebar.tsx`
- Create: `frontend/src/components/app-layout.tsx`
- Modify: `frontend/src/App.tsx`
- Modify: `frontend/src/main.tsx`

**Step 1: Create AppSidebar**

`src/components/app-sidebar.tsx`:

Uses shadcn Sidebar component. Navigation items: Deliveries, Sources, Worker.
Each item uses React Router `NavLink` for active state.

```tsx
import { Package, GitFork, Activity } from "lucide-react"
import { NavLink } from "react-router"
import {
  Sidebar,
  SidebarContent,
  SidebarGroup,
  SidebarGroupContent,
  SidebarGroupLabel,
  SidebarHeader,
  SidebarMenu,
  SidebarMenuButton,
  SidebarMenuItem,
} from "@/components/ui/sidebar"

const NAV_ITEMS = [
  { to: "/deliveries", label: "Deliveries", icon: Package },
  { to: "/sources", label: "Sources", icon: GitFork },
  { to: "/worker", label: "Worker", icon: Activity },
]

export function AppSidebar() {
  return (
    <Sidebar>
      <SidebarHeader>
        <span className="px-2 text-lg font-semibold">JakeOps</span>
      </SidebarHeader>
      <SidebarContent>
        <SidebarGroup>
          <SidebarGroupLabel>Navigation</SidebarGroupLabel>
          <SidebarGroupContent>
            <SidebarMenu>
              {NAV_ITEMS.map((item) => (
                <SidebarMenuItem key={item.to}>
                  <SidebarMenuButton asChild>
                    <NavLink to={item.to}>
                      <item.icon />
                      <span>{item.label}</span>
                    </NavLink>
                  </SidebarMenuButton>
                </SidebarMenuItem>
              ))}
            </SidebarMenu>
          </SidebarGroupContent>
        </SidebarGroup>
      </SidebarContent>
    </Sidebar>
  )
}
```

Note: `lucide-react` is installed as a shadcn dependency.

**Step 2: Create AppLayout**

`src/components/app-layout.tsx`:

```tsx
import { Outlet } from "react-router"
import { SidebarInset, SidebarProvider, SidebarTrigger } from "@/components/ui/sidebar"
import { Separator } from "@/components/ui/separator"
import { AppSidebar } from "./app-sidebar"

export function AppLayout() {
  return (
    <SidebarProvider>
      <AppSidebar />
      <SidebarInset>
        <header className="flex h-12 items-center gap-2 border-b px-4">
          <SidebarTrigger />
          <Separator orientation="vertical" className="h-4" />
          <span className="text-sm text-muted-foreground">Control Plane for Agent-Driven DevOps</span>
        </header>
        <main className="flex-1 p-4">
          <Outlet />
        </main>
      </SidebarInset>
    </SidebarProvider>
  )
}
```

**Step 3: Set up routing in App.tsx**

`src/App.tsx`:

```tsx
import { BrowserRouter, Routes, Route, Navigate } from "react-router"
import { AppLayout } from "./components/app-layout"

// Placeholder pages — replaced in subsequent tasks
function Placeholder({ name }: { name: string }) {
  return <div className="text-lg">{name}</div>
}

export default function App() {
  return (
    <BrowserRouter>
      <Routes>
        <Route element={<AppLayout />}>
          <Route index element={<Navigate to="/deliveries" replace />} />
          <Route path="deliveries" element={<Placeholder name="Deliveries" />} />
          <Route path="deliveries/:id" element={<Placeholder name="Delivery Detail" />} />
          <Route path="deliveries/:id/runs/:runId/transcript" element={<Placeholder name="Transcript" />} />
          <Route path="sources" element={<Placeholder name="Sources" />} />
          <Route path="worker" element={<Placeholder name="Worker" />} />
        </Route>
      </Routes>
    </BrowserRouter>
  )
}
```

**Step 4: Verify build + dev server**

```bash
cd frontend && npm run build
```

Expected: SUCCESS

**Step 5: Commit**

```bash
git add frontend/src/
git commit -m "feat: add app shell with sidebar navigation and routing"
```

---

### Task 5: Delivery List Page

**Files:**
- Create: `frontend/src/hooks/use-deliveries.ts`
- Create: `frontend/src/pages/deliveries/list.tsx`
- Test: `frontend/src/hooks/__tests__/use-deliveries.test.ts`
- Modify: `frontend/src/App.tsx` (swap placeholder)

**Step 1: Write failing test for useDeliveries hook**

`src/hooks/__tests__/use-deliveries.test.ts`:

```typescript
import { describe, it, expect, vi, beforeEach } from "vitest"
import { renderHook, waitFor } from "@testing-library/react"
import { useDeliveries } from "../use-deliveries"
import * as api from "@/utils/api"

vi.mock("@/utils/api")

const MOCK_DELIVERIES = [
  {
    id: "abc123",
    phase: "plan",
    run_status: "succeeded",
    summary: "Test delivery",
    repository: "owner/repo",
    updated_at: new Date().toISOString(),
    refs: [],
    runs: [],
    phase_runs: [],
  },
]

describe("useDeliveries", () => {
  beforeEach(() => {
    vi.mocked(api.apiFetch).mockResolvedValue(MOCK_DELIVERIES)
  })

  it("fetches deliveries on mount", async () => {
    const { result } = renderHook(() => useDeliveries())
    expect(result.current.loading).toBe(true)
    await waitFor(() => expect(result.current.loading).toBe(false))
    expect(result.current.deliveries).toEqual(MOCK_DELIVERIES)
    expect(api.apiFetch).toHaveBeenCalledWith("/deliveries")
  })
})
```

**Step 2: Run test — verify fail**

```bash
cd frontend && npx vitest run src/hooks/__tests__/use-deliveries.test.ts
```

**Step 3: Implement useDeliveries hook**

`src/hooks/use-deliveries.ts`:

```typescript
import { useCallback, useEffect, useState } from "react"
import type { Delivery } from "@/types"
import { apiFetch } from "@/utils/api"

export function useDeliveries() {
  const [deliveries, setDeliveries] = useState<Delivery[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)

  const refresh = useCallback(async () => {
    setLoading(true)
    setError(null)
    try {
      const data = await apiFetch<Delivery[]>("/deliveries")
      setDeliveries(data)
    } catch (e) {
      setError(e instanceof Error ? e.message : "Unknown error")
    } finally {
      setLoading(false)
    }
  }, [])

  useEffect(() => { refresh() }, [refresh])

  return { deliveries, loading, error, refresh }
}
```

**Step 4: Run test — verify pass**

```bash
cd frontend && npx vitest run src/hooks/__tests__/use-deliveries.test.ts
```

**Step 5: Create DeliveryList page**

`src/pages/deliveries/list.tsx`:

Uses shadcn Table + Badge. Links to detail page via React Router.

```tsx
import { Link } from "react-router"
import { Badge } from "@/components/ui/badge"
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table"
import { useDeliveries } from "@/hooks/use-deliveries"
import { formatRelativeTime } from "@/utils/format"
import type { Phase, RunStatus } from "@/types"

const PHASE_VARIANT: Record<Phase, string> = {
  intake: "bg-slate-100 text-slate-700",
  plan: "bg-blue-100 text-blue-700",
  implement: "bg-violet-100 text-violet-700",
  review: "bg-amber-100 text-amber-700",
  verify: "bg-cyan-100 text-cyan-700",
  deploy: "bg-green-100 text-green-700",
  observe: "bg-emerald-100 text-emerald-700",
  close: "bg-gray-100 text-gray-500",
}

const STATUS_VARIANT: Record<RunStatus, string> = {
  pending: "bg-gray-100 text-gray-700",
  running: "bg-blue-100 text-blue-700",
  succeeded: "bg-green-100 text-green-700",
  failed: "bg-red-100 text-red-700",
  blocked: "bg-yellow-100 text-yellow-700",
  canceled: "bg-gray-100 text-gray-500",
}

export function DeliveryList() {
  const { deliveries, loading, error } = useDeliveries()

  if (loading) return <div className="p-4 text-muted-foreground">Loading...</div>
  if (error) return <div className="p-4 text-destructive">{error}</div>

  return (
    <div>
      <h1 className="mb-4 text-2xl font-semibold">Deliveries</h1>
      <Table>
        <TableHeader>
          <TableRow>
            <TableHead>Summary</TableHead>
            <TableHead>Phase</TableHead>
            <TableHead>Status</TableHead>
            <TableHead>Repository</TableHead>
            <TableHead>Updated</TableHead>
          </TableRow>
        </TableHeader>
        <TableBody>
          {deliveries.map((d) => (
            <TableRow key={d.id}>
              <TableCell>
                <Link to={`/deliveries/${d.id}`} className="font-medium hover:underline">
                  {d.summary}
                </Link>
              </TableCell>
              <TableCell>
                <Badge className={PHASE_VARIANT[d.phase]}>{d.phase}</Badge>
              </TableCell>
              <TableCell>
                <Badge className={STATUS_VARIANT[d.run_status]}>{d.run_status}</Badge>
              </TableCell>
              <TableCell className="text-muted-foreground">{d.repository}</TableCell>
              <TableCell className="text-muted-foreground">
                {formatRelativeTime(d.updated_at)}
              </TableCell>
            </TableRow>
          ))}
          {deliveries.length === 0 && (
            <TableRow>
              <TableCell colSpan={5} className="text-center text-muted-foreground">
                No deliveries yet.
              </TableCell>
            </TableRow>
          )}
        </TableBody>
      </Table>
    </div>
  )
}
```

**Step 6: Wire into App.tsx**

Replace the deliveries placeholder route with:
```tsx
import { DeliveryList } from "./pages/deliveries/list"
// ...
<Route path="deliveries" element={<DeliveryList />} />
```

**Step 7: Verify build**

```bash
cd frontend && npm run build
```

**Step 8: Commit**

```bash
git add frontend/src/
git commit -m "feat: add delivery list page with phase/status badges"
```

---

### Task 6: Delivery Detail Page

**Files:**
- Create: `frontend/src/hooks/use-delivery.ts`
- Create: `frontend/src/pages/deliveries/show.tsx`
- Test: `frontend/src/hooks/__tests__/use-delivery.test.ts`
- Modify: `frontend/src/App.tsx` (swap placeholder)

**Step 1: Write failing test for useDelivery hook**

`src/hooks/__tests__/use-delivery.test.ts`:

```typescript
import { describe, it, expect, vi, beforeEach } from "vitest"
import { renderHook, waitFor } from "@testing-library/react"
import { useDelivery } from "../use-delivery"
import * as api from "@/utils/api"

vi.mock("@/utils/api")

const MOCK_DELIVERY = {
  id: "abc123",
  phase: "plan",
  run_status: "succeeded",
  summary: "Test delivery",
  repository: "owner/repo",
  refs: [],
  runs: [],
  phase_runs: [
    { phase: "intake", run_status: "succeeded", executor: "system", started_at: "2026-02-20T10:00:00" },
    { phase: "plan", run_status: "succeeded", executor: "agent", started_at: "2026-02-20T10:01:00" },
  ],
}

describe("useDelivery", () => {
  beforeEach(() => {
    vi.mocked(api.apiFetch).mockResolvedValue(MOCK_DELIVERY)
  })

  it("fetches delivery by id", async () => {
    const { result } = renderHook(() => useDelivery("abc123"))
    await waitFor(() => expect(result.current.loading).toBe(false))
    expect(result.current.delivery).toEqual(MOCK_DELIVERY)
    expect(api.apiFetch).toHaveBeenCalledWith("/deliveries/abc123")
  })
})
```

**Step 2: Run test — verify fail**

```bash
cd frontend && npx vitest run src/hooks/__tests__/use-delivery.test.ts
```

**Step 3: Implement useDelivery hook**

`src/hooks/use-delivery.ts`:

```typescript
import { useCallback, useEffect, useState } from "react"
import type { Delivery } from "@/types"
import { apiFetch, apiPost } from "@/utils/api"

export function useDelivery(id: string) {
  const [delivery, setDelivery] = useState<Delivery | null>(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)

  const refresh = useCallback(async () => {
    setLoading(true)
    setError(null)
    try {
      const data = await apiFetch<Delivery>(`/deliveries/${id}`)
      setDelivery(data)
    } catch (e) {
      setError(e instanceof Error ? e.message : "Unknown error")
    } finally {
      setLoading(false)
    }
  }, [id])

  useEffect(() => { refresh() }, [refresh])

  const approve = useCallback(async () => {
    await apiPost(`/deliveries/${id}/approve`)
    await refresh()
  }, [id, refresh])

  const reject = useCallback(async (reason: string) => {
    await apiPost(`/deliveries/${id}/reject`, { reason })
    await refresh()
  }, [id, refresh])

  const retry = useCallback(async () => {
    await apiPost(`/deliveries/${id}/retry`)
    await refresh()
  }, [id, refresh])

  const cancel = useCallback(async () => {
    await apiPost(`/deliveries/${id}/cancel`)
    await refresh()
  }, [id, refresh])

  const generatePlan = useCallback(async () => {
    await apiPost(`/deliveries/${id}/generate-plan`)
    await refresh()
  }, [id, refresh])

  return { delivery, loading, error, refresh, approve, reject, retry, cancel, generatePlan }
}
```

**Step 4: Run test — verify pass**

```bash
cd frontend && npx vitest run src/hooks/__tests__/use-delivery.test.ts
```

**Step 5: Create DeliveryShow page**

`src/pages/deliveries/show.tsx`:

This page shows:
- Header with summary, badges, repository
- Action buttons (conditional on phase + run_status)
- Refs section
- Plan section (if exists)
- Phase runs history with executor badges (system/agent/human — KEY DIFFERENTIATOR)
- Agent runs list with links to transcript viewer

Gate phases from backend: `plan`, `review`, `deploy`.
Approve requires: gate phase + `run_status === "succeeded"`.
Reject: gate phase only.
Retry: `run_status === "failed"`.
Generate Plan: `phase === "intake"`.

Uses: shadcn Badge, Button, Card, Separator.

Executor badge colors (Tailwind classes):
- system: `bg-gray-100 text-gray-700`
- agent: `bg-violet-100 text-violet-700`
- human: `bg-blue-100 text-blue-700`

**Step 6: Wire into App.tsx**

Replace placeholder with `DeliveryShow` component, using `useParams` for the `id`.

**Step 7: Verify build**

```bash
cd frontend && npm run build
```

**Step 8: Commit**

```bash
git add frontend/src/
git commit -m "feat: add delivery detail page with actions and phase run history"
```

---

### Task 7: Transcript Viewer Page

**Files:**
- Create: `frontend/src/hooks/use-transcript.ts`
- Create: `frontend/src/pages/deliveries/transcript.tsx`
- Test: `frontend/src/hooks/__tests__/use-transcript.test.ts`
- Modify: `frontend/src/App.tsx` (swap placeholder)

**Step 1: Write failing test for useTranscript hook**

`src/hooks/__tests__/use-transcript.test.ts`:

```typescript
import { describe, it, expect, vi, beforeEach } from "vitest"
import { renderHook, waitFor } from "@testing-library/react"
import { useTranscript } from "../use-transcript"
import * as api from "@/utils/api"

vi.mock("@/utils/api")

const MOCK_TRANSCRIPT = {
  meta: { agents: { leader: { model: "claude-opus-4-6" } } },
  leader: [
    { role: "assistant", content: [{ type: "thinking", thinking: "Let me analyze..." }] },
    { role: "assistant", content: [{ type: "text", text: "I'll fix the bug." }] },
    { role: "assistant", content: [{ type: "tool_use", name: "Read", input: { file_path: "/src/main.ts" } }] },
  ],
}

describe("useTranscript", () => {
  beforeEach(() => {
    vi.mocked(api.apiFetch).mockResolvedValue(MOCK_TRANSCRIPT)
  })

  it("fetches transcript by delivery and run id", async () => {
    const { result } = renderHook(() => useTranscript("abc123", "run01"))
    await waitFor(() => expect(result.current.loading).toBe(false))
    expect(result.current.transcript).toEqual(MOCK_TRANSCRIPT)
    expect(api.apiFetch).toHaveBeenCalledWith("/deliveries/abc123/runs/run01/transcript")
  })
})
```

**Step 2: Run test — verify fail**

```bash
cd frontend && npx vitest run src/hooks/__tests__/use-transcript.test.ts
```

**Step 3: Implement useTranscript hook**

`src/hooks/use-transcript.ts`:

```typescript
import { useCallback, useEffect, useState } from "react"
import type { TranscriptData } from "@/types"
import { apiFetch } from "@/utils/api"

export function useTranscript(deliveryId: string, runId: string) {
  const [transcript, setTranscript] = useState<TranscriptData | null>(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)

  const refresh = useCallback(async () => {
    setLoading(true)
    setError(null)
    try {
      const data = await apiFetch<TranscriptData>(`/deliveries/${deliveryId}/runs/${runId}/transcript`)
      setTranscript(data)
    } catch (e) {
      setError(e instanceof Error ? e.message : "Unknown error")
    } finally {
      setLoading(false)
    }
  }, [deliveryId, runId])

  useEffect(() => { refresh() }, [refresh])

  return { transcript, loading, error, refresh }
}
```

**Step 4: Run test — verify pass**

```bash
cd frontend && npx vitest run src/hooks/__tests__/use-transcript.test.ts
```

**Step 5: Create TranscriptViewer page**

`src/pages/deliveries/transcript.tsx`:

Layout:
- Top bar: agent model, execution stats (cost, tokens, duration)
- Left panel: agent list (leader + subagent_* keys), clickable to switch
- Right panel: selected agent's messages

Content block rendering (all Tailwind, no custom CSS):
- `thinking` block: collapsible via shadcn Collapsible, muted background (`bg-muted`), label "Thinking"
- `tool_use` block: collapsible, shows tool name as label, `pre` for JSON input
- `tool_result` block: collapsible, `pre` for content
- `text` block: rendered as-is in a div

Uses: shadcn Collapsible, Badge, Separator, Card.
All styling via Tailwind utility classes.

**Step 6: Wire into App.tsx**

Replace placeholder with `TranscriptViewer` using `useParams` for `id` and `runId`.

**Step 7: Verify build**

```bash
cd frontend && npm run build
```

**Step 8: Commit**

```bash
git add frontend/src/
git commit -m "feat: add transcript viewer with thinking/tool block rendering"
```

---

### Task 8: Sources Page

**Files:**
- Create: `frontend/src/hooks/use-sources.ts`
- Create: `frontend/src/pages/sources/list.tsx`
- Test: `frontend/src/hooks/__tests__/use-sources.test.ts`
- Modify: `frontend/src/App.tsx` (swap placeholder)

**Step 1: Write failing test for useSources hook**

Test should cover: fetch on mount, create, update, delete, sync.

**Step 2: Run test — verify fail**

**Step 3: Implement useSources hook**

`src/hooks/use-sources.ts`:

Provides: `sources`, `loading`, `error`, `refresh`, `createSource`, `updateSource`, `deleteSource`, `syncNow`.

Uses `apiFetch`, `apiPost`, `apiPatch`, `apiDelete` from `@/utils/api`.

**Step 4: Run test — verify pass**

**Step 5: Create SourceList page**

`src/pages/sources/list.tsx`:

- shadcn Table for list display
- shadcn Dialog for create/edit forms
- shadcn Button for actions (Create, Edit, Delete, Sync Now)
- shadcn Input + Label for form fields (type, owner, repo, token, default_exit_phase)
- shadcn Badge for active status
- Delete with confirmation (shadcn Dialog)

**Step 6: Wire into App.tsx, verify build, commit**

```bash
git commit -m "feat: add sources page with CRUD and sync"
```

---

### Task 9: Worker Status Page

**Files:**
- Create: `frontend/src/hooks/use-worker.ts`
- Create: `frontend/src/pages/worker/status.tsx`
- Test: `frontend/src/hooks/__tests__/use-worker.test.ts`
- Modify: `frontend/src/App.tsx` (swap placeholder)

**Step 1: Write failing test for useWorker hook**

**Step 2: Run test — verify fail**

**Step 3: Implement useWorker hook**

`src/hooks/use-worker.ts`:

Fetches `/worker/status`, returns `workers` array.

**Step 4: Run test — verify pass**

**Step 5: Create WorkerStatus page**

`src/pages/worker/status.tsx`:

- shadcn Card per worker
- Shows: name, label, enabled (badge), interval, last_poll_at
- Color-coded: green if recent + no error, red if error, gray if disabled
- Last result/error displayed in `pre` block if present

**Step 6: Wire into App.tsx, verify build, commit**

```bash
git commit -m "feat: add worker status page"
```

---

### Task 10: Final Verification

**Step 1: Run all tests**

```bash
cd frontend && npx vitest run
```

Expected: ALL PASS

**Step 2: Run lint**

```bash
cd frontend && npm run lint
```

Expected: No errors

**Step 3: Run build**

```bash
cd frontend && npm run build
```

Expected: SUCCESS

**Step 4: Fix any issues found in steps 1-3**

**Step 5: Final commit if any fixes needed**

```bash
git commit -m "fix: resolve lint/test/build issues"
```

---

### Task 11: Clean up App.tsx and remove Placeholder

**Step 1: Verify no Placeholder references remain in App.tsx**

All routes should point to real page components. Remove the `Placeholder` function if it still exists.

**Step 2: Verify build**

```bash
cd frontend && npm run build
```

**Step 3: Commit**

```bash
git commit -m "chore: remove placeholder components"
```
