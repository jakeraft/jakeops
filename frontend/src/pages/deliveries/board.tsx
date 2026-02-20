import { useMemo } from "react"
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs"
import { useDeliveries } from "@/hooks/use-deliveries"
import { KanbanBoard } from "@/components/kanban/board"
import { isTerminal } from "@/utils/kanban-rules"
import type { Delivery } from "@/types"

export function DeliveryBoard() {
  const { deliveries, loading, error } = useDeliveries()

  const { active, closed } = useMemo(() => {
    const active: Delivery[] = []
    const closed: Delivery[] = []
    for (const d of deliveries) {
      if (isTerminal(d.phase, d.run_status)) {
        closed.push(d)
      } else {
        active.push(d)
      }
    }
    return { active, closed }
  }, [deliveries])

  if (loading) {
    return <p className="p-4 text-muted-foreground">Loading...</p>
  }

  if (error) {
    return <p className="p-4 text-destructive">Error: {error}</p>
  }

  return (
    <Tabs defaultValue="active">
      <TabsList>
        <TabsTrigger value="active">Active ({active.length})</TabsTrigger>
        <TabsTrigger value="closed">Closed ({closed.length})</TabsTrigger>
      </TabsList>
      <TabsContent value="active">
        <KanbanBoard deliveries={active} excludePhases={["close"]} />
      </TabsContent>
      <TabsContent value="closed">
        <KanbanBoard deliveries={closed} />
      </TabsContent>
    </Tabs>
  )
}
