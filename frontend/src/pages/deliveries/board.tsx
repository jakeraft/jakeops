import { useMemo } from "react"
import { useDeliveries } from "@/hooks/use-deliveries"
import { KanbanBoard } from "@/components/kanban/board"
import { isTerminal } from "@/utils/kanban-rules"

export function DeliveryBoard() {
  const { deliveries, loading, error } = useDeliveries()

  const active = useMemo(
    () => deliveries.filter((d) => !isTerminal(d.phase, d.run_status)),
    [deliveries],
  )

  if (loading) {
    return <p className="p-4 text-muted-foreground">Loading...</p>
  }

  if (error) {
    return <p className="p-4 text-destructive">Error: {error}</p>
  }

  return <KanbanBoard deliveries={active} showClosedPlaceholder />
}
