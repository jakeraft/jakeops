# JakeOps Architecture

System principle: **System repeats, Agent decides.**

## Responsibility Split

### System (deterministic)

- state machine and transition validation
- polling/retry/timeout orchestration
- external system calls and artifact persistence
- policy gates (approve/reject/retry/cancel)

### Agent (non-deterministic)

- implementation planning
- code changes
- failure analysis and fix suggestions
- run summaries

### Human

- gate approval/rejection on critical transitions

## Core Domain

### Delivery

Single orchestration unit for a delivery workflow.

- workflow phase (`phase`) + execution status (`run_status`)
- variable-length pipeline via `exit_phase`
- references (`refs`: trigger/output/parent)
- optional plan metadata
- run history and transcripts
- phase transition history (`phase_runs`)

### Source

Delivery ingestion source (currently GitHub repositories).

- owner/repo coordinates
- optional token
- active flag
- `default_exit_phase` for pipeline length control

### Worker status

In-memory status for background runners (currently delivery sync poller).

## Phase Model (v4)

```text
intake -> plan -> implement -> review -> verify -> deploy -> observe -> close
```

Each phase has an independent `run_status`: `pending | running | succeeded | failed | blocked | canceled`.

Gate phases requiring human approval: `plan`, `review`, `deploy`.

Actions:

- `approve` — advance past gate phase (requires `run_status == succeeded`)
- `reject` — revert to previous phase at gate
- `retry` — reset `run_status` to `pending` on same phase (from `failed`)
- `cancel` — set `run_status = canceled` (terminal)
- `generate-plan` — trigger plan generation (only from `intake`)

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
