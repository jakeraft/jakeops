import { useMemo } from "react"
import { useNavigate } from "react-router"
import { Badge } from "@/components/ui/badge"
import type { Delivery, Phase } from "@/types"
import { PHASE_CLASSES } from "@/utils/badge-styles"
import { PHASES } from "@/utils/kanban-rules"
import { KanbanColumn } from "./column"

const CI_PHASES: Phase[] = ["intake", "plan", "implement", "review"]
const CD_PHASES: Phase[] = ["verify", "deploy", "observe", "close"]

interface KanbanBoardProps {
  deliveries: Delivery[]
  showClosedPlaceholder?: boolean
}

function ClosedPlaceholder({ onClick }: { onClick: () => void }) {
  return (
    <div
      className="flex min-w-0 cursor-pointer flex-col rounded-lg border bg-muted/50 opacity-60 transition-opacity hover:opacity-80"
      onClick={onClick}
    >
      <div className="flex items-center justify-between p-3 pb-2">
        <Badge variant="secondary" className={PHASE_CLASSES.close}>
          close
        </Badge>
      </div>
      <div className="flex flex-1 items-center justify-center p-4">
        <span className="text-xs text-muted-foreground">
          View in Deliveries
        </span>
      </div>
    </div>
  )
}

export function KanbanBoard({ deliveries, showClosedPlaceholder = false }: KanbanBoardProps) {
  const navigate = useNavigate()

  const cdPhases = showClosedPlaceholder
    ? CD_PHASES.filter((p) => p !== "close")
    : CD_PHASES

  const columns = useMemo(() => {
    const grouped = {} as Record<Phase, Delivery[]>
    for (const phase of PHASES) {
      grouped[phase] = []
    }
    for (const d of deliveries) {
      grouped[d.phase].push(d)
    }
    return grouped
  }, [deliveries])

  const handleCardClick = (d: Delivery) => navigate(`/deliveries/${d.id}`)

  const cdCount = cdPhases.length + (showClosedPlaceholder ? 1 : 0)

  return (
    <div className="space-y-4">
      <div>
        <h2 className="mb-2 text-xs font-semibold uppercase tracking-wide text-muted-foreground">CI</h2>
        <div className="grid gap-3" style={{ gridTemplateColumns: `repeat(${CI_PHASES.length}, minmax(0, 1fr))` }}>
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
        <div className="grid gap-3" style={{ gridTemplateColumns: `repeat(${cdCount}, minmax(0, 1fr))` }}>
          {cdPhases.map((phase) => (
            <KanbanColumn
              key={phase}
              phase={phase}
              deliveries={columns[phase]}
              onCardClick={handleCardClick}
            />
          ))}
          {showClosedPlaceholder && (
            <ClosedPlaceholder
              onClick={() => navigate("/deliveries?tab=closed")}
            />
          )}
        </div>
      </div>
    </div>
  )
}
