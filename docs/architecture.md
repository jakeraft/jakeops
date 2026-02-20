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

### Issue

Single orchestration unit for a delivery workflow.

- lifecycle state (`status`)
- references (`refs`: trigger/output/parent)
- optional plan metadata
- run history and transcripts

### Source

Issue ingestion source (currently GitHub repositories).

- owner/repo coordinates
- optional token
- active flag

### Worker status

In-memory status for background runners (currently issue sync poller).

## Current State Model

```text
new -> planned -> approved -> implemented -> ci_passed -> deployed -> done
* -> failed
* -> canceled
```

Gate transitions currently exposed by API actions:

- `approve`
- `reject`
- `retry`
- `cancel`
- `generate-plan`

## Runtime Components

- FastAPI backend (`backend/app/main.py`)
- React frontend (`frontend/src`)
- file-based repositories (`issues/`, `sources/`)
- GitHub polling loop (`IssueSyncUseCase`)

## API Surface (current)

- `/api/issues/*`
- `/api/sources/*`
- `/api/worker/status`

## Evolution Path

- formal phase model (`phase` + `run_status`)
- stronger actor attribution (`system|agent|human`)
- deeper CI/CD provider integrations
- move persistence from local files to DB/object storage
