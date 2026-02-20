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

RunStatus values: `pending`, `running`, `succeeded`, `failed`, `blocked`, `canceled`.

### Exit Phase

Not every Delivery needs the full pipeline.
`exit_phase` controls where the lifecycle ends:

- Library repo → `exit_phase: verify` (no deploy)
- Docs repo → `exit_phase: review` (no CI)
- Default → `exit_phase: deploy`

When `phase == exit_phase` and `run_status == succeeded`, the Delivery
transitions directly to `close`.

## Transition Rules

### Forward (gate phases)

Gate phases (`plan`, `review`, `deploy`) require explicit human **approve**
before advancing. The Delivery must have `run_status == succeeded`.

### Reject

At gate phases, human can **reject** to send the Delivery back:
- `plan` → `intake`
- `review` → `implement`
- `deploy` → `verify`

### Retry

From `run_status == failed`, **retry** resets to `pending` in the same phase.

### Cancel

Sets `run_status = canceled`. Phase unchanged. Terminal.

## Terminal State (computed)

```python
def is_terminal(delivery) -> bool:
    return (
        (delivery.phase == "close" and delivery.run_status == "succeeded")
        or delivery.run_status == "canceled"
    )
```

## Schema

The canonical schema is defined in code: `backend/app/domain/models/delivery.py`.
Use `GET /api/deliveries/schema` for the JSON Schema endpoint.
