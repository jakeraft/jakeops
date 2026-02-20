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

JakeOps connects the lifecycle into one orchestration unit: a **Delivery**.

## What JakeOps Does

- **Delivery-based orchestration** — one unit tracks the entire lifecycle
- **Plan → Approval → Execution** workflow with human gates
- **Source polling** — ingest changes from GitHub automatically
- **Run history and transcript capture** — full evidence trail
- **Status-gated transitions** — `approve`, `reject`, `retry`, `cancel`

## How Is This Different?

| | Keptn | Harness | JakeOps |
|---|---|---|---|
| **Focus** | SLO-based deployment gates | All-in-one CI/CD platform | Agent↔Human delivery orchestration |
| **AI Agents** | None | Built-in, closed ecosystem | External, pluggable (Claude Code, Devin, etc.) |
| **CI/CD relationship** | Extends K8s deployments | Replaces your CI/CD | Sits above your existing CI/CD |
| **Actor tracking** | System only | System + internal AI | System / Agent / Human (explicit) |

JakeOps is purpose-built for the emerging pattern where AI agents generate plans,
write code, and trigger pipelines — while humans retain approval authority at
critical gates. Existing tools either ignore agents entirely (Keptn) or lock you
into a proprietary agent ecosystem (Harness).

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
