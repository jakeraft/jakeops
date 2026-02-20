import { useMemo } from "react"
import { useNavigate } from "react-router"
import type { Delivery, Phase } from "@/types"
import { PHASES } from "@/utils/kanban-rules"
import { KanbanColumn } from "./column"

interface KanbanBoardProps {
  deliveries: Delivery[]
  excludePhases?: Phase[]
}

export function KanbanBoard({ deliveries, excludePhases = [] }: KanbanBoardProps) {
  const navigate = useNavigate()

  const visiblePhases = useMemo(
    () => PHASES.filter((p) => !excludePhases.includes(p)),
    [excludePhases],
  )

  const ciPhases = visiblePhases.filter((p) =>
    ["intake", "plan", "implement", "review"].includes(p),
  )
  const cdPhases = visiblePhases.filter((p) =>
    ["verify", "deploy", "observe", "close"].includes(p),
  )

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
      {ciPhases.length > 0 && (
        <div>
          <h2 className="mb-2 text-xs font-semibold uppercase tracking-wide text-muted-foreground">CI</h2>
          <div className="grid gap-3" style={{ gridTemplateColumns: `repeat(${ciPhases.length}, minmax(0, 1fr))` }}>
            {ciPhases.map((phase) => (
              <KanbanColumn
                key={phase}
                phase={phase}
                deliveries={columns[phase]}
                onCardClick={handleCardClick}
              />
            ))}
          </div>
        </div>
      )}
      {cdPhases.length > 0 && (
        <div>
          <h2 className="mb-2 text-xs font-semibold uppercase tracking-wide text-muted-foreground">CD</h2>
          <div className="grid gap-3" style={{ gridTemplateColumns: `repeat(${cdPhases.length}, minmax(0, 1fr))` }}>
            {cdPhases.map((phase) => (
              <KanbanColumn
                key={phase}
                phase={phase}
                deliveries={columns[phase]}
                onCardClick={handleCardClick}
              />
            ))}
          </div>
        </div>
      )}
    </div>
  )
}
