import { useState } from "react"
import { Link, useParams } from "react-router"
import { ChevronRight, ChevronDown } from "lucide-react"
import { Badge } from "@/components/ui/badge"
import {
  Collapsible,
  CollapsibleContent,
  CollapsibleTrigger,
} from "@/components/ui/collapsible"
import { useTranscript } from "@/hooks/use-transcript"
import type { TranscriptBlock, TranscriptMessage } from "@/types"

// Maximum characters to display in tool_result content before truncation
const MAX_RESULT_LENGTH = 5000

// --- Content block renderers ---

function TextBlock({ text }: { text: string }) {
  return <div className="whitespace-pre-wrap text-sm">{text}</div>
}

function ThinkingBlock({ thinking }: { thinking: string }) {
  return (
    <Collapsible>
      <div className="bg-muted rounded-lg p-3">
        <CollapsibleTrigger className="flex items-center gap-1.5 text-sm font-medium cursor-pointer [&[data-state=open]>svg.chevron-right]:hidden [&[data-state=closed]>svg.chevron-down]:hidden">
          <ChevronRight className="chevron-right h-4 w-4" />
          <ChevronDown className="chevron-down h-4 w-4" />
          Thinking
        </CollapsibleTrigger>
        <CollapsibleContent>
          <pre className="mt-2 whitespace-pre-wrap text-sm text-muted-foreground">
            {thinking}
          </pre>
        </CollapsibleContent>
      </div>
    </Collapsible>
  )
}

function ToolUseBlock({ name, input }: { name: string; input?: Record<string, unknown> }) {
  return (
    <Collapsible>
      <div className="border rounded-lg p-3">
        <CollapsibleTrigger className="flex items-center gap-1.5 text-sm font-medium cursor-pointer [&[data-state=open]>svg.chevron-right]:hidden [&[data-state=closed]>svg.chevron-down]:hidden">
          <ChevronRight className="chevron-right h-4 w-4" />
          <ChevronDown className="chevron-down h-4 w-4" />
          <Badge variant="outline" className="text-xs">
            {name}
          </Badge>
        </CollapsibleTrigger>
        <CollapsibleContent>
          <pre className="mt-2 whitespace-pre-wrap text-xs bg-muted rounded p-2 overflow-x-auto">
            {JSON.stringify(input, null, 2)}
          </pre>
        </CollapsibleContent>
      </div>
    </Collapsible>
  )
}

function ToolResultBlock({ content }: { content: unknown }) {
  const text = typeof content === "string" ? content : JSON.stringify(content, null, 2)
  const truncated = text.length > MAX_RESULT_LENGTH
    ? text.slice(0, MAX_RESULT_LENGTH) + "\n... (truncated)"
    : text

  return (
    <Collapsible>
      <div className="border rounded-lg p-3">
        <CollapsibleTrigger className="flex items-center gap-1.5 text-sm font-medium cursor-pointer [&[data-state=open]>svg.chevron-right]:hidden [&[data-state=closed]>svg.chevron-down]:hidden">
          <ChevronRight className="chevron-right h-4 w-4" />
          <ChevronDown className="chevron-down h-4 w-4" />
          Result
        </CollapsibleTrigger>
        <CollapsibleContent>
          <pre className="mt-2 whitespace-pre-wrap text-xs bg-muted rounded p-2 overflow-x-auto">
            {truncated}
          </pre>
        </CollapsibleContent>
      </div>
    </Collapsible>
  )
}

function ContentBlockRenderer({ block }: { block: TranscriptBlock }) {
  switch (block.type) {
    case "text":
      return block.text ? <TextBlock text={block.text} /> : null
    case "thinking":
      return block.thinking ? <ThinkingBlock thinking={block.thinking} /> : null
    case "tool_use":
      return block.name ? <ToolUseBlock name={block.name} input={block.input} /> : null
    case "tool_result":
      return block.content != null ? <ToolResultBlock content={block.content} /> : null
    default:
      return (
        <pre className="whitespace-pre-wrap text-xs bg-muted rounded p-2">
          {JSON.stringify(block, null, 2)}
        </pre>
      )
  }
}

// --- Message renderer ---

export function MessageRenderer({ message }: { message: TranscriptMessage }) {
  const { role, content } = message

  if (content == null) return null

  const isAssistant = role === "assistant"
  const borderClass = isAssistant ? "border-l-2 border-violet-300 pl-3" : "border-l-2 border-blue-300 pl-3"

  return (
    <div className={`mb-3 ${borderClass}`}>
      <span className="text-xs font-medium text-muted-foreground uppercase mb-1 block">
        {role}
      </span>
      {typeof content === "string" ? (
        <div className="whitespace-pre-wrap text-sm">{content}</div>
      ) : (
        <div className="space-y-2">
          {content.map((block, i) => (
            <ContentBlockRenderer key={i} block={block} />
          ))}
        </div>
      )}
    </div>
  )
}

// --- Agent panel sidebar ---

function AgentList({
  agents,
  agentKeys,
  selectedAgent,
  onSelect,
}: {
  agents: Record<string, { model: string }>
  agentKeys: string[]
  selectedAgent: string
  onSelect: (key: string) => void
}) {
  return (
    <div className="space-y-1">
      {agentKeys.map((key) => {
        const isSelected = key === selectedAgent
        const isLeader = key === "leader"
        const label = isLeader ? "Leader" : "Subagent"
        const model = agents[key]?.model ?? "unknown"

        return (
          <button
            key={key}
            onClick={() => onSelect(key)}
            className={`w-full text-left px-3 py-2 rounded-md text-sm transition-colors cursor-pointer ${
              isSelected
                ? "bg-accent text-accent-foreground font-medium"
                : "hover:bg-muted"
            }`}
          >
            <div className="font-medium">{label}</div>
            <div className="text-xs text-muted-foreground truncate">{model}</div>
          </button>
        )
      })}
    </div>
  )
}

// --- Main page ---

export function TranscriptViewer() {
  const { id, runId } = useParams<{ id: string; runId: string }>()
  const { transcript, loading, error } = useTranscript(id!, runId!)
  const [selectedAgent, setSelectedAgent] = useState("leader")

  if (loading) {
    return <p className="p-4 text-muted-foreground">Loading transcript...</p>
  }

  if (error) {
    return <p className="p-4 text-destructive">Error: {error}</p>
  }

  if (!transcript) {
    return <p className="p-4 text-muted-foreground">Transcript not found.</p>
  }

  const { meta, ...agentData } = transcript
  const agentKeys = Object.keys(agentData)
  const agents = meta.agents

  // Get messages for the selected agent
  const messages = (agentData[selectedAgent] ?? []) as TranscriptMessage[]
  const selectedModel = agents[selectedAgent]?.model ?? "unknown"

  return (
    <div className="space-y-4">
      {/* Back navigation */}
      <Link
        to={`/deliveries/${id}`}
        className="text-sm text-muted-foreground hover:text-foreground inline-flex items-center gap-1"
      >
        &larr; Back to Delivery
      </Link>

      {/* Top bar metadata */}
      <div className="flex items-center gap-3">
        <h1 className="text-lg font-semibold">Transcript</h1>
        <Badge variant="secondary" className="text-xs">
          {selectedModel}
        </Badge>
      </div>

      {/* Two-panel layout */}
      <div className="flex gap-6">
        {/* Left panel: agent list */}
        <div className="w-64 shrink-0">
          <h2 className="text-sm font-medium text-muted-foreground mb-2">Agents</h2>
          <AgentList
            agents={agents}
            agentKeys={agentKeys}
            selectedAgent={selectedAgent}
            onSelect={setSelectedAgent}
          />
        </div>

        {/* Right panel: messages */}
        <div className="flex-1 min-w-0">
          {messages.length === 0 ? (
            <p className="text-sm text-muted-foreground">No messages for this agent.</p>
          ) : (
            <div className="space-y-1">
              {messages.map((msg, i) => (
                <MessageRenderer key={i} message={msg} />
              ))}
            </div>
          )}
        </div>
      </div>
    </div>
  )
}
