import { useCallback, useEffect, useState } from "react"
import type { Delivery } from "@/types"
import { apiFetch, apiPost } from "@/utils/api"
import { logger } from "@/utils/logger"

export function useDelivery(id: string | undefined) {
  const [delivery, setDelivery] = useState<Delivery | null>(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [actionError, setActionError] = useState<string | null>(null)

  const refresh = useCallback(async () => {
    if (!id) return
    try {
      const data = await apiFetch<Delivery>(`/deliveries/${id}`)
      setDelivery(data)
      setError(null)
    } catch (e) {
      const message = e instanceof Error ? e.message : "Unknown error"
      logger.error("Failed to fetch delivery", { id, error: message })
      setError(message)
    } finally {
      setLoading(false)
    }
  }, [id])

  useEffect(() => {
    refresh()
  }, [refresh])

  // Poll for status updates while delivery is running
  useEffect(() => {
    if (delivery?.run_status !== "running") return
    const interval = setInterval(() => {
      refresh()
    }, 3000)
    return () => clearInterval(interval)
  }, [delivery?.run_status, refresh])

  const performAction = useCallback(
    async (action: () => Promise<unknown>) => {
      setActionError(null)
      try {
        await action()
        await refresh()
      } catch (e) {
        const message = e instanceof Error ? e.message : "Unknown error"
        logger.error("Delivery action failed", { id, error: message })
        setActionError(message)
        await refresh()
        throw e
      }
    },
    [id, refresh],
  )

  const approve = useCallback(
    () => performAction(() => apiPost(`/deliveries/${id}/approve`)),
    [id, performAction],
  )

  const reject = useCallback(
    () => performAction(() => apiPost(`/deliveries/${id}/reject`)),
    [id, performAction],
  )

  const cancel = useCallback(
    () => performAction(() => apiPost(`/deliveries/${id}/cancel`)),
    [id, performAction],
  )

  const runAgent = useCallback(
    () => performAction(async () => {
      const d = await apiFetch<{ phase: string; run_status: string }>(`/deliveries/${id}`)
      if (d.run_status === "failed") {
        await apiPost(`/deliveries/${id}/retry`)
      }
      setDelivery((prev) => prev ? { ...prev, run_status: "running" } : prev)
      if (d.phase === "plan") await apiPost(`/deliveries/${id}/generate-plan`)
      else if (d.phase === "implement") await apiPost(`/deliveries/${id}/run-implement`)
      else if (d.phase === "review") await apiPost(`/deliveries/${id}/run-review`)
    }),
    [id, performAction],
  )

  return {
    delivery,
    loading,
    error,
    actionError,
    clearActionError: useCallback(() => setActionError(null), []),
    refresh,
    approve,
    reject,
    cancel,
    runAgent,
  }
}
