import { useEffect, useRef, useState } from "react"

export interface StreamEvent {
  type: string
  subtype?: string
  parent_tool_use_id?: string
  message?: Record<string, unknown>
  session_id?: string
}

export function useEventStream(deliveryId: string, active: boolean) {
  const [events, setEvents] = useState<StreamEvent[]>([])
  const [done, setDone] = useState(false)
  const esRef = useRef<EventSource | null>(null)
  const eventsRef = useRef<StreamEvent[]>([])

  useEffect(() => {
    if (!active) {
      return
    }

    // Reset accumulated state via refs (avoids synchronous setState in effect)
    eventsRef.current = []
    const es = new EventSource(`/api/deliveries/${deliveryId}/stream`)
    esRef.current = es

    es.onmessage = (event) => {
      try {
        const data = JSON.parse(event.data) as StreamEvent
        eventsRef.current = [...eventsRef.current, data]
        setEvents(eventsRef.current)
      } catch {
        // skip malformed events
      }
    }

    const handleDone = () => {
      setDone(true)
      es.close()
    }

    es.addEventListener("done", handleDone)

    es.onerror = () => {
      es.close()
      setDone(true)
    }

    return () => {
      es.removeEventListener("done", handleDone)
      es.close()
      esRef.current = null
      setEvents([])
      setDone(false)
    }
  }, [deliveryId, active])

  return { events, done }
}
