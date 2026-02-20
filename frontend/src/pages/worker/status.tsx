import { Badge } from "@/components/ui/badge"
import { Button } from "@/components/ui/button"
import {
  Card,
  CardContent,
  CardHeader,
  CardTitle,
} from "@/components/ui/card"
import { useWorker } from "@/hooks/use-worker"
import type { WorkerStatus } from "@/types"
import { formatRelativeTime } from "@/utils/format"

function workerBorderClass(worker: WorkerStatus): string {
  if (worker.last_error) return "border-red-200"
  if (worker.enabled) return "border-green-200"
  return "border-gray-200"
}

function WorkerCard({ worker }: { worker: WorkerStatus }) {
  return (
    <Card className={workerBorderClass(worker)}>
      <CardHeader>
        <div className="flex items-center justify-between">
          <CardTitle>{worker.label}</CardTitle>
          <Badge
            variant={worker.enabled ? "default" : "secondary"}
            className={worker.enabled ? "bg-green-600" : ""}
          >
            {worker.enabled ? "enabled" : "disabled"}
          </Badge>
        </div>
      </CardHeader>
      <CardContent className="space-y-2 text-sm">
        <div>
          <span className="text-muted-foreground">Interval:</span>{" "}
          {worker.interval_sec}s
        </div>
        <div>
          <span className="text-muted-foreground">Last poll:</span>{" "}
          {worker.last_poll_at
            ? formatRelativeTime(worker.last_poll_at)
            : "never"}
        </div>
        {worker.last_result && (
          <div>
            <span className="text-muted-foreground">Last result:</span>
            <pre className="mt-1 rounded bg-muted p-2 text-sm">
              {JSON.stringify(worker.last_result, null, 2)}
            </pre>
          </div>
        )}
        {worker.last_error && (
          <div className="text-red-600">
            <span className="font-medium">Error:</span> {worker.last_error}
          </div>
        )}
      </CardContent>
    </Card>
  )
}

export function WorkerStatusPage() {
  const { workers, loading, error, refresh } = useWorker()

  if (loading) {
    return <p className="p-4 text-muted-foreground">Loading...</p>
  }

  if (error) {
    return <p className="p-4 text-destructive">Error: {error}</p>
  }

  return (
    <div className="space-y-4">
      <div className="flex items-center justify-between">
        <h1 className="text-2xl font-semibold">Worker Status</h1>
        <Button variant="outline" onClick={refresh}>
          Refresh
        </Button>
      </div>

      {workers.length === 0 ? (
        <p className="text-muted-foreground">No workers registered.</p>
      ) : (
        <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-3">
          {workers.map((w) => (
            <WorkerCard key={w.name} worker={w} />
          ))}
        </div>
      )}
    </div>
  )
}
