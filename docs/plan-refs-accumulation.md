# Refs-based Context Accumulation

## Context

Current agent prompts pass only `summary` text, which is effectively useless.
As a DevOps pipeline, context should accumulate through refs as phases complete.
Each phase's output (PR URL, commits, etc.) becomes the next phase's input.

The fix flow is redundant — frontend already treats it the same as implement.
When review rejects, the implement agent sees the PR with review comments naturally.

## Principle

JakeOps prompts follow a minimal principle:
- **system prompt**: what to do (one-liner role)
- **user prompt**: refs URLs (accumulated context)
- **cwd**: cloned repo + user's CLAUDE.md

Never tell the agent HOW to work.

## Ref Accumulation Flow

```
intake:     refs = [trigger: issue URL]
                ↓
plan:       agent reads issue URL, produces plan
            → create branch jakeops/{id}, commit plan
            → create draft PR
            → refs += [output:pr → PR URL]
                ↓
implement:  agent checks out PR branch, reads PR + issue
            → implements changes, pushes commits
            → refs += [output:commit → commit URLs] (future)
                ↓
review:     agent checks out PR branch, reads PR diff
            → produces review verdict
                ↓ (reject)
implement:  agent sees PR with review comments + reject_reason
            → fixes and pushes
                ↓ (approve)
verify → deploy → observe → close
```

## Changes

### 1. Remove Fix Flow

- Delete: `FIX_SYSTEM_PROMPT`, `build_fix_prompt`
- Delete: `run_fix` method, `/run-fix` endpoint, `RunFixBody`
- Delete: `run_fix` from Protocol
- Delete: related tests

### 2. Refs-based Prompts

Add `_collect_ref_urls(delivery, role=None)` helper.
All builders extract URLs from refs as `## References` section.

```python
def build_plan_prompt(delivery):     # summary + trigger URLs
def build_implement_prompt(delivery): # summary + all URLs + plan + reject_reason
def build_review_prompt(delivery):    # summary + all URLs
```

implement includes `reject_reason` when present → fix is unnecessary.

### 3. Git: checkout_branch

Add to Protocol and GitCliAdapter:

```python
def checkout_branch(self, cwd: str, branch: str) -> None:
    git fetch origin {branch} && git checkout {branch}
```

### 4. Draft PR on Plan Success

After `generate_plan` succeeds:
1. `create_branch_with_file` → `jakeops/{delivery_id}` branch with plan
2. `create_draft_pr` → draft PR
3. Append `output:pr` ref with PR URL

Failure is non-fatal (warning log, plan still succeeds).

### 5. Branch-aware Agent Execution

Add `branch` param to `_run_agent_phase`.
After clone: `checkout_branch(work_dir, branch)`.

- `run_implement`: checkout PR branch if `output:pr` ref exists
- `run_review`: same

### 6. Cleanup reject_reason

On `_run_agent_phase` success: `delivery.pop("reject_reason", None)`.

## Files to Modify

| File | Change |
|------|--------|
| `backend/app/domain/prompts.py` | Remove fix, refs-based builders |
| `backend/app/usecases/delivery_usecases.py` | Remove fix, draft PR, branch-aware |
| `backend/app/ports/inbound/delivery_usecases.py` | Remove `run_fix` |
| `backend/app/ports/outbound/git_operations.py` | Add `checkout_branch` |
| `backend/app/adapters/outbound/git_cli.py` | Implement `checkout_branch` |
| `backend/app/adapters/inbound/deliveries.py` | Remove `/run-fix` endpoint |
| `backend/tests/test_agent_execution.py` | Remove fix tests, add ref tests |
| `backend/tests/test_prompts.py` | Update prompt tests |
| `backend/tests/test_deliveries_api.py` | Remove fix endpoint tests |
