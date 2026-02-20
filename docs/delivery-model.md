# Delivery Model

## Why "Delivery"

JakeOps needs a name for its core orchestration unit — the object that tracks
a change from intake through deployment to close. The term must:

1. Cover the **entire lifecycle**, not just one step.
2. Avoid collision with established tool concepts.
3. Be intuitive to engineers.

### Industry References

| System | Term | Scope |
|--------|------|-------|
| **DORA** | Change | Measured from commit to production |
| **Keptn** | Sequence | Ordered list of tasks in a lifecycle |
| **Argo Workflows** | Workflow | DAG of containers |
| **GitHub Actions** | Workflow Run | Single CI/CD execution |

"Change" is too generic and conflicts with git/DORA usage.
"Sequence" and "Workflow" imply execution mechanics rather than business intent.

**Delivery** captures the end-to-end intent: taking a change request and
delivering it through plan, implementation, review, verification, and
deployment. It is the natural answer to "what are we doing?" — delivering.

### Naming Collision Avoidance

- "Issue" — conflicts with GitHub Issues, Jira Issues (external tracker objects)
- "Ticket" — same collision
- "Pipeline" — conflicts with CI/CD pipeline (the infrastructure, not the instance)
- "Delivery" — no collision with common dev tool concepts

## Phase Model

Each Delivery progresses through an ordered sequence of phases:

```
intake → plan → implement → review → verify → deploy → observe → close
```

### Phase + RunStatus Separation

Two orthogonal axes describe a Delivery's state:

| Axis | Field | Question |
|------|-------|----------|
| **Phase** | `phase` | Where are we in the lifecycle? |
| **Run Status** | `run_status` | How is the current phase going? |

RunStatus values: `pending`, `running`, `succeeded`, `failed`, `blocked`.

### Executor

Two executor types: `system` and `agent`.

Human is **not** an executor. Human performs **actions** (approve, reject, retry, cancel)
at configured checkpoint phases. The distinction:

- **Executor**: who runs the phase (system or agent)
- **Action**: what human decides after a phase completes

### Verdict (Review)

The review phase is unique — the agent produces a **verdict** alongside the run_status:

| run_status | verdict | Meaning |
|------------|---------|---------|
| succeeded | pass | Code passed review |
| succeeded | not_pass | Code failed review (with feedback) |
| failed | — | Agent execution crashed |

This separation ensures we can distinguish "agent crashed" from "code didn't pass review".

### Endpoint

Not every Delivery needs the full pipeline.
`endpoint` controls where the lifecycle ends:

- Library repo → `endpoint: verify` (no deploy)
- Docs repo → `endpoint: review` (no CI)
- Default → `endpoint: deploy`

When `phase == endpoint` and `run_status == succeeded`, the Delivery
transitions directly to `close`.

### Checkpoints

`checkpoints` controls where the pipeline pauses for human action.
Checkpoint = Full Control:

- **checkpoint ON** → human must trigger (pending→running) AND approve (succeeded→next)
- **checkpoint OFF** → system auto-triggers AND auto-advances

Presets:
- Default → `checkpoints: ["plan", "implement", "review"]` (pause at every action phase)
- Trusted repo → `checkpoints: ["plan"]` (only review the plan)
- Full auto → `checkpoints: []` (no human intervention)

Both `endpoint` and `checkpoints` are configured at the Source level
and copied to each Delivery on creation.

## Transition Rules

### Forward (action phases)

Action phases (`plan`, `implement`, `review`) support human **approve**
to advance. The Delivery must have `run_status == succeeded`.

At non-checkpoint phases, the system auto-advances without human intervention.

### Reject

At action phases, human can **reject** to send the Delivery back:
- `plan` → `plan` (stays at plan/pending with reject reason preserved)
- `implement` → `plan`
- `review` → `implement`

### Retry

From `run_status == failed`, **retry** resets to `pending` in the same phase.

### Cancel

Sets `run_status = failed` with `error = "Canceled by user"`. Only allowed when
`run_status == running`. Kills the running agent subprocess. Phase unchanged.

## Auto-Flow Logic

### Intake

Deliveries are created at `intake/succeeded` and immediately advanced to
`plan/pending`. Intake is a system phase that completes at creation time.

### Phase Completion

```
Phase completed (succeeded):
  ├─ phase in checkpoints → PAUSE, wait for human action
  ├─ phase == endpoint → auto-advance to close
  └─ else → auto-advance to next phase
      ├─ next is system phase → auto-succeed, continue chain
      └─ next is agent phase → auto-trigger agent

Phase failed:
  └─ always PAUSE (human decides retry)

Review completed (succeeded):
  ├─ verdict = pass
  │   ├─ "review" in checkpoints → PAUSE
  │   └─ else → auto-advance
  └─ verdict = not_pass
      └─ auto-reject → implement (with feedback, always)
```

### Approve with Auto-Flow

When human approves at a checkpoint:
1. Advance to next phase
2. If next phase is a system phase (not a checkpoint), auto-succeed and repeat
3. If next phase is an agent phase (not a checkpoint), auto-trigger via background task
4. If next phase is a checkpoint, stop and wait

## Terminal State (computed)

```python
def is_terminal(delivery) -> bool:
    return delivery.phase == "close" and delivery.run_status == "succeeded"
```

## Schema

The canonical schema is defined in code: `backend/app/domain/models/delivery.py`.
Use `GET /api/deliveries/schema` for the JSON Schema endpoint.
