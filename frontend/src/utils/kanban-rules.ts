import type { Phase, RunStatus } from "@/types"

export const PHASES: Phase[] = [
  "intake", "plan", "implement", "review",
  "verify", "deploy", "observe", "close",
]

// Action phases: phases that support human actions (approve/reject/retry)
export const ACTION_PHASES: Set<Phase> = new Set(["plan", "implement", "review"])

// A delivery is terminal (closed) when it has completed the close phase successfully.
export function isTerminal(phase: Phase, runStatus: RunStatus): boolean {
  return phase === "close" && runStatus === "succeeded"
}
