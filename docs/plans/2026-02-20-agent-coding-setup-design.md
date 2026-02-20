# Agent Coding Setup Design

**Date**: 2026-02-20
**Issue**: #1 (feat: Agent Coding Setup)
**Scope**: Agent coding conventions only (Claude Code). Frontend implementation is a separate task.

## Context

JakeOps frontend uses React 19 + shadcn/ui + TailwindCSS. Agent coding conventions ensure AI agents produce consistent, high-quality code.

## Decision

### Approach: Rules First

1. Write `.claude/rules/frontend.md` and `.claude/rules/backend.md`
2. Install 6 skills from external repositories
3. Configure shadcn MCP server in `.claude/mcp.json`
4. Update project documentation (CLAUDE.md, docs/frontend-conventions.md)

### File Structure

```
project-root/
├── CLAUDE.md                              # Updated for new stack
├── .claude/
│   ├── rules/
│   │   ├── frontend.md                    # paths: frontend/**
│   │   └── backend.md                     # paths: backend/**
│   ├── skills/
│   │   ├── react-best-practices/SKILL.md
│   │   ├── composition-patterns/SKILL.md
│   │   ├── web-design-guidelines/SKILL.md
│   │   ├── fastapi-expert/SKILL.md
│   │   ├── architecture-patterns/SKILL.md
│   │   └── vitest/SKILL.md
│   └── mcp.json                           # shadcn MCP server
├── docs/
│   └── frontend-conventions.md            # Updated for new stack
├── frontend/                              # No changes in this task
└── backend/                               # No changes
```

### Rules Content

#### .claude/rules/frontend.md

- Stack: React 19 + TypeScript + shadcn/ui + TailwindCSS + React Router 7 + Vite 7
- Absolute rules: no modifying components/ui/, no custom CSS, use shadcn when available, proven libraries for complex features
- Allowed libraries: shadcn/ui, TailwindCSS, dnd-kit, TanStack Table, React Router 7
- File structure: pages/<domain>/, components/, components/ui/ (read-only), hooks/, utils/, types.ts
- Naming: kebab-case files, PascalCase components, camelCase hooks/utils
- State management: React hooks only, no global state library
- API calls: use utils/api.ts wrappers exclusively

#### .claude/rules/backend.md

- Stack: Python 3.11+ / FastAPI / uvicorn / Pydantic v2
- Architecture: Hexagonal (Ports & Adapters)
- Dependency direction: adapters/inbound -> usecases -> ports/outbound <- adapters/outbound
- domain/services/ must not depend on ports or adapters (pure domain logic)
- DI assembly only in main.py
- Environment variables read only at top of main.py
- File creation order for new features defined
- Testing: pytest + httpx

### Skills (6 total)

| Skill | Source | Purpose |
|-------|--------|---------|
| react-best-practices | vercel-labs/agent-skills | React performance and rendering optimization |
| composition-patterns | vercel-labs/agent-skills | Component API composition patterns |
| web-design-guidelines | vercel-labs/agent-skills | UI review/audit guidelines |
| fastapi-expert | Jeffallan/claude-skills | FastAPI + Pydantic v2 patterns |
| architecture-patterns | wshobson/agents | Hexagonal/Clean architecture guardrails |
| vitest | supabase/supabase | Vitest testing patterns |

### MCP Server

shadcn/ui official MCP at `https://www.shadcn.io/api/mcp` for component registry search and installation.

## Alternatives Considered

- **Skills First**: Install skills before writing rules. Rejected because rules establish the foundation that skills complement.
- **All-at-Once**: Do everything simultaneously. Rejected because incremental approach allows validation at each step.
- **Include Codex support**: AGENTS.md, .agents/, .codex/. Rejected to keep scope focused on Claude Code only.
