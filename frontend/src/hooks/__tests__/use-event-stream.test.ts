import { renderHook, act } from "@testing-library/react"
import { describe, it, expect, vi, beforeEach, afterEach } from "vitest"
import { useEventStream } from "../use-event-stream"

class MockEventSource {
  url: string
  onmessage: ((event: MessageEvent) => void) | null = null
  onerror: ((event: Event) => void) | null = null
  listeners: Record<string, ((event: Event) => void)[]> = {}
  readyState = 0

  constructor(url: string) {
    this.url = url
    MockEventSource.instances.push(this)
  }

  addEventListener(event: string, handler: (event: Event) => void) {
    if (!this.listeners[event]) this.listeners[event] = []
    this.listeners[event].push(handler)
  }

  removeEventListener(event: string, handler: (event: Event) => void) {
    if (this.listeners[event]) {
      this.listeners[event] = this.listeners[event].filter((h) => h !== handler)
    }
  }

  close() {
    this.readyState = 2
  }

  // Test helpers
  simulateMessage(data: string) {
    if (this.onmessage) {
      this.onmessage(new MessageEvent("message", { data }))
    }
  }

  simulateDone() {
    for (const handler of this.listeners["done"] ?? []) {
      handler(new Event("done"))
    }
  }

  static instances: MockEventSource[] = []
  static reset() {
    MockEventSource.instances = []
  }
}

describe("useEventStream", () => {
  beforeEach(() => {
    MockEventSource.reset()
    vi.stubGlobal("EventSource", MockEventSource)
  })

  afterEach(() => {
    vi.unstubAllGlobals()
  })

  it("connects when active is true", () => {
    renderHook(() => useEventStream("d1", true))
    expect(MockEventSource.instances).toHaveLength(1)
    expect(MockEventSource.instances[0].url).toBe("/api/deliveries/d1/stream")
  })

  it("does not connect when active is false", () => {
    renderHook(() => useEventStream("d1", false))
    expect(MockEventSource.instances).toHaveLength(0)
  })

  it("accumulates events from messages", () => {
    const { result } = renderHook(() => useEventStream("d1", true))
    const es = MockEventSource.instances[0]

    act(() => {
      es.simulateMessage(JSON.stringify({ type: "assistant", message: { role: "assistant" } }))
    })

    expect(result.current.events).toHaveLength(1)
    expect(result.current.events[0].type).toBe("assistant")
  })

  it("closes on done event", () => {
    const { result } = renderHook(() => useEventStream("d1", true))
    const es = MockEventSource.instances[0]

    act(() => {
      es.simulateDone()
    })

    expect(es.readyState).toBe(2)
    expect(result.current.done).toBe(true)
  })
})
