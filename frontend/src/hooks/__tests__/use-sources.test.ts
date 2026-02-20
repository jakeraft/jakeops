import { describe, it, expect, vi, beforeEach } from "vitest"
import { renderHook, waitFor, act } from "@testing-library/react"
import { useSources } from "../use-sources"
import * as api from "@/utils/api"

vi.mock("@/utils/api")

const MOCK_SOURCES = [
  {
    id: "src-1",
    type: "github" as const,
    owner: "acme",
    repo: "backend",
    created_at: new Date().toISOString(),
    token: "ghp_***",
    active: true,
    default_exit_phase: "deploy",
  },
]

describe("useSources", () => {
  beforeEach(() => {
    vi.resetAllMocks()
    vi.mocked(api.apiFetch).mockResolvedValue(MOCK_SOURCES)
    vi.mocked(api.apiPost).mockResolvedValue({})
    vi.mocked(api.apiPatch).mockResolvedValue({})
    vi.mocked(api.apiDelete).mockResolvedValue({})
  })

  it("fetches sources on mount", async () => {
    const { result } = renderHook(() => useSources())
    expect(result.current.loading).toBe(true)
    await waitFor(() => expect(result.current.loading).toBe(false))
    expect(result.current.sources).toEqual(MOCK_SOURCES)
    expect(api.apiFetch).toHaveBeenCalledWith("/sources")
  })

  it("sets error when fetch fails", async () => {
    vi.mocked(api.apiFetch).mockRejectedValue(new Error("Network error"))
    const { result } = renderHook(() => useSources())
    await waitFor(() => expect(result.current.loading).toBe(false))
    expect(result.current.error).toBe("Network error")
    expect(result.current.sources).toEqual([])
  })

  it("refresh re-fetches sources", async () => {
    const { result } = renderHook(() => useSources())
    await waitFor(() => expect(result.current.loading).toBe(false))
    expect(api.apiFetch).toHaveBeenCalledTimes(1)

    await act(async () => {
      await result.current.refresh()
    })
    expect(api.apiFetch).toHaveBeenCalledTimes(2)
  })

  it("createSource posts and refreshes", async () => {
    const { result } = renderHook(() => useSources())
    await waitFor(() => expect(result.current.loading).toBe(false))

    const body = { type: "github" as const, owner: "acme", repo: "api" }
    await act(async () => {
      await result.current.createSource(body)
    })
    expect(api.apiPost).toHaveBeenCalledWith("/sources", body)
    // refresh called after create
    expect(api.apiFetch).toHaveBeenCalledTimes(2)
  })

  it("updateSource patches and refreshes", async () => {
    const { result } = renderHook(() => useSources())
    await waitFor(() => expect(result.current.loading).toBe(false))

    const body = { active: false }
    await act(async () => {
      await result.current.updateSource("src-1", body)
    })
    expect(api.apiPatch).toHaveBeenCalledWith("/sources/src-1", body)
    expect(api.apiFetch).toHaveBeenCalledTimes(2)
  })

  it("deleteSource deletes and refreshes", async () => {
    const { result } = renderHook(() => useSources())
    await waitFor(() => expect(result.current.loading).toBe(false))

    await act(async () => {
      await result.current.deleteSource("src-1")
    })
    expect(api.apiDelete).toHaveBeenCalledWith("/sources/src-1")
    expect(api.apiFetch).toHaveBeenCalledTimes(2)
  })

  it("syncNow posts to /sources/sync and refreshes", async () => {
    const { result } = renderHook(() => useSources())
    await waitFor(() => expect(result.current.loading).toBe(false))

    await act(async () => {
      await result.current.syncNow()
    })
    expect(api.apiPost).toHaveBeenCalledWith("/sources/sync")
    expect(api.apiFetch).toHaveBeenCalledTimes(2)
  })
})
