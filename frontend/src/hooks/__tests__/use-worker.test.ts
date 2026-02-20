import { describe, it, expect, vi, beforeEach } from "vitest"
import { renderHook, waitFor, act } from "@testing-library/react"
import { useWorker } from "../use-worker"
import * as api from "@/utils/api"

vi.mock("@/utils/api")

const MOCK_RESPONSE = {
  workers: [
    {
      name: "delivery_sync",
      label: "Delivery Sync",
      enabled: true,
      interval_sec: 60,
      last_poll_at: new Date().toISOString(),
      last_result: { created: 2 },
      last_error: null,
    },
  ],
}

describe("useWorker", () => {
  beforeEach(() => {
    vi.resetAllMocks()
    vi.mocked(api.apiFetch).mockResolvedValue(MOCK_RESPONSE)
  })

  it("fetches worker status on mount", async () => {
    const { result } = renderHook(() => useWorker())
    expect(result.current.loading).toBe(true)
    await waitFor(() => expect(result.current.loading).toBe(false))
    expect(result.current.workers).toEqual(MOCK_RESPONSE.workers)
    expect(api.apiFetch).toHaveBeenCalledWith("/worker/status")
  })

  it("sets error when fetch fails", async () => {
    vi.mocked(api.apiFetch).mockRejectedValue(new Error("Network error"))
    const { result } = renderHook(() => useWorker())
    await waitFor(() => expect(result.current.loading).toBe(false))
    expect(result.current.error).toBe("Network error")
    expect(result.current.workers).toEqual([])
  })

  it("refresh re-fetches worker status", async () => {
    const { result } = renderHook(() => useWorker())
    await waitFor(() => expect(result.current.loading).toBe(false))
    expect(api.apiFetch).toHaveBeenCalledTimes(1)

    await act(async () => {
      await result.current.refresh()
    })
    expect(api.apiFetch).toHaveBeenCalledTimes(2)
  })
})
