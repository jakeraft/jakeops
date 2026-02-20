import { useCallback, useEffect, useState } from "react"
import type { Delivery } from "@/types"
import { apiFetch, apiPost } from "@/utils/api"

export function useDelivery(id: string | undefined) {
  const [delivery, setDelivery] = useState<Delivery | null>(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [actionError, setActionError] = useState<string | null>(null)

  const refresh = useCallback(async () => {
    if (!id) return
    setLoading(true)
    setError(null)
    try {
      const data = await apiFetch<Delivery>(`/deliveries/${id}`)
      setDelivery(data)
    } catch (e) {
      setError(e instanceof Error ? e.message : "Unknown error")
    } finally {
      setLoading(false)
    }
  }, [id])

  useEffect(() => {
    refresh()
  }, [refresh])

  const performAction = useCallback(
    async (action: () => Promise<unknown>) => {
      setActionError(null)
      try {
        await action()
        await refresh()
      } catch (e) {
        const message = e instanceof Error ? e.message : "Unknown error"
        setActionError(message)
        throw e
      }
    },
    [refresh],
  )

  const approve = useCallback(
    () => performAction(() => apiPost(`/deliveries/${id}/approve`)),
    [id, performAction],
  )

  const reject = useCallback(
    (reason: string) =>
      performAction(() => apiPost(`/deliveries/${id}/reject`, { reason })),
    [id, performAction],
  )

  const retry = useCallback(
    () => performAction(() => apiPost(`/deliveries/${id}/retry`)),
    [id, performAction],
  )

  const cancel = useCallback(
    () => performAction(() => apiPost(`/deliveries/${id}/cancel`)),
    [id, performAction],
  )

  const generatePlan = useCallback(
    () => performAction(() => apiPost(`/deliveries/${id}/generate-plan`)),
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
    retry,
    cancel,
    generatePlan,
  }
}
