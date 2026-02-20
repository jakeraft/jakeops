import { Badge } from "@/components/ui/badge"
import type { Delivery, Phase } from "@/types"
import { PHASE_CLASSES } from "@/utils/badge-styles"
import { KanbanCard } from "./card"

interface KanbanColumnProps {
  phase: Phase
  deliveries: Delivery[]
  onCardClick: (delivery: Delivery) => void
}

export function KanbanColumn({
  phase,
  deliveries,
  onCardClick,
}: KanbanColumnProps) {
  return (
    <div className="flex w-64 shrink-0 flex-col rounded-lg border">
      <div className="flex items-center justify-between p-3 pb-2">
        <Badge variant="secondary" className={PHASE_CLASSES[phase]}>
          {phase}
        </Badge>
        <span className="text-xs text-muted-foreground">
          {deliveries.length}
        </span>
      </div>
      <div className="flex-1 space-y-2 overflow-y-auto p-2 pt-0">
        {deliveries.map((delivery) => (
          <KanbanCard
            key={delivery.id}
            delivery={delivery}
            onClick={onCardClick}
          />
        ))}
      </div>
    </div>
  )
}
