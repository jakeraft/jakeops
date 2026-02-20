import { useMemo } from "react"
import { Skeleton } from "@/components/ui/skeleton"
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
    return (
      <div className="flex gap-4 p-4">
        {Array.from({ length: 5 }).map((_, i) => (
          <div key={i} className="flex-1 space-y-3">
            <Skeleton className="h-6 w-24" />
            <Skeleton className="h-24 w-full" />
            <Skeleton className="h-24 w-full" />
          </div>
        ))}
      </div>
    )
  }

  if (error) {
    return <p className="p-4 text-destructive">Error: {error}</p>
  }

  return <KanbanBoard deliveries={active} showClosedPlaceholder />
}
