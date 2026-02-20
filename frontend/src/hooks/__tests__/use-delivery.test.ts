import { describe, it, expect, vi, beforeEach } from "vitest"
import { renderHook, waitFor } from "@testing-library/react"
import { useDelivery } from "../use-delivery"
import * as api from "@/utils/api"

vi.mock("@/utils/api")

const MOCK_DELIVERY = {
  id: "abc123",
  phase: "plan",
  run_status: "succeeded",
  summary: "Test delivery",
  repository: "owner/repo",
  refs: [
    {
      role: "trigger",
      type: "github_issue",
      label: "#42",
      url: "https://github.com/test/repo/issues/42",
    },
  ],
  runs: [
    {
      id: "run01",
      mode: "execution",
      status: "success",
      created_at: "2026-02-20T10:00:00+09:00",
      session: { model: "claude-opus-4-6" },
      stats: {
        cost_usd: 0.12,
        input_tokens: 5000,
        output_tokens: 3000,
        duration_ms: 45000,
      },
      summary: "Implemented the feature",
    },
  ],
  phase_runs: [
    {
      phase: "intake",
      run_status: "succeeded",
      executor: "system",
      started_at: "2026-02-20T09:00:00+09:00",
    },
    {
      phase: "plan",
      run_status: "succeeded",
      executor: "agent",
      started_at: "2026-02-20T09:01:00+09:00",
    },
  ],
}

describe("useDelivery", () => {
  beforeEach(() => {
    vi.mocked(api.apiFetch).mockResolvedValue(MOCK_DELIVERY)
    vi.mocked(api.apiPost).mockResolvedValue({
      id: "abc123",
      phase: "implement",
      run_status: "pending",
    })
  })

  it("fetches delivery by id", async () => {
    const { result } = renderHook(() => useDelivery("abc123"))
    await waitFor(() => expect(result.current.loading).toBe(false))
    expect(result.current.delivery).toEqual(MOCK_DELIVERY)
    expect(api.apiFetch).toHaveBeenCalledWith("/deliveries/abc123")
  })

  it("provides approve action", async () => {
    const { result } = renderHook(() => useDelivery("abc123"))
    await waitFor(() => expect(result.current.loading).toBe(false))
    await result.current.approve()
    expect(api.apiPost).toHaveBeenCalledWith("/deliveries/abc123/approve")
  })

  it("provides reject action", async () => {
    const { result } = renderHook(() => useDelivery("abc123"))
    await waitFor(() => expect(result.current.loading).toBe(false))
    await result.current.reject("Needs more detail")
    expect(api.apiPost).toHaveBeenCalledWith("/deliveries/abc123/reject", {
      reason: "Needs more detail",
    })
  })

  it("provides retry action", async () => {
    const { result } = renderHook(() => useDelivery("abc123"))
    await waitFor(() => expect(result.current.loading).toBe(false))
    await result.current.retry()
    expect(api.apiPost).toHaveBeenCalledWith("/deliveries/abc123/retry")
  })

  it("provides cancel action", async () => {
    const { result } = renderHook(() => useDelivery("abc123"))
    await waitFor(() => expect(result.current.loading).toBe(false))
    await result.current.cancel()
    expect(api.apiPost).toHaveBeenCalledWith("/deliveries/abc123/cancel")
  })

  it("provides generatePlan action", async () => {
    const { result } = renderHook(() => useDelivery("abc123"))
    await waitFor(() => expect(result.current.loading).toBe(false))
    await result.current.generatePlan()
    expect(api.apiPost).toHaveBeenCalledWith(
      "/deliveries/abc123/generate-plan",
    )
  })
})
