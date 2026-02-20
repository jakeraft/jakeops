import { useEffect, useMemo, useRef, useState } from "react"
import { useParams } from "react-router"
import { Badge } from "@/components/ui/badge"
import { Button } from "@/components/ui/button"
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card"
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog"
import { Input } from "@/components/ui/input"
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select"
import { Separator } from "@/components/ui/separator"
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs"
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table"
import { RunStatusBadge } from "@/components/run-status-badge"
import { useDelivery } from "@/hooks/use-delivery"
import { useEventStream } from "@/hooks/use-event-stream"
import type { StreamEvent } from "@/hooks/use-event-stream"
import { useStreamLog } from "@/hooks/use-stream-log"
import { MessageRenderer } from "@/pages/deliveries/transcript"
import type { AgentRun, Phase, PhaseRun, Ref, RunStatus, TranscriptMessage } from "@/types"
import {
  EXECUTOR_CLASSES,
  MODE_CLASSES,
  PHASE_CLASSES,
  RUN_STATUS_CLASSES,
} from "@/utils/badge-styles"
import { formatDateTime } from "@/utils/format"
import { ACTION_PHASES } from "@/utils/kanban-rules"

// --- Sub-components ---

function RejectDialog({
  open,
  onOpenChange,
  onConfirm,
}: {
  open: boolean
  onOpenChange: (open: boolean) => void
  onConfirm: (reason: string) => void
}) {
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

const AGENT_PHASES = new Set<Phase>(["plan", "implement", "review"])

const AGENT_BUTTON_LABELS: Record<string, string> = {
  plan: "Generate Plan",
  implement: "Run Implement",
  review: "Run Review",
}

function ActionButtons({
  phase,
  runStatus,
  onApprove,
  onReject,
  onCancel,
  onRunAgent,
}: {
  phase: Phase
  runStatus: RunStatus
  onApprove: () => void
  onReject: (reason: string) => void
  onCancel: () => void
  onRunAgent: () => void
}) {
  const [rejectOpen, setRejectOpen] = useState(false)

  if (runStatus === "running") {
    return (
      <div className="flex gap-2 flex-wrap">
        <Button variant="destructive" onClick={onCancel}>
          Cancel
        </Button>
      </div>
    )
  }

  const canApproveReject = ACTION_PHASES.has(phase) && runStatus === "succeeded"
  const canRunAgent = AGENT_PHASES.has(phase) && (runStatus === "pending" || runStatus === "failed")

  return (
    <div className="flex gap-2 flex-wrap">
      {canRunAgent && (
        <Button className="bg-violet-600 hover:bg-violet-700" onClick={onRunAgent}>
          {AGENT_BUTTON_LABELS[phase] ?? "Run Agent"}
        </Button>
      )}
      {canApproveReject && (
        <>
          <Button className="bg-blue-600 hover:bg-blue-700" onClick={onApprove}>
            Approve
          </Button>
          <Button variant="outline" className="border-red-300 text-red-700 hover:bg-red-50" onClick={() => setRejectOpen(true)}>
            Reject
          </Button>
          <RejectDialog
            open={rejectOpen}
            onOpenChange={setRejectOpen}
            onConfirm={onReject}
          />
        </>
      )}
    </div>
  )
}

function ErrorBox({ message }: { message: string }) {
  return (
    <div className="rounded-md border border-red-200 bg-red-50 p-4 text-sm text-red-800">
      <p className="font-medium">Error</p>
      <p className="mt-1">{message}</p>
    </div>
  )
}

function RefsList({ refs }: { refs: Ref[] }) {
  if (refs.length === 0) return null

  return (
    <Card>
      <CardHeader>
        <CardTitle>References</CardTitle>
      </CardHeader>
      <CardContent>
        <Table>
          <TableHeader>
            <TableRow>
              <TableHead>Role</TableHead>
              <TableHead>Type</TableHead>
              <TableHead>Label</TableHead>
            </TableRow>
          </TableHeader>
          <TableBody>
            {refs.map((ref, i) => (
              <TableRow key={i}>
                <TableCell>
                  <Badge variant="outline" className="text-xs">
                    {ref.role}
                  </Badge>
                </TableCell>
                <TableCell>
                  <Badge variant="secondary" className="text-xs">
                    {ref.type}
                  </Badge>
                </TableCell>
                <TableCell>
                  {ref.url ? (
                    <a
                      href={ref.url}
                      target="_blank"
                      rel="noopener noreferrer"
                      className="text-sm text-blue-600 underline-offset-4 hover:underline"
                    >
                      {ref.label}
                    </a>
                  ) : (
                    <span className="text-sm">{ref.label}</span>
                  )}
                </TableCell>
              </TableRow>
            ))}
          </TableBody>
        </Table>
      </CardContent>
    </Card>
  )
}

function PhaseRunsTable({ phaseRuns }: { phaseRuns: PhaseRun[] }) {
  if (phaseRuns.length === 0) return null

  return (
    <Card>
      <CardHeader>
        <CardTitle>Phase Runs History</CardTitle>
      </CardHeader>
      <CardContent>
        <Table>
          <TableHeader>
            <TableRow>
              <TableHead>Phase</TableHead>
              <TableHead>Status</TableHead>
              <TableHead>Executor</TableHead>
              <TableHead>Started At</TableHead>
            </TableRow>
          </TableHeader>
          <TableBody>
            {phaseRuns.map((pr, i) => (
              <TableRow key={i}>
                <TableCell>
                  <Badge
                    variant="secondary"
                    className={PHASE_CLASSES[pr.phase]}
                  >
                    {pr.phase}
                  </Badge>
                </TableCell>
                <TableCell>
                  <RunStatusBadge status={pr.run_status} />
                </TableCell>
                <TableCell>
                  <Badge
                    variant="secondary"
                    className={EXECUTOR_CLASSES[pr.executor]}
                  >
                    {pr.executor}
                  </Badge>
                </TableCell>
                <TableCell className="text-muted-foreground">
                  {pr.started_at ? formatDateTime(pr.started_at) : "-"}
                </TableCell>
              </TableRow>
            ))}
          </TableBody>
        </Table>
      </CardContent>
    </Card>
  )
}

function AgentRunsSection({
  runs,
}: {
  runs: AgentRun[]
}) {
  if (runs.length === 0) return null

  return (
    <Card>
      <CardHeader>
        <CardTitle>Agent Runs</CardTitle>
      </CardHeader>
      <CardContent>
        <Table>
          <TableHeader>
            <TableRow>
              <TableHead>Mode</TableHead>
              <TableHead>Status</TableHead>
              <TableHead>Model</TableHead>
              <TableHead>Cost</TableHead>
              <TableHead>Tokens</TableHead>
              <TableHead>Duration</TableHead>
              <TableHead>Summary</TableHead>
            </TableRow>
          </TableHeader>
          <TableBody>
            {runs.map((run) => (
              <TableRow key={run.id}>
                <TableCell>
                  <Badge
                    variant="secondary"
                    className={MODE_CLASSES[run.mode]}
                  >
                    {run.mode}
                  </Badge>
                </TableCell>
                <TableCell>
                  <Badge
                    variant="secondary"
                    className={RUN_STATUS_CLASSES[run.status]}
                  >
                    {run.status}
                  </Badge>
                </TableCell>
                <TableCell className="text-sm">
                  {run.session.model}
                </TableCell>
                <TableCell className="text-sm">
                  ${run.stats.cost_usd.toFixed(2)}
                </TableCell>
                <TableCell className="text-sm">
                  {run.stats.input_tokens.toLocaleString()} in /{" "}
                  {run.stats.output_tokens.toLocaleString()} out
                </TableCell>
                <TableCell className="text-sm">
                  {(run.stats.duration_ms / 1000).toFixed(1)}s
                </TableCell>
                <TableCell className="text-sm text-muted-foreground max-w-xs truncate">
                  {run.summary ?? "-"}
                </TableCell>
              </TableRow>
            ))}
          </TableBody>
        </Table>
      </CardContent>
    </Card>
  )
}

// --- Live transcript helpers ---

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
  const messages = useMemo(() => streamEventsToMessages(events), [events])

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: "smooth" })
  }, [messages.length])

  if (events.length === 0 && !done) return null

  if (events.length === 0 && done) {
    return (
      <Card>
        <CardHeader>
          <CardTitle>Live Transcript</CardTitle>
        </CardHeader>
        <CardContent>
          <p className="text-sm text-muted-foreground">No events received.</p>
        </CardContent>
      </Card>
    )
  }

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

// --- Agents Log tab ---

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

// --- Main page ---

export function DeliveryShow() {
  const { id } = useParams<{ id: string }>()
  const {
    delivery,
    loading,
    error,
    actionError,
    clearActionError,
    approve,
    reject,
    cancel,
    runAgent,
  } = useDelivery(id!)

  if (!id) {
    return <p className="p-4 text-muted-foreground">Invalid delivery ID.</p>
  }

  if (loading) {
    return <p className="p-4 text-muted-foreground">Loading...</p>
  }

  if (error) {
    return <p className="p-4 text-destructive">Error: {error}</p>
  }

  if (!delivery) {
    return <p className="p-4 text-muted-foreground">Delivery not found.</p>
  }

  return (
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
          <Button
            variant="ghost"
            size="sm"
            onClick={clearActionError}
            className="h-auto p-1 text-red-800 hover:text-red-900"
          >
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
          <AgentRunsSection runs={delivery.runs} />
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
  )
}
