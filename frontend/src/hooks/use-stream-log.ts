import { useCallback, useEffect, useState } from "react"
import { apiFetch } from "@/utils/api"
import type { StreamEvent } from "@/hooks/use-event-stream"

export interface AgentBucket {
  id: string
  label: string
}

export interface StreamLog {
  run_id: string
  started_at: string
  completed_at: string
  events: StreamEvent[]
  agent_buckets?: AgentBucket[]
}

export function useStreamLog(deliveryId: string, runId: string | null) {
  const [log, setLog] = useState<StreamLog | null>(null)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)

  const refresh = useCallback(async () => {
    if (!runId) {
      setLog(null)
      return
    }
    setLoading(true)
    setError(null)
    setLog(null)
    try {
      const data = await apiFetch<StreamLog>(
        `/deliveries/${deliveryId}/runs/${runId}/stream_log`,
      )
      setLog(data)
    } catch (e) {
      setError(e instanceof Error ? e.message : "Unknown error")
    } finally {
      setLoading(false)
    }
  }, [deliveryId, runId])

  useEffect(() => {
    refresh()
  }, [refresh])

  return { log, loading, error, refresh }
}
