---
paths:
  - "frontend/**"
---

# Frontend Convention

## Stack
- React 19 + TypeScript + shadcn/ui + TailwindCSS + React Router 7
- Vite 7 build + vitest testing

## Absolute Rules
- Never modify files in components/ui/ (keep shadcn originals intact)
- Never create custom CSS files
- Never implement components from scratch — use shadcn if available
- Complex features (DnD, editors, charts) must use proven libraries

## Allowed Libraries
- shadcn/ui: UI components
- TailwindCSS: Styling
- dnd-kit: Drag and drop
- TanStack Table: Advanced tables
- React Router 7: Routing

## File Structure
- src/pages/<domain>/: Page components (list.tsx, show.tsx, etc.)
- src/components/: Shared components (ErrorBoundary, etc.)
- src/components/ui/: shadcn components (never modify)
- src/hooks/: Custom hooks
- src/utils/: Utility functions (api.ts, format.ts, etc.)
- src/types.ts: Shared type definitions

## Naming
- Component files: kebab-case or domain-grouped (list.tsx, show.tsx)
- Components: PascalCase (DeliveryList)
- Hooks: camelCase with use prefix (useDeliveries)
- Utilities: camelCase (formatDateTime)

## State Management
- React hooks (useState, useEffect, useCallback) only
- No global state management library
- Server state: fetch + useEffect pattern

## API Calls
- Use utils/api.ts wrappers (apiFetch, apiPost, apiPatch, apiDelete)
- Never call fetch() directly
