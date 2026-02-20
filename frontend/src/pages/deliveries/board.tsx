import { useDeliveries } from "@/hooks/use-deliveries"
import { KanbanBoard } from "@/components/kanban/board"

export function DeliveryBoard() {
  const { deliveries, loading, error, refresh } = useDeliveries()

  if (loading) {
    return <p className="p-4 text-muted-foreground">Loading...</p>
  }

  if (error) {
    return <p className="p-4 text-destructive">Error: {error}</p>
  }

  return <KanbanBoard deliveries={deliveries} onRefresh={refresh} />
}
