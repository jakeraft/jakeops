import { useMemo } from "react"
import { useNavigate } from "react-router"
import { Badge } from "@/components/ui/badge"
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table"
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs"
import { useDeliveries } from "@/hooks/use-deliveries"
import type { Delivery } from "@/types"
import { PHASE_CLASSES, STATUS_CLASSES } from "@/utils/badge-styles"
import { formatRelativeTime } from "@/utils/format"
import { isTerminal } from "@/utils/kanban-rules"

function DeliveryTable({ deliveries }: { deliveries: Delivery[] }) {
  const navigate = useNavigate()

  if (deliveries.length === 0) {
    return <p className="p-4 text-muted-foreground">No deliveries.</p>
  }

  return (
    <Table>
      <TableHeader>
        <TableRow>
          <TableHead className="w-12">#</TableHead>
          <TableHead>Summary</TableHead>
          <TableHead>Phase</TableHead>
          <TableHead>Status</TableHead>
          <TableHead>Repository</TableHead>
          <TableHead>Updated</TableHead>
        </TableRow>
      </TableHeader>
      <TableBody>
        {deliveries.map((d) => (
          <TableRow
            key={d.id}
            className="cursor-pointer"
            onClick={() => navigate(`/deliveries/${d.id}`)}
          >
            <TableCell className="text-muted-foreground">#{d.seq}</TableCell>
            <TableCell className="font-medium">{d.summary}</TableCell>
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

export function DeliveryList() {
  const { deliveries, loading, error } = useDeliveries()

  const { active, closed } = useMemo(() => {
    const active: Delivery[] = []
    const closed: Delivery[] = []
    for (const d of deliveries) {
      if (isTerminal(d.phase, d.run_status)) {
        closed.push(d)
      } else {
        active.push(d)
      }
    }
    return { active, closed }
  }, [deliveries])

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
    <Tabs defaultValue="active">
      <TabsList>
        <TabsTrigger value="active">Active ({active.length})</TabsTrigger>
        <TabsTrigger value="closed">Closed ({closed.length})</TabsTrigger>
      </TabsList>
      <TabsContent value="active">
        <DeliveryTable deliveries={active} />
      </TabsContent>
      <TabsContent value="closed">
        <DeliveryTable deliveries={closed} />
      </TabsContent>
    </Tabs>
  )
}
