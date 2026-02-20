# Refs-based Context Accumulation

## Principle

GitHub is the single source of truth. Agent reads all context from URLs.

JakeOps prompts follow a minimal principle:
- **system prompt**: what to do (one-liner role)
- **user prompt**: summary + all ref URLs
- **cwd**: cloned repo + user's CLAUDE.md

Never tell the agent HOW to work. Never duplicate context into prompts.

## Ref Roles

| Role | Meaning | Example |
|------|---------|---------|
| `request` | What initiated this delivery | Issue URL, Jira ticket |
| `work` | Where the work happens | Draft PR URL |
| `parent` | Parent delivery reference | Parent delivery URL |

## Ref Accumulation Flow

```
intake:     refs = [request: issue URL]
                ↓
plan:       agent reads issue URL, produces plan
            → create branch jakeops/{id}, commit plan
            → create draft PR
            → refs += [work:pr → PR URL]
                ↓
implement:  agent checks out PR branch, reads PR + issue
            → implements changes, pushes commits
                ↓
review:     agent checks out PR branch, reads PR diff
            → produces review verdict
                ↓ (reject)
implement:  agent sees PR with review comments naturally
            → fixes and pushes
                ↓ (approve)
verify → deploy → observe → close
```

## Unified Prompt Builder

All phases use the same `build_prompt(delivery)`:

```python
def build_prompt(delivery: dict) -> str:
    urls = _collect_ref_urls(delivery)
    return f"{delivery['summary']}{_refs_section(urls)}"
```

No phase-specific builders. No `plan.content` injection. No `reject_reason` injection.
Agent reads plan from PR branch (`docs/plan.md`), review feedback from PR comments.

## Key Design Decisions

1. **No reject_reason field** — rejection feedback lives in PR thread comments
2. **No plan.content in prompt** — plan is committed to PR branch, agent reads it from cwd
3. **Single prompt builder** — all phases get summary + all ref URLs
4. **GitHub threads as context** — issue thread for requirements, PR thread for work history
