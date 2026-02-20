import { describe, it, expect, vi, beforeEach, afterEach } from "vitest"
import { logger } from "../logger"

let logSpy: ReturnType<typeof vi.spyOn>
let warnSpy: ReturnType<typeof vi.spyOn>
let errorSpy: ReturnType<typeof vi.spyOn>

beforeEach(() => {
  logSpy = vi.spyOn(console, "log").mockImplementation(() => {})
  warnSpy = vi.spyOn(console, "warn").mockImplementation(() => {})
  errorSpy = vi.spyOn(console, "error").mockImplementation(() => {})
})

afterEach(() => {
  vi.restoreAllMocks()
})

describe("logger in dev mode", () => {
  it("logs debug messages via console.log", () => {
    logger.debug("test debug")
    expect(logSpy).toHaveBeenCalledWith("[jakeops:debug]", "test debug")
  })

  it("logs info messages via console.log", () => {
    logger.info("test info")
    expect(logSpy).toHaveBeenCalledWith("[jakeops:info]", "test info")
  })

  it("logs warn messages via console.warn", () => {
    logger.warn("test warn")
    expect(warnSpy).toHaveBeenCalledWith("[jakeops:warn]", "test warn")
  })

  it("logs error messages via console.error", () => {
    logger.error("test error")
    expect(errorSpy).toHaveBeenCalledWith("[jakeops:error]", "test error")
  })

  it("passes context object when provided", () => {
    const ctx = { key: "value", count: 42 }
    logger.info("with context", ctx)
    expect(logSpy).toHaveBeenCalledWith("[jakeops:info]", "with context", ctx)
  })

  it("omits context argument when not provided", () => {
    logger.debug("no context")
    expect(logSpy).toHaveBeenCalledWith("[jakeops:debug]", "no context")
    expect(logSpy.mock.calls[0]).toHaveLength(2)
  })
})

describe("logger in prod mode", () => {
  beforeEach(() => {
    vi.stubEnv("DEV", "")
  })

  afterEach(() => {
    vi.unstubAllEnvs()
  })

  it("suppresses debug messages", () => {
    logger.debug("should not appear")
    expect(logSpy).not.toHaveBeenCalled()
  })

  it("suppresses info messages", () => {
    logger.info("should not appear")
    expect(logSpy).not.toHaveBeenCalled()
  })

  it("allows warn messages", () => {
    logger.warn("should appear")
    expect(warnSpy).toHaveBeenCalledWith("[jakeops:warn]", "should appear")
  })

  it("allows error messages", () => {
    logger.error("should appear")
    expect(errorSpy).toHaveBeenCalledWith("[jakeops:error]", "should appear")
  })
})
