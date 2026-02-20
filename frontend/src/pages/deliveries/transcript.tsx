import { ChevronRight, ChevronDown } from "lucide-react"
import { Badge } from "@/components/ui/badge"
import {
  Collapsible,
  CollapsibleContent,
  CollapsibleTrigger,
} from "@/components/ui/collapsible"
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
