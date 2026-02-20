import { Badge } from "@/components/ui/badge"
import { StableText } from "@/components/stable-text"
import type { RunStatus } from "@/types"
import { STATUS_CLASSES } from "@/utils/badge-styles"

const STATUS_CANDIDATES = Object.keys(STATUS_CLASSES)

export function RunStatusBadge({ status }: { status: RunStatus }) {
  return (
    <Badge variant="secondary" className={STATUS_CLASSES[status]}>
      <StableText candidates={STATUS_CANDIDATES}>{status}</StableText>
    </Badge>
  )
}
