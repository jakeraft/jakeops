import { useSortable } from "@dnd-kit/sortable"
import { CSS } from "@dnd-kit/utilities"
import { Badge } from "@/components/ui/badge"
import type { Delivery } from "@/types"
import { STATUS_CLASSES } from "@/utils/badge-styles"
import { formatRelativeTime } from "@/utils/format"

interface KanbanCardProps {
  delivery: Delivery
  onClick: (delivery: Delivery) => void
}

export function KanbanCard({ delivery, onClick }: KanbanCardProps) {
  const {
    attributes,
    listeners,
    setNodeRef,
    transform,
    transition,
    isDragging,
  } = useSortable({ id: delivery.id, data: { delivery } })

  const style = {
    transform: CSS.Transform.toString(transform),
    transition,
  }

  return (
    <div
      ref={setNodeRef}
      style={style}
      {...attributes}
      {...listeners}
      className={`rounded-lg border bg-card p-3 shadow-sm cursor-grab active:cursor-grabbing space-y-2 ${
        isDragging ? "opacity-50" : ""
      }`}
      onClick={(e) => {
        if (!isDragging) {
          e.stopPropagation()
          onClick(delivery)
        }
      }}
    >
      <p className="text-sm font-medium line-clamp-2">{delivery.summary}</p>
      <div className="flex items-center justify-between gap-2">
        <Badge variant="secondary" className={`text-xs ${STATUS_CLASSES[delivery.run_status]}`}>
          {delivery.run_status}
        </Badge>
        <span className="text-xs text-muted-foreground truncate">
          {delivery.repository}
        </span>
      </div>
      <p className="text-xs text-muted-foreground">
        {formatRelativeTime(delivery.updated_at)}
      </p>
    </div>
  )
}
