import { useCallback, useEffect, useState } from "react"
import type { Delivery } from "@/types"
import { apiFetch } from "@/utils/api"

export function useDeliveries() {
  const [deliveries, setDeliveries] = useState<Delivery[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)

  const refresh = useCallback(async () => {
    setLoading(true)
    setError(null)
    try {
      const data = await apiFetch<Delivery[]>("/deliveries")
      setDeliveries(data)
    } catch (e) {
      setError(e instanceof Error ? e.message : "Unknown error")
    } finally {
      setLoading(false)
    }
  }, [])

  useEffect(() => {
    refresh()
  }, [refresh])

  return { deliveries, loading, error, refresh }
}
