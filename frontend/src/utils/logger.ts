type LogLevel = "debug" | "info" | "warn" | "error"

const LEVELS: Record<LogLevel, number> = {
  debug: 0,
  info: 1,
  warn: 2,
  error: 3,
}

function getMinLevel(): number {
  return import.meta.env.DEV ? LEVELS.debug : LEVELS.warn
}

function log(level: LogLevel, message: string, context?: Record<string, unknown>) {
  if (LEVELS[level] < getMinLevel()) return
  const prefix = `[jakeops:${level}]`
  const fn = level === "error" ? console.error : level === "warn" ? console.warn : console.log
  if (context) {
    fn(prefix, message, context)
  } else {
    fn(prefix, message)
  }
}

export const logger = {
  debug: (msg: string, ctx?: Record<string, unknown>) => log("debug", msg, ctx),
  info: (msg: string, ctx?: Record<string, unknown>) => log("info", msg, ctx),
  warn: (msg: string, ctx?: Record<string, unknown>) => log("warn", msg, ctx),
  error: (msg: string, ctx?: Record<string, unknown>) => log("error", msg, ctx),
}
