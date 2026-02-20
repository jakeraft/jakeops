import type { AgentRun, ExecutorKind, Phase, RunStatus } from "@/types"

export const PHASE_CLASSES: Record<Phase, string> = {
  intake: "bg-slate-100 text-slate-700",
  plan: "bg-blue-100 text-blue-700",
  implement: "bg-violet-100 text-violet-700",
  review: "bg-amber-100 text-amber-700",
  verify: "bg-cyan-100 text-cyan-700",
  deploy: "bg-green-100 text-green-700",
  observe: "bg-emerald-100 text-emerald-700",
  close: "bg-gray-100 text-gray-500",
}

export const STATUS_CLASSES: Record<RunStatus, string> = {
  pending: "bg-gray-100 text-gray-700",
  running: "bg-blue-100 text-blue-700",
  succeeded: "bg-green-100 text-green-700",
  failed: "bg-red-100 text-red-700",
  blocked: "bg-yellow-100 text-yellow-700",
  canceled: "bg-gray-100 text-gray-500",
}

export const EXECUTOR_CLASSES: Record<ExecutorKind, string> = {
  system: "bg-gray-100 text-gray-700",
  agent: "bg-violet-100 text-violet-700",
  human: "bg-blue-100 text-blue-700",
}

export const MODE_CLASSES: Record<AgentRun["mode"], string> = {
  plan: "bg-blue-100 text-blue-700",
  execution: "bg-violet-100 text-violet-700",
  fix: "bg-amber-100 text-amber-700",
}

export const RUN_STATUS_CLASSES: Record<AgentRun["status"], string> = {
  success: "bg-green-100 text-green-700",
  failed: "bg-red-100 text-red-700",
}
