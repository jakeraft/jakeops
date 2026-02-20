// Auto-generated from backend domain models. DO NOT EDIT.
// Run: python3 scripts/sync-types.py

// --- Enums ---

export type Phase = "intake" | "plan" | "implement" | "review" | "verify" | "deploy" | "observe" | "close"
export const PHASES = ["intake", "plan", "implement", "review", "verify", "deploy", "observe", "close"] as const

export type RunStatus = "pending" | "running" | "succeeded" | "failed" | "blocked"
export const RUN_STATUSES = ["pending", "running", "succeeded", "failed", "blocked"] as const

export type ExecutorKind = "system" | "agent"
export const EXECUTOR_KINDS = ["system", "agent"] as const

export type Verdict = "pass" | "not_pass"
export const VERDICTS = ["pass", "not_pass"] as const

export type RefRole = "request" | "work" | "parent"
export const REF_ROLES = ["request", "work", "parent"] as const

export type RefType = "jira" | "verbal" | "pr" | "commit" | "repo" | "github_issue" | "pull_request" | "issue"
export const REF_TYPES = ["jira", "verbal", "pr", "commit", "repo", "github_issue", "pull_request", "issue"] as const

export type SourceType = "github"
export const SOURCE_TYPES = ["github"] as const

export type AgentRunMode = "plan" | "execution"
export const AGENT_RUN_MODES = ["plan", "execution"] as const

export type AgentRunStatus = "success" | "failed"
export const AGENT_RUN_STATUSES = ["success", "failed"] as const

// --- Interfaces ---

export interface Ref {
  role: RefRole
  type: RefType
  label: string
  url?: string
}

export interface Session {
  model: string
}

export interface Plan {
  content: string
  generated_at: string
  model: string
  cwd: string
}

export interface ExecutionStats {
  cost_usd: number
  input_tokens: number
  output_tokens: number
  duration_ms: number
}

export interface PhaseRun {
  phase: Phase
  run_status: RunStatus
  executor: ExecutorKind
  verdict?: Verdict
  started_at?: string
  ended_at?: string
}

export interface AgentRun {
  id: string
  mode: AgentRunMode
  status: AgentRunStatus
  created_at: string
  session: Session
  stats: ExecutionStats
  error?: string
  summary?: string
  session_id?: string
}

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
  token: string
  endpoint: string
  checkpoints: string[]
}

export interface SourceUpdate {
  token?: string
  active?: boolean
  endpoint?: string
  checkpoints?: string[]
}
