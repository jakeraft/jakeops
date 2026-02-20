# CLAUDE.md

See:

- `README.md` for project overview
- `docs/planning.md` for product intent
- `docs/architecture.md` for system design

## Documentation Rule

When a design decision is finalized, write it to `docs/` immediately.

- Location: `docs/<topic>.md`
- Include: context, decision, alternatives, implementation order

## Local Setup

- Node.js (LTS)
- Python 3.11+
- pip

## Build

```bash
# Frontend
cd frontend && npm install && npm run build

# Backend
cd backend && pip install -e .
```

## Run

```bash
# Backend first
cd backend && uvicorn app.main:app --reload --host 0.0.0.0

# Frontend in another terminal
cd frontend && npm run dev -- --host 0.0.0.0
```

## Lint and Test

```bash
# Frontend
cd frontend && npm run lint
cd frontend && npm run test

# Backend
cd backend && pip install -e ".[test]" && python -m pytest -v
```

## Architecture Notes

- Monorepo: `frontend/` + `backend/`
- File-based data: `deliveries/`, `sources/`
- API proxy in dev: `/api` -> `http://localhost:8000`
- Backend architecture: Ports/Adapters + Use Cases

Useful environment variables:

- `JAKEOPS_DATA_DIR`
- `JAKEOPS_SOURCES_DIR`

## Agent Conventions

- Frontend rules: `.claude/rules/frontend.md`
- Backend rules: `.claude/rules/backend.md`
- Skills: `.claude/skills/` (6 skills installed)
- MCP: `.claude/mcp.json` (shadcn component registry)
