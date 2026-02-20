import { useState } from "react"
import { Link, useParams } from "react-router"
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
import { Separator } from "@/components/ui/separator"
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table"
import { useDelivery } from "@/hooks/use-delivery"
import type { AgentRun, Phase, PhaseRun, Ref, RunStatus } from "@/types"
import {
  EXECUTOR_CLASSES,
  MODE_CLASSES,
  PHASE_CLASSES,
  RUN_STATUS_CLASSES,
  STATUS_CLASSES,
} from "@/utils/badge-styles"
import { formatDateTime } from "@/utils/format"
import { ACTION_PHASES } from "@/utils/kanban-rules"

function isTerminal(phase: Phase, runStatus: RunStatus): boolean {
  return (
    (phase === "close" && runStatus === "succeeded") ||
    runStatus === "canceled"
  )
}

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

function ActionButtons({
  phase,
  runStatus,
  onApprove,
  onReject,
  onRetry,
  onCancel,
  onGeneratePlan,
}: {
  phase: Phase
  runStatus: RunStatus
  onApprove: () => void
  onReject: (reason: string) => void
  onRetry: () => void
  onCancel: () => void
  onGeneratePlan: () => void
}) {
  const [rejectOpen, setRejectOpen] = useState(false)
  const terminal = isTerminal(phase, runStatus)
  const isActionPhase = ACTION_PHASES.has(phase)

  return (
    <div className="flex gap-2 flex-wrap">
      {isActionPhase && runStatus === "succeeded" && (
        <>
          <Button onClick={onApprove}>Approve</Button>
          <Button variant="outline" onClick={() => setRejectOpen(true)}>
            Reject
          </Button>
          <RejectDialog
            open={rejectOpen}
            onOpenChange={setRejectOpen}
            onConfirm={onReject}
          />
        </>
      )}

      {runStatus === "failed" && (
        <Button variant="outline" onClick={onRetry}>
          Retry
        </Button>
      )}

      {phase === "intake" && (
        <Button variant="outline" onClick={onGeneratePlan}>
          Generate Plan
        </Button>
      )}

      {!terminal && (
        <Button variant="destructive" onClick={onCancel}>
          Cancel
        </Button>
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
    <div className="space-y-2">
      <h2 className="text-lg font-semibold">References</h2>
      <div className="flex flex-wrap gap-2">
        {refs.map((ref, i) => (
          <div key={i} className="flex items-center gap-1.5">
            <Badge variant="outline" className="text-xs">
              {ref.role}
            </Badge>
            <Badge variant="secondary" className="text-xs">
              {ref.type}
            </Badge>
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
          </div>
        ))}
      </div>
    </div>
  )
}

function PlanSection({
  plan,
}: {
  plan: { content: string; generated_at: string; model: string }
}) {
  return (
    <Card>
      <CardHeader>
        <CardTitle>Plan</CardTitle>
      </CardHeader>
      <CardContent className="space-y-2">
        <div className="flex gap-4 text-xs text-muted-foreground">
          <span>Model: {plan.model}</span>
          <span>Generated: {formatDateTime(plan.generated_at)}</span>
        </div>
        <pre className="whitespace-pre-wrap rounded-md bg-muted p-4 text-sm">
          {plan.content}
        </pre>
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
                  <Badge
                    variant="secondary"
                    className={STATUS_CLASSES[pr.run_status]}
                  >
                    {pr.run_status}
                  </Badge>
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
  deliveryId,
  runs,
}: {
  deliveryId: string
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
              <TableHead></TableHead>
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
                <TableCell>
                  <Link
                    to={`/deliveries/${deliveryId}/runs/${run.id}/transcript`}
                    className="text-sm text-blue-600 underline-offset-4 hover:underline whitespace-nowrap"
                  >
                    View Transcript
                  </Link>
                </TableCell>
              </TableRow>
            ))}
          </TableBody>
        </Table>
      </CardContent>
    </Card>
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
    retry,
    cancel,
    generatePlan,
  } = useDelivery(id)

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
        <div className="flex items-center gap-3">
          <Badge variant="secondary" className={PHASE_CLASSES[delivery.phase]}>
            {delivery.phase}
          </Badge>
          <Badge
            variant="secondary"
            className={STATUS_CLASSES[delivery.run_status]}
          >
            {delivery.run_status}
          </Badge>
          <span className="text-sm text-muted-foreground">
            {delivery.repository}
          </span>
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
        onRetry={retry}
        onCancel={cancel}
        onGeneratePlan={generatePlan}
      />

      <Separator />

      {/* Error */}
      {delivery.error && <ErrorBox message={delivery.error} />}

      {/* Refs */}
      <RefsList refs={delivery.refs} />

      {/* Plan */}
      {delivery.plan && <PlanSection plan={delivery.plan} />}

      {/* Phase Runs History */}
      <PhaseRunsTable phaseRuns={delivery.phase_runs} />

      {/* Agent Runs */}
      <AgentRunsSection deliveryId={delivery.id} runs={delivery.runs} />
    </div>
  )
}
