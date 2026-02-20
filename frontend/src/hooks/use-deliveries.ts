import { useCallback, useEffect, useState } from "react"
import type { Delivery } from "@/types"
import { apiFetch } from "@/utils/api"
import { logger } from "@/utils/logger"

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
      const message = e instanceof Error ? e.message : "Unknown error"
      logger.error("Failed to fetch deliveries", { error: message })
      setError(message)
    } finally {
      setLoading(false)
    }
  }, [])

  useEffect(() => {
    refresh()
  }, [refresh])

  return { deliveries, loading, error, refresh }
}
