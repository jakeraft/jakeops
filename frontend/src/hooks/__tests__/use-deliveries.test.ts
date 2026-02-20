import { describe, it, expect, vi, beforeEach } from "vitest"
import { renderHook, waitFor } from "@testing-library/react"
import { useDeliveries } from "../use-deliveries"
import * as api from "@/utils/api"

vi.mock("@/utils/api")

const MOCK_DELIVERIES = [
  {
    id: "abc123",
    phase: "plan",
    run_status: "succeeded",
    summary: "Test delivery",
    repository: "owner/repo",
    updated_at: new Date().toISOString(),
    refs: [],
    runs: [],
    phase_runs: [],
  },
]

describe("useDeliveries", () => {
  beforeEach(() => {
    vi.mocked(api.apiFetch).mockResolvedValue(MOCK_DELIVERIES)
  })

  it("fetches deliveries on mount", async () => {
    const { result } = renderHook(() => useDeliveries())
    expect(result.current.loading).toBe(true)
    await waitFor(() => expect(result.current.loading).toBe(false))
    expect(result.current.deliveries).toEqual(MOCK_DELIVERIES)
    expect(api.apiFetch).toHaveBeenCalledWith("/deliveries")
  })
})
