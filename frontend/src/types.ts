// Phase pipeline
export type Phase =
  | "intake"
  | "plan"
  | "implement"
  | "review"
  | "verify"
  | "deploy"
  | "observe"
  | "close"

export type RunStatus =
  | "pending"
  | "running"
  | "succeeded"
  | "failed"
  | "blocked"

export type ExecutorKind = "system" | "agent"

export type Verdict = "pass" | "not_pass"

// Refs
export type RefRole = "trigger" | "output" | "parent"
export type RefType =
  | "jira"
  | "verbal"
  | "pr"
  | "commit"
  | "repo"
  | "github_issue"
  | "pull_request"
  | "issue"

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
  verdict?: Verdict
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
  seq: number
  schema_version: number
  created_at: string
  updated_at: string
  phase: Phase
  run_status: RunStatus
  endpoint: Phase
  checkpoints: Phase[]
  summary: string
  repository: string
  refs: Ref[]
  runs: AgentRun[]
  phase_runs: PhaseRun[]
  plan?: Plan
  error?: string
  reject_reason?: string
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
  endpoint: string
  checkpoints: string[]
  last_polled_at?: string
}

export interface SourceCreate {
  type: SourceType
  owner: string
  repo: string
  token?: string
  endpoint?: string
  checkpoints?: string[]
}

export interface SourceUpdate {
  token?: string
  active?: boolean
  endpoint?: string
  checkpoints?: string[]
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
