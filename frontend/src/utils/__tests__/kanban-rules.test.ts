import { describe, it, expect } from "vitest"
import { PHASES, ACTION_PHASES } from "../kanban-rules"

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
