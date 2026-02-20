import { useState } from "react"
import { Badge } from "@/components/ui/badge"
import { Button } from "@/components/ui/button"
import { Checkbox } from "@/components/ui/checkbox"
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
  DialogTrigger,
} from "@/components/ui/dialog"
import { Input } from "@/components/ui/input"
import { Label } from "@/components/ui/label"
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select"
import { Switch } from "@/components/ui/switch"
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table"
import { useSources } from "@/hooks/use-sources"
import type { Phase, Source, SourceCreate, SourceUpdate } from "@/types"
import { PHASE_CLASSES } from "@/utils/badge-styles"
import { formatRelativeTime } from "@/utils/format"
import { PHASES } from "@/utils/kanban-rules"

// --- Add Source Dialog ---

function AddSourceDialog({
  onSubmit,
}: {
  onSubmit: (body: SourceCreate) => Promise<void>
}) {
  const [open, setOpen] = useState(false)
  const [owner, setOwner] = useState("")
  const [repo, setRepo] = useState("")
  const [token, setToken] = useState("")
  const [endpoint, setEndpoint] = useState("deploy")
  const [checkpoints, setCheckpoints] = useState<string[]>(["plan", "implement", "review"])
  const [submitting, setSubmitting] = useState(false)

  function reset() {
    setOwner("")
    setRepo("")
    setToken("")
    setEndpoint("deploy")
    setCheckpoints(["plan", "implement", "review"])
  }

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault()
    setSubmitting(true)
    try {
      await onSubmit({
        type: "github",
        owner,
        repo,
        token: token || undefined,
        endpoint: endpoint || undefined,
        checkpoints,
      })
      reset()
      setOpen(false)
    } finally {
      setSubmitting(false)
    }
  }

  return (
    <Dialog open={open} onOpenChange={setOpen}>
      <DialogTrigger asChild>
        <Button>Add Source</Button>
      </DialogTrigger>
      <DialogContent>
        <form onSubmit={handleSubmit}>
          <DialogHeader>
            <DialogTitle>Add Source</DialogTitle>
            <DialogDescription>
              Connect a GitHub repository as a delivery source.
            </DialogDescription>
          </DialogHeader>
          <div className="mt-4 grid gap-4">
            <div className="grid gap-2">
              <Label htmlFor="add-type">Type</Label>
              <Input id="add-type" value="github" disabled />
            </div>
            <div className="grid gap-2">
              <Label htmlFor="add-owner">Owner</Label>
              <Input
                id="add-owner"
                placeholder="e.g. acme"
                value={owner}
                onChange={(e) => setOwner(e.target.value)}
                required
              />
            </div>
            <div className="grid gap-2">
              <Label htmlFor="add-repo">Repo</Label>
              <Input
                id="add-repo"
                placeholder="e.g. backend"
                value={repo}
                onChange={(e) => setRepo(e.target.value)}
                required
              />
            </div>
            <div className="grid gap-2">
              <Label htmlFor="add-token">Token</Label>
              <Input
                id="add-token"
                type="password"
                placeholder="GitHub personal access token"
                value={token}
                onChange={(e) => setToken(e.target.value)}
              />
            </div>
            <div className="grid gap-2">
              <Label htmlFor="add-endpoint">Endpoint</Label>
              <Select value={endpoint} onValueChange={setEndpoint}>
                <SelectTrigger id="add-endpoint">
                  <SelectValue />
                </SelectTrigger>
                <SelectContent>
                  {PHASES.map((p) => (
                    <SelectItem key={p} value={p}>
                      {p}
                    </SelectItem>
                  ))}
                </SelectContent>
              </Select>
            </div>
            <div className="grid gap-2">
              <Label>Checkpoints</Label>
              <div className="grid grid-cols-2 gap-2">
                {PHASES.filter((p) => p !== "intake" && p !== "close").map(
                  (p) => (
                    <label
                      key={p}
                      className="flex items-center gap-2 text-sm"
                    >
                      <Checkbox
                        checked={checkpoints.includes(p)}
                        onCheckedChange={(checked) => {
                          setCheckpoints((prev) =>
                            checked
                              ? [...prev, p]
                              : prev.filter((c) => c !== p),
                          )
                        }}
                      />
                      {p}
                    </label>
                  ),
                )}
              </div>
            </div>
          </div>
          <DialogFooter className="mt-6">
            <Button type="submit" disabled={submitting}>
              {submitting ? "Creating..." : "Create"}
            </Button>
          </DialogFooter>
        </form>
      </DialogContent>
    </Dialog>
  )
}

// --- Edit Source Dialog ---

function EditSourceDialog({
  source,
  onSubmit,
}: {
  source: Source
  onSubmit: (id: string, body: SourceUpdate) => Promise<void>
}) {
  const [open, setOpen] = useState(false)
  const [token, setToken] = useState("")
  const [active, setActive] = useState(source.active)
  const [endpoint, setEndpoint] = useState(source.endpoint)
  const [checkpoints, setCheckpoints] = useState<string[]>(source.checkpoints)
  const [submitting, setSubmitting] = useState(false)

  function resetToSource() {
    setToken("")
    setActive(source.active)
    setEndpoint(source.endpoint)
    setCheckpoints(source.checkpoints)
  }

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault()
    setSubmitting(true)
    try {
      const body: SourceUpdate = {
        active,
        endpoint: endpoint,
        checkpoints,
      }
      if (token) {
        body.token = token
      }
      await onSubmit(source.id, body)
      setOpen(false)
    } finally {
      setSubmitting(false)
    }
  }

  return (
    <Dialog
      open={open}
      onOpenChange={(v) => {
        setOpen(v)
        if (v) resetToSource()
      }}
    >
      <DialogTrigger asChild>
        <Button variant="outline" size="sm" className="h-7 text-xs">
          Edit
        </Button>
      </DialogTrigger>
      <DialogContent>
        <form onSubmit={handleSubmit}>
          <DialogHeader>
            <DialogTitle>Edit Source</DialogTitle>
            <DialogDescription>
              Update settings for {source.owner}/{source.repo}.
            </DialogDescription>
          </DialogHeader>
          <div className="mt-4 grid gap-4">
            <div className="grid gap-2">
              <Label htmlFor={`edit-token-${source.id}`}>Token</Label>
              <Input
                id={`edit-token-${source.id}`}
                type="password"
                placeholder="Leave blank to keep current"
                value={token}
                onChange={(e) => setToken(e.target.value)}
              />
            </div>
            <div className="flex items-center gap-3">
              <Switch
                id={`edit-active-${source.id}`}
                checked={active}
                onCheckedChange={setActive}
              />
              <Label htmlFor={`edit-active-${source.id}`}>Active</Label>
            </div>
            <div className="grid gap-2">
              <Label htmlFor={`edit-endpoint-${source.id}`}>
                Endpoint
              </Label>
              <Select value={endpoint} onValueChange={setEndpoint}>
                <SelectTrigger id={`edit-endpoint-${source.id}`}>
                  <SelectValue />
                </SelectTrigger>
                <SelectContent>
                  {PHASES.map((p) => (
                    <SelectItem key={p} value={p}>
                      {p}
                    </SelectItem>
                  ))}
                </SelectContent>
              </Select>
            </div>
            <div className="grid gap-2">
              <Label>Checkpoints</Label>
              <div className="grid grid-cols-2 gap-2">
                {PHASES.filter((p) => p !== "intake" && p !== "close").map(
                  (p) => (
                    <label
                      key={p}
                      className="flex items-center gap-2 text-sm"
                    >
                      <Checkbox
                        checked={checkpoints.includes(p)}
                        onCheckedChange={(checked) => {
                          setCheckpoints((prev) =>
                            checked
                              ? [...prev, p]
                              : prev.filter((c) => c !== p),
                          )
                        }}
                      />
                      {p}
                    </label>
                  ),
                )}
              </div>
            </div>
          </div>
          <DialogFooter className="mt-6">
            <Button type="submit" disabled={submitting}>
              {submitting ? "Saving..." : "Save"}
            </Button>
          </DialogFooter>
        </form>
      </DialogContent>
    </Dialog>
  )
}

// --- Source List Page ---

export function SourceList() {
  const {
    sources,
    loading,
    error,
    createSource,
    updateSource,
    deleteSource,
    syncNow,
  } = useSources()
  const [syncing, setSyncing] = useState(false)

  async function handleSyncNow() {
    setSyncing(true)
    try {
      await syncNow()
    } finally {
      setSyncing(false)
    }
  }

  async function handleDelete(source: Source) {
    const confirmed = window.confirm(
      `Delete source ${source.owner}/${source.repo}? This cannot be undone.`,
    )
    if (!confirmed) return
    await deleteSource(source.id)
  }

  if (loading) {
    return <p className="p-4 text-muted-foreground">Loading...</p>
  }

  if (error) {
    return <p className="p-4 text-destructive">Error: {error}</p>
  }

  return (
    <div className="space-y-4">
      <div className="flex items-center justify-end">
        <div className="flex items-center gap-2">
          <Button
            variant="outline"
            onClick={handleSyncNow}
            disabled={syncing}
          >
            {syncing ? "Syncing..." : "Sync Now"}
          </Button>
          <AddSourceDialog onSubmit={createSource} />
        </div>
      </div>

      {sources.length === 0 ? (
        <p className="text-muted-foreground">
          No sources configured. Add a GitHub repository to get started.
        </p>
      ) : (
        <Table>
          <TableHeader>
            <TableRow>
              <TableHead className="w-12">#</TableHead>
              <TableHead>Source</TableHead>
              <TableHead>Type</TableHead>
              <TableHead>Active</TableHead>
              <TableHead>Endpoint</TableHead>
              <TableHead>Checkpoints</TableHead>
              <TableHead>Last Synced</TableHead>
              <TableHead className="text-right">Actions</TableHead>
            </TableRow>
          </TableHeader>
          <TableBody>
            {sources.map((s, i) => (
              <TableRow key={s.id}>
                <TableCell className="text-muted-foreground">{i + 1}</TableCell>
                <TableCell className="font-medium">
                  <a
                    href={`https://github.com/${s.owner}/${s.repo}`}
                    target="_blank"
                    rel="noopener noreferrer"
                    className="text-blue-600 underline-offset-4 hover:underline"
                  >
                    {s.owner}/{s.repo}
                  </a>
                </TableCell>
                <TableCell>{s.type}</TableCell>
                <TableCell>
                  <Badge variant={s.active ? "default" : "secondary"}>
                    {s.active ? "active" : "inactive"}
                  </Badge>
                </TableCell>
                <TableCell>{s.endpoint}</TableCell>
                <TableCell>
                  <div className="flex flex-wrap gap-1">
                    {s.checkpoints.map((cp) => (
                      <Badge
                        key={cp}
                        variant="secondary"
                        className={PHASE_CLASSES[cp as Phase]}
                      >
                        {cp}
                      </Badge>
                    ))}
                  </div>
                </TableCell>
                <TableCell className="text-muted-foreground">
                  {s.last_polled_at
                    ? formatRelativeTime(s.last_polled_at)
                    : "Never"}
                </TableCell>
                <TableCell className="text-right">
                  <div className="flex items-center justify-end gap-2">
                    <EditSourceDialog
                      source={s}
                      onSubmit={updateSource}
                    />
                    <Button
                      variant="destructive"
                      size="sm"
                      className="h-7 text-xs"
                      onClick={() => handleDelete(s)}
                    >
                      Delete
                    </Button>
                  </div>
                </TableCell>
              </TableRow>
            ))}
          </TableBody>
        </Table>
      )}
    </div>
  )
}
