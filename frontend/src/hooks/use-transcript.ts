import { useCallback, useEffect, useState } from "react"
import type { TranscriptData } from "@/types"
import { apiFetch } from "@/utils/api"

export function useTranscript(deliveryId: string, runId: string) {
  const [transcript, setTranscript] = useState<TranscriptData | null>(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)

  const refresh = useCallback(async () => {
    setLoading(true)
    setError(null)
    try {
      const data = await apiFetch<TranscriptData>(
        `/deliveries/${deliveryId}/runs/${runId}/transcript`,
      )
      setTranscript(data)
    } catch (e) {
      setError(e instanceof Error ? e.message : "Unknown error")
    } finally {
      setLoading(false)
    }
  }, [deliveryId, runId])

  useEffect(() => {
    refresh()
  }, [refresh])

  return { transcript, loading, error, refresh }
}
