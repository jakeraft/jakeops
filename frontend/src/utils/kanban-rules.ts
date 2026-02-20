import type { Phase, RunStatus } from "@/types"

export const PHASES: Phase[] = [
  "intake", "plan", "implement", "review",
  "verify", "deploy", "observe", "close",
]

const GATE_PHASES: Set<Phase> = new Set(["plan", "review", "deploy"])

export type DropAction =
  | { type: "approve" }
  | { type: "reject" }

export function getDropAction(
  fromPhase: Phase,
  runStatus: RunStatus,
  toPhase: Phase,
): DropAction | null {
  if (fromPhase === toPhase) return null
  if (runStatus !== "succeeded") return null
  if (fromPhase === "close") return null

  const fromIndex = PHASES.indexOf(fromPhase)
  const toIndex = PHASES.indexOf(toPhase)
  const diff = toIndex - fromIndex

  // Only gate phases support manual transitions
  if (!GATE_PHASES.has(fromPhase)) return null

  // Forward: must be exactly +1
  if (diff === 1) {
    return { type: "approve" }
  }

  // Backward: must be exactly -1
  if (diff === -1) {
    return { type: "reject" }
  }

  return null
}
