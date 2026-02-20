import { useState, useMemo, useCallback } from "react"
import {
  DndContext,
  DragOverlay,
  type DragStartEvent,
  type DragOverEvent,
  type DragEndEvent,
  PointerSensor,
  useSensor,
  useSensors,
  closestCenter,
} from "@dnd-kit/core"
import { Badge } from "@/components/ui/badge"
import type { Delivery, Phase } from "@/types"
import { STATUS_CLASSES } from "@/utils/badge-styles"
import { formatRelativeTime } from "@/utils/format"
import { PHASES, getDropAction } from "@/utils/kanban-rules"
import { apiPost } from "@/utils/api"
import { KanbanColumn } from "./column"
import { DetailSheet } from "./detail-sheet"
import { RejectDialog } from "./reject-dialog"

interface KanbanBoardProps {
  deliveries: Delivery[]
  onRefresh: () => void
}

export function KanbanBoard({ deliveries, onRefresh }: KanbanBoardProps) {
  const [activeDelivery, setActiveDelivery] = useState<Delivery | null>(null)
  const [overPhase, setOverPhase] = useState<Phase | null>(null)
  const [selectedId, setSelectedId] = useState<string | null>(null)
  const [rejectTarget, setRejectTarget] = useState<Delivery | null>(null)

  const sensors = useSensors(
    useSensor(PointerSensor, { activationConstraint: { distance: 8 } }),
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

  const dropAction = useMemo(() => {
    if (!activeDelivery || !overPhase) return null
    return getDropAction(activeDelivery.phase, activeDelivery.run_status, overPhase)
  }, [activeDelivery, overPhase])

  function handleDragStart(event: DragStartEvent) {
    const delivery = event.active.data.current?.delivery as Delivery | undefined
    if (delivery) setActiveDelivery(delivery)
  }

  function handleDragOver(event: DragOverEvent) {
    const overId = event.over?.id as Phase | undefined
    if (overId && PHASES.includes(overId)) {
      setOverPhase(overId)
    } else {
      setOverPhase(null)
    }
  }

  const handleDragEnd = useCallback(
    async (event: DragEndEvent) => {
      const delivery = activeDelivery
      const targetPhase = event.over?.id as Phase | undefined

      setActiveDelivery(null)
      setOverPhase(null)

      if (!delivery || !targetPhase) return
      if (delivery.phase === targetPhase) return

      const action = getDropAction(delivery.phase, delivery.run_status, targetPhase)
      if (!action) return

      if (action.type === "reject") {
        setRejectTarget(delivery)
        return
      }

      // approve
      await apiPost(`/deliveries/${delivery.id}/approve`)
      onRefresh()
    },
    [activeDelivery, onRefresh],
  )

  async function handleRejectConfirm(reason: string) {
    if (!rejectTarget) return
    await apiPost(`/deliveries/${rejectTarget.id}/reject`, { reason })
    setRejectTarget(null)
    onRefresh()
  }

  return (
    <>
      <DndContext
        sensors={sensors}
        collisionDetection={closestCenter}
        onDragStart={handleDragStart}
        onDragOver={handleDragOver}
        onDragEnd={handleDragEnd}
      >
        <div className="flex gap-3 overflow-x-auto pb-4">
          {PHASES.map((phase) => (
            <KanbanColumn
              key={phase}
              phase={phase}
              deliveries={columns[phase]}
              onCardClick={(d) => setSelectedId(d.id)}
              isDropTarget={overPhase === phase}
              isInvalidDrop={overPhase === phase && !dropAction}
            />
          ))}
        </div>

        <DragOverlay>
          {activeDelivery && (
            <div className="w-64 rounded-lg border bg-card p-3 shadow-lg space-y-2">
              <p className="text-sm font-medium line-clamp-2">
                {activeDelivery.summary}
              </p>
              <div className="flex items-center justify-between gap-2">
                <Badge
                  variant="secondary"
                  className={`text-xs ${STATUS_CLASSES[activeDelivery.run_status]}`}
                >
                  {activeDelivery.run_status}
                </Badge>
                <span className="text-xs text-muted-foreground truncate">
                  {activeDelivery.repository}
                </span>
              </div>
              <p className="text-xs text-muted-foreground">
                {formatRelativeTime(activeDelivery.updated_at)}
              </p>
            </div>
          )}
        </DragOverlay>
      </DndContext>

      <DetailSheet
        deliveryId={selectedId}
        onOpenChange={(open) => {
          if (!open) setSelectedId(null)
        }}
        onActionComplete={onRefresh}
      />

      <RejectDialog
        open={!!rejectTarget}
        onOpenChange={(open) => {
          if (!open) setRejectTarget(null)
        }}
        onConfirm={handleRejectConfirm}
      />
    </>
  )
}
