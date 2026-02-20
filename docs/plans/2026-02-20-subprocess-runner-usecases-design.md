# SubprocessRunner Use Cases Extension Design

Refs: https://github.com/jakeraft/jakeops/issues/3

## Problem

Agent execution is limited to plan validation only. `generate_plan` checks
the phase but never calls `SubprocessRunner`. The `ClaudeCliAdapter` exists
and works, but is not injected into the use case layer.

## Decision

Extend `DeliveryUseCasesImpl` to drive `SubprocessRunner` for plan,
implement, review, and fix phases. Each method builds a phase-appropriate
prompt, calls the runner, and saves the result as an AgentRun with transcript.

## Architecture

```
API Endpoint (trigger)
  -> UseCase (phase logic + prompt template)
    -> GitOperations (clone repo to temp dir)
    -> SubprocessRunner (phase-agnostic execution)
    -> DeliveryRepository (save run + transcript)
```

Key principle: executors do not know which phase they serve. Phase logic
and prompt templates live in the use case layer.

## Components

### 1. domain/prompts.py (new)

Phase-specific prompt templates extracted from the use case layer.

- `build_plan_prompt(issue_title, issue_url, owner, repo, issue_body)` — analyze
  codebase and generate implementation plan (read-only tools)
- `build_implement_prompt(plan_content, summary)` — implement changes based on
  approved plan (all tools)
- `build_review_prompt(summary)` — review changes for quality (read-only tools)
- `build_fix_prompt(review_feedback)` — fix issues from review feedback (all tools)

### 2. usecases/delivery_usecases.py (modified)

Constructor takes `SubprocessRunner` and `GitOperations` in addition to
`DeliveryRepository`.

New/modified methods:

- `generate_plan(delivery_id)` — transitions intake->plan, clones repo,
  runs plan prompt, saves plan + transcript, sets run_status=succeeded
- `run_implement(delivery_id)` — validates phase=implement+pending, clones
  repo, runs implement prompt, saves transcript, sets run_status=succeeded
- `run_review(delivery_id)` — validates phase=review+pending, runs review
  prompt on repo, saves transcript, sets run_status=succeeded
- `run_fix(delivery_id)` — validates phase=implement (after reject from
  review), runs fix prompt, saves transcript

Common pattern for all methods:
1. Load delivery, validate phase + run_status
2. Set run_status=running
3. Clone repo via GitOperations (temp dir)
4. Build phase-specific prompt
5. Call SubprocessRunner.run_with_stream(prompt, cwd)
6. Parse metadata + transcript from stream events
7. Save AgentRun to delivery.runs[]
8. Save transcript to run-{id}.transcript.json
9. Set run_status=succeeded (or failed on error)

### 3. ports/inbound/delivery_usecases.py (modified)

Add protocol methods: `generate_plan`, `run_implement`, `run_review`, `run_fix`.
Note: `generate_plan` already exists but its signature changes (now async).

### 4. adapters/inbound/deliveries.py (modified)

New endpoints:
- `POST /api/deliveries/{id}/run-implement`
- `POST /api/deliveries/{id}/run-review`
- `POST /api/deliveries/{id}/run-fix`

Existing endpoint modified:
- `POST /api/deliveries/{id}/generate-plan` — now triggers actual execution

### 5. adapters/outbound/claude_cli.py (modified)

Remove `PLAN_PROMPT_TEMPLATE` and `SYSTEM_PROMPT` constants (moved to
domain/prompts.py). ClaudeCliAdapter becomes a pure SubprocessRunner
implementation with no phase knowledge.

### 6. main.py (modified)

Inject `ClaudeCliAdapter` and `GitCliAdapter` into `DeliveryUseCasesImpl`:

```python
runner = ClaudeCliAdapter()
git_ops = GitCliAdapter()
app.state.delivery_usecases = DeliveryUseCasesImpl(delivery_repo, runner, git_ops)
```

## Execution Flow (generate_plan)

```
POST /api/deliveries/{id}/generate-plan
  -> validate: phase=intake
  -> set phase=plan, run_status=running
  -> clone repo to /tmp/jakeops-work-{id}/
  -> build_plan_prompt(issue info)
  -> SubprocessRunner.run_with_stream(prompt, cwd, allowed_tools=["Read","Glob","Grep","LS"], system_prompt=plan_system)
  -> extract_metadata(events) + extract_transcript(events)
  -> save AgentRun + transcript
  -> set plan content, run_status=succeeded
  -> (or run_status=failed + error message on exception)
```

## Execution Flow (run_implement)

```
POST /api/deliveries/{id}/run-implement
  -> validate: phase=implement, run_status=pending
  -> set run_status=running
  -> clone repo to /tmp/jakeops-work-{id}/
  -> build_implement_prompt(plan_content, summary)
  -> SubprocessRunner.run_with_stream(prompt, cwd)  // all tools
  -> extract_metadata(events) + extract_transcript(events)
  -> save AgentRun + transcript
  -> set run_status=succeeded
```

## Error Handling

- SubprocessRunner failure (timeout, non-zero exit) -> run_status=failed, error field set
- Clone failure -> run_status=failed, error field set
- Failed runs retryable via existing `retry` action (resets to pending)
- Temp directory cleaned up in finally block

## Out of Scope

- verify/deploy/observe phase execution (CI/CD integration, issue #4)
- Multi-agent coordination within a phase
- Remote execution environments
- Configurable timeout/cost limits (hardcoded for now)
