# Deployment Strategy

## Go-to-Market Strategy

OSS first, hosted later.

### Phase 1: Fully Open Source

Everything is open source. Users self-host the entire stack.

- Server + Worker both public (Apache 2.0)
- Users run their own server (`docker compose up`)
- Goal: community, contributors, user base, feedback loop
- Revenue: none (intentional)

### Phase 2: Hosted SaaS

Once the community validates the product, offer hosted convenience.

- jakeops.io — server hosted and operated by jakeraft
- "Don't want to run your own server? We'll host it for you."
- Worker remains open source, installed on user's machine
- Revenue: SaaS subscription (hosting fee)

### Phase 3: Premium Features (optional, future)

- Team management, SSO, role-based access
- Audit log dashboard, compliance reports
- SLA, priority support
- Open source version continues to exist and receive updates

### Precedent

| Project | Phase 1 (OSS) | Phase 2 (Hosted) |
|---------|---------------|-------------------|
| GitLab | Fully OSS (CE) | gitlab.com + EE |
| Grafana | Fully OSS | Grafana Cloud |
| Supabase | Fully OSS | supabase.com |
| Sentry | Fully OSS | sentry.io |
| n8n | Fully OSS | n8n.cloud |

## Architecture Overview

JakeOps separates **orchestration** from **execution**.

- **JakeOps Server** — UI, Delivery state, transcript storage, API
- **JakeOps Worker** (user's machine) — agent execution, local credentials, local runtimes

The server never runs agents or touches user credentials. It sends execution
requests to the worker; the worker runs them locally and returns results.

```
┌─────────────────────────────────────┐
│  JakeOps Server (SaaS)              │
│                                     │
│  ┌──────────┐  ┌─────────────────┐  │
│  │ Frontend │  │ Backend (API)   │  │
│  │ (CDN)    │  │ - Delivery CRUD │  │
│  │          │  │ - Phase machine │  │
│  └──────────┘  │ - Transcript DB │  │
│                │ - GitHub polling│  │
│                │ - Worker broker │  │
│                └────────┬────────┘  │
└─────────────────────────┼───────────┘
                          │ WebSocket
                          │
┌─────────────────────────▼───────────┐
│  JakeOps Worker (user's machine)    │
│                                     │
│  SubprocessRunner (ClaudeCliAdapter)│
│  ├── claude -p (user's auth)        │
│  ├── git / gh  (user's auth)        │
│  └── any local runtime              │
│      (Unity, Xcode, CUDA, ...)      │
└─────────────────────────────────────┘
```

## Design Principles

### 1. Server orchestrates, Worker executes

The server does not know how to run agents. It constructs a prompt and
delegates execution to a connected worker via `SubprocessRunner`. The worker
runs `claude -p` locally and streams results back.

### 2. Credentials never leave the user's machine

Claude authentication (`~/.claude/`), GitHub tokens (`~/.config/gh/`), SSH
keys, and any other credentials stay on the worker machine. The server
receives only execution results and transcripts — never credentials.

### 3. Runtime-agnostic

The server does not bundle any build/test runtimes. Whether the project
needs Unity Editor, Xcode, CUDA, or just Python — it's available on the
worker machine where the user already develops. JakeOps does not constrain
the user's toolchain.

### 4. SubprocessRunner as the boundary

The `SubprocessRunner` protocol is the single interface between orchestration
and execution. It is phase-agnostic: it takes a prompt and returns results.
Phase logic lives in the use case layer.

```python
class SubprocessRunner(Protocol):
    async def run_with_stream(
        self, prompt, cwd, allowed_tools, append_system_prompt
    ) -> tuple[str, list[StreamEvent], str | None]: ...
```

Two adapters, same protocol:

| Adapter | Where it runs | Used when |
|---------|--------------|-----------|
| `ClaudeCliAdapter` | Same machine as server | Local development, self-hosted |
| `RemoteWorkerAdapter` | Server delegates to remote worker | SaaS deployment |

Use case code does not change between modes. DI selects the adapter.

## Components

### JakeOps Server

Hosted and operated by jakeraft. Users access via browser.

**Responsibilities:**
- Delivery lifecycle management (phase transitions, approvals)
- GitHub polling (DeliverySyncUseCase)
- Transcript storage and retrieval
- Worker connection management (broker)
- UI dashboard

**Deployment:**
- Docker image built in CI (GitHub Actions)
- Deployed to cloud infrastructure
- Frontend served via CDN (static build)
- Database for Delivery/Source/Transcript persistence

**Not responsible for:**
- Running agents
- Holding user credentials
- Build/test execution

### JakeOps Worker

Installed on the user's machine. Lightweight process that connects to the
SaaS server and executes agent tasks locally.

**Responsibilities:**
- Maintain WebSocket connection to server
- Receive execution requests (prompt, cwd, allowed_tools)
- Run `claude -p` via `ClaudeCliAdapter`
- Run git/gh operations with local credentials
- Stream results + transcript back to server

**Distribution:**
- PyPI package: `pip install jakeops-worker`
- Single command to connect: `jakeops-worker --token <token>`

**What it reuses:**
- `ClaudeCliAdapter` — same code as local mode
- `StreamEvent`, `parse_stream_lines`, `extract_metadata`, `extract_transcript`
  — same parsing logic

### Worker Lifecycle

```
1. User signs up on JakeOps SaaS
2. User generates a worker token from the dashboard
3. User installs worker:
   $ pip install jakeops-worker
   $ jakeops-worker --token eyJ...
4. Worker connects to server via WebSocket
5. Server shows worker as "online" in dashboard
6. When a Delivery needs agent execution:
   - Server sends prompt to worker
   - Worker runs claude -p locally
   - Worker returns result + events + session_id
   - Server saves transcript, updates Delivery state
7. Worker stays connected, waiting for next request
```

## Execution Flow (SaaS Mode)

### Example: plan phase

```
[Browser]                    [Server]                      [Worker]
    │                           │                              │
    ├── "Generate Plan" ───────→│                              │
    │                           ├── build prompt               │
    │                           │   (PLAN_PROMPT_TEMPLATE)     │
    │                           │                              │
    │                           ├── RemoteWorkerAdapter        │
    │                           │   .run_with_stream() ───────→│
    │                           │                              ├── git clone (local)
    │                           │                              ├── claude -p (local auth)
    │                           │                              │   ├── read files
    │                           │                              │   ├── analyze codebase
    │                           │                              │   └── generate plan
    │                           │   ◀── (result, events, sid) ─┤
    │                           │                              │
    │                           ├── extract_metadata(events)   │
    │                           ├── extract_transcript(events) │
    │                           ├── save_run_transcript()      │
    │                           ├── update delivery            │
    │                           │   phase=plan                 │
    │                           │   run_status=succeeded       │
    │   ◀── UI update ─────────┤                              │
    │   (plan content,          │                              │
    │    transcript viewer,     │                              │
    │    approve/reject buttons)│                              │
```

## Comparison with Industry

| Platform | Server | Local Agent | Install |
|----------|--------|-------------|---------|
| GitHub Actions | github.com | Self-hosted Runner | `./config.sh && ./run.sh` |
| Buildkite | buildkite.com | Buildkite Agent | `brew install buildkite-agent` |
| Tailscale | controlplane | Tailscale client | `brew install tailscale` |
| **JakeOps** | **jakeops.io** | **jakeops-worker** | **`pip install jakeops-worker`** |

## What Users Do NOT Need

- Docker
- docker-compose
- Environment variable configuration files
- Credential management on server
- Runtime installation on server (Unity, Xcode, etc.)
- Server hosting or maintenance

## Deployment Modes

| Mode | Server | Worker | SubprocessRunner Adapter | Phase |
|------|--------|--------|-------------------------|-------|
| **Local dev** | `uvicorn` on localhost | Not needed | `ClaudeCliAdapter` | Phase 1 |
| **Self-hosted** | User's server (Docker) | Same machine or remote | Either adapter | Phase 1 |
| **SaaS** | jakeraft cloud | `pip install jakeops-worker` | `RemoteWorkerAdapter` | Phase 2 |

All three modes share the same codebase. The only difference is which
`SubprocessRunner` adapter is injected via DI in `main.py`.

Phase 1 focuses on local dev and self-hosted modes. SaaS mode is introduced
in Phase 2 after the community and user base are established.

## Worker Trust Strategy

The worker runs on the user's machine with access to local credentials and
tools. User resistance is expected and must be addressed deliberately.

### Open Source Model

Both server and worker are fully open source (Phase 1). When a hosted SaaS
is introduced (Phase 2), the worker remains open source regardless.

| Component | Phase 1 | Phase 2 (SaaS) |
|-----------|---------|----------------|
| JakeOps Server | Open Source (Apache 2.0) | Hosted by jakeraft, source still public |
| JakeOps Worker | Open Source (Apache 2.0) | Open Source (Apache 2.0) |

The worker running on user machines will always be open source. This is
non-negotiable — users must be able to audit what runs on their machine.

Industry precedent for local clients being open source:

| Product | Server | Local Client | Client OSS |
|---------|--------|-------------|------------|
| GitHub Actions | github.com (closed) | actions/runner | Yes |
| Buildkite | buildkite.com (closed) | buildkite/agent | Yes |
| Tailscale | controlplane (closed) | tailscale/tailscale | Yes |
| GitLab | gitlab.com (closed) | GitLab Runner | Yes |

### Trust Layers

#### 1. Code transparency

Worker source code is public. Anyone can read, audit, fork, and build
from source. The worker should stay minimal — ideally under 200 lines of
core logic — so that a security review takes minutes, not days.

#### 2. Minimal scope

The worker does exactly three things:

```
✓ Receive prompt from server
✓ Run claude -p locally
✓ Return result + transcript to server
```

It does NOT:

```
✗ Upload files or directory listings
✗ Transmit credentials to the server
✗ Collect telemetry or background data
✗ Execute anything the server did not request
✗ Access files outside the cloned working directory
```

#### 3. Local audit log

Every execution is logged locally, regardless of server connectivity:

```
~/.jakeops/logs/
├── 2026-02-20T14:30:00.log
└── 2026-02-20T15:00:00.log
```

Each log entry records: prompt received, tools allowed, working directory,
result summary, and bytes transmitted to server. Users can verify exactly
what their worker did.

#### 4. Interactive approval mode (opt-in)

For sensitive environments, the worker can require explicit user approval
before each execution:

```
[jakeops-worker] Execution request from server:
  Prompt: "Analyze codebase and generate plan for issue #42"
  Cwd: /tmp/jakeops-clone-abc123
  Allowed tools: Read, Glob, Grep (read-only)

  Accept? [Y/n] ▌
```

This mode is opt-in. Default behavior is automatic execution (like
GitHub self-hosted runners).

#### 5. Build from source

Users who do not trust PyPI can build directly:

```bash
git clone https://github.com/jakeraft/jakeops-worker
cd jakeops-worker
pip install .
```

### Trust Summary

| Layer | Strategy | User confidence |
|-------|----------|----------------|
| Code | Open source, minimal codebase | "I can read every line" |
| Scope | Prompt execution only | "It only does what I see" |
| Transparency | Local audit logs | "I can verify after the fact" |
| Control | Interactive approval mode | "Nothing runs without my OK" |
| Supply chain | Build from source option | "I don't have to trust PyPI" |

## Implementation Order

### Phase 1: Local mode (current)

Already working. Server and execution on the same machine.

### Phase 2: Worker protocol

- Define worker↔server message format (WebSocket)
- Implement `RemoteWorkerAdapter` (server side)
- Implement `jakeops-worker` CLI (client side, reuses `ClaudeCliAdapter`)
- Worker token generation in dashboard

### Phase 3: SaaS deployment

- Server Docker image + CI pipeline
- Frontend CDN deployment
- Database migration (file-based → DB)
- Worker token auth + connection management

### Phase 4: Multi-worker support

- Multiple workers per user (different machines/runtimes)
- Worker selection based on capability tags (e.g., "has Unity", "has CUDA")
- Worker health monitoring and reconnection
