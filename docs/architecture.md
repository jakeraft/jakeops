# JakeOps Architecture

System principle: **System repeats, Agent decides.**

## Responsibility Split

### System (deterministic)

- state machine and transition validation
- polling/retry/timeout orchestration
- external system calls and artifact persistence
- auto-advance between phases (non-checkpoint phases)

### Agent (non-deterministic)

- implementation planning
- code changes
- code review and verdict (pass/not_pass)
- failure analysis and fix suggestions
- run summaries

### Human

- actions at checkpoint phases (approve/reject/retry/cancel)
- pipeline configuration (endpoint, checkpoints)

## Core Domain

### Delivery

Single orchestration unit for a delivery workflow.

- workflow phase (`phase`) + execution status (`run_status`)
- variable-length pipeline via `endpoint`
- configurable pause points via `checkpoints`
- references (`refs`: trigger/output/parent)
- optional plan metadata
- run history and transcripts
- phase transition history (`phase_runs`)

### Source

Delivery ingestion source (currently GitHub repositories).

- owner/repo coordinates
- optional token
- active flag
- `endpoint` for pipeline length control
- `checkpoints` for pause point configuration

### Worker status

In-memory status for background runners (currently delivery sync poller).

## State Machine

### Phase Pipeline

```text
intake -> plan -> implement -> review -> verify -> deploy -> observe -> close
```

### Two-Dimensional State

Each Delivery has two orthogonal state axes:

| Axis | Field | Question |
|------|-------|----------|
| Phase | `phase` | Where are we in the lifecycle? |
| Run Status | `run_status` | How is the current phase going? |

RunStatus values: `pending | running | succeeded | failed | blocked`.

### Executor

Each phase has a default executor:

| Phase | Executor | Description |
|-------|----------|-------------|
| intake | system | Auto-detected from source sync |
| plan | agent | AI generates implementation plan |
| implement | agent | AI writes code changes |
| review | agent | AI reviews code, produces verdict |
| verify | system | CI/CD runs tests |
| deploy | system | CI/CD deploys |
| observe | system | Monitoring |
| close | system | Terminal |

Only two executor types exist: `system` and `agent`.
Human is not an executor — human performs **actions** at checkpoint phases.

### Verdict (Review Phase)

Review is unique: the agent produces a **verdict** in addition to run_status.

- `run_status` tracks execution: did the agent complete its work?
- `verdict` tracks business outcome: did the code pass review?

| run_status | verdict | Meaning |
|------------|---------|---------|
| succeeded | pass | Agent reviewed, code passed |
| succeeded | not_pass | Agent reviewed, code failed review |
| failed | — | Agent crashed/errored |

### Actions

Human actions are available at **action phases** (`plan`, `implement`, `review`):

| Phase | run_status | Action | Result |
|-------|-----------|--------|--------|
| plan | succeeded | approve | → implement (running) |
| plan | failed | retry | → plan (pending) |
| implement | succeeded | approve | → review (running) |
| implement | succeeded | reject | → plan (pending) |
| implement | failed | retry | → implement (pending) |
| review | succeeded + pass | approve | → verify (pending) |
| review | succeeded + not_pass | reject | → implement (pending, with feedback) |
| review | failed | retry | → review (pending) |
| any | running | cancel | → failed (error: "Canceled by user") |

### Checkpoints and Endpoint

Two Source-level configurations control pipeline behavior:

| Setting | Purpose | Default |
|---------|---------|---------|
| `endpoint` | Where the pipeline ends | `"deploy"` |
| `checkpoints` | Where the pipeline pauses for human action | `["plan", "implement", "review"]` |

**Auto-flow rule**: when a phase completes (succeeded), the pipeline automatically
advances to the next phase **unless** the current phase is in `checkpoints`.
If the current phase equals `endpoint`, it advances to `close`.

**Failed phases always pause** regardless of checkpoint configuration.

**Review verdict=not_pass auto-rejects** to implement regardless of checkpoints.

### Flow Diagram

```text
                         reject
                    ┌───────────────┐
                    ▼               │
 [intake] ──→ [plan] ──approve──→ [implement] ──approve──→ [review]
  system       agent    (action)     agent       (action)    agent
                                       ▲                      │
                                       │    reject (not_pass)  │
                                       └──────────────────────┘
                                                              │
                                              approve (pass)  │
                                                              ▼
                                                          [verify]
                                                           system
                                                              │
              [close] ←── [observe] ←── [deploy] ←───────────┘
              system       system        system

Legend:
  ── auto-advance (no checkpoint)
  ──action──  pauses at checkpoint for human action
  Dashed paths depend on checkpoint configuration
```

### Terminal State

```python
def is_terminal(delivery) -> bool:
    return delivery.phase == "close" and delivery.run_status == "succeeded"
```

## Runtime Components

- FastAPI backend (`backend/app/main.py`)
- React frontend (`frontend/src`)
- file-based repositories (`deliveries/`, `sources/`)
- GitHub polling loop (`DeliverySyncUseCase`)

## API Surface (current)

- `/api/deliveries/*`
- `/api/sources/*`
- `/api/worker/status`

## Evolution Path

- deeper CI/CD provider integrations
- move persistence from local files to DB/object storage
