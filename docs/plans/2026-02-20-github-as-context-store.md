# GitHub as Context Store — Prompt Simplification Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Simplify agent prompts so GitHub (issue thread + PR thread) is the single source of truth, eliminating redundant context duplication in prompts.

**Architecture:** Remove `reject_reason` from delivery model, unify 3 prompt builders into 1 (`build_prompt`), stop injecting `plan.content` into prompts. Agent reads all context directly from GitHub URLs in refs.

**Tech Stack:** Python / FastAPI / Pydantic v2 / pytest

---

### Task 1: Unify prompt builders + remove reject_reason from prompts

**Files:**
- Modify: `backend/app/domain/prompts.py` (full rewrite — 78 lines)
- Modify: `backend/tests/test_prompts.py` (full rewrite — 111 lines)

**Step 1: Write the failing tests**

Replace `backend/tests/test_prompts.py` entirely:

```python
from app.domain.prompts import build_prompt, _collect_ref_urls


def _delivery(**overrides) -> dict:
    base = {
        "summary": "Fix login bug",
        "repository": "owner/repo",
        "refs": [{"role": "trigger", "type": "github_issue", "label": "#1",
                  "url": "https://github.com/owner/repo/issues/1"}],
    }
    base.update(overrides)
    return base


class TestCollectRefUrls:
    def test_all_urls(self):
        d = _delivery(refs=[
            {"role": "trigger", "url": "https://a"},
            {"role": "output", "type": "pr", "url": "https://b"},
        ])
        assert _collect_ref_urls(d) == ["https://a", "https://b"]

    def test_filter_by_role(self):
        d = _delivery(refs=[
            {"role": "trigger", "url": "https://a"},
            {"role": "output", "type": "pr", "url": "https://b"},
        ])
        assert _collect_ref_urls(d, role="trigger") == ["https://a"]

    def test_skips_empty_urls(self):
        d = _delivery(refs=[{"role": "trigger"}])
        assert _collect_ref_urls(d) == []


class TestBuildPrompt:
    def test_includes_summary(self):
        result = build_prompt(_delivery())
        assert "Fix login bug" in result

    def test_includes_trigger_url(self):
        result = build_prompt(_delivery())
        assert "https://github.com/owner/repo/issues/1" in result

    def test_no_refs(self):
        result = build_prompt(_delivery(refs=[]))
        assert "Fix login bug" in result
        assert "References" not in result

    def test_includes_all_ref_urls(self):
        d = _delivery(refs=[
            {"role": "trigger", "url": "https://issue"},
            {"role": "output", "type": "pr", "url": "https://pr"},
        ])
        result = build_prompt(d)
        assert "https://issue" in result
        assert "https://pr" in result

    def test_ignores_plan_content(self):
        """build_prompt does NOT inject plan.content — agent reads it from PR."""
        d = _delivery(plan={"content": "SECRET_PLAN", "generated_at": "", "model": "", "cwd": ""})
        result = build_prompt(d)
        assert "SECRET_PLAN" not in result

    def test_ignores_reject_reason(self):
        """build_prompt does NOT inject reject_reason — feedback lives in PR thread."""
        d = _delivery(reject_reason="Missing error handling")
        result = build_prompt(d)
        assert "Missing error handling" not in result
```

**Step 2: Run tests to verify they fail**

Run: `cd backend && python -m pytest tests/test_prompts.py -v`
Expected: FAIL — `build_prompt` not found, old imports still exist

**Step 3: Write the unified prompt builder**

Replace `backend/app/domain/prompts.py`:

```python
"""Phase-specific prompt templates for agent execution.

JakeOps prompts follow a minimal principle:
- system prompt: what to do (one-liner role)
- user prompt: summary + refs URLs (agent reads full context from GitHub)
- cwd: cloned repo + user's CLAUDE.md

Never tell the agent HOW to do its job.
"""

_NON_INTERACTIVE = (
    "You are running non-interactively in a CI pipeline. "
    "Do NOT ask questions, request clarification, or present options. "
    "Complete the task fully and return the result directly."
)

PLAN_SYSTEM_PROMPT = (
    f"Analyze this codebase and produce an implementation plan. {_NON_INTERACTIVE}"
)

REVIEW_SYSTEM_PROMPT = (
    f"Review the recent changes in this repository. {_NON_INTERACTIVE}"
)

IMPLEMENT_SYSTEM_PROMPT = (
    f"Implement the changes described in the plan. {_NON_INTERACTIVE}"
)


def _collect_ref_urls(delivery: dict, role: str | None = None) -> list[str]:
    """Extract URLs from refs, optionally filtered by role."""
    urls = []
    for ref in delivery.get("refs", []):
        if role and ref.get("role") != role:
            continue
        url = ref.get("url", "")
        if url:
            urls.append(url)
    return urls


def _refs_section(urls: list[str]) -> str:
    if not urls:
        return ""
    lines = "\n".join(f"- {url}" for url in urls)
    return f"\n\n## References\n{lines}"


def build_prompt(delivery: dict) -> str:
    """Unified prompt builder — summary + all ref URLs.

    Agent reads full context (plan, review feedback, etc.)
    directly from GitHub issue/PR threads via the URLs.
    """
    urls = _collect_ref_urls(delivery)
    return f"{delivery['summary']}{_refs_section(urls)}"
```

**Step 4: Run tests to verify they pass**

Run: `cd backend && python -m pytest tests/test_prompts.py -v`
Expected: PASS (all 9 tests)

**Step 5: Commit**

```
git add backend/app/domain/prompts.py backend/tests/test_prompts.py
git commit -m "refactor: unify prompt builders into single build_prompt

GitHub issue/PR threads are the single source of truth.
Agent reads plan, review feedback, etc. directly from URLs.
Remove plan.content injection and reject_reason from prompts."
```

---

### Task 2: Update usecases to use unified build_prompt

**Files:**
- Modify: `backend/app/usecases/delivery_usecases.py:13-16` (imports), `:482`, `:552`, `:579`

**Step 1: Update imports and call sites**

In `delivery_usecases.py`, change:

```python
# OLD (lines 13-20)
from app.domain.prompts import (
    build_plan_prompt,
    build_implement_prompt,
    build_review_prompt,
    PLAN_SYSTEM_PROMPT,
    IMPLEMENT_SYSTEM_PROMPT,
    REVIEW_SYSTEM_PROMPT,
)

# NEW
from app.domain.prompts import (
    build_prompt,
    PLAN_SYSTEM_PROMPT,
    IMPLEMENT_SYSTEM_PROMPT,
    REVIEW_SYSTEM_PROMPT,
)
```

Then replace three call sites:
- Line 482: `build_plan_prompt(existing)` → `build_prompt(existing)`
- Line 552: `build_implement_prompt(existing)` → `build_prompt(existing)`
- Line 579: `build_review_prompt(existing)` → `build_prompt(existing)`

**Step 2: Run all backend tests**

Run: `cd backend && python -m pytest -v`
Expected: PASS (except reject_reason tests — will fix in Task 3)

**Step 3: Commit**

```
git add backend/app/usecases/delivery_usecases.py
git commit -m "refactor: use unified build_prompt in all agent phases"
```

---

### Task 3: Remove reject_reason from delivery model and usecases

**Files:**
- Modify: `backend/app/domain/models/delivery.py:107` — remove `reject_reason` field
- Modify: `backend/app/usecases/delivery_usecases.py:320`, `:441` — remove reject_reason storage/cleanup
- Modify: `backend/tests/test_delivery_usecases.py:192-196` — remove test
- Modify: `backend/tests/test_agent_execution.py:237-249` — remove TestRejectReasonCleanup class
- Modify: `frontend/src/types.ts:56` — remove `reject_reason` field

**Step 1: Remove from delivery model**

In `backend/app/domain/models/delivery.py`, delete line 107:
```python
    reject_reason: str | None = None
```

**Step 2: Remove from usecases**

In `delivery_usecases.py`:
- Line 320: delete `existing["reject_reason"] = reason`
- Line 441: delete `delivery.pop("reject_reason", None)`

**Step 3: Remove tests**

In `test_delivery_usecases.py`, delete the `test_reject_stores_reason` test (lines 192-196).

In `test_agent_execution.py`, delete the entire `TestRejectReasonCleanup` class (lines 237-249).

**Step 4: Remove from frontend type**

In `frontend/src/types.ts`, delete line 56:
```typescript
  reject_reason?: string
```

**Step 5: Run all tests**

Run: `cd backend && python -m pytest -v`
Run: `cd frontend && npm run test`
Expected: ALL PASS

**Step 6: Commit**

```
git add -A
git commit -m "refactor: remove reject_reason from delivery model

Rejection feedback now lives in GitHub PR thread comments.
Agent reads feedback directly from PR URL in refs."
```

---

### Task 4: Update plan-refs-accumulation doc

**Files:**
- Modify: `docs/plan-refs-accumulation.md`

**Step 1: Update doc to reflect new architecture**

Replace the `## Changes` section onward to remove references to `reject_reason` in prompt builders and note the unified `build_prompt`. Mark completed items.

**Step 2: Commit**

```
git add docs/plan-refs-accumulation.md
git commit -m "docs: update refs accumulation doc for unified prompt architecture"
```
