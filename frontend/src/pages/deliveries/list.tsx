import { useMemo, useState } from "react"
import { useNavigate, useSearchParams } from "react-router"
import { Badge } from "@/components/ui/badge"
import { Button } from "@/components/ui/button"
import { RunStatusBadge } from "@/components/run-status-badge"
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

type ActionKind = "run-agent" | "approve" | "reject" | "cancel" | null

function getNextAction(phase: Phase, runStatus: RunStatus): ActionKind {
  if (runStatus === "running") return "cancel"
  if (AGENT_PHASES.has(phase) && (runStatus === "pending" || runStatus === "failed")) return "run-agent"
  if (ACTION_PHASES.has(phase) && runStatus === "succeeded") return "approve"
  return null
}

const ACTION_CONFIG: Record<string, { className: string }> = {
  "run-agent": { className: "bg-violet-600 hover:bg-violet-700 text-white" },
  approve: { className: "bg-blue-600 hover:bg-blue-700 text-white" },
  cancel: { className: "bg-red-600 hover:bg-red-700 text-white" },
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

  const config = ACTION_CONFIG[action]
  const label = action === "run-agent"
    ? (AGENT_ACTION_LABELS[delivery.phase] ?? "Run Agent")
    : action === "approve" ? "Approve" : "Cancel"

  return (
    <div className="flex gap-1.5">
      <Button
        size="sm"
        className={`h-7 text-xs ${config.className}`}
        onClick={(e) => { e.stopPropagation(); onAction(delivery, action) }}
      >
        {label}
      </Button>
      {action === "approve" && (
        <Button
          size="sm"
          variant="outline"
          className="h-7 text-xs border-red-300 text-red-700 hover:bg-red-50"
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
            onClick={() => navigate(`/deliveries/${d.id}`)}
          >
            <TableCell className="text-muted-foreground">#{d.seq}</TableCell>
            <TableCell>
              <span
                className="text-sm text-blue-600 underline-offset-4 hover:underline cursor-pointer"
                onClick={(e) => { e.stopPropagation(); navigate("/sources") }}
              >
                {d.repository}
              </span>
            </TableCell>
            <TableCell className="font-medium">{d.summary}</TableCell>
            <TableCell>
              <Badge variant="secondary" className={PHASE_CLASSES[d.phase]}>
                {d.phase}
              </Badge>
            </TableCell>
            <TableCell>
              <RunStatusBadge status={d.run_status} animate />
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
          await apiPost(`/deliveries/${d.id}/reject`, { reason: "" })
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
    return <p className="p-4 text-muted-foreground">Loading...</p>
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
          {syncing ? "Syncing..." : "Sync"}
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
