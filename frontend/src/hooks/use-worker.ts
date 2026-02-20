import { useCallback, useEffect, useState } from "react"
import type { WorkerStatus } from "@/types"
import { apiFetch } from "@/utils/api"

export function useWorker() {
  const [workers, setWorkers] = useState<WorkerStatus[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)

  const refresh = useCallback(async () => {
    setLoading(true)
    setError(null)
    try {
      const data = await apiFetch<{ workers: WorkerStatus[] }>("/worker/status")
      setWorkers(data.workers)
    } catch (e) {
      setError(e instanceof Error ? e.message : "Unknown error")
    } finally {
      setLoading(false)
    }
  }, [])

  useEffect(() => {
    refresh()
  }, [refresh])

  return { workers, loading, error, refresh }
}
