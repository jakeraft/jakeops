import { useEffect, useMemo, useRef, useState } from "react"
import { useParams, useSearchParams } from "react-router"
import { Alert, AlertDescription, AlertTitle } from "@/components/ui/alert"
import { Badge } from "@/components/ui/badge"
import { Button } from "@/components/ui/button"
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card"
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
import { Skeleton } from "@/components/ui/skeleton"
import { RunStatusBadge } from "@/components/run-status-badge"
import { StableText } from "@/components/stable-text"
import { useDelivery } from "@/hooks/use-delivery"
import { useEventStream } from "@/hooks/use-event-stream"
import type { StreamEvent } from "@/hooks/use-event-stream"
import { useStreamLog, type AgentBucket } from "@/hooks/use-stream-log"
import type { AgentRun, Phase, PhaseRun, Ref, RunStatus, TranscriptBlock } from "@/types"
import {
  EXECUTOR_CLASSES,
  PHASE_CLASSES,
  RUN_STATUS_CLASSES,
} from "@/utils/badge-styles"
import { formatDateTime } from "@/utils/format"
import { ACTION_PHASES } from "@/utils/kanban-rules"

// --- Sub-components ---

const AGENT_PHASES = new Set<Phase>(["plan", "implement", "review"])

const AGENT_BUTTON_LABELS: Record<string, string> = {
  plan: "Generate Plan",
  implement: "Run Implement",
  review: "Run Review",
}
const AGENT_LABEL_CANDIDATES = Object.values(AGENT_BUTTON_LABELS)
const PHASE_CANDIDATES = Object.keys(PHASE_CLASSES)
const EXECUTOR_CANDIDATES = Object.keys(EXECUTOR_CLASSES)
const MODE_CANDIDATES = Object.keys(PHASE_CLASSES)
const RUN_STATUS_CANDIDATES = Object.keys(RUN_STATUS_CLASSES)

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
  onReject: () => void
  onCancel: () => void
  onRunAgent: () => void
}) {

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
        <Button variant="agent" onClick={onRunAgent}>
          <StableText candidates={AGENT_LABEL_CANDIDATES}>
            {AGENT_BUTTON_LABELS[phase] ?? "Run Agent"}
          </StableText>
        </Button>
      )}
      {canApproveReject && (
        <>
          <Button variant="approve" onClick={onApprove}>
            Approve
          </Button>
          <Button variant="reject" onClick={onReject}>
            Reject
          </Button>
        </>
      )}
    </div>
  )
}

function ErrorBox({ message }: { message: string }) {
  return (
    <Alert variant="destructive">
      <AlertTitle>Error</AlertTitle>
      <AlertDescription>{message}</AlertDescription>
    </Alert>
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
                      className="text-sm text-primary underline-offset-4 hover:underline"
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

const VISIBLE_RUNS = 10

function PhaseRunRow({ pr }: { pr: PhaseRun }) {
  return (
    <TableRow>
      <TableCell>
        <Badge variant="colorized" className={PHASE_CLASSES[pr.phase]}>
          <StableText candidates={PHASE_CANDIDATES}>{pr.phase}</StableText>
        </Badge>
      </TableCell>
      <TableCell>
        <RunStatusBadge status={pr.run_status} />
      </TableCell>
      <TableCell>
        <Badge variant="colorized" className={EXECUTOR_CLASSES[pr.executor]}>
          <StableText candidates={EXECUTOR_CANDIDATES}>{pr.executor}</StableText>
        </Badge>
      </TableCell>
      <TableCell className="text-muted-foreground">
        {pr.started_at ? formatDateTime(pr.started_at) : "-"}
      </TableCell>
    </TableRow>
  )
}

function PhaseRunsTable({ phaseRuns }: { phaseRuns: PhaseRun[] }) {
  const [expanded, setExpanded] = useState(false)

  if (phaseRuns.length === 0) return null

  const hasOlder = phaseRuns.length > VISIBLE_RUNS
  const olderRuns = hasOlder ? phaseRuns.slice(0, -VISIBLE_RUNS) : []
  const recentRuns = hasOlder ? phaseRuns.slice(-VISIBLE_RUNS) : phaseRuns

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
            {hasOlder && !expanded && (
              <TableRow>
                <TableCell colSpan={4} className="p-0">
                  <Button
                    variant="ghost"
                    size="sm"
                    className="w-full text-muted-foreground text-xs"
                    onClick={() => setExpanded(true)}
                  >
                    Show {olderRuns.length} older runs
                  </Button>
                </TableCell>
              </TableRow>
            )}
            {hasOlder && expanded && (
              <>
                <TableRow>
                  <TableCell colSpan={4} className="p-0">
                    <Button
                      variant="ghost"
                      size="sm"
                      className="w-full text-muted-foreground text-xs"
                      onClick={() => setExpanded(false)}
                    >
                      Hide older runs
                    </Button>
                  </TableCell>
                </TableRow>
                {olderRuns.map((pr, i) => (
                  <PhaseRunRow key={i} pr={pr} />
                ))}
              </>
            )}
            {recentRuns.map((pr, i) => (
              <PhaseRunRow key={hasOlder ? olderRuns.length + i : i} pr={pr} />
            ))}
          </TableBody>
        </Table>
      </CardContent>
    </Card>
  )
}

function AgentRunsSection({
  runs,
  liveMeta,
}: {
  runs: AgentRun[]
  liveMeta?: LiveMeta | null
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
            {runs.map((run) => {
              const isRunning = run.status === "running"
              const model = (isRunning && liveMeta?.model) ? liveMeta.model : run.session.model
              return (
                <TableRow key={run.id}>
                  <TableCell>
                    <Badge
                      variant="colorized"
                      className={PHASE_CLASSES[run.mode]}
                    >
                      <StableText candidates={MODE_CANDIDATES}>{run.mode}</StableText>
                    </Badge>
                  </TableCell>
                  <TableCell>
                    <Badge
                      variant="colorized"
                      className={RUN_STATUS_CLASSES[run.status]}
                    >
                      <StableText candidates={RUN_STATUS_CANDIDATES}>{run.status}</StableText>
                    </Badge>
                  </TableCell>
                  <TableCell className="text-sm">
                    {model}
                  </TableCell>
                  <TableCell className="text-sm">
                    {isRunning ? <span className="text-muted-foreground italic">-</span> : `$${run.stats.cost_usd.toFixed(2)}`}
                  </TableCell>
                  <TableCell className="text-sm">
                    {isRunning ? <span className="text-muted-foreground italic">-</span> : (
                      <>{run.stats.input_tokens.toLocaleString()} in / {run.stats.output_tokens.toLocaleString()} out</>
                    )}
                  </TableCell>
                  <TableCell className="text-sm">
                    {isRunning ? <span className="text-muted-foreground italic">streaming...</span> : `${(run.stats.duration_ms / 1000).toFixed(1)}s`}
                  </TableCell>
                  <TableCell className="text-sm text-muted-foreground max-w-xs truncate">
                    {run.summary ?? "-"}
                  </TableCell>
                </TableRow>
              )
            })}
          </TableBody>
        </Table>
      </CardContent>
    </Card>
  )
}

// --- Transcript helpers ---

function filterEventsByAgent(events: StreamEvent[], agentId: string): StreamEvent[] {
  if (agentId === "all") return events
  if (agentId === "leader") return events.filter(e => !e.parent_tool_use_id)
  return events.filter(e => e.parent_tool_use_id === agentId)
}

interface AssistantTurn {
  blocks: TranscriptBlock[]
}

function extractTurns(events: StreamEvent[]): AssistantTurn[] {
  const turns: AssistantTurn[] = []
  for (const event of events) {
    if (event.type !== "assistant") continue
    const rawContent = event.message?.content
    if (!Array.isArray(rawContent)) continue
    const blocks: TranscriptBlock[] = []
    for (const block of rawContent as TranscriptBlock[]) {
      if (block.type === "text" || block.type === "thinking" || block.type === "tool_use") {
        blocks.push(block)
      }
    }
    if (blocks.length > 0) {
      turns.push({ blocks })
    }
  }
  return turns
}

// --- Transcript sub-components ---

const MAX_VISIBLE_BADGES = 5

function BadgeList({ items }: { items: string[] }) {
  const visible = items.slice(0, MAX_VISIBLE_BADGES)
  const remaining = items.length - MAX_VISIBLE_BADGES
  return (
    <div className="flex flex-wrap items-center gap-1">
      {visible.map((item) => (
        <Badge key={item} variant="secondary" className="text-[10px] px-1.5 py-0">
          {item}
        </Badge>
      ))}
      {remaining > 0 && (
        <span className="text-xs text-muted-foreground">+{remaining} more</span>
      )}
    </div>
  )
}

function PromptBlock({ prompt }: { prompt: string }) {
  return (
    <div className="border-l-2 border-green-300 pl-3 mb-3">
      <span className="text-xs font-medium text-muted-foreground uppercase mb-1 block">
        Prompt
      </span>
      <div className="whitespace-pre-wrap break-words text-sm">{prompt}</div>
    </div>
  )
}

const TOOL_DISPLAY_KEYS: Record<string, string[]> = {
  Bash: ["command"],
  Read: ["file_path"],
  Glob: ["pattern"],
  Grep: ["pattern"],
  Skill: ["skill"],
  Task: ["description", "subagent_type"],
  Edit: ["file_path"],
  Write: ["file_path"],
}

function ToolUseRenderer({ block }: { block: TranscriptBlock }) {
  const name = block.name ?? "Tool"
  const input = block.input ?? {}
  const keys = TOOL_DISPLAY_KEYS[name] ?? Object.keys(input).slice(0, 2)
  const args = keys
    .map((k) => input[k])
    .filter((v) => v != null)
    .map((v) => (typeof v === "string" ? v : JSON.stringify(v)))
    .join(", ")

  return (
    <div className="border-l-2 border-slate-300 pl-3">
      <span className="font-mono text-xs text-muted-foreground truncate block">
        {name}({args})
      </span>
    </div>
  )
}

function BlockRenderer({ block }: { block: TranscriptBlock }) {
  if (block.type === "thinking" && block.thinking) {
    return (
      <div className="border-l-2 border-amber-300 pl-3">
        <span className="text-xs font-medium text-muted-foreground uppercase mb-1 block">
          Thinking
        </span>
        <div className="whitespace-pre-wrap break-words text-sm">{block.thinking}</div>
      </div>
    )
  }
  if (block.type === "text" && block.text) {
    return (
      <div className="border-l-2 border-blue-300 pl-3">
        <span className="text-xs font-medium text-muted-foreground uppercase mb-1 block">
          Response
        </span>
        <div className="whitespace-pre-wrap break-words text-sm">{block.text}</div>
      </div>
    )
  }
  if (block.type === "tool_use") {
    return <ToolUseRenderer block={block} />
  }
  return null
}

function RunOverview({ run, liveMeta }: { run: AgentRun; liveMeta?: LiveMeta | null }) {
  const isLive = run.status === "running"
  const model = isLive ? liveMeta?.model : run.session.model
  const usedSkills = liveMeta?.used_skills ?? run.used_skills ?? []
  const plugins = run.plugins ?? []
  const agents = run.agents ?? []

  if (isLive && !model) return null

  const rows: { label: string; value: React.ReactNode }[] = []

  if (model) rows.push({ label: "Model", value: model })

  if (!isLive) {
    rows.push({ label: "Cost", value: `$${run.stats.cost_usd.toFixed(2)}` })
    rows.push({
      label: "Tokens",
      value: `${run.stats.input_tokens.toLocaleString()} in / ${run.stats.output_tokens.toLocaleString()} out`,
    })
    rows.push({ label: "Duration", value: `${(run.stats.duration_ms / 1000).toFixed(1)}s` })
  }

  if (usedSkills.length > 0) rows.push({ label: "Skills", value: <BadgeList items={usedSkills} /> })
  if (plugins.length > 0) rows.push({ label: "Plugins", value: <BadgeList items={plugins} /> })
  if (agents.length > 0) rows.push({ label: "Agents", value: <BadgeList items={agents} /> })

  if (isLive) rows.push({ label: "Status", value: <span className="italic">streaming...</span> })

  if (rows.length === 0) return null

  return (
    <Table className="mb-3">
      <TableBody>
        {rows.map((row) => (
          <TableRow key={row.label} className="border-0">
            <TableCell className="py-1 pl-0 pr-4 w-20 text-xs text-muted-foreground font-medium">
              {row.label}
            </TableCell>
            <TableCell className="py-1 px-0 text-xs">{row.value}</TableCell>
          </TableRow>
        ))}
      </TableBody>
    </Table>
  )
}

function TranscriptView({
  events,
  selectedRun,
  liveMeta,
  bottomRef,
}: {
  events: StreamEvent[]
  selectedRun?: AgentRun
  liveMeta?: LiveMeta | null
  bottomRef?: React.RefObject<HTMLDivElement | null>
}) {
  const turns = useMemo(() => extractTurns(events), [events])

  return (
    <div className="space-y-3 overflow-hidden">
      {selectedRun && <RunOverview run={selectedRun} liveMeta={liveMeta} />}
      {selectedRun?.prompt && <PromptBlock prompt={selectedRun.prompt} />}
      {turns.length > 0 ? (
        <div>
          {turns.map((turn, ti) => (
            <div key={ti}>
              {ti > 0 && <div className="border-t border-dashed border-border my-4" />}
              <div className="space-y-2">
                {turn.blocks.map((block, bi) => (
                  <BlockRenderer key={bi} block={block} />
                ))}
              </div>
            </div>
          ))}
          {bottomRef && <div ref={bottomRef} />}
        </div>
      ) : (
        <p className="text-sm text-muted-foreground">No messages to display.</p>
      )}
    </div>
  )
}

// --- Live meta from backend SSE "meta" events ---

interface LiveMeta {
  model: string | null
  agent_buckets: AgentBucket[]
  used_skills: string[]
}

function extractLiveMeta(events: StreamEvent[]): LiveMeta {
  let model: string | null = null
  let buckets: AgentBucket[] = []
  let usedSkills: string[] = []
  for (const ev of events) {
    if (ev.type === "meta" && ev.message) {
      if (ev.message.model) model = ev.message.model as string
      if (Array.isArray(ev.message.agent_buckets)) {
        buckets = ev.message.agent_buckets as AgentBucket[]
      }
      if (Array.isArray(ev.message.used_skills)) {
        usedSkills = ev.message.used_skills as string[]
      }
    }
  }
  return { model, agent_buckets: buckets, used_skills: usedSkills }
}

// --- Agents Log tab ---

function AgentsLogTab({ deliveryId, runs, runStatus, liveEvents, liveDone, liveMeta }: {
  deliveryId: string
  runs: AgentRun[]
  runStatus: RunStatus
  liveEvents: StreamEvent[]
  liveDone: boolean
  liveMeta: LiveMeta
}) {
  const latestRunId = runs.length > 0 ? runs[runs.length - 1].id : null
  const [userSelectedRunId, setUserSelectedRunId] = useState<string | null>(latestRunId)
  const [agentFilter, setAgentFilter] = useState("all")

  const selectedRunId = runStatus === "running" ? latestRunId : (userSelectedRunId ?? latestRunId)
  const selectedRun = runs.find(r => r.id === selectedRunId)
  const isLive = runStatus === "running"

  const bottomRef = useRef<HTMLDivElement>(null)

  useEffect(() => {
    if (isLive) bottomRef.current?.scrollIntoView({ behavior: "smooth" })
  }, [isLive, liveEvents.length])

  // Completed: stream_log from backend
  const { log, loading: logLoading } = useStreamLog(
    deliveryId,
    isLive ? null : selectedRunId,
  )

  // Unified events & agent buckets (backend SSOT for both live and completed)
  const rawEvents = useMemo(
    () => isLive ? liveEvents : (log?.events ?? []),
    [isLive, liveEvents, log?.events],
  )
  const agentBuckets = isLive ? liveMeta.agent_buckets : (log?.agent_buckets ?? [])
  const filteredEvents = useMemo(
    () => filterEventsByAgent(rawEvents, agentFilter),
    [rawEvents, agentFilter],
  )

  if (runs.length === 0) {
    return <p className="text-sm text-muted-foreground">No agent runs yet.</p>
  }

  const runSelector = (
    <Select value={selectedRunId ?? ""} onValueChange={setUserSelectedRunId}>
      <SelectTrigger className="h-7 w-auto gap-1.5 text-xs">
        <SelectValue />
      </SelectTrigger>
      <SelectContent position="popper" sideOffset={4}>
        {runs.map((run) => (
          <SelectItem key={run.id} value={run.id}>
            <span className="flex items-center gap-1.5">
              <Badge variant="colorized" className={`${PHASE_CLASSES[run.mode]} text-[10px] px-1.5 py-0`}><StableText candidates={MODE_CANDIDATES}>{run.mode}</StableText></Badge>
              <Badge variant="colorized" className={`${RUN_STATUS_CLASSES[run.status]} text-[10px] px-1.5 py-0`}><StableText candidates={RUN_STATUS_CANDIDATES}>{run.status}</StableText></Badge>
              <span className="text-muted-foreground">{run.session.model}</span>
            </span>
          </SelectItem>
        ))}
      </SelectContent>
    </Select>
  )

  const agentSelector = agentBuckets.length > 1 ? (
    <Select value={agentFilter} onValueChange={setAgentFilter}>
      <SelectTrigger className="h-7 w-auto gap-1.5 text-xs">
        <SelectValue />
      </SelectTrigger>
      <SelectContent position="popper" sideOffset={4}>
        <SelectItem value="all">All agents</SelectItem>
        {agentBuckets.map((b) => (
          <SelectItem key={b.id} value={b.id}>
            {b.label}
          </SelectItem>
        ))}
      </SelectContent>
    </Select>
  ) : null

  // Content: live, loading, completed, or empty
  let content: React.ReactNode
  if (isLive) {
    if (liveEvents.length === 0 && !liveDone) {
      content = null
    } else if (liveEvents.length === 0 && liveDone) {
      content = <p className="text-sm text-muted-foreground">No events received.</p>
    } else {
      content = <TranscriptView events={filteredEvents} selectedRun={selectedRun} liveMeta={liveMeta} bottomRef={bottomRef} />
    }
  } else if (logLoading) {
    content = <p className="text-sm text-muted-foreground">Loading log...</p>
  } else if (log) {
    content = <TranscriptView events={filteredEvents} selectedRun={selectedRun} />
  } else {
    content = <p className="text-sm text-muted-foreground">No log available for this run.</p>
  }

  return (
    <Card>
      <CardHeader>
        <div className="flex items-center gap-3">
          <CardTitle className="text-base">Run Log</CardTitle>
          {runSelector}
          {agentSelector}
        </div>
      </CardHeader>
      <CardContent>{content}</CardContent>
    </Card>
  )
}

// --- Main page ---

export function DeliveryShow() {
  const { id } = useParams<{ id: string }>()
  const [searchParams] = useSearchParams()
  const defaultTab = searchParams.get("tab") === "agents-log" ? "agents-log" : "overview"
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

  // Page-level SSE subscription (shared by Overview + Agents Log tabs)
  const isLive = delivery?.run_status === "running"
  const { events: liveEvents, done: liveDone } = useEventStream(id!, isLive ?? false)
  const liveMeta = useMemo(() => extractLiveMeta(liveEvents), [liveEvents])

  if (!id) {
    return <p className="p-4 text-muted-foreground">Invalid delivery ID.</p>
  }

  if (loading) {
    return (
      <div className="space-y-6 p-4">
        <Skeleton className="h-8 w-2/3" />
        <div className="flex gap-2">
          <Skeleton className="h-5 w-20 rounded-full" />
          <Skeleton className="h-5 w-20 rounded-full" />
        </div>
        <Skeleton className="h-40 w-full" />
      </div>
    )
  }

  if (error) {
    return (
      <div className="p-4">
        <Alert variant="destructive">
          <AlertTitle>Error</AlertTitle>
          <AlertDescription>{error}</AlertDescription>
        </Alert>
      </div>
    )
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
          <Badge variant="colorized" className={PHASE_CLASSES[delivery.phase]}>
            <StableText candidates={PHASE_CANDIDATES}>{delivery.phase}</StableText>
          </Badge>
          <RunStatusBadge status={delivery.run_status} />
        </div>
      </div>

      {/* Action Error */}
      {actionError && (
        <Alert variant="destructive">
          <AlertDescription className="flex items-center justify-between">
            <span>{actionError}</span>
            <Button variant="ghost" size="sm" onClick={clearActionError} className="h-auto p-1">
              Dismiss
            </Button>
          </AlertDescription>
        </Alert>
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

      <Tabs defaultValue={defaultTab}>
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
          <AgentRunsSection runs={delivery.runs} liveMeta={isLive ? liveMeta : null} />
        </TabsContent>

        <TabsContent value="agents-log" className="mt-4">
          <AgentsLogTab
            deliveryId={delivery.id}
            runs={delivery.runs}
            runStatus={delivery.run_status}
            liveEvents={liveEvents}
            liveDone={liveDone}
            liveMeta={liveMeta}
          />
        </TabsContent>
      </Tabs>
    </div>
  )
}
