import { useState } from "react"
import { Plus } from "lucide-react"
import { Badge } from "@/components/ui/badge"
import { Button } from "@/components/ui/button"
import { Skeleton } from "@/components/ui/skeleton"
import { StableText } from "@/components/stable-text"
import { Checkbox } from "@/components/ui/checkbox"
import {
  AlertDialog,
  AlertDialogAction,
  AlertDialogCancel,
  AlertDialogContent,
  AlertDialogDescription,
  AlertDialogFooter,
  AlertDialogHeader,
  AlertDialogTitle,
} from "@/components/ui/alert-dialog"
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
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
import { PHASE_CLASSES, STATUS_CLASSES } from "@/utils/badge-styles"

const PHASE_CANDIDATES = Object.keys(PHASE_CLASSES)
import { formatRelativeTime } from "@/utils/format"
import { PHASES } from "@/utils/kanban-rules"

// --- Source Form Dialog (shared by Add / Edit) ---

function SourceFormDialog({
  source,
  open,
  onOpenChange,
  onCreate,
  onUpdate,
  onDelete,
}: {
  source: Source | null
  open: boolean
  onOpenChange: (open: boolean) => void
  onCreate: (body: SourceCreate) => Promise<void>
  onUpdate: (id: string, body: SourceUpdate) => Promise<void>
  onDelete: (source: Source) => Promise<void>
}) {
  const isEdit = !!source
  const [owner, setOwner] = useState(source?.owner ?? "")
  const [repo, setRepo] = useState(source?.repo ?? "")
  const [token, setToken] = useState("")
  const [active, setActive] = useState(source?.active ?? true)
  const [endpoint, setEndpoint] = useState(source?.endpoint ?? "deploy")
  const [checkpoints, setCheckpoints] = useState<string[]>(
    source?.checkpoints ?? ["plan", "implement", "review"],
  )
  const [submitting, setSubmitting] = useState(false)

  function reset() {
    setOwner(source?.owner ?? "")
    setRepo(source?.repo ?? "")
    setToken("")
    setActive(source?.active ?? true)
    setEndpoint(source?.endpoint ?? "deploy")
    setCheckpoints(source?.checkpoints ?? ["plan", "implement", "review"])
  }

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault()
    setSubmitting(true)
    try {
      if (isEdit) {
        const body: SourceUpdate = { active, endpoint, checkpoints }
        if (token) body.token = token
        await onUpdate(source.id, body)
      } else {
        await onCreate({
          type: "github",
          owner,
          repo,
          token: token || undefined,
          endpoint: endpoint || undefined,
          checkpoints,
        })
      }
      onOpenChange(false)
    } finally {
      setSubmitting(false)
    }
  }

  return (
    <Dialog open={open} onOpenChange={(v) => { onOpenChange(v); if (v) reset() }}>
      <DialogContent>
        <form onSubmit={handleSubmit}>
          <DialogHeader>
            <DialogTitle>{isEdit ? "Edit Source" : "Add Source"}</DialogTitle>
            <DialogDescription>
              {isEdit
                ? `Update settings for ${source.owner}/${source.repo}.`
                : "Connect a GitHub repository as a delivery source."}
            </DialogDescription>
          </DialogHeader>
          <div className="mt-4 grid gap-4">
            <div className="grid gap-2">
              <Label>Type</Label>
              <Input value="github" disabled />
            </div>
            <div className="grid gap-2">
              <Label>Owner</Label>
              <Input
                placeholder="e.g. acme"
                value={owner}
                onChange={(e) => setOwner(e.target.value)}
                disabled={isEdit}
                required
              />
            </div>
            <div className="grid gap-2">
              <Label>Repo</Label>
              <Input
                placeholder="e.g. backend"
                value={repo}
                onChange={(e) => setRepo(e.target.value)}
                disabled={isEdit}
                required
              />
            </div>
            <div className="grid gap-2">
              <Label>Token</Label>
              <Input
                type="password"
                placeholder={isEdit ? "Leave blank to keep current" : "GitHub personal access token"}
                value={token}
                onChange={(e) => setToken(e.target.value)}
              />
            </div>
            {isEdit && (
              <div className="flex items-center gap-3">
                <Switch checked={active} onCheckedChange={setActive} />
                <Badge variant="colorized" className={active ? STATUS_CLASSES.succeeded : ""}>
                  <StableText candidates={["synced", "inactive"]}>
                    {active ? "synced" : "inactive"}
                  </StableText>
                </Badge>
              </div>
            )}
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
            <div className="grid gap-2">
              <Label>Endpoint</Label>
              <Select value={endpoint} onValueChange={setEndpoint}>
                <SelectTrigger>
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
          </div>
          <DialogFooter className="mt-6">
            <div className="flex w-full items-center justify-between">
              {isEdit ? (
                <Button
                  type="button"
                  variant="destructive"
                  size="sm"
                  onClick={() => onDelete(source)}
                >
                  Delete
                </Button>
              ) : (
                <div />
              )}
              <Button type="submit" disabled={submitting}>
                <StableText candidates={["Create", "Creating...", "Save", "Saving..."]}>
                  {submitting
                    ? isEdit ? "Saving..." : "Creating..."
                    : isEdit ? "Save" : "Create"}
                </StableText>
              </Button>
            </div>
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
  } = useSources()
  const [addOpen, setAddOpen] = useState(false)
  const [editSource, setEditSource] = useState<Source | null>(null)
  const [deleteTarget, setDeleteTarget] = useState<Source | null>(null)

  async function handleDelete(source: Source) {
    setDeleteTarget(source)
  }

  async function confirmDelete() {
    if (!deleteTarget) return
    await deleteSource(deleteTarget.id)
    setDeleteTarget(null)
    setEditSource(null)
  }

  if (loading) {
    return (
      <div className="space-y-3 p-4">
        {Array.from({ length: 3 }).map((_, i) => (
          <Skeleton key={i} className="h-10 w-full" />
        ))}
      </div>
    )
  }

  if (error) {
    return <p className="p-4 text-destructive">Error: {error}</p>
  }

  return (
    <div className="space-y-0">
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
              <TableHead>Checkpoints</TableHead>
              <TableHead>Endpoint</TableHead>
              <TableHead>Last Synced</TableHead>
            </TableRow>
          </TableHeader>
          <TableBody>
            {sources.map((s, i) => (
              <TableRow
                key={s.id}
                className="cursor-pointer"
                onClick={() => setEditSource(s)}
              >
                <TableCell className="text-muted-foreground">{i + 1}</TableCell>
                <TableCell className="font-medium">
                  <a
                    href={`https://github.com/${s.owner}/${s.repo}`}
                    target="_blank"
                    rel="noopener noreferrer"
                    className="text-primary underline-offset-4 hover:underline"
                    onClick={(e) => e.stopPropagation()}
                  >
                    {s.owner}/{s.repo}
                  </a>
                </TableCell>
                <TableCell>{s.type}</TableCell>
                <TableCell>
                  <Badge variant="colorized" className={s.active ? STATUS_CLASSES.succeeded : ""}>
                    <StableText candidates={["synced", "inactive"]}>
                      {s.active ? "synced" : "inactive"}
                    </StableText>
                  </Badge>
                </TableCell>
                <TableCell>
                  <div className="flex flex-wrap gap-1">
                    {s.checkpoints.map((cp) => (
                      <Badge
                        key={cp}
                        variant="colorized"
                        className={PHASE_CLASSES[cp as Phase]}
                      >
                        <StableText candidates={PHASE_CANDIDATES}>{cp}</StableText>
                      </Badge>
                    ))}
                  </div>
                </TableCell>
                <TableCell>
                  <Badge
                    variant="colorized"
                    className={PHASE_CLASSES[s.endpoint as Phase]}
                  >
                    <StableText candidates={PHASE_CANDIDATES}>{s.endpoint}</StableText>
                  </Badge>
                </TableCell>
                <TableCell className="text-muted-foreground">
                  {s.last_polled_at
                    ? formatRelativeTime(s.last_polled_at)
                    : "Never"}
                </TableCell>
              </TableRow>
            ))}
          </TableBody>
        </Table>
      )}

      <div className="flex justify-center pt-4">
        <Button
          variant="outline"
          size="sm"
          onClick={() => setAddOpen(true)}
          className="border-dashed text-muted-foreground hover:border-foreground/30 hover:text-foreground"
        >
          <Plus className="size-3.5" />
          Add Source
        </Button>
      </div>

      <SourceFormDialog
        source={null}
        open={addOpen}
        onOpenChange={setAddOpen}
        onCreate={createSource}
        onUpdate={updateSource}
        onDelete={handleDelete}
      />

      {editSource && (
        <SourceFormDialog
          source={editSource}
          open={!!editSource}
          onOpenChange={(v) => { if (!v) setEditSource(null) }}
          onCreate={createSource}
          onUpdate={updateSource}
          onDelete={handleDelete}
        />
      )}

      <AlertDialog open={!!deleteTarget} onOpenChange={(v) => { if (!v) setDeleteTarget(null) }}>
        <AlertDialogContent>
          <AlertDialogHeader>
            <AlertDialogTitle>Delete source?</AlertDialogTitle>
            <AlertDialogDescription>
              Delete source {deleteTarget?.owner}/{deleteTarget?.repo}? This cannot be undone.
            </AlertDialogDescription>
          </AlertDialogHeader>
          <AlertDialogFooter>
            <AlertDialogCancel>Cancel</AlertDialogCancel>
            <AlertDialogAction variant="destructive" onClick={confirmDelete}>
              Delete
            </AlertDialogAction>
          </AlertDialogFooter>
        </AlertDialogContent>
      </AlertDialog>
    </div>
  )
}
