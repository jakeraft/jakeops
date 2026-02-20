import { useCallback, useEffect, useState } from "react"
import type { Delivery } from "@/types"
import { apiFetch, apiPost } from "@/utils/api"

export function useDelivery(id: string) {
  const [delivery, setDelivery] = useState<Delivery | null>(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)

  const refresh = useCallback(async () => {
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

  const approve = useCallback(async () => {
    await apiPost(`/deliveries/${id}/approve`)
    await refresh()
  }, [id, refresh])

  const reject = useCallback(async (reason: string) => {
    await apiPost(`/deliveries/${id}/reject`, { reason })
    await refresh()
  }, [id, refresh])

  const retry = useCallback(async () => {
    await apiPost(`/deliveries/${id}/retry`)
    await refresh()
  }, [id, refresh])

  const cancel = useCallback(async () => {
    await apiPost(`/deliveries/${id}/cancel`)
    await refresh()
  }, [id, refresh])

  const generatePlan = useCallback(async () => {
    await apiPost(`/deliveries/${id}/generate-plan`)
    await refresh()
  }, [id, refresh])

  return {
    delivery,
    loading,
    error,
    refresh,
    approve,
    reject,
    retry,
    cancel,
    generatePlan,
  }
}
