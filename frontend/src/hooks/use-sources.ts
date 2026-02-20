import { useCallback, useEffect, useState } from "react"
import type { Source, SourceCreate, SourceUpdate } from "@/types"
import { apiFetch, apiPost, apiPatch, apiDelete } from "@/utils/api"

export function useSources() {
  const [sources, setSources] = useState<Source[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)

  const refresh = useCallback(async () => {
    setLoading(true)
    setError(null)
    try {
      await apiPost("/sources/sync")
      const data = await apiFetch<Source[]>("/sources")
      setSources(data)
    } catch (e) {
      setError(e instanceof Error ? e.message : "Unknown error")
    } finally {
      setLoading(false)
    }
  }, [])

  useEffect(() => {
    refresh()
  }, [refresh])

  const createSource = useCallback(
    async (body: SourceCreate) => {
      await apiPost("/sources", body)
      await refresh()
    },
    [refresh],
  )

  const updateSource = useCallback(
    async (id: string, body: SourceUpdate) => {
      await apiPatch(`/sources/${id}`, body)
      await refresh()
    },
    [refresh],
  )

  const deleteSource = useCallback(
    async (id: string) => {
      await apiDelete(`/sources/${id}`)
      await refresh()
    },
    [refresh],
  )

  const syncNow = useCallback(async () => {
    await refresh()
  }, [refresh])

  return {
    sources,
    loading,
    error,
    refresh,
    createSource,
    updateSource,
    deleteSource,
    syncNow,
  }
}
