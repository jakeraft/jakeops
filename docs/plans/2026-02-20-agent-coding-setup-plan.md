# Agent Coding Setup Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Set up Claude Code agent conventions (rules, skills, MCP) so AI agents produce consistent code during the upcoming frontend rewrite.

**Architecture:** File-based configuration in `.claude/` directory. Rules define project conventions, skills provide domain expertise, MCP enables shadcn component access.

**Tech Stack:** Claude Code rules/skills/MCP system, shadcn/ui MCP server

---

### Task 1: Create frontend rules

**Files:**
- Create: `.claude/rules/frontend.md`

**Step 1: Create directory**

Run: `mkdir -p .claude/rules`

**Step 2: Write frontend.md**

```markdown
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
- Components: PascalCase (IssueList)
- Hooks: camelCase with use prefix (useIssues)
- Utilities: camelCase (formatDateTime)

## State Management
- React hooks (useState, useEffect, useCallback) only
- No global state management library
- Server state: fetch + useEffect pattern

## API Calls
- Use utils/api.ts wrappers (apiFetch, apiPost, apiPatch, apiDelete)
- Never call fetch() directly
```

**Step 3: Commit**

```bash
git add .claude/rules/frontend.md
git commit -m "chore: add frontend convention rules for Claude Code"
```

---

### Task 2: Create backend rules

**Files:**
- Create: `.claude/rules/backend.md`

**Step 1: Write backend.md**

```markdown
---
paths:
  - "backend/**"
---

# Backend Convention

## Stack
- Python 3.11+ / FastAPI / uvicorn / Pydantic v2

## Architecture Rules (Absolute)
- Dependency direction: adapters/inbound -> usecases -> ports/outbound <- adapters/outbound
- usecases must only depend on ports/outbound Protocols, never import adapters/outbound directly
- adapters/inbound (routers) must only depend on usecases, may reference domain/models
- domain/services/ must not depend on ports or adapters (pure domain logic only)
- DI assembly happens only in main.py

## File Creation Order for New Features
1. domain/models/ — Define Pydantic domain models
2. ports/outbound/ — Define Repository Protocol (if needed)
3. ports/inbound/ — Define Use Case Protocol
4. usecases/ — Implement Use Case
5. adapters/outbound/ — Implement Repository (if needed)
6. adapters/inbound/ — FastAPI router
7. main.py — Add DI assembly

## Coding Rules
- Use Python typing for all functions/methods
- Domain models inherit from Pydantic BaseModel
- Protocols use typing.Protocol
- No business logic in routers — delegate to usecases
- Environment variables are read only at the top of main.py

## Testing
- pytest + httpx (TestClient)
- Usecase unit tests: inject mock repositories
- Router integration tests: use TestClient
```

**Step 2: Commit**

```bash
git add .claude/rules/backend.md
git commit -m "chore: add backend convention rules for Claude Code"
```

---

### Task 3: Install frontend skills (3 skills)

**Files:**
- Create: `.claude/skills/react-best-practices/SKILL.md`
- Create: `.claude/skills/composition-patterns/SKILL.md`
- Create: `.claude/skills/web-design-guidelines/SKILL.md`

**Step 1: Create directories**

Run: `mkdir -p .claude/skills/react-best-practices .claude/skills/composition-patterns .claude/skills/web-design-guidelines`

**Step 2: Download skills from vercel-labs/agent-skills**

```bash
curl -sL https://raw.githubusercontent.com/vercel-labs/agent-skills/main/skills/react-best-practices/SKILL.md -o .claude/skills/react-best-practices/SKILL.md
curl -sL https://raw.githubusercontent.com/vercel-labs/agent-skills/main/skills/composition-patterns/SKILL.md -o .claude/skills/composition-patterns/SKILL.md
curl -sL https://raw.githubusercontent.com/vercel-labs/agent-skills/main/skills/web-design-guidelines/SKILL.md -o .claude/skills/web-design-guidelines/SKILL.md
```

**Step 3: Verify files downloaded correctly**

Run: `head -5 .claude/skills/react-best-practices/SKILL.md .claude/skills/composition-patterns/SKILL.md .claude/skills/web-design-guidelines/SKILL.md`

Expected: Each file starts with `---` (YAML frontmatter)

**Step 4: Commit**

```bash
git add .claude/skills/react-best-practices/ .claude/skills/composition-patterns/ .claude/skills/web-design-guidelines/
git commit -m "chore: install frontend skills (react-best-practices, composition-patterns, web-design-guidelines)"
```

---

### Task 4: Install backend and testing skills (3 skills)

**Files:**
- Create: `.claude/skills/fastapi-expert/SKILL.md`
- Create: `.claude/skills/architecture-patterns/SKILL.md`
- Create: `.claude/skills/vitest/SKILL.md`

**Step 1: Create directories**

Run: `mkdir -p .claude/skills/fastapi-expert .claude/skills/architecture-patterns .claude/skills/vitest`

**Step 2: Download skills**

```bash
curl -sL https://raw.githubusercontent.com/Jeffallan/claude-skills/main/skills/fastapi-expert/SKILL.md -o .claude/skills/fastapi-expert/SKILL.md
curl -sL https://raw.githubusercontent.com/wshobson/agents/main/plugins/backend-development/skills/architecture-patterns/SKILL.md -o .claude/skills/architecture-patterns/SKILL.md
curl -sL https://raw.githubusercontent.com/supabase/supabase/master/.agents/skills/vitest/SKILL.md -o .claude/skills/vitest/SKILL.md
```

**Step 3: Verify files downloaded correctly**

Run: `head -5 .claude/skills/fastapi-expert/SKILL.md .claude/skills/architecture-patterns/SKILL.md .claude/skills/vitest/SKILL.md`

Expected: Each file starts with `---` (YAML frontmatter)

**Step 4: Commit**

```bash
git add .claude/skills/fastapi-expert/ .claude/skills/architecture-patterns/ .claude/skills/vitest/
git commit -m "chore: install backend and testing skills (fastapi-expert, architecture-patterns, vitest)"
```

---

### Task 5: Configure shadcn MCP server

**Files:**
- Create: `.claude/mcp.json`

**Step 1: Write mcp.json**

```json
{
  "mcpServers": {
    "shadcn": {
      "type": "url",
      "url": "https://www.shadcn.io/api/mcp"
    }
  }
}
```

**Step 2: Commit**

```bash
git add .claude/mcp.json
git commit -m "chore: configure shadcn MCP server for component registry access"
```

---

### Task 6: Update docs/frontend-conventions.md

**Files:**
- Modify: `docs/frontend-conventions.md`

**Step 1: Rewrite frontend-conventions.md for new stack**

```markdown
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
```

**Step 2: Commit**

```bash
git add docs/frontend-conventions.md
git commit -m "docs: update frontend conventions for shadcn/ui + TailwindCSS stack"
```

---

### Task 7: Update CLAUDE.md

**Files:**
- Modify: `CLAUDE.md`

**Step 1: Add agent conventions section to CLAUDE.md**

Add after the "Architecture Notes" section:

```markdown
## Agent Conventions

- Frontend rules: `.claude/rules/frontend.md`
- Backend rules: `.claude/rules/backend.md`
- Skills: `.claude/skills/` (6 skills installed)
- MCP: `.claude/mcp.json` (shadcn component registry)
```

**Step 2: Commit**

```bash
git add CLAUDE.md
git commit -m "docs: add agent conventions section to CLAUDE.md"
```

---

### Task 8: Verify setup

**Step 1: Verify all files exist**

Run: `find .claude -type f | sort`

Expected output:
```
.claude/mcp.json
.claude/rules/backend.md
.claude/rules/frontend.md
.claude/skills/architecture-patterns/SKILL.md
.claude/skills/composition-patterns/SKILL.md
.claude/skills/fastapi-expert/SKILL.md
.claude/skills/react-best-practices/SKILL.md
.claude/skills/vitest/SKILL.md
.claude/skills/web-design-guidelines/SKILL.md
```

**Step 2: Verify git log shows all commits**

Run: `git log --oneline -8`

Expected: 7 new commits for tasks 1-7
