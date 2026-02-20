import { useMemo, useState } from "react"
import { useNavigate, useSearchParams } from "react-router"
import { Badge } from "@/components/ui/badge"
import { Button } from "@/components/ui/button"
import { Skeleton } from "@/components/ui/skeleton"
import { RunStatusBadge } from "@/components/run-status-badge"
import { StableText } from "@/components/stable-text"
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
import type { Delivery, Phase, RunStatus } from "@/types"
import { apiPost } from "@/utils/api"
import { PHASE_CLASSES } from "@/utils/badge-styles"
import { formatRelativeTime } from "@/utils/format"
import { ACTION_PHASES, isTerminal } from "@/utils/kanban-rules"

const AGENT_PHASES = new Set<Phase>(["plan", "implement", "review"])

const AGENT_ACTION_LABELS: Record<string, string> = {
  plan: "Generate Plan",
  implement: "Run Implement",
  review: "Run Review",
}
const ACTION_LABEL_CANDIDATES = [...Object.values(AGENT_ACTION_LABELS), "Approve", "Cancel"]
const PHASE_CANDIDATES = Object.keys(PHASE_CLASSES)

type ActionKind = "run-agent" | "approve" | "reject" | "cancel" | null

function getNextAction(phase: Phase, runStatus: RunStatus): ActionKind {
  if (runStatus === "running") return "cancel"
  if (AGENT_PHASES.has(phase) && (runStatus === "pending" || runStatus === "failed")) return "run-agent"
  if (ACTION_PHASES.has(phase) && runStatus === "succeeded") return "approve"
  return null
}

const ACTION_VARIANT: Record<string, "agent" | "approve" | "destructive"> = {
  "run-agent": "agent",
  approve: "approve",
  cancel: "destructive",
}

function ActionCell({
  delivery,
  onAction,
}: {
  delivery: Delivery
  onAction: (d: Delivery, action: ActionKind) => void
}) {
  const action = getNextAction(delivery.phase, delivery.run_status)
  if (!action) return <span className="text-muted-foreground">—</span>

  const variant = ACTION_VARIANT[action]
  const label = action === "run-agent"
    ? (AGENT_ACTION_LABELS[delivery.phase] ?? "Run Agent")
    : action === "approve" ? "Approve" : "Cancel"

  return (
    <div className="flex gap-1.5">
      <Button
        size="sm"
        variant={variant}
        className="h-7 text-xs"
        onClick={(e) => { e.stopPropagation(); onAction(delivery, action) }}
      >
        <StableText candidates={ACTION_LABEL_CANDIDATES}>{label}</StableText>
      </Button>
      {action === "approve" && (
        <Button
          size="sm"
          variant="reject"
          className="h-7 text-xs"
          onClick={(e) => { e.stopPropagation(); onAction(delivery, "reject") }}
        >
          Reject
        </Button>
      )}
    </div>
  )
}

function DeliveryTable({
  deliveries,
  onAction,
}: {
  deliveries: Delivery[]
  onAction: (d: Delivery, action: ActionKind) => void
}) {
  const navigate = useNavigate()

  if (deliveries.length === 0) {
    return <p className="p-4 text-muted-foreground">No deliveries.</p>
  }

  return (
    <Table>
      <TableHeader>
        <TableRow>
          <TableHead className="w-12">#</TableHead>
          <TableHead>Source</TableHead>
          <TableHead>Summary</TableHead>
          <TableHead>Phase</TableHead>
          <TableHead>Status</TableHead>
          <TableHead>Action</TableHead>
          <TableHead>Updated</TableHead>
        </TableRow>
      </TableHeader>
      <TableBody>
        {deliveries.map((d) => (
          <TableRow
            key={d.id}
            className="cursor-pointer"
            onClick={() => navigate(
              d.run_status === "running"
                ? `/deliveries/${d.id}?tab=agents-log`
                : `/deliveries/${d.id}`
            )}
          >
            <TableCell className="text-muted-foreground">#{d.seq}</TableCell>
            <TableCell>
              <span
                className="text-sm text-primary underline-offset-4 hover:underline cursor-pointer"
                onClick={(e) => { e.stopPropagation(); navigate("/sources") }}
              >
                {d.repository}
              </span>
            </TableCell>
            <TableCell className="font-medium">{d.summary}</TableCell>
            <TableCell>
              <Badge variant="colorized" className={PHASE_CLASSES[d.phase]}>
                <StableText candidates={PHASE_CANDIDATES}>{d.phase}</StableText>
              </Badge>
            </TableCell>
            <TableCell>
              <RunStatusBadge status={d.run_status} />
            </TableCell>
            <TableCell>
              <ActionCell delivery={d} onAction={onAction} />
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
  const [searchParams] = useSearchParams()
  const defaultTab = searchParams.get("tab") === "closed" ? "closed" : "active"
  const { deliveries, loading, error, refresh, updateOne } = useDeliveries()
  const [syncing, setSyncing] = useState(false)

  async function handleSync() {
    setSyncing(true)
    try {
      await apiPost("/sources/sync")
      await refresh()
    } finally {
      setSyncing(false)
    }
  }

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

  async function handleAction(d: Delivery, action: ActionKind) {
    if (!action) return
    try {
      switch (action) {
        case "run-agent":
          if (d.run_status === "failed") await apiPost(`/deliveries/${d.id}/retry`)
          updateOne(d.id, { run_status: "running" })
          if (d.phase === "plan") await apiPost(`/deliveries/${d.id}/generate-plan`)
          else if (d.phase === "implement") await apiPost(`/deliveries/${d.id}/run-implement`)
          else if (d.phase === "review") await apiPost(`/deliveries/${d.id}/run-review`)
          break
        case "approve":
          await apiPost(`/deliveries/${d.id}/approve`)
          break
        case "reject":
          await apiPost(`/deliveries/${d.id}/reject`)
          break
        case "cancel":
          await apiPost(`/deliveries/${d.id}/cancel`)
          break
      }
    } finally {
      await refresh()
    }
  }

  if (loading) {
    return (
      <div className="space-y-3 p-4">
        {Array.from({ length: 5 }).map((_, i) => (
          <Skeleton key={i} className="h-10 w-full" />
        ))}
      </div>
    )
  }

  if (error) {
    return <p className="p-4 text-destructive">Error: {error}</p>
  }

  return (
    <Tabs defaultValue={defaultTab}>
      <div className="flex items-center justify-between">
        <TabsList>
          <TabsTrigger value="active">Active ({active.length})</TabsTrigger>
          <TabsTrigger value="closed">Closed ({closed.length})</TabsTrigger>
        </TabsList>
        <Button
          size="sm"
          variant="outline"
          disabled={syncing}
          onClick={handleSync}
        >
          <StableText candidates={["Sync", "Syncing..."]}>
            {syncing ? "Syncing..." : "Sync"}
          </StableText>
        </Button>
      </div>
      <TabsContent value="active">
        <DeliveryTable deliveries={active} onAction={handleAction} />
      </TabsContent>
      <TabsContent value="closed">
        <DeliveryTable deliveries={closed} onAction={handleAction} />
      </TabsContent>
    </Tabs>
  )
}
