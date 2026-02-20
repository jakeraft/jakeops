import { useState, useMemo } from "react"
import type { Delivery, Phase } from "@/types"
import { PHASES } from "@/utils/kanban-rules"
import { KanbanColumn } from "./column"
import { DetailSheet } from "./detail-sheet"

interface KanbanBoardProps {
  deliveries: Delivery[]
  onRefresh: () => void
}

export function KanbanBoard({ deliveries, onRefresh }: KanbanBoardProps) {
  const [selectedId, setSelectedId] = useState<string | null>(null)

  const columns = useMemo(() => {
    const grouped: Record<Phase, Delivery[]> = {} as Record<Phase, Delivery[]>
    for (const phase of PHASES) {
      grouped[phase] = []
    }
    for (const d of deliveries) {
      grouped[d.phase].push(d)
    }
    return grouped
  }, [deliveries])

  return (
    <>
      <div className="flex gap-3 overflow-x-auto pb-4">
        {PHASES.map((phase) => (
          <KanbanColumn
            key={phase}
            phase={phase}
            deliveries={columns[phase]}
            onCardClick={(d) => setSelectedId(d.id)}
          />
        ))}
      </div>

      <DetailSheet
        deliveryId={selectedId}
        onOpenChange={(open) => {
          if (!open) setSelectedId(null)
        }}
        onActionComplete={onRefresh}
      />
    </>
  )
}
