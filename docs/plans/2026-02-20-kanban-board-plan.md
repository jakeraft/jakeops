# Kanban Board Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Build an interactive Kanban board at `/board` where Deliveries are displayed as draggable cards in phase columns, with drag-and-drop workflow transitions and a detail Sheet.

**Architecture:** New page component at `src/pages/deliveries/board.tsx` with supporting Kanban components under `src/components/kanban/`. Uses `@dnd-kit/core` and `@dnd-kit/sortable` for drag-and-drop. Reuses existing `useDeliveries` and `useDelivery` hooks. A utility module `src/utils/kanban-rules.ts` encapsulates state-machine transition logic.

**Tech Stack:** React 19, TypeScript, dnd-kit, shadcn/ui (Card, Badge, Sheet, Button, Dialog), TailwindCSS, React Router 7, vitest

**Worktree:** `/Users/jake_kakao/workspace/jakeops/.worktrees/feature-kanban-board`

---

### Task 1: Install dnd-kit

**Files:**
- Modify: `frontend/package.json`

**Step 1: Install dnd-kit packages**

Run:
```bash
cd /Users/jake_kakao/workspace/jakeops/.worktrees/feature-kanban-board/frontend && npm install @dnd-kit/core @dnd-kit/sortable @dnd-kit/utilities
```

**Step 2: Verify installation**

Run:
```bash
cd /Users/jake_kakao/workspace/jakeops/.worktrees/feature-kanban-board/frontend && npm run build
```
Expected: Build succeeds

**Step 3: Commit**

```bash
git add frontend/package.json frontend/package-lock.json
git commit -m "chore: install @dnd-kit/core, @dnd-kit/sortable, @dnd-kit/utilities"
```

---

### Task 2: Kanban transition rules utility

**Files:**
- Create: `frontend/src/utils/kanban-rules.ts`
- Create: `frontend/src/utils/__tests__/kanban-rules.test.ts`

This module encapsulates the state-machine logic: which drops are valid, what API action to call.

**Step 1: Write the failing tests**

Create `frontend/src/utils/__tests__/kanban-rules.test.ts`:

```typescript
import { describe, it, expect } from "vitest"
import { getDropAction, PHASES } from "../kanban-rules"
import type { Phase, RunStatus } from "@/types"

describe("PHASES", () => {
  it("lists all 8 phases in order", () => {
    expect(PHASES).toEqual([
      "intake", "plan", "implement", "review",
      "verify", "deploy", "observe", "close",
    ])
  })
})

describe("getDropAction", () => {
  it("returns approve when moving forward from gate phase with succeeded status", () => {
    expect(getDropAction("plan", "succeeded", "implement")).toEqual({
      type: "approve",
    })
  })

  it("returns approve when moving forward from non-gate phase with succeeded status", () => {
    expect(getDropAction("implement", "succeeded", "review")).toEqual({
      type: "approve",
    })
  })

  it("returns reject when moving backward from gate phase with succeeded status", () => {
    expect(getDropAction("review", "succeeded", "implement")).toEqual({
      type: "reject",
    })
  })

  it("returns null when moving backward from non-gate phase", () => {
    expect(getDropAction("implement", "succeeded", "plan")).toBeNull()
  })

  it("returns null when status is not succeeded for forward move", () => {
    expect(getDropAction("plan", "running", "implement")).toBeNull()
  })

  it("returns null when status is not succeeded for backward move", () => {
    expect(getDropAction("review", "running", "implement")).toBeNull()
  })

  it("returns null when skipping phases", () => {
    expect(getDropAction("plan", "succeeded", "review")).toBeNull()
  })

  it("returns null when dropping on same phase", () => {
    expect(getDropAction("plan", "succeeded", "plan")).toBeNull()
  })

  it("returns null when source phase is close", () => {
    expect(getDropAction("close", "succeeded", "observe")).toBeNull()
  })

  it("returns null when status is canceled", () => {
    expect(getDropAction("plan", "canceled", "implement")).toBeNull()
  })

  it("returns approve for intake to plan with succeeded", () => {
    expect(getDropAction("intake", "succeeded", "plan")).toEqual({
      type: "approve",
    })
  })
})
```

**Step 2: Run tests to verify they fail**

Run:
```bash
cd /Users/jake_kakao/workspace/jakeops/.worktrees/feature-kanban-board/frontend && npx vitest run src/utils/__tests__/kanban-rules.test.ts
```
Expected: FAIL - module not found

**Step 3: Write implementation**

Create `frontend/src/utils/kanban-rules.ts`:

```typescript
import type { Phase, RunStatus } from "@/types"

export const PHASES: Phase[] = [
  "intake", "plan", "implement", "review",
  "verify", "deploy", "observe", "close",
]

const GATE_PHASES: Set<Phase> = new Set(["plan", "review", "deploy"])

export type DropAction =
  | { type: "approve" }
  | { type: "reject" }

export function getDropAction(
  fromPhase: Phase,
  runStatus: RunStatus,
  toPhase: Phase,
): DropAction | null {
  if (fromPhase === toPhase) return null
  if (runStatus !== "succeeded") return null
  if (fromPhase === "close") return null

  const fromIndex = PHASES.indexOf(fromPhase)
  const toIndex = PHASES.indexOf(toPhase)
  const diff = toIndex - fromIndex

  // Forward: must be exactly +1
  if (diff === 1) {
    return { type: "approve" }
  }

  // Backward: must be exactly -1 and from a gate phase
  if (diff === -1 && GATE_PHASES.has(fromPhase)) {
    return { type: "reject" }
  }

  return null
}
```

**Step 4: Run tests to verify they pass**

Run:
```bash
cd /Users/jake_kakao/workspace/jakeops/.worktrees/feature-kanban-board/frontend && npx vitest run src/utils/__tests__/kanban-rules.test.ts
```
Expected: All 11 tests PASS

**Step 5: Commit**

```bash
git add frontend/src/utils/kanban-rules.ts frontend/src/utils/__tests__/kanban-rules.test.ts
git commit -m "feat: add kanban transition rules utility with tests"
```

---

### Task 3: KanbanCard component

**Files:**
- Create: `frontend/src/components/kanban/card.tsx`

**Step 1: Create the KanbanCard component**

Create `frontend/src/components/kanban/card.tsx`:

```tsx
import { useSortable } from "@dnd-kit/sortable"
import { CSS } from "@dnd-kit/utilities"
import { Badge } from "@/components/ui/badge"
import type { Delivery } from "@/types"
import { STATUS_CLASSES } from "@/utils/badge-styles"
import { formatRelativeTime } from "@/utils/format"

interface KanbanCardProps {
  delivery: Delivery
  onClick: (delivery: Delivery) => void
}

export function KanbanCard({ delivery, onClick }: KanbanCardProps) {
  const {
    attributes,
    listeners,
    setNodeRef,
    transform,
    transition,
    isDragging,
  } = useSortable({ id: delivery.id, data: { delivery } })

  const style = {
    transform: CSS.Transform.toString(transform),
    transition,
  }

  return (
    <div
      ref={setNodeRef}
      style={style}
      {...attributes}
      {...listeners}
      className={`rounded-lg border bg-card p-3 shadow-sm cursor-grab active:cursor-grabbing space-y-2 ${
        isDragging ? "opacity-50" : ""
      }`}
      onClick={(e) => {
        // Only trigger onClick if not dragging
        if (!isDragging) {
          e.stopPropagation()
          onClick(delivery)
        }
      }}
    >
      <p className="text-sm font-medium line-clamp-2">{delivery.summary}</p>
      <div className="flex items-center justify-between gap-2">
        <Badge variant="secondary" className={`text-xs ${STATUS_CLASSES[delivery.run_status]}`}>
          {delivery.run_status}
        </Badge>
        <span className="text-xs text-muted-foreground truncate">
          {delivery.repository}
        </span>
      </div>
      <p className="text-xs text-muted-foreground">
        {formatRelativeTime(delivery.updated_at)}
      </p>
    </div>
  )
}
```

**Step 2: Verify build**

Run:
```bash
cd /Users/jake_kakao/workspace/jakeops/.worktrees/feature-kanban-board/frontend && npm run build
```
Expected: Build succeeds (dnd-kit must be installed from Task 1)

**Step 3: Commit**

```bash
git add frontend/src/components/kanban/card.tsx
git commit -m "feat: add KanbanCard component with drag support"
```

---

### Task 4: KanbanColumn component

**Files:**
- Create: `frontend/src/components/kanban/column.tsx`

**Step 1: Create the KanbanColumn component**

Create `frontend/src/components/kanban/column.tsx`:

```tsx
import { useDroppable } from "@dnd-kit/core"
import {
  SortableContext,
  verticalListSortingStrategy,
} from "@dnd-kit/sortable"
import { Badge } from "@/components/ui/badge"
import type { Delivery, Phase } from "@/types"
import { PHASE_CLASSES } from "@/utils/badge-styles"
import { KanbanCard } from "./card"

interface KanbanColumnProps {
  phase: Phase
  deliveries: Delivery[]
  onCardClick: (delivery: Delivery) => void
  isDropTarget: boolean
  isInvalidDrop: boolean
}

export function KanbanColumn({
  phase,
  deliveries,
  onCardClick,
  isDropTarget,
  isInvalidDrop,
}: KanbanColumnProps) {
  const { setNodeRef } = useDroppable({ id: phase })

  let borderClass = "border-transparent"
  if (isDropTarget) {
    borderClass = isInvalidDrop
      ? "border-red-400 bg-red-50/50"
      : "border-blue-400 bg-blue-50/50"
  }

  return (
    <div
      ref={setNodeRef}
      className={`flex w-64 shrink-0 flex-col rounded-lg border-2 ${borderClass} transition-colors`}
    >
      <div className="flex items-center justify-between p-3 pb-2">
        <Badge variant="secondary" className={PHASE_CLASSES[phase]}>
          {phase}
        </Badge>
        <span className="text-xs text-muted-foreground">
          {deliveries.length}
        </span>
      </div>
      <div className="flex-1 space-y-2 overflow-y-auto p-2 pt-0">
        <SortableContext
          items={deliveries.map((d) => d.id)}
          strategy={verticalListSortingStrategy}
        >
          {deliveries.map((delivery) => (
            <KanbanCard
              key={delivery.id}
              delivery={delivery}
              onClick={onCardClick}
            />
          ))}
        </SortableContext>
      </div>
    </div>
  )
}
```

**Step 2: Verify build**

Run:
```bash
cd /Users/jake_kakao/workspace/jakeops/.worktrees/feature-kanban-board/frontend && npm run build
```
Expected: Build succeeds

**Step 3: Commit**

```bash
git add frontend/src/components/kanban/column.tsx
git commit -m "feat: add KanbanColumn component with droppable zone"
```

---

### Task 5: DetailSheet component

**Files:**
- Create: `frontend/src/components/kanban/detail-sheet.tsx`

Requires shadcn Sheet component already installed (confirmed from `frontend/src/components/ui/sheet.tsx`).

**Step 1: Create the DetailSheet component**

Create `frontend/src/components/kanban/detail-sheet.tsx`:

```tsx
import { Link } from "react-router"
import { Badge } from "@/components/ui/badge"
import { Button } from "@/components/ui/button"
import { Separator } from "@/components/ui/separator"
import {
  Sheet,
  SheetContent,
  SheetHeader,
  SheetTitle,
} from "@/components/ui/sheet"
import { useDelivery } from "@/hooks/use-delivery"
import { PHASE_CLASSES, STATUS_CLASSES } from "@/utils/badge-styles"
import { formatRelativeTime } from "@/utils/format"
import { RejectDialog } from "./reject-dialog"
import { useState } from "react"
import type { Phase, RunStatus } from "@/types"

const GATE_PHASES: Phase[] = ["plan", "review", "deploy"]

function isTerminal(phase: Phase, runStatus: RunStatus): boolean {
  return (
    (phase === "close" && runStatus === "succeeded") ||
    runStatus === "canceled"
  )
}

interface DetailSheetProps {
  deliveryId: string | null
  onOpenChange: (open: boolean) => void
  onActionComplete: () => void
}

export function DetailSheet({
  deliveryId,
  onOpenChange,
  onActionComplete,
}: DetailSheetProps) {
  const {
    delivery,
    loading,
    approve,
    reject,
    retry,
    cancel,
    generatePlan,
    actionError,
    clearActionError,
  } = useDelivery(deliveryId ?? undefined)
  const [rejectOpen, setRejectOpen] = useState(false)

  async function handleAction(action: () => Promise<unknown>) {
    await action()
    onActionComplete()
  }

  return (
    <Sheet open={!!deliveryId} onOpenChange={onOpenChange}>
      <SheetContent className="overflow-y-auto">
        {loading && (
          <p className="p-4 text-muted-foreground">Loading...</p>
        )}
        {delivery && (
          <>
            <SheetHeader>
              <SheetTitle>{delivery.summary}</SheetTitle>
            </SheetHeader>
            <div className="mt-4 space-y-4">
              <div className="flex items-center gap-2">
                <Badge variant="secondary" className={PHASE_CLASSES[delivery.phase]}>
                  {delivery.phase}
                </Badge>
                <Badge variant="secondary" className={STATUS_CLASSES[delivery.run_status]}>
                  {delivery.run_status}
                </Badge>
              </div>

              <div className="space-y-1 text-sm">
                <p className="text-muted-foreground">{delivery.repository}</p>
                <p className="text-muted-foreground">
                  Updated {formatRelativeTime(delivery.updated_at)}
                </p>
              </div>

              {delivery.refs.length > 0 && (
                <>
                  <Separator />
                  <div className="space-y-1">
                    <p className="text-sm font-medium">References</p>
                    {delivery.refs.map((ref, i) => (
                      <div key={i} className="flex items-center gap-1.5 text-sm">
                        <Badge variant="outline" className="text-xs">{ref.role}</Badge>
                        {ref.url ? (
                          <a
                            href={ref.url}
                            target="_blank"
                            rel="noopener noreferrer"
                            className="text-blue-600 underline-offset-4 hover:underline"
                          >
                            {ref.label}
                          </a>
                        ) : (
                          <span>{ref.label}</span>
                        )}
                      </div>
                    ))}
                  </div>
                </>
              )}

              {actionError && (
                <div className="flex items-center justify-between rounded-md border border-red-200 bg-red-50 p-2 text-sm text-red-800">
                  <span>{actionError}</span>
                  <Button
                    variant="ghost"
                    size="sm"
                    onClick={clearActionError}
                    className="h-auto p-1"
                  >
                    Dismiss
                  </Button>
                </div>
              )}

              <Separator />

              {/* Action Buttons */}
              <div className="flex flex-wrap gap-2">
                {GATE_PHASES.includes(delivery.phase) &&
                  delivery.run_status === "succeeded" && (
                    <>
                      <Button size="sm" onClick={() => handleAction(approve)}>
                        Approve
                      </Button>
                      <Button
                        size="sm"
                        variant="outline"
                        onClick={() => setRejectOpen(true)}
                      >
                        Reject
                      </Button>
                    </>
                  )}
                {delivery.run_status === "failed" && (
                  <Button
                    size="sm"
                    variant="outline"
                    onClick={() => handleAction(retry)}
                  >
                    Retry
                  </Button>
                )}
                {delivery.phase === "intake" && (
                  <Button
                    size="sm"
                    variant="outline"
                    onClick={() => handleAction(generatePlan)}
                  >
                    Generate Plan
                  </Button>
                )}
                {!isTerminal(delivery.phase, delivery.run_status) && (
                  <Button
                    size="sm"
                    variant="destructive"
                    onClick={() => handleAction(cancel)}
                  >
                    Cancel
                  </Button>
                )}
              </div>

              <Separator />

              <Link
                to={`/deliveries/${delivery.id}`}
                className="block text-sm text-blue-600 underline-offset-4 hover:underline"
              >
                View Full Details
              </Link>
            </div>

            <RejectDialog
              open={rejectOpen}
              onOpenChange={setRejectOpen}
              onConfirm={async (reason) => {
                await handleAction(() => reject(reason))
                setRejectOpen(false)
              }}
            />
          </>
        )}
      </SheetContent>
    </Sheet>
  )
}
```

**Step 2: Extract RejectDialog as shared component**

The RejectDialog is duplicated from `show.tsx`. Extract it to `frontend/src/components/kanban/reject-dialog.tsx`:

```tsx
import { useState } from "react"
import { Button } from "@/components/ui/button"
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog"
import { Input } from "@/components/ui/input"

interface RejectDialogProps {
  open: boolean
  onOpenChange: (open: boolean) => void
  onConfirm: (reason: string) => void
}

export function RejectDialog({ open, onOpenChange, onConfirm }: RejectDialogProps) {
  const [reason, setReason] = useState("")

  function handleSubmit() {
    if (reason.trim()) {
      onConfirm(reason.trim())
      handleOpenChange(false)
    }
  }

  function handleOpenChange(nextOpen: boolean) {
    if (!nextOpen) setReason("")
    onOpenChange(nextOpen)
  }

  return (
    <Dialog open={open} onOpenChange={handleOpenChange}>
      <DialogContent>
        <DialogHeader>
          <DialogTitle>Reject Delivery</DialogTitle>
          <DialogDescription>
            Provide a reason for rejecting this delivery.
          </DialogDescription>
        </DialogHeader>
        <Input
          placeholder="Rejection reason..."
          value={reason}
          onChange={(e) => setReason(e.target.value)}
          onKeyDown={(e) => {
            if (e.key === "Enter") handleSubmit()
          }}
        />
        <DialogFooter>
          <Button variant="outline" onClick={() => onOpenChange(false)}>
            Cancel
          </Button>
          <Button onClick={handleSubmit} disabled={!reason.trim()}>
            Reject
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  )
}
```

**Step 3: Verify build**

Run:
```bash
cd /Users/jake_kakao/workspace/jakeops/.worktrees/feature-kanban-board/frontend && npm run build
```
Expected: Build succeeds

**Step 4: Commit**

```bash
git add frontend/src/components/kanban/detail-sheet.tsx frontend/src/components/kanban/reject-dialog.tsx
git commit -m "feat: add DetailSheet and RejectDialog components for kanban"
```

---

### Task 6: KanbanBoard component

**Files:**
- Create: `frontend/src/components/kanban/board.tsx`

This is the main orchestrator: DndContext, columns, drag overlay, drop validation.

**Step 1: Create the KanbanBoard component**

Create `frontend/src/components/kanban/board.tsx`:

```tsx
import { useState, useMemo, useCallback } from "react"
import {
  DndContext,
  DragOverlay,
  DragStartEvent,
  DragOverEvent,
  DragEndEvent,
  PointerSensor,
  useSensor,
  useSensors,
  closestCenter,
} from "@dnd-kit/core"
import { Badge } from "@/components/ui/badge"
import type { Delivery, Phase } from "@/types"
import { STATUS_CLASSES } from "@/utils/badge-styles"
import { formatRelativeTime } from "@/utils/format"
import { PHASES, getDropAction } from "@/utils/kanban-rules"
import { apiPost } from "@/utils/api"
import { KanbanColumn } from "./column"
import { DetailSheet } from "./detail-sheet"
import { RejectDialog } from "./reject-dialog"

interface KanbanBoardProps {
  deliveries: Delivery[]
  onRefresh: () => void
}

export function KanbanBoard({ deliveries, onRefresh }: KanbanBoardProps) {
  const [activeDelivery, setActiveDelivery] = useState<Delivery | null>(null)
  const [overPhase, setOverPhase] = useState<Phase | null>(null)
  const [selectedId, setSelectedId] = useState<string | null>(null)
  const [rejectTarget, setRejectTarget] = useState<Delivery | null>(null)

  const sensors = useSensors(
    useSensor(PointerSensor, { activationConstraint: { distance: 8 } }),
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

  const dropAction = useMemo(() => {
    if (!activeDelivery || !overPhase) return null
    return getDropAction(activeDelivery.phase, activeDelivery.run_status, overPhase)
  }, [activeDelivery, overPhase])

  function handleDragStart(event: DragStartEvent) {
    const delivery = event.active.data.current?.delivery as Delivery | undefined
    if (delivery) setActiveDelivery(delivery)
  }

  function handleDragOver(event: DragOverEvent) {
    const overId = event.over?.id as Phase | undefined
    if (overId && PHASES.includes(overId)) {
      setOverPhase(overId)
    } else {
      setOverPhase(null)
    }
  }

  const handleDragEnd = useCallback(
    async (event: DragEndEvent) => {
      const delivery = activeDelivery
      const targetPhase = event.over?.id as Phase | undefined

      setActiveDelivery(null)
      setOverPhase(null)

      if (!delivery || !targetPhase) return
      if (delivery.phase === targetPhase) return

      const action = getDropAction(delivery.phase, delivery.run_status, targetPhase)
      if (!action) return

      if (action.type === "reject") {
        setRejectTarget(delivery)
        return
      }

      // approve
      await apiPost(`/deliveries/${delivery.id}/approve`)
      onRefresh()
    },
    [activeDelivery, onRefresh],
  )

  async function handleRejectConfirm(reason: string) {
    if (!rejectTarget) return
    await apiPost(`/deliveries/${rejectTarget.id}/reject`, { reason })
    setRejectTarget(null)
    onRefresh()
  }

  return (
    <>
      <DndContext
        sensors={sensors}
        collisionDetection={closestCenter}
        onDragStart={handleDragStart}
        onDragOver={handleDragOver}
        onDragEnd={handleDragEnd}
      >
        <div className="flex gap-3 overflow-x-auto pb-4">
          {PHASES.map((phase) => (
            <KanbanColumn
              key={phase}
              phase={phase}
              deliveries={columns[phase]}
              onCardClick={(d) => setSelectedId(d.id)}
              isDropTarget={overPhase === phase}
              isInvalidDrop={overPhase === phase && !dropAction}
            />
          ))}
        </div>

        <DragOverlay>
          {activeDelivery && (
            <div className="w-64 rounded-lg border bg-card p-3 shadow-lg space-y-2">
              <p className="text-sm font-medium line-clamp-2">
                {activeDelivery.summary}
              </p>
              <div className="flex items-center justify-between gap-2">
                <Badge
                  variant="secondary"
                  className={`text-xs ${STATUS_CLASSES[activeDelivery.run_status]}`}
                >
                  {activeDelivery.run_status}
                </Badge>
                <span className="text-xs text-muted-foreground truncate">
                  {activeDelivery.repository}
                </span>
              </div>
              <p className="text-xs text-muted-foreground">
                {formatRelativeTime(activeDelivery.updated_at)}
              </p>
            </div>
          )}
        </DragOverlay>
      </DndContext>

      <DetailSheet
        deliveryId={selectedId}
        onOpenChange={(open) => {
          if (!open) setSelectedId(null)
        }}
        onActionComplete={onRefresh}
      />

      <RejectDialog
        open={!!rejectTarget}
        onOpenChange={(open) => {
          if (!open) setRejectTarget(null)
        }}
        onConfirm={handleRejectConfirm}
      />
    </>
  )
}
```

**Step 2: Verify build**

Run:
```bash
cd /Users/jake_kakao/workspace/jakeops/.worktrees/feature-kanban-board/frontend && npm run build
```
Expected: Build succeeds

**Step 3: Commit**

```bash
git add frontend/src/components/kanban/board.tsx
git commit -m "feat: add KanbanBoard component with DnD orchestration"
```

---

### Task 7: Board page + routing + sidebar

**Files:**
- Create: `frontend/src/pages/deliveries/board.tsx`
- Modify: `frontend/src/App.tsx`
- Modify: `frontend/src/components/app-sidebar.tsx`

**Step 1: Create the board page**

Create `frontend/src/pages/deliveries/board.tsx`:

```tsx
import { useDeliveries } from "@/hooks/use-deliveries"
import { KanbanBoard } from "@/components/kanban/board"

export function DeliveryBoard() {
  const { deliveries, loading, error, refresh } = useDeliveries()

  if (loading) {
    return <p className="p-4 text-muted-foreground">Loading...</p>
  }

  if (error) {
    return <p className="p-4 text-destructive">Error: {error}</p>
  }

  return <KanbanBoard deliveries={deliveries} onRefresh={refresh} />
}
```

**Step 2: Add route to App.tsx**

In `frontend/src/App.tsx`, add import and route:

```tsx
import { DeliveryBoard } from "./pages/deliveries/board"
```

Add route inside the `<Route element={<AppLayout />}>` block:

```tsx
<Route path="board" element={<DeliveryBoard />} />
```

**Step 3: Add sidebar nav item**

In `frontend/src/components/app-sidebar.tsx`, add `Columns3` to the lucide import:

```tsx
import { Package, GitFork, Activity, Columns3 } from "lucide-react"
```

Add to `NAV_ITEMS` array:

```tsx
{ to: "/board", label: "Board", icon: Columns3 },
```

**Step 4: Verify build**

Run:
```bash
cd /Users/jake_kakao/workspace/jakeops/.worktrees/feature-kanban-board/frontend && npm run build
```
Expected: Build succeeds

**Step 5: Run all existing tests**

Run:
```bash
cd /Users/jake_kakao/workspace/jakeops/.worktrees/feature-kanban-board/frontend && npm run test
```
Expected: All tests pass (existing 31 + new kanban-rules tests)

**Step 6: Run lint**

Run:
```bash
cd /Users/jake_kakao/workspace/jakeops/.worktrees/feature-kanban-board/frontend && npm run lint
```
Expected: No errors

**Step 7: Commit**

```bash
git add frontend/src/pages/deliveries/board.tsx frontend/src/App.tsx frontend/src/components/app-sidebar.tsx
git commit -m "feat: add kanban board page with routing and sidebar entry"
```

---

### Task 8: Final verification

**Step 1: Full build**

Run:
```bash
cd /Users/jake_kakao/workspace/jakeops/.worktrees/feature-kanban-board/frontend && npm run build
```

**Step 2: Full test suite**

Run:
```bash
cd /Users/jake_kakao/workspace/jakeops/.worktrees/feature-kanban-board/frontend && npm run test
```

**Step 3: Lint**

Run:
```bash
cd /Users/jake_kakao/workspace/jakeops/.worktrees/feature-kanban-board/frontend && npm run lint
```

**Step 4: Backend tests (ensure nothing broken)**

Run:
```bash
cd /Users/jake_kakao/workspace/jakeops/.worktrees/feature-kanban-board/backend && python -m pytest -v
```

Expected: All tests pass across frontend and backend.
