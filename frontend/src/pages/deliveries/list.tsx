import { Link } from "react-router"
import { Badge } from "@/components/ui/badge"
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table"
import { useDeliveries } from "@/hooks/use-deliveries"
import type { Phase, RunStatus } from "@/types"
import { formatRelativeTime } from "@/utils/format"

const PHASE_CLASSES: Record<Phase, string> = {
  intake: "bg-slate-100 text-slate-700",
  plan: "bg-blue-100 text-blue-700",
  implement: "bg-violet-100 text-violet-700",
  review: "bg-amber-100 text-amber-700",
  verify: "bg-cyan-100 text-cyan-700",
  deploy: "bg-green-100 text-green-700",
  observe: "bg-emerald-100 text-emerald-700",
  close: "bg-gray-100 text-gray-500",
}

const STATUS_CLASSES: Record<RunStatus, string> = {
  pending: "bg-gray-100 text-gray-700",
  running: "bg-blue-100 text-blue-700",
  succeeded: "bg-green-100 text-green-700",
  failed: "bg-red-100 text-red-700",
  blocked: "bg-yellow-100 text-yellow-700",
  canceled: "bg-gray-100 text-gray-500",
}

export function DeliveryList() {
  const { deliveries, loading, error } = useDeliveries()

  if (loading) {
    return <p className="p-4 text-muted-foreground">Loading...</p>
  }

  if (error) {
    return <p className="p-4 text-destructive">Error: {error}</p>
  }

  if (deliveries.length === 0) {
    return <p className="p-4 text-muted-foreground">No deliveries yet.</p>
  }

  return (
    <Table>
      <TableHeader>
        <TableRow>
          <TableHead>Summary</TableHead>
          <TableHead>Phase</TableHead>
          <TableHead>Status</TableHead>
          <TableHead>Repository</TableHead>
          <TableHead>Updated</TableHead>
        </TableRow>
      </TableHeader>
      <TableBody>
        {deliveries.map((d) => (
          <TableRow key={d.id}>
            <TableCell>
              <Link
                to={`/deliveries/${d.id}`}
                className="font-medium underline-offset-4 hover:underline"
              >
                {d.summary}
              </Link>
            </TableCell>
            <TableCell>
              <Badge variant="secondary" className={PHASE_CLASSES[d.phase]}>
                {d.phase}
              </Badge>
            </TableCell>
            <TableCell>
              <Badge
                variant="secondary"
                className={STATUS_CLASSES[d.run_status]}
              >
                {d.run_status}
              </Badge>
            </TableCell>
            <TableCell className="text-muted-foreground">
              {d.repository}
            </TableCell>
            <TableCell className="text-muted-foreground">
              {formatRelativeTime(d.updated_at)}
            </TableCell>
          </TableRow>
        ))}
      </TableBody>
    </Table>
  )
}
