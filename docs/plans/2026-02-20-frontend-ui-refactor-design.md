# Frontend UI Refactor Design

## Context

The frontend has accumulated several UX issues: sidebar not filling viewport height, inconsistent header hierarchy, missing domain model fields (checkpoints/endpoint) in Source forms, closed deliveries cluttering active views, redundant page titles, inconsistent table row heights, and missing current-state display on delivery detail pages (Issue #9).

## Changes

### 1. Sidebar Full Height

The sidebar does not fill the viewport vertically. Add `className="h-full"` to `<Sidebar>` so it stretches to match the `SidebarProvider`'s `min-h-svh`.

- File: `frontend/src/components/app-sidebar.tsx`

### 2. Main Header Matches Sidebar Header

The main content header (`h-10, text-sm font-medium`) is visually weaker than the sidebar header (`text-lg font-semibold`). Promote the main header to the same level.

- File: `frontend/src/components/app-layout.tsx`
- Change: `h-10` -> `h-12`, `text-sm font-medium` -> `text-lg font-semibold`

### 3. Source Tab: Checkpoint and Endpoint Support

The backend `Source` model already has `checkpoints: string[]` and `endpoint: string`. The frontend `types.ts` already defines these fields. The UI needs to expose them.

**Table columns:**
- Keep existing `Endpoint` column
- Add `Checkpoints` column showing phase badges

**Add Source dialog:**
- `Endpoint`: Replace text input with a `<Select>` dropdown of Phase values (intake through close). Default: `deploy`
- `Checkpoints`: Multi-checkbox list of Phase values. Default: `["plan", "implement", "review"]`

**Edit Source dialog:**
- Same controls as Add, pre-populated with current values

- Files: `frontend/src/pages/sources/list.tsx`

### 4. Active/Closed Tab Separation

Terminal condition: `(phase === "close" && run_status === "succeeded") || run_status === "canceled"`

**Delivery List page:**
- Add `Active` / `Closed` tabs at the top using shadcn Tabs component
- Active tab (default): non-terminal deliveries only
- Closed tab: terminal deliveries only

**Kanban Board page:**
- Add `Active` / `Closed` tabs at the top
- Active tab (default): hide the `close` column entirely (show 7 phase columns)
- Closed tab: show only closed deliveries in a simple list/grid view

- Files: `frontend/src/pages/deliveries/list.tsx`, `frontend/src/pages/deliveries/board.tsx`, `frontend/src/components/kanban/board.tsx`

### 5. Remove Redundant "Sources" Title

The Source list page has `<h1>Sources</h1>` which duplicates the main header. Remove it. Keep the action buttons (Sync Now, Add Source) aligned right in the same area.

- File: `frontend/src/pages/sources/list.tsx`

### 6. Table Row Height Consistency

Source table Actions column has `Button size="sm"` which makes rows taller than other tables. Reduce button size with `h-7 text-xs` to match surrounding row height, or switch to icon-only buttons.

- File: `frontend/src/pages/sources/list.tsx`

### 7. Clickable Table Rows

Delivery List table currently requires clicking the Summary link to navigate. Make the entire `<TableRow>` clickable with `onClick` navigation and `cursor-pointer` styling. Remove the dedicated `<Link>` wrapper on Summary text (keep font-medium styling).

- File: `frontend/src/pages/deliveries/list.tsx`

### 8. Delivery Detail Current State (Issue #9)

Add a compact metadata row below the title showing current phase, run_status, and repository. Uses existing badge styles.

Layout:
```
<h1>Delivery Summary Title</h1>
<div>  [phase badge]  [status badge]  repository-text  </div>
```

- File: `frontend/src/pages/deliveries/show.tsx`

## Alternatives Considered

- **Closed items filter toggle** instead of tabs: simpler but harder to browse closed-only items
- **Collapsible close column** on kanban: adds complexity without clear benefit over tabs
- **Sidebar status card** for Issue #9: takes horizontal space, metadata row is more compact

## Implementation Order

1. Layout fixes (sidebar height, header hierarchy) - independent, low risk
2. Remove redundant title + table row fixes - small scope
3. Source tab checkpoint/endpoint support - form changes
4. Active/Closed tab separation - delivery list and kanban
5. Clickable table rows - delivery list
6. Delivery detail metadata row - Issue #9
