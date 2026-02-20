// All shared types — re-exported from generated file (SSOT: backend Python models)
// Run `npm run sync-types` after changing backend domain models.
export type {
  Phase,
  RunStatus,
  ExecutorKind,
  Verdict,
  RefRole,
  RefType,
  SourceType,
  AgentRunMode,
  AgentRunStatus,
  Ref,
  Session,
  Plan,
  ExecutionStats,
  PhaseRun,
  AgentRun,
  Source,
  SourceCreate,
  SourceUpdate,
} from "./types.generated"

export {
  PHASES,
  RUN_STATUSES,
  EXECUTOR_KINDS,
  VERDICTS,
  SOURCE_TYPES,
  AGENT_RUN_MODES,
  AGENT_RUN_STATUSES,
} from "./types.generated"

// --- Hand-authored types below (no backend Pydantic model) ---

import type { AgentRun, Phase, PhaseRun, Plan, Ref, RunStatus } from "./types.generated"

// Delivery — full entity assembled at usecase level
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
}

// Transcript — frontend-only representation
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
