import { Badge } from "@/components/ui/badge"
import type { RunStatus } from "@/types"
import { STATUS_CLASSES } from "@/utils/badge-styles"

export function RunStatusBadge({
  status,
  animate = false,
}: {
  status: RunStatus
  animate?: boolean
}) {
  return (
    <Badge variant="secondary" className={STATUS_CLASSES[status]}>
      {status === "running" && animate && (
        <span className="relative mr-1.5 flex size-2">
          <span className="absolute inline-flex size-full animate-ping rounded-full bg-blue-400 opacity-75" />
          <span className="relative inline-flex size-2 rounded-full bg-blue-500" />
        </span>
      )}
      {status}
    </Badge>
  )
}
