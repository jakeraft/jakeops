import { describe, it, expect, vi, beforeEach } from "vitest"
import { renderHook, waitFor } from "@testing-library/react"
import { useTranscript } from "../use-transcript"
import * as api from "@/utils/api"

vi.mock("@/utils/api")

const MOCK_TRANSCRIPT = {
  meta: {
    agents: {
      leader: { model: "claude-opus-4-6" },
      subagent_tool123: { model: "claude-haiku-4-5" },
    },
  },
  leader: [
    { role: "assistant", content: [{ type: "thinking", thinking: "Let me analyze the codebase..." }] },
    { role: "assistant", content: [{ type: "text", text: "I'll fix the authentication bug." }] },
    { role: "assistant", content: [{ type: "tool_use", name: "Read", input: { file_path: "/src/auth.ts" } }] },
    { role: "user", content: [{ type: "tool_result", content: "file contents here...", tool_use_id: "abc" }] },
  ],
  subagent_tool123: [
    { role: "assistant", content: [{ type: "text", text: "Searching for references..." }] },
  ],
}

describe("useTranscript", () => {
  beforeEach(() => {
    vi.mocked(api.apiFetch).mockResolvedValue(MOCK_TRANSCRIPT)
  })

  it("fetches transcript by delivery and run id", async () => {
    const { result } = renderHook(() => useTranscript("abc123", "run01"))
    await waitFor(() => expect(result.current.loading).toBe(false))
    expect(result.current.transcript).toEqual(MOCK_TRANSCRIPT)
    expect(api.apiFetch).toHaveBeenCalledWith("/deliveries/abc123/runs/run01/transcript")
  })
})
