# Frontend Conventions

## Stack

- React 19 + TypeScript
- Ant Design 6
- React Router 7
- Vite 7
- Vitest + Testing Library

## Principles

- Prefer Ant Design native components over custom UI primitives.
- Keep styling token-driven (`theme.useToken()`).
- Avoid custom CSS files unless absolutely necessary.
- Keep tables responsive (`scroll={{ x: "max-content" }}` when needed).

## Layout

- Use `Layout`, `Sider`, `Header`, `Content`.
- Use built-in responsive behavior:
  - `breakpoint="md"`
  - `collapsedWidth={0}`
  - `Grid.useBreakpoint()` for adaptive interactions

## Theming

Global theming should be centralized in `App.tsx` via `ConfigProvider`.

## Data Views

- Use `Table` for list pages.
- Use `Descriptions` for detail pages.
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
└── utils/
```

## Quality Checks

```bash
npm run lint
npm run test
npm run build
```
