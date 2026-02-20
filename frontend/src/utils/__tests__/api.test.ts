import { describe, it, expect, vi, beforeEach } from "vitest"
import { apiFetch, apiPost, apiPatch, apiDelete } from "../api"

const mockFetch = vi.fn()
globalThis.fetch = mockFetch

beforeEach(() => {
  mockFetch.mockReset()
})

describe("apiFetch", () => {
  it("sends GET request to /api + path", async () => {
    mockFetch.mockResolvedValue({ ok: true, json: () => Promise.resolve([]) })
    const result = await apiFetch<unknown[]>("/deliveries")
    expect(mockFetch).toHaveBeenCalledWith("/api/deliveries", { method: "GET" })
    expect(result).toEqual([])
  })

  it("throws on non-ok response", async () => {
    mockFetch.mockResolvedValue({
      ok: false,
      status: 404,
      json: () => Promise.resolve({ detail: "Not found" }),
    })
    await expect(apiFetch("/deliveries/xxx")).rejects.toThrow("Not found")
  })
})

describe("apiPost", () => {
  it("sends POST with JSON body", async () => {
    mockFetch.mockResolvedValue({
      ok: true,
      json: () => Promise.resolve({ id: "abc" }),
    })
    const result = await apiPost("/deliveries", { summary: "test" })
    expect(mockFetch).toHaveBeenCalledWith("/api/deliveries", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ summary: "test" }),
    })
    expect(result).toEqual({ id: "abc" })
  })
})

describe("apiPatch", () => {
  it("sends PATCH with JSON body", async () => {
    mockFetch.mockResolvedValue({
      ok: true,
      json: () => Promise.resolve({ id: "abc" }),
    })
    await apiPatch("/deliveries/abc", { phase: "plan" })
    expect(mockFetch).toHaveBeenCalledWith("/api/deliveries/abc", {
      method: "PATCH",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ phase: "plan" }),
    })
  })
})

describe("apiDelete", () => {
  it("sends DELETE request", async () => {
    mockFetch.mockResolvedValue({
      ok: true,
      json: () => Promise.resolve({ status: "deleted" }),
    })
    await apiDelete("/sources/abc")
    expect(mockFetch).toHaveBeenCalledWith("/api/sources/abc", {
      method: "DELETE",
    })
  })
})
