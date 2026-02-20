import { describe, it, expect } from "vitest"
import { PHASES, ACTION_PHASES, isTerminal } from "../kanban-rules"

describe("PHASES", () => {
  it("lists all 8 phases in order", () => {
    expect(PHASES).toEqual([
      "intake", "plan", "implement", "review",
      "verify", "deploy", "observe", "close",
    ])
  })
})

describe("ACTION_PHASES", () => {
  it("contains plan, implement, review", () => {
    expect(ACTION_PHASES.has("plan")).toBe(true)
    expect(ACTION_PHASES.has("implement")).toBe(true)
    expect(ACTION_PHASES.has("review")).toBe(true)
  })

  it("does not contain non-action phases", () => {
    expect(ACTION_PHASES.has("intake")).toBe(false)
    expect(ACTION_PHASES.has("verify")).toBe(false)
    expect(ACTION_PHASES.has("deploy")).toBe(false)
    expect(ACTION_PHASES.has("observe")).toBe(false)
    expect(ACTION_PHASES.has("close")).toBe(false)
  })
})

describe("isTerminal", () => {
  it("returns true when phase is close and run_status is succeeded", () => {
    expect(isTerminal("close", "succeeded")).toBe(true)
  })

  it("returns false for active deliveries", () => {
    expect(isTerminal("intake", "pending")).toBe(false)
    expect(isTerminal("plan", "running")).toBe(false)
    expect(isTerminal("review", "succeeded")).toBe(false)
    expect(isTerminal("deploy", "failed")).toBe(false)
  })

  it("returns false for close phase with non-succeeded status", () => {
    expect(isTerminal("close", "running")).toBe(false)
    expect(isTerminal("close", "failed")).toBe(false)
    expect(isTerminal("close", "pending")).toBe(false)
  })
})
