# Frontend UI Refactor Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Fix layout issues, add checkpoint/endpoint UI to sources, separate active/closed deliveries, make table rows clickable, and display delivery current state.

**Architecture:** Component-level changes across layout, source forms, delivery list/board, and detail page. No new hooks or API changes needed — all data already available from existing endpoints.

**Tech Stack:** React 19, TypeScript, shadcn/ui (Tabs + Select to install), TailwindCSS, React Router 7, Vitest

---

### Task 1: Install shadcn Tabs and Select components

**Files:**
- Create: `frontend/src/components/ui/tabs.tsx`
- Create: `frontend/src/components/ui/select.tsx`
- Create: `frontend/src/components/ui/checkbox.tsx`

**Step 1: Install Tabs component**

Run: `cd frontend && npx shadcn@latest add tabs`

**Step 2: Install Select component**

Run: `cd frontend && npx shadcn@latest add select`

**Step 3: Install Checkbox component**

Run: `cd frontend && npx shadcn@latest add checkbox`

**Step 4: Verify files exist**

Run: `ls frontend/src/components/ui/tabs.tsx frontend/src/components/ui/select.tsx frontend/src/components/ui/checkbox.tsx`

**Step 5: Commit**

```bash
git add frontend/src/components/ui/tabs.tsx frontend/src/components/ui/select.tsx frontend/src/components/ui/checkbox.tsx
git commit -m "chore: add shadcn tabs, select, checkbox components"
```

---

### Task 2: Fix sidebar height and main header hierarchy

**Files:**
- Modify: `frontend/src/components/app-sidebar.tsx:22` — add `className="h-full"`
- Modify: `frontend/src/components/app-layout.tsx:27-28` — promote header styling

**Step 1: Fix sidebar height**

In `frontend/src/components/app-sidebar.tsx`, change:
```tsx
<Sidebar collapsible="none">
```
to:
```tsx
<Sidebar collapsible="none" className="h-full">
```

**Step 2: Promote main header**

In `frontend/src/components/app-layout.tsx`, change:
```tsx
<header className="flex h-10 items-center border-b px-4">
  <span className="text-sm font-medium">{title}</span>
</header>
```
to:
```tsx
<header className="flex h-12 items-center border-b px-4">
  <span className="text-lg font-semibold">{title}</span>
</header>
```

**Step 3: Run build to verify**

Run: `cd frontend && npm run build`
Expected: No errors

**Step 4: Commit**

```bash
git add frontend/src/components/app-sidebar.tsx frontend/src/components/app-layout.tsx
git commit -m "fix: sidebar full height and consistent header hierarchy"
```

---

### Task 3: Remove redundant Sources title and fix table row height

**Files:**
- Modify: `frontend/src/pages/sources/list.tsx:276-289` — remove h1, move buttons into page header area
- Modify: `frontend/src/components/app-layout.tsx:27-30` — add slot for page actions in header

**Step 1: Add action slot to layout header**

The main header currently only shows a title. We need to support page-level action buttons (like "Sync Now" and "Add Source") in the header bar so that removing the redundant `<h1>` doesn't lose the button placement.

In `frontend/src/components/app-layout.tsx`, add an `Outlet` context or just move to a pattern where pages render their own header actions.

Simpler approach: keep the header showing title only, and let each page render its own action bar below. For Sources, just remove the `<h1>` and keep the button row.

In `frontend/src/pages/sources/list.tsx`, change:
```tsx
<div className="space-y-4">
  <div className="flex items-center justify-between">
    <h1 className="text-2xl font-semibold">Sources</h1>
    <div className="flex items-center gap-2">
      <Button
        variant="outline"
        onClick={handleSyncNow}
        disabled={syncing}
      >
        {syncing ? "Syncing..." : "Sync Now"}
      </Button>
      <AddSourceDialog onSubmit={createSource} />
    </div>
  </div>
```
to:
```tsx
<div className="space-y-4">
  <div className="flex items-center justify-end">
    <div className="flex items-center gap-2">
      <Button
        variant="outline"
        onClick={handleSyncNow}
        disabled={syncing}
      >
        {syncing ? "Syncing..." : "Sync Now"}
      </Button>
      <AddSourceDialog onSubmit={createSource} />
    </div>
  </div>
```

**Step 2: Fix table action button height**

In `frontend/src/pages/sources/list.tsx`, in the `EditSourceDialog` trigger button and the Delete button, add compact sizing. Change:
```tsx
<Button variant="outline" size="sm">
  Edit
</Button>
```
to:
```tsx
<Button variant="outline" size="sm" className="h-7 text-xs">
  Edit
</Button>
```

And for Delete button, change:
```tsx
<Button
  variant="destructive"
  size="sm"
  onClick={() => handleDelete(s)}
>
  Delete
</Button>
```
to:
```tsx
<Button
  variant="destructive"
  size="sm"
  className="h-7 text-xs"
  onClick={() => handleDelete(s)}
>
  Delete
</Button>
```

**Step 3: Run build to verify**

Run: `cd frontend && npm run build`
Expected: No errors

**Step 4: Commit**

```bash
git add frontend/src/pages/sources/list.tsx
git commit -m "fix: remove redundant Sources title, compact table action buttons"
```

---

### Task 4: Add isTerminal utility and test

**Files:**
- Modify: `frontend/src/utils/kanban-rules.ts` — add `isTerminal` function
- Modify: `frontend/src/utils/__tests__/kanban-rules.test.ts` — add tests

This utility will be shared by delivery list, board, and detail page.

**Step 1: Write the failing test**

Add to `frontend/src/utils/__tests__/kanban-rules.test.ts`:
```typescript
import { PHASES, ACTION_PHASES, isTerminal } from "../kanban-rules"

// ... existing tests ...

describe("isTerminal", () => {
  it("returns true when phase is close and run_status is succeeded", () => {
    expect(isTerminal("close", "succeeded")).toBe(true)
  })

  it("returns true when run_status is canceled regardless of phase", () => {
    expect(isTerminal("intake", "canceled")).toBe(true)
    expect(isTerminal("plan", "canceled")).toBe(true)
    expect(isTerminal("close", "canceled")).toBe(true)
  })

  it("returns false for active deliveries", () => {
    expect(isTerminal("intake", "pending")).toBe(false)
    expect(isTerminal("plan", "running")).toBe(false)
    expect(isTerminal("review", "succeeded")).toBe(false)
    expect(isTerminal("deploy", "failed")).toBe(false)
  })

  it("returns false for close phase with non-succeeded status", () => {
    expect(isTerminal("close", "running")).toBe(false)
    expect(isTerminal("close", "failed")).toBe(false)
    expect(isTerminal("close", "pending")).toBe(false)
  })
})
```

**Step 2: Run test to verify it fails**

Run: `cd frontend && npx vitest run src/utils/__tests__/kanban-rules.test.ts`
Expected: FAIL — `isTerminal` is not exported

**Step 3: Implement isTerminal**

Add to `frontend/src/utils/kanban-rules.ts`:
```typescript
import type { Phase, RunStatus } from "@/types"

// ... existing code ...

export function isTerminal(phase: Phase, runStatus: RunStatus): boolean {
  return (
    (phase === "close" && runStatus === "succeeded") ||
    runStatus === "canceled"
  )
}
```

**Step 4: Run test to verify it passes**

Run: `cd frontend && npx vitest run src/utils/__tests__/kanban-rules.test.ts`
Expected: All tests PASS

**Step 5: Commit**

```bash
git add frontend/src/utils/kanban-rules.ts frontend/src/utils/__tests__/kanban-rules.test.ts
git commit -m "feat: add isTerminal utility for delivery state classification"
```

---

### Task 5: Source tab — add checkpoint and endpoint controls to forms

**Files:**
- Modify: `frontend/src/pages/sources/list.tsx` — replace endpoint Input with Select, add checkpoints multi-checkbox, add Checkpoints column to table

**Step 1: Update imports**

In `frontend/src/pages/sources/list.tsx`, add imports:
```typescript
import { Checkbox } from "@/components/ui/checkbox"
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select"
import { Badge } from "@/components/ui/badge"
import { PHASES } from "@/utils/kanban-rules"
import { PHASE_CLASSES } from "@/utils/badge-styles"
import type { Phase } from "@/types"
```

Note: `Badge` is already imported. `PHASES` provides the list of all phases for dropdowns/checkboxes.

**Step 2: Update AddSourceDialog state and form**

Add `checkpoints` state:
```typescript
const [checkpoints, setCheckpoints] = useState<string[]>(["plan", "implement", "review"])
```

Add to `reset()`:
```typescript
setCheckpoints(["plan", "implement", "review"])
```

Update `handleSubmit` to include checkpoints:
```typescript
await onSubmit({
  type: "github",
  owner,
  repo,
  token: token || undefined,
  endpoint: endpoint || undefined,
  checkpoints,
})
```

Replace the endpoint `<Input>` with:
```tsx
<div className="grid gap-2">
  <Label htmlFor="add-endpoint">Endpoint</Label>
  <Select value={endpoint} onValueChange={setEndpoint}>
    <SelectTrigger>
      <SelectValue />
    </SelectTrigger>
    <SelectContent>
      {PHASES.map((p) => (
        <SelectItem key={p} value={p}>{p}</SelectItem>
      ))}
    </SelectContent>
  </Select>
</div>
```

Add checkpoints section after endpoint:
```tsx
<div className="grid gap-2">
  <Label>Checkpoints</Label>
  <div className="grid grid-cols-2 gap-2">
    {PHASES.filter((p) => p !== "intake" && p !== "close").map((p) => (
      <label key={p} className="flex items-center gap-2 text-sm">
        <Checkbox
          checked={checkpoints.includes(p)}
          onCheckedChange={(checked) => {
            setCheckpoints((prev) =>
              checked
                ? [...prev, p]
                : prev.filter((c) => c !== p)
            )
          }}
        />
        {p}
      </label>
    ))}
  </div>
</div>
```

**Step 3: Update EditSourceDialog similarly**

Add `checkpoints` state:
```typescript
const [checkpoints, setCheckpoints] = useState<string[]>(source.checkpoints)
```

Add to `resetToSource()`:
```typescript
setCheckpoints(source.checkpoints)
```

Update `handleSubmit` body:
```typescript
const body: SourceUpdate = {
  active,
  endpoint,
  checkpoints,
}
```

Replace endpoint Input with the same Select pattern. Add checkpoints checkboxes after it (same pattern as AddSourceDialog).

**Step 4: Add Checkpoints column to table**

Add header after Endpoint:
```tsx
<TableHead>Checkpoints</TableHead>
```

Add cell after endpoint cell:
```tsx
<TableCell>
  <div className="flex flex-wrap gap-1">
    {s.checkpoints.map((cp) => (
      <Badge
        key={cp}
        variant="secondary"
        className={`text-xs ${PHASE_CLASSES[cp as Phase]}`}
      >
        {cp}
      </Badge>
    ))}
  </div>
</TableCell>
```

**Step 5: Run build to verify**

Run: `cd frontend && npm run build`
Expected: No errors

**Step 6: Commit**

```bash
git add frontend/src/pages/sources/list.tsx
git commit -m "feat: add checkpoint and endpoint controls to source forms and table"
```

---

### Task 6: Delivery list — Active/Closed tabs with clickable rows

**Files:**
- Modify: `frontend/src/pages/deliveries/list.tsx` — add tabs, clickable rows

**Step 1: Rewrite DeliveryList component**

Replace the entire content of `frontend/src/pages/deliveries/list.tsx`:

```typescript
import { useMemo } from "react"
import { useNavigate } from "react-router"
import { Badge } from "@/components/ui/badge"
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table"
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs"
import { useDeliveries } from "@/hooks/use-deliveries"
import type { Delivery } from "@/types"
import { PHASE_CLASSES, STATUS_CLASSES } from "@/utils/badge-styles"
import { formatRelativeTime } from "@/utils/format"
import { isTerminal } from "@/utils/kanban-rules"

function DeliveryTable({ deliveries }: { deliveries: Delivery[] }) {
  const navigate = useNavigate()

  if (deliveries.length === 0) {
    return <p className="p-4 text-muted-foreground">No deliveries.</p>
  }

  return (
    <Table>
      <TableHeader>
        <TableRow>
          <TableHead className="w-12">#</TableHead>
          <TableHead>Summary</TableHead>
          <TableHead>Phase</TableHead>
          <TableHead>Status</TableHead>
          <TableHead>Repository</TableHead>
          <TableHead>Updated</TableHead>
        </TableRow>
      </TableHeader>
      <TableBody>
        {deliveries.map((d) => (
          <TableRow
            key={d.id}
            className="cursor-pointer"
            onClick={() => navigate(`/deliveries/${d.id}`)}
          >
            <TableCell className="text-muted-foreground">#{d.seq}</TableCell>
            <TableCell className="font-medium">{d.summary}</TableCell>
            <TableCell>
              <Badge variant="secondary" className={PHASE_CLASSES[d.phase]}>
                {d.phase}
              </Badge>
            </TableCell>
            <TableCell>
              <Badge
                variant="secondary"
                className={STATUS_CLASSES[d.run_status]}
              >
                {d.run_status}
              </Badge>
            </TableCell>
            <TableCell className="text-muted-foreground">
              {d.repository}
            </TableCell>
            <TableCell className="text-muted-foreground">
              {formatRelativeTime(d.updated_at)}
            </TableCell>
          </TableRow>
        ))}
      </TableBody>
    </Table>
  )
}

export function DeliveryList() {
  const { deliveries, loading, error } = useDeliveries()

  const { active, closed } = useMemo(() => {
    const active: Delivery[] = []
    const closed: Delivery[] = []
    for (const d of deliveries) {
      if (isTerminal(d.phase, d.run_status)) {
        closed.push(d)
      } else {
        active.push(d)
      }
    }
    return { active, closed }
  }, [deliveries])

  if (loading) {
    return <p className="p-4 text-muted-foreground">Loading...</p>
  }

  if (error) {
    return <p className="p-4 text-destructive">Error: {error}</p>
  }

  if (deliveries.length === 0) {
    return <p className="p-4 text-muted-foreground">No deliveries yet.</p>
  }

  return (
    <Tabs defaultValue="active">
      <TabsList>
        <TabsTrigger value="active">Active ({active.length})</TabsTrigger>
        <TabsTrigger value="closed">Closed ({closed.length})</TabsTrigger>
      </TabsList>
      <TabsContent value="active">
        <DeliveryTable deliveries={active} />
      </TabsContent>
      <TabsContent value="closed">
        <DeliveryTable deliveries={closed} />
      </TabsContent>
    </Tabs>
  )
}
```

**Step 2: Run build to verify**

Run: `cd frontend && npm run build`
Expected: No errors

**Step 3: Commit**

```bash
git add frontend/src/pages/deliveries/list.tsx
git commit -m "feat: delivery list with active/closed tabs and clickable rows"
```

---

### Task 7: Kanban board — Active/Closed tabs

**Files:**
- Modify: `frontend/src/pages/deliveries/board.tsx` — add tabs wrapper
- Modify: `frontend/src/components/kanban/board.tsx` — accept `exclude` prop for hiding close column

**Step 1: Update KanbanBoard to support excluding phases**

In `frontend/src/components/kanban/board.tsx`, change:
```typescript
const CI_PHASES = PHASES.slice(0, 4)
const CD_PHASES = PHASES.slice(4)
```
These become dynamic based on an `excludePhases` prop:

```typescript
import { useMemo } from "react"
import { useNavigate } from "react-router"
import type { Delivery, Phase } from "@/types"
import { PHASES } from "@/utils/kanban-rules"
import { KanbanColumn } from "./column"

interface KanbanBoardProps {
  deliveries: Delivery[]
  excludePhases?: Phase[]
}

export function KanbanBoard({ deliveries, excludePhases = [] }: KanbanBoardProps) {
  const navigate = useNavigate()

  const visiblePhases = useMemo(
    () => PHASES.filter((p) => !excludePhases.includes(p)),
    [excludePhases],
  )

  const ciPhases = visiblePhases.filter((p) =>
    ["intake", "plan", "implement", "review"].includes(p),
  )
  const cdPhases = visiblePhases.filter((p) =>
    ["verify", "deploy", "observe", "close"].includes(p),
  )

  const columns = useMemo(() => {
    const grouped: Record<Phase, Delivery[]> = {} as Record<Phase, Delivery[]>
    for (const phase of PHASES) {
      grouped[phase] = []
    }
    for (const d of deliveries) {
      grouped[d.phase].push(d)
    }
    return grouped
  }, [deliveries])

  const handleCardClick = (d: Delivery) => navigate(`/deliveries/${d.id}`)

  return (
    <div className="space-y-4">
      {ciPhases.length > 0 && (
        <div>
          <h2 className="mb-2 text-xs font-semibold uppercase tracking-wide text-muted-foreground">CI</h2>
          <div className={`grid gap-3`} style={{ gridTemplateColumns: `repeat(${ciPhases.length}, minmax(0, 1fr))` }}>
            {ciPhases.map((phase) => (
              <KanbanColumn
                key={phase}
                phase={phase}
                deliveries={columns[phase]}
                onCardClick={handleCardClick}
              />
            ))}
          </div>
        </div>
      )}
      {cdPhases.length > 0 && (
        <div>
          <h2 className="mb-2 text-xs font-semibold uppercase tracking-wide text-muted-foreground">CD</h2>
          <div className={`grid gap-3`} style={{ gridTemplateColumns: `repeat(${cdPhases.length}, minmax(0, 1fr))` }}>
            {cdPhases.map((phase) => (
              <KanbanColumn
                key={phase}
                phase={phase}
                deliveries={columns[phase]}
                onCardClick={handleCardClick}
              />
            ))}
          </div>
        </div>
      )}
    </div>
  )
}
```

**Step 2: Update DeliveryBoard with tabs**

Replace `frontend/src/pages/deliveries/board.tsx`:

```typescript
import { useMemo } from "react"
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs"
import { useDeliveries } from "@/hooks/use-deliveries"
import { KanbanBoard } from "@/components/kanban/board"
import { isTerminal } from "@/utils/kanban-rules"
import type { Delivery } from "@/types"

export function DeliveryBoard() {
  const { deliveries, loading, error } = useDeliveries()

  const { active, closed } = useMemo(() => {
    const active: Delivery[] = []
    const closed: Delivery[] = []
    for (const d of deliveries) {
      if (isTerminal(d.phase, d.run_status)) {
        closed.push(d)
      } else {
        active.push(d)
      }
    }
    return { active, closed }
  }, [deliveries])

  if (loading) {
    return <p className="p-4 text-muted-foreground">Loading...</p>
  }

  if (error) {
    return <p className="p-4 text-destructive">Error: {error}</p>
  }

  return (
    <Tabs defaultValue="active">
      <TabsList>
        <TabsTrigger value="active">Active ({active.length})</TabsTrigger>
        <TabsTrigger value="closed">Closed ({closed.length})</TabsTrigger>
      </TabsList>
      <TabsContent value="active">
        <KanbanBoard deliveries={active} excludePhases={["close"]} />
      </TabsContent>
      <TabsContent value="closed">
        <KanbanBoard deliveries={closed} />
      </TabsContent>
    </Tabs>
  )
}
```

**Step 3: Run build to verify**

Run: `cd frontend && npm run build`
Expected: No errors

**Step 4: Commit**

```bash
git add frontend/src/pages/deliveries/board.tsx frontend/src/components/kanban/board.tsx
git commit -m "feat: kanban board with active/closed tabs, hide close column in active view"
```

---

### Task 8: Delivery detail — current state metadata row (Issue #9)

**Files:**
- Modify: `frontend/src/pages/deliveries/show.tsx:411-414` — add metadata row below title

**Step 1: Add metadata row**

In `frontend/src/pages/deliveries/show.tsx`, replace:
```tsx
{/* Header */}
<h1 className="text-2xl font-bold">{delivery.summary}</h1>
```
with:
```tsx
{/* Header */}
<div className="space-y-2">
  <h1 className="text-2xl font-bold">{delivery.summary}</h1>
  <div className="flex items-center gap-2 text-sm">
    <Badge variant="secondary" className={PHASE_CLASSES[delivery.phase]}>
      {delivery.phase}
    </Badge>
    <Badge variant="secondary" className={STATUS_CLASSES[delivery.run_status]}>
      {delivery.run_status}
    </Badge>
    <span className="text-muted-foreground">{delivery.repository}</span>
  </div>
</div>
```

**Step 2: Remove duplicate isTerminal from show.tsx**

The `isTerminal` function is defined locally in `show.tsx` (lines 36-41). Replace it with the shared import:

Remove:
```typescript
function isTerminal(phase: Phase, runStatus: RunStatus): boolean {
  return (
    (phase === "close" && runStatus === "succeeded") ||
    runStatus === "canceled"
  )
}
```

Add import:
```typescript
import { ACTION_PHASES, isTerminal } from "@/utils/kanban-rules"
```

And remove the now-unused `ACTION_PHASES` from the existing import (it's already in the new import line).

**Step 3: Run build to verify**

Run: `cd frontend && npm run build`
Expected: No errors

**Step 4: Run all tests**

Run: `cd frontend && npx vitest run`
Expected: All tests pass

**Step 5: Commit**

```bash
git add frontend/src/pages/deliveries/show.tsx
git commit -m "feat: display current phase/status/repo on delivery detail page

Closes #9"
```

---

### Task 9: Final verification

**Step 1: Run full lint**

Run: `cd frontend && npm run lint`
Expected: No errors

**Step 2: Run full test suite**

Run: `cd frontend && npx vitest run`
Expected: All tests pass

**Step 3: Run build**

Run: `cd frontend && npm run build`
Expected: Successful build

**Step 4: Manual smoke test**

Run: `cd frontend && npm run dev -- --host 0.0.0.0`

Verify:
- [ ] Sidebar fills full viewport height
- [ ] Main header matches sidebar header visual level
- [ ] Sources page has no redundant title
- [ ] Source table buttons are compact, rows consistent height
- [ ] Source table shows Checkpoints column with badges
- [ ] Add Source dialog has endpoint Select and checkpoint checkboxes
- [ ] Edit Source dialog has same controls, pre-populated
- [ ] Delivery list has Active/Closed tabs
- [ ] Delivery list rows are clickable (cursor pointer, navigates to detail)
- [ ] Kanban board has Active/Closed tabs
- [ ] Kanban Active tab hides close column
- [ ] Delivery detail shows phase/status badges and repository below title
