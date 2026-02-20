# Product Strategy

## Go-to-Market Strategy

Self-hosted first. SaaS is a future option, not a given.

### Phase 1: Fully Open Source (current focus)

Everything is open source. Users self-host the entire stack on their own
machine. Server and agent execution happen on the same machine — no data
leaves the user's environment.

- Apache 2.0 license
- Users install via pip and run locally
- Goal: community, contributors, user base, feedback loop
- Revenue: none (intentional)

### Phase 2: Open Core (future)

Once the community validates the product, introduce enterprise features
behind a commercial license. The core remains free and open source.

- Free: all current features (individual / small team)
- Paid: team workspace, SSO, RBAC, audit dashboard, compliance reports
- Revenue: license sales
- No SaaS required — users still self-host

### Phase 3: Hosted SaaS (future, conditional)

Only viable after solving the trust problem (see "SaaS Trust Problem"
section below). Not guaranteed to happen.

- jakeops.io — server hosted and operated by jakeraft
- Worker remains open source, installed on user's machine
- Revenue: SaaS subscription (hosting fee)
- Requires container isolation, tool restrictions, and transparent audit

### Precedent

| Project | Phase 1 (OSS) | Phase 2+ |
|---------|---------------|----------|
| GitLab | Fully OSS (CE) | gitlab.com + EE |
| Grafana | Fully OSS | Grafana Cloud |
| Supabase | Fully OSS | supabase.com |
| Sentry | Fully OSS | sentry.io |
| n8n | Fully OSS | n8n.cloud |

## Architecture Overview (Phase 1)

In Phase 1, everything runs on a single machine. No server/worker split.

```
User's Machine
┌──────────────────────────────────────┐
│  Frontend (React)                    │
│  Backend (FastAPI / uvicorn)         │
│  ClaudeCliAdapter                    │
│  ├── claude -p (user's auth)         │
│  ├── git / gh  (user's auth)         │
│  └── any local runtime              │
│                                      │
│  All data stays here:               │
│  ├── deliveries/                    │
│  ├── sources/                       │
│  └── ~/.claude/ (credentials)       │
└──────────────────────────────────────┘
```

No data leaves the machine. No trust problem.

## Design Principles

### 1. Orchestration and execution on the same machine

The server constructs prompts and delegates execution to `ClaudeCliAdapter`
which runs `claude` locally. Everything happens in the same process space.

### 2. Credentials never leave the user's machine

Claude authentication (`~/.claude/`), GitHub tokens (`~/.config/gh/`), SSH
keys, and any other credentials stay local. In Phase 1 there is no remote
server to leak to. This remains true in all future phases.

### 3. Runtime-agnostic

The server does not bundle any build/test runtimes. Whether the project
needs Unity Editor, Xcode, CUDA, or just Python — it's available on the
user's machine where they already develop.

### 4. SubprocessRunner as the boundary

The `SubprocessRunner` protocol is the single interface between orchestration
and execution. It is phase-agnostic: it takes a prompt and returns results.
Phase logic lives in the use case layer.

```python
class SubprocessRunner(Protocol):
    async def run(self, prompt, cwd, ...) -> tuple[str, str | None]: ...
    def run_stream(self, prompt, cwd, ...) -> AsyncGenerator[dict, None]: ...
    def kill(self, delivery_id) -> bool: ...
```

In Phase 1, only one adapter exists:

| Adapter | Where it runs | Used when |
|---------|--------------|-----------|
| `ClaudeCliAdapter` | Same machine as server | Phase 1 (self-hosted) |

Future adapters (e.g. `RemoteWorkerAdapter`) can be added via DI without
changing use case code.

## Agent Execution Modes

The system supports two execution modes for the Claude CLI. The mode is
determined per phase based on the Source's `checkpoints` configuration —
checkpoint phases run in interactive mode, non-checkpoint phases run in
headless mode.

| | Headless | Interactive |
|--|----------|-------------|
| CLI invocation | `claude -p "prompt" --output-format stream-json` | `claude "prompt"` |
| User visibility | None — result only | Full TUI in user's terminal |
| User intervention | Not possible | Can interact mid-execution |
| Data collection | stdout stream (stream-json) | Session file tailing (`~/.claude/projects/.../sessions/<id>.jsonl`) |
| Parser path | `parse_stream_lines()` | `parse_session_lines()` + `synthesize_result_event()` |

### Data format differences

The two sources produce structurally similar but not identical JSONL:

| | stream-json (headless) | session file (interactive) |
|--|------------------------|---------------------------|
| Key naming | `snake_case` (`parent_tool_use_id`, `session_id`) | `camelCase` (`parentToolUseID`, `sessionId`) |
| Result event | Included in stream | Not present — must be synthesized |
| Noise events | Absent | Includes `progress`, `file-history-snapshot` |

Both paths converge to the same `list[StreamEvent]` via their respective
parsers, then feed into shared `extract_metadata()` and `extract_transcript()`.

### Non-interactive system prompt

When running in headless mode, the user's global Claude Code skills
(e.g. brainstorming, plan-mode) may cause the agent to ask clarifying
questions instead of completing the task. All phase system prompts include
a non-interactive directive to prevent this:

```
You are running non-interactively in a CI pipeline.
Do NOT ask questions, request clarification, or present options.
Complete the task fully and return the result directly.
```

This is appended via `--append-system-prompt`. Skills remain loaded (their
knowledge is still useful) but the directive overrides interactive behavior.

In interactive mode, this directive is not needed — the user can respond
to any questions directly in the TUI.

### Why not `--disable-slash-commands`?

The Claude CLI provides `--disable-slash-commands` to disable all skills.
However, this is too aggressive — it also disables project-specific skills
that contain useful patterns and conventions. The system prompt approach
selectively suppresses interactive behavior while preserving skill knowledge.

### Completion detection

| Mode | How we know it's done |
|------|----------------------|
| Headless | Process exits → exit code + stdout result |
| Interactive | **User clicks Approve/Reject in web UI** |

In interactive mode, there is no programmatic "task complete" signal.
The Claude TUI stays open after finishing work, waiting for more input.
The completion signal comes from the user via the browser, not from the
terminal process.

## Phase-per-Session Model

Each phase execution spawns an independent Claude session. Sessions are
not reused across phases.

**Why per-phase, not per-delivery:**
- Not all phases need user intervention — only checkpoint phases are
  interactive, the rest run headless in the background.
- Refs accumulation provides full context to each new session. All
  phases receive the same refs (request + work URLs). The agent reads
  full context directly from GitHub issue/PR threads. No context is
  lost between sessions.
- Clean lifecycle — each session has a clear start (phase begins) and
  the completion signal comes from the web UI (user clicks Approve).

**Interactive session lifecycle:**

```
1. Server transitions delivery to a checkpoint phase
2. Server launches: claude "prompt + accumulated refs"
3. New terminal session opens on user's machine
4. User observes / intervenes in the TUI
5. User goes to browser, clicks "Approve" (or "Reject")
6. Server collects session file, transitions to next phase
7. Terminal session is left as-is — user closes it at their convenience
8. Next phase: new session (headless or interactive depending on config)
```

The previous terminal session becomes inert after the phase transitions.
It has no connection to the next phase's session, and leaving it open
has no side effects.

**Example with checkpoints=[plan, implement]:**

```
plan (interactive):      terminal #1 opens → user approves → terminal #1 inert
implement (interactive): terminal #2 opens → user approves → terminal #2 inert
review (headless):       claude -p in background, user sees nothing
verify (headless):       system phase, no agent
```

## Distribution (Phase 1)

Single pip package. Pre-built frontend static files are bundled inside the
Python package. No Node.js required for end users.

```bash
pip install jakeops    # backend + pre-built frontend static bundle
jakeops start          # uvicorn serves API + static files on one port
```

Precedent: Jupyter, Streamlit, MLflow — all distribute pre-built frontends
inside a Python package.

### Why pip, not npm/npx

Target users are Claude Code users who already have Node.js. However:

- Backend is Python (FastAPI) — pip is the natural distribution channel.
- npm distributing a Python backend creates an awkward dependency chain
  (npm spawning pip spawning uvicorn).
- Bundling pre-built frontend into the pip package eliminates the need
  for Node.js at runtime entirely.
- Docker is avoided for local use because `claude` CLI needs access to
  `~/.claude/`, `~/.config/gh/`, `~/.ssh/` — mounting credentials into
  containers adds friction and user resistance.

### What Users Need

- Python 3.11+
- Claude Code CLI installed and authenticated
- GitHub CLI (`gh`) authenticated (for GitHub sources)

### What Users Do NOT Need

- Node.js (frontend is pre-built)
- Docker
- External server or cloud account
- Credential management beyond their existing CLI auth
- Runtime installation on a separate machine

---

# Future: SaaS Architecture (Design Record)

The following sections document the SaaS architecture design discussed
during development. This is not currently being implemented but is
preserved as a design record for when/if Phase 3 is pursued.

## SaaS Trust Problem

A hosted SaaS model introduces a fundamental trust issue. The worker
runs on the user's machine with an AI agent that has broad file system
access. Agent responses (transcripts) are transmitted to the server,
which is operated by a third party.

| | CI Runners (GitHub, Buildkite) | JakeOps Worker |
|--|-------------------------------|----------------|
| Execution environment | Dedicated CI machine / container | **User's personal machine** |
| Execution content | Deterministic workflow yaml | **AI agent (non-deterministic)** |
| Access scope | Repo + env vars | **Entire machine** |

Potential mitigations if SaaS is pursued:
- Container isolation (Docker) for worker execution
- `--allowedTools` restriction per phase
- Local audit logs of all data transmitted
- Interactive approval mode (opt-in)
- Dedicated machine guidance (not personal laptop)

Until these mitigations are validated, **self-hosted is the only mode**.

## SaaS Architecture Overview

JakeOps would separate **orchestration** from **execution**.

- **JakeOps Server (SaaS)** — UI, Delivery state, transcript storage, API
- **JakeOps Worker (user's machine)** — agent execution, local credentials

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

Two adapters, same protocol:

| Adapter | Where it runs | Used when |
|---------|--------------|-----------|
| `ClaudeCliAdapter` | Same machine as server | Self-hosted |
| `RemoteWorkerAdapter` | Server delegates to remote worker | SaaS |

Use case code does not change between modes. DI selects the adapter.

## SaaS Components

### JakeOps Server (SaaS)

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

### JakeOps Worker (SaaS)

Installed on the user's machine. Lightweight process that connects to the
SaaS server and executes agent tasks locally.

**Responsibilities:**
- Maintain WebSocket connection to server
- Receive execution requests (prompt, cwd, allowed_tools)
- Execute Claude CLI in headless or interactive mode
- Run git/gh operations with local credentials
- Stream results + transcript back to server

**Distribution:**
- PyPI package: `pip install jakeops-worker`
- Single command to connect: `jakeops-worker --token <token>`

### Worker Lifecycle (SaaS)

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
   - Headless: worker runs claude -p, streams stdout to server
   - Interactive: worker launches claude TUI, tails session file to server
   - Server receives events, saves transcript, updates Delivery state
7. Worker stays connected, waiting for next request
```

## SaaS Execution Flow

### Headless mode: plan phase

```
[Browser]                    [Server]                      [Worker]
    │                           │                              │
    ├── "Generate Plan" ───────→│                              │
    │                           ├── build prompt               │
    │                           │                              │
    │                           ├── RemoteWorkerAdapter        │
    │                           │   .run() ─────── prompt ───→ │
    │                           │                              ├── git clone (local)
    │                           │                              ├── claude -p --output-format stream-json
    │                           │   ◀── stream-json events ─── │   (stdout pipe)
    │                           │   ◀── result ─────────────── │
    │                           │                              │
    │                           ├── parse_stream_lines(events) │
    │                           ├── extract_metadata / transcript
    │                           ├── update delivery            │
    │   ◀── UI update ─────────┤                              │
```

### Interactive mode: plan phase

```
[User Terminal]              [Server]                      [Worker]
    │                           │                              │
    │                           ├── build prompt               │
    │                           │   .run() ─────── prompt ───→ │
    │                           │                              │
    │  ◀── claude "prompt" launches TUI ──────────────────────┤
    │   (user sees full execution,                             │
    │    can interact mid-run)                                 │
    │                           │                              │
    │                           │  ◀── tail session.jsonl ──── │
    │                           │      (parse_session_lines)   │
    │                           │  ◀── synthesize_result_event │
    │                           │                              │
    │                           ├── extract_metadata / transcript
    │                           ├── update delivery            │
    │   (Browser) ◀── UI update┤                              │
```

## SaaS Comparison with Industry

| Platform | Server | Local Agent | Install |
|----------|--------|-------------|---------|
| GitHub Actions | github.com | Self-hosted Runner | `./config.sh && ./run.sh` |
| Buildkite | buildkite.com | Buildkite Agent | `brew install buildkite-agent` |
| Tailscale | controlplane | Tailscale client | `brew install tailscale` |
| **JakeOps** | **jakeops.io** | **jakeops-worker** | **`pip install jakeops-worker`** |

## Worker Trust Strategy (SaaS)

The worker runs on the user's machine with access to local credentials and
tools. User resistance is expected and must be addressed deliberately.

### Open Source Model

Both server and worker are fully open source (Phase 1). When a hosted SaaS
is introduced, the worker remains open source regardless.

| Component | Phase 1 | Phase 3 (SaaS) |
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

## SaaS Deployment Modes

| Mode | Server | Worker | SubprocessRunner Adapter |
|------|--------|--------|-------------------------|
| **Self-hosted** | User's machine (Docker) | Same machine | `ClaudeCliAdapter` |
| **SaaS** | jakeraft cloud | `pip install jakeops-worker` | `RemoteWorkerAdapter` |

All modes share the same codebase. The only difference is which
`SubprocessRunner` adapter is injected via DI in `main.py`.

## SaaS Implementation Order

### Step 1: Worker protocol

- Define worker↔server message format (WebSocket)
- Implement `RemoteWorkerAdapter` (server side)
- Implement `jakeops-worker` CLI (client side, reuses `ClaudeCliAdapter`)
- Worker token generation in dashboard

### Step 2: SaaS deployment

- Server Docker image + CI pipeline
- Frontend CDN deployment
- Database migration (file-based → DB)
- Worker token auth + connection management

### Step 3: Multi-worker support

- Multiple workers per user (different machines/runtimes)
- Worker selection based on capability tags (e.g., "has Unity", "has CUDA")
- Worker health monitoring and reconnection
