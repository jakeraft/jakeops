# Frontend Conventions

## Stack

- React 19 + TypeScript
- shadcn/ui + TailwindCSS
- React Router 7
- Vite 7
- Vitest + Testing Library

## Principles

- Use shadcn/ui components from components/ui/ — never modify originals.
- Style with TailwindCSS utility classes only — no custom CSS files.
- Use proven libraries for complex interactions (dnd-kit, TanStack Table).
- Keep state management simple: React hooks, no global state library.

## Layout

- Use shadcn Sidebar component for navigation.
- Responsive behavior via TailwindCSS breakpoints.

## Data Views

- Use shadcn Table (+ TanStack Table for advanced needs) for list pages.
- Keep transcript rendering plain text (`pre`) for debugging.

## Current Frontend Structure

```text
frontend/src/
├── App.tsx
├── main.tsx
├── pages/
│   ├── issues/
│   ├── sources/
│   └── worker/
├── components/
│   └── ui/          # shadcn components (read-only)
├── hooks/
├── utils/
└── types.ts
```

## Quality Checks

```bash
npm run lint
npm run test
npm run build
```
