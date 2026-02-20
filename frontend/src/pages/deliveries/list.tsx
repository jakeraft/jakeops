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
import { PHASE_CLASSES, STATUS_CLASSES } from "@/utils/badge-styles"
import { formatRelativeTime } from "@/utils/format"

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
