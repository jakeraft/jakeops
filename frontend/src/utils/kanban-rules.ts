import type { Phase } from "@/types"

export const PHASES: Phase[] = [
  "intake", "plan", "implement", "review",
  "verify", "deploy", "observe", "close",
]

// Action phases: phases that support human actions (approve/reject/retry)
export const ACTION_PHASES: Set<Phase> = new Set(["plan", "implement", "review"])
