# Kanban Board Design

## Context

JakeOps tracks Deliveries through an 8-phase pipeline:
`intake -> plan -> implement -> review -> verify -> deploy -> observe -> close`.
The current UI shows Deliveries in a flat table. A Kanban board maps each phase
to a column, giving an at-a-glance view of the pipeline and enabling drag-and-drop
workflow actions.

## Decision

Build an interactive Kanban board using dnd-kit (already in the allowed libraries
list). The board lives at `/board` as a separate sidebar entry, keeping the existing
table view intact.

## Alternatives Considered

1. **react-beautiful-dnd** - Not in allowed libraries. Rejected.
2. **External kanban library (react-kanban)** - Not in allowed libraries, and
   dnd-kit + shadcn is sufficient. Rejected.

## Design

### Component Structure

```
src/pages/deliveries/board.tsx          # Page component (route: /board)
src/components/kanban/board.tsx         # KanbanBoard - DndContext + column layout
src/components/kanban/column.tsx        # KanbanColumn - Droppable phase column
src/components/kanban/card.tsx          # KanbanCard - Draggable delivery card
src/components/kanban/detail-sheet.tsx  # DetailSheet - click card to view/act
```

### Routing

- Route: `/board` under AppLayout
- Sidebar: new "Board" nav item with `Columns3` icon from lucide-react

### Data Flow

- Reuse `useDeliveries()` hook to fetch all deliveries
- Group deliveries by `phase` field into 8 columns
- On drag-and-drop: call appropriate API (approve/reject/retry) then refresh
- On card click: open Sheet with delivery details + action buttons

### Card Content

Each card shows:
- `summary` (title, truncated to 2 lines)
- `run_status` badge (with existing STATUS_CLASSES colors)
- `repository` (muted text)
- `updated_at` (relative time)

### Drag-and-Drop Rules

The board enforces the backend state machine:

| Current State                           | Drop Target         | API Call        |
|-----------------------------------------|---------------------|-----------------|
| Gate phase + succeeded -> next phase    | Next phase column   | POST /approve   |
| Gate phase + succeeded -> previous phase| Previous phase col  | POST /reject    |
| Any phase + failed -> same phase        | Same column         | POST /retry     |
| intake -> plan (non-gate advance)       | plan column         | POST /approve   |
| Invalid transition                      | Any                 | Drop blocked    |

Gate phases: `plan`, `review`, `deploy`.

Drop validation:
- Only allow drop to adjacent phase (no skipping)
- Only allow forward drop when `run_status === succeeded`
- Reject drop shows a reason dialog before calling API
- Invalid drops show visual feedback (red overlay on column)

### Detail Sheet

Right-side Sheet opens on card click:
- Header: summary + phase badge + status badge
- Repository info
- Refs list
- Action buttons (approve/reject/retry/cancel/generate-plan)
- "View Full Details" link to `/deliveries/:id`
- Uses `useDelivery(id)` hook for single-delivery data + actions

### Styling

- Horizontal scroll for 8 columns on narrow screens
- Column header uses existing `PHASE_CLASSES` colors
- Card uses shadcn Card component
- Drag overlay shows semi-transparent card copy
