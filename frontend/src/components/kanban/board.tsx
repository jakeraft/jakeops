import { useMemo } from "react"
import { useNavigate } from "react-router"
import type { Delivery, Phase } from "@/types"
import { PHASES } from "@/utils/kanban-rules"
import { KanbanColumn } from "./column"

const CI_PHASES = PHASES.slice(0, 4) // intake, plan, implement, review
const CD_PHASES = PHASES.slice(4)    // verify, deploy, observe, close

interface KanbanBoardProps {
  deliveries: Delivery[]
}

export function KanbanBoard({ deliveries }: KanbanBoardProps) {
  const navigate = useNavigate()

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

  const handleCardClick = (d: Delivery) => navigate(`/deliveries/${d.id}`)

  return (
    <div className="space-y-4">
      <div>
        <h2 className="mb-2 text-xs font-semibold uppercase tracking-wide text-muted-foreground">CI</h2>
        <div className="grid grid-cols-4 gap-3">
          {CI_PHASES.map((phase) => (
            <KanbanColumn
              key={phase}
              phase={phase}
              deliveries={columns[phase]}
              onCardClick={handleCardClick}
            />
          ))}
        </div>
      </div>
      <div>
        <h2 className="mb-2 text-xs font-semibold uppercase tracking-wide text-muted-foreground">CD</h2>
        <div className="grid grid-cols-4 gap-3">
          {CD_PHASES.map((phase) => (
            <KanbanColumn
              key={phase}
              phase={phase}
              deliveries={columns[phase]}
              onCardClick={handleCardClick}
            />
          ))}
        </div>
      </div>
    </div>
  )
}
