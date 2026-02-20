import { Badge } from "@/components/ui/badge"
import { ScrollArea } from "@/components/ui/scroll-area"
import { StableText } from "@/components/stable-text"
import type { Delivery, Phase } from "@/types"
import { PHASE_CLASSES } from "@/utils/badge-styles"

const PHASE_CANDIDATES = Object.keys(PHASE_CLASSES)
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
    <div className="flex min-w-0 flex-col rounded-lg border">
      <div className="flex items-center justify-between p-3 pb-2">
        <Badge variant="colorized" className={PHASE_CLASSES[phase]}>
          <StableText candidates={PHASE_CANDIDATES}>{phase}</StableText>
        </Badge>
        <span className="text-xs text-muted-foreground">
          {deliveries.length}
        </span>
      </div>
      <ScrollArea className="flex-1">
        <div className="space-y-2 p-2 pt-0">
          {deliveries.map((delivery) => (
            <KanbanCard
              key={delivery.id}
              delivery={delivery}
              onClick={onCardClick}
            />
          ))}
        </div>
      </ScrollArea>
    </div>
  )
}
