import { describe, it, expect } from "vitest"
import { formatRelativeTime, formatDateTime } from "../format"

describe("formatRelativeTime", () => {
  it("returns 'just now' for recent timestamps", () => {
    const now = new Date().toISOString()
    expect(formatRelativeTime(now)).toBe("just now")
  })

  it("returns '5m ago' for 5 minutes ago", () => {
    const date = new Date(Date.now() - 5 * 60 * 1000).toISOString()
    expect(formatRelativeTime(date)).toBe("5m ago")
  })

  it("returns '2h ago' for 2 hours ago", () => {
    const date = new Date(Date.now() - 2 * 60 * 60 * 1000).toISOString()
    expect(formatRelativeTime(date)).toBe("2h ago")
  })

  it("returns '3d ago' for 3 days ago", () => {
    const date = new Date(Date.now() - 3 * 24 * 60 * 60 * 1000).toISOString()
    expect(formatRelativeTime(date)).toBe("3d ago")
  })
})

describe("formatDateTime", () => {
  it("formats ISO string to readable date", () => {
    const result = formatDateTime("2026-02-20T10:30:00+09:00")
    expect(result).toMatch(/2026/)
  })
})
