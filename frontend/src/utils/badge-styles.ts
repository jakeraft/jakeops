import type { AgentRunStatus, ExecutorKind, Phase, RunStatus } from "@/types"

export const PHASE_CLASSES: Record<Phase, string> = {
  intake: "bg-badge-slate text-badge-slate-fg",
  plan: "bg-badge-blue text-badge-blue-fg",
  implement: "bg-badge-violet text-badge-violet-fg",
  review: "bg-badge-amber text-badge-amber-fg",
  verify: "bg-badge-cyan text-badge-cyan-fg",
  deploy: "bg-badge-green text-badge-green-fg",
  observe: "bg-badge-emerald text-badge-emerald-fg",
  close: "bg-badge-gray text-badge-gray-fg",
}

export const STATUS_CLASSES: Record<RunStatus, string> = {
  pending: "bg-badge-gray text-badge-gray-fg",
  running: "bg-badge-blue text-badge-blue-fg",
  succeeded: "bg-badge-green text-badge-green-fg",
  failed: "bg-badge-red text-badge-red-fg",
  blocked: "bg-badge-yellow text-badge-yellow-fg",
}

export const EXECUTOR_CLASSES: Record<ExecutorKind, string> = {
  system: "bg-badge-gray text-badge-gray-fg",
  agent: "bg-badge-violet text-badge-violet-fg",
}

export const RUN_STATUS_CLASSES: Record<AgentRunStatus, string> = {
  running: "bg-badge-blue text-badge-blue-fg",
  success: "bg-badge-green text-badge-green-fg",
  failed: "bg-badge-red text-badge-red-fg",
}
