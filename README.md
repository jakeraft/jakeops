# JakeOps

**Control Plane for Agent-driven DevOps**

JakeOps connects Agent execution to your existing software delivery pipeline.

It does not replace your CI/CD tools.
It does not replace your coding Agents.

JakeOps orchestrates, tracks, and records Agent-driven changes inside a structured workflow.

## Why JakeOps?

When Agents participate in DevOps workflows:

- Execution becomes fragmented
- Change context gets lost
- Approval boundaries become unclear
- Evidence is scattered across tools
- Reasoning and decision paths are hard to reconstruct

JakeOps connects the lifecycle into one orchestration unit: an **Issue**.

## What JakeOps Does

- **Issue-based orchestration** — one unit tracks the entire lifecycle
- **Plan → Approval → Execution** workflow with human gates
- **Source polling** — ingest issues from GitHub automatically
- **Run history and transcript capture** — full evidence trail
- **Status-gated transitions** — `approve`, `reject`, `retry`, `cancel`

## Quick Start

```bash
# Backend
cd backend
pip install -e .
uvicorn app.main:app --reload

# Frontend (another terminal)
cd frontend
npm install
npm run dev
```

Open `http://localhost:5173`.

## Contributing

See [CONTRIBUTING.md](CONTRIBUTING.md) for development setup, architecture, and guidelines.

## License

[Apache License 2.0](LICENSE)
