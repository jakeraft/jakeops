import { Link } from "react-router"
import { Badge } from "@/components/ui/badge"
import { Button } from "@/components/ui/button"
import { Separator } from "@/components/ui/separator"
import {
  Sheet,
  SheetContent,
  SheetHeader,
  SheetTitle,
} from "@/components/ui/sheet"
import { useDelivery } from "@/hooks/use-delivery"
import { PHASE_CLASSES, STATUS_CLASSES } from "@/utils/badge-styles"
import { formatRelativeTime } from "@/utils/format"
import { RejectDialog } from "./reject-dialog"
import { useState } from "react"
import type { Phase, RunStatus } from "@/types"

const GATE_PHASES: Phase[] = ["plan", "review", "deploy"]

function isTerminal(phase: Phase, runStatus: RunStatus): boolean {
  return (
    (phase === "close" && runStatus === "succeeded") ||
    runStatus === "canceled"
  )
}

interface DetailSheetProps {
  deliveryId: string | null
  onOpenChange: (open: boolean) => void
  onActionComplete: () => void
}

export function DetailSheet({
  deliveryId,
  onOpenChange,
  onActionComplete,
}: DetailSheetProps) {
  const {
    delivery,
    loading,
    approve,
    reject,
    retry,
    cancel,
    generatePlan,
    actionError,
    clearActionError,
  } = useDelivery(deliveryId ?? undefined)
  const [rejectOpen, setRejectOpen] = useState(false)

  async function handleAction(action: () => Promise<unknown>) {
    await action()
    onActionComplete()
  }

  return (
    <Sheet open={!!deliveryId} onOpenChange={onOpenChange}>
      <SheetContent className="overflow-y-auto">
        {loading && (
          <p className="p-4 text-muted-foreground">Loading...</p>
        )}
        {delivery && (
          <>
            <SheetHeader>
              <SheetTitle>{delivery.summary}</SheetTitle>
            </SheetHeader>
            <div className="mt-4 space-y-4">
              <div className="flex items-center gap-2">
                <Badge variant="secondary" className={PHASE_CLASSES[delivery.phase]}>
                  {delivery.phase}
                </Badge>
                <Badge variant="secondary" className={STATUS_CLASSES[delivery.run_status]}>
                  {delivery.run_status}
                </Badge>
              </div>

              <div className="space-y-1 text-sm">
                <p className="text-muted-foreground">{delivery.repository}</p>
                <p className="text-muted-foreground">
                  Updated {formatRelativeTime(delivery.updated_at)}
                </p>
              </div>

              {delivery.refs.length > 0 && (
                <>
                  <Separator />
                  <div className="space-y-1">
                    <p className="text-sm font-medium">References</p>
                    {delivery.refs.map((ref, i) => (
                      <div key={i} className="flex items-center gap-1.5 text-sm">
                        <Badge variant="outline" className="text-xs">{ref.role}</Badge>
                        {ref.url ? (
                          <a
                            href={ref.url}
                            target="_blank"
                            rel="noopener noreferrer"
                            className="text-blue-600 underline-offset-4 hover:underline"
                          >
                            {ref.label}
                          </a>
                        ) : (
                          <span>{ref.label}</span>
                        )}
                      </div>
                    ))}
                  </div>
                </>
              )}

              {actionError && (
                <div className="flex items-center justify-between rounded-md border border-red-200 bg-red-50 p-2 text-sm text-red-800">
                  <span>{actionError}</span>
                  <Button
                    variant="ghost"
                    size="sm"
                    onClick={clearActionError}
                    className="h-auto p-1"
                  >
                    Dismiss
                  </Button>
                </div>
              )}

              <Separator />

              {/* Action Buttons */}
              <div className="flex flex-wrap gap-2">
                {GATE_PHASES.includes(delivery.phase) &&
                  delivery.run_status === "succeeded" && (
                    <>
                      <Button size="sm" onClick={() => handleAction(approve)}>
                        Approve
                      </Button>
                      <Button
                        size="sm"
                        variant="outline"
                        onClick={() => setRejectOpen(true)}
                      >
                        Reject
                      </Button>
                    </>
                  )}
                {delivery.run_status === "failed" && (
                  <Button
                    size="sm"
                    variant="outline"
                    onClick={() => handleAction(retry)}
                  >
                    Retry
                  </Button>
                )}
                {delivery.phase === "intake" && (
                  <Button
                    size="sm"
                    variant="outline"
                    onClick={() => handleAction(generatePlan)}
                  >
                    Generate Plan
                  </Button>
                )}
                {!isTerminal(delivery.phase, delivery.run_status) && (
                  <Button
                    size="sm"
                    variant="destructive"
                    onClick={() => handleAction(cancel)}
                  >
                    Cancel
                  </Button>
                )}
              </div>

              <Separator />

              <Link
                to={`/deliveries/${delivery.id}`}
                className="block text-sm text-blue-600 underline-offset-4 hover:underline"
              >
                View Full Details
              </Link>
            </div>

            <RejectDialog
              open={rejectOpen}
              onOpenChange={setRejectOpen}
              onConfirm={async (reason) => {
                await handleAction(() => reject(reason))
                setRejectOpen(false)
              }}
            />
          </>
        )}
      </SheetContent>
    </Sheet>
  )
}
