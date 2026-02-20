import { describe, it, expect } from "vitest"
import { getDropAction, PHASES } from "../kanban-rules"

describe("PHASES", () => {
  it("lists all 8 phases in order", () => {
    expect(PHASES).toEqual([
      "intake", "plan", "implement", "review",
      "verify", "deploy", "observe", "close",
    ])
  })
})

describe("getDropAction", () => {
  it("returns approve when moving forward from gate phase with succeeded status", () => {
    expect(getDropAction("plan", "succeeded", "implement")).toEqual({
      type: "approve",
    })
  })

  it("returns null when moving forward from non-gate phase", () => {
    expect(getDropAction("implement", "succeeded", "review")).toBeNull()
  })

  it("returns reject when moving backward from gate phase with succeeded status", () => {
    expect(getDropAction("review", "succeeded", "implement")).toEqual({
      type: "reject",
    })
  })

  it("returns null when moving backward from non-gate phase", () => {
    expect(getDropAction("implement", "succeeded", "plan")).toBeNull()
  })

  it("returns null when status is not succeeded for forward move", () => {
    expect(getDropAction("plan", "running", "implement")).toBeNull()
  })

  it("returns null when status is not succeeded for backward move", () => {
    expect(getDropAction("review", "running", "implement")).toBeNull()
  })

  it("returns null when skipping phases", () => {
    expect(getDropAction("plan", "succeeded", "review")).toBeNull()
  })

  it("returns null when dropping on same phase", () => {
    expect(getDropAction("plan", "succeeded", "plan")).toBeNull()
  })

  it("returns null when source phase is close", () => {
    expect(getDropAction("close", "succeeded", "observe")).toBeNull()
  })

  it("returns null when status is canceled", () => {
    expect(getDropAction("plan", "canceled", "implement")).toBeNull()
  })

  it("returns null for intake to plan (intake is not a gate phase)", () => {
    expect(getDropAction("intake", "succeeded", "plan")).toBeNull()
  })
})
