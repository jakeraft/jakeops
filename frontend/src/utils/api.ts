import { logger } from "@/utils/logger"

class ApiError extends Error {
  status: number

  constructor(status: number, message: string) {
    super(message)
    this.status = status
  }
}

async function handleResponse<T>(response: Response): Promise<T> {
  if (!response.ok) {
    const body = await response.json().catch(() => ({}))
    const message = body.detail || `HTTP ${response.status}`
    logger.error("API error response", { status: response.status, message })
    throw new ApiError(response.status, message)
  }
  return response.json()
}

export async function apiFetch<T>(path: string): Promise<T> {
  const start = performance.now()
  logger.debug("API request", { method: "GET", path })
  const response = await fetch(`/api${path}`, { method: "GET" })
  const duration = Math.round(performance.now() - start)
  logger.debug("API response", { method: "GET", path, status: response.status, duration_ms: duration })
  return handleResponse<T>(response)
}

export async function apiPost<T>(path: string, body?: unknown): Promise<T> {
  const start = performance.now()
  logger.debug("API request", { method: "POST", path })
  const response = await fetch(`/api${path}`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(body),
  })
  const duration = Math.round(performance.now() - start)
  logger.debug("API response", { method: "POST", path, status: response.status, duration_ms: duration })
  return handleResponse<T>(response)
}

export async function apiPatch<T>(path: string, body: unknown): Promise<T> {
  const start = performance.now()
  logger.debug("API request", { method: "PATCH", path })
  const response = await fetch(`/api${path}`, {
    method: "PATCH",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(body),
  })
  const duration = Math.round(performance.now() - start)
  logger.debug("API response", { method: "PATCH", path, status: response.status, duration_ms: duration })
  return handleResponse<T>(response)
}

export async function apiDelete<T>(path: string): Promise<T> {
  const start = performance.now()
  logger.debug("API request", { method: "DELETE", path })
  const response = await fetch(`/api${path}`, { method: "DELETE" })
  const duration = Math.round(performance.now() - start)
  logger.debug("API response", { method: "DELETE", path, status: response.status, duration_ms: duration })
  return handleResponse<T>(response)
}
