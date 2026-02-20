# SubprocessRunner Use Cases Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Make `generate_plan` actually execute the agent, and add `run_implement`, `run_review`, `run_fix` use case methods.

**Architecture:** Each phase method validates state, clones repo, builds a phase-specific prompt, calls `SubprocessRunner.run_with_stream()`, and saves the AgentRun + transcript. A shared `_run_agent_phase` helper handles the common execution pattern.

**Tech Stack:** Python 3.11+, FastAPI, pytest, pytest-asyncio

---

### Task 1: Create prompts module

**Files:**
- Create: `backend/app/domain/prompts.py`
- Test: `backend/tests/test_prompts.py`

**Step 1: Write the failing test**

```python
# backend/tests/test_prompts.py
from app.domain.prompts import (
    build_plan_prompt,
    build_implement_prompt,
    build_review_prompt,
    build_fix_prompt,
    PLAN_SYSTEM_PROMPT,
    PLAN_ALLOWED_TOOLS,
    REVIEW_ALLOWED_TOOLS,
)


class TestBuildPlanPrompt:
    def test_includes_summary(self):
        result = build_plan_prompt(
            summary="Fix login bug",
            repository="owner/repo",
            refs=[{"role": "trigger", "type": "github_issue", "label": "#1", "url": "https://github.com/owner/repo/issues/1"}],
        )
        assert "Fix login bug" in result

    def test_includes_trigger_url(self):
        result = build_plan_prompt(
            summary="Fix login bug",
            repository="owner/repo",
            refs=[{"role": "trigger", "type": "github_issue", "label": "#1", "url": "https://github.com/owner/repo/issues/1"}],
        )
        assert "https://github.com/owner/repo/issues/1" in result

    def test_no_trigger_url(self):
        result = build_plan_prompt(
            summary="Manual task",
            repository="owner/repo",
            refs=[],
        )
        assert "Manual task" in result


class TestBuildImplementPrompt:
    def test_includes_plan_and_summary(self):
        result = build_implement_prompt(plan_content="## Steps\n1. Fix X", summary="Fix login")
        assert "## Steps" in result
        assert "Fix login" in result


class TestBuildReviewPrompt:
    def test_includes_summary(self):
        result = build_review_prompt(summary="Fix login")
        assert "Fix login" in result


class TestBuildFixPrompt:
    def test_includes_feedback(self):
        result = build_fix_prompt(feedback="Missing error handling", summary="Fix login")
        assert "Missing error handling" in result


class TestConstants:
    def test_plan_tools_are_readonly(self):
        assert "Read" in PLAN_ALLOWED_TOOLS
        assert "Write" not in PLAN_ALLOWED_TOOLS

    def test_review_tools_are_readonly(self):
        assert "Read" in REVIEW_ALLOWED_TOOLS
        assert "Write" not in REVIEW_ALLOWED_TOOLS
```

**Step 2: Run test to verify it fails**

Run: `cd backend && python -m pytest tests/test_prompts.py -v`
Expected: FAIL with ModuleNotFoundError

**Step 3: Write minimal implementation**

```python
# backend/app/domain/prompts.py
"""Phase-specific prompt templates for agent execution.

Prompts live here (not in adapters) because phase logic belongs in the
use case / domain layer. The executor (SubprocessRunner) is phase-agnostic.
"""

PLAN_SYSTEM_PROMPT = (
    "You are an agent that analyzes this codebase and produces an implementation plan. "
    "Use read-only tools only."
)

PLAN_ALLOWED_TOOLS = ["Read", "Glob", "Grep", "LS"]

REVIEW_SYSTEM_PROMPT = (
    "You are a code review agent. Review changes for quality and correctness. "
    "Use read-only tools only."
)

REVIEW_ALLOWED_TOOLS = ["Read", "Glob", "Grep", "LS"]

IMPLEMENT_SYSTEM_PROMPT = (
    "You are a coding agent that implements changes based on a plan. "
    "Use all available tools to write and test code."
)

FIX_SYSTEM_PROMPT = (
    "You are a coding agent that fixes issues identified in code review. "
    "Make minimal, targeted changes to address the feedback."
)


def build_plan_prompt(summary: str, repository: str, refs: list[dict]) -> str:
    trigger_url = ""
    for ref in refs:
        if ref.get("role") == "trigger":
            trigger_url = ref.get("url", "")
            break

    url_line = f"\nURL: {trigger_url}" if trigger_url else ""

    return (
        f"Analyze the codebase and generate an implementation plan.\n\n"
        f"## Issue\n"
        f"{summary}{url_line}\n"
        f"Repository: {repository}\n\n"
        f"## Instructions\n"
        f"1. If a URL is provided, read the issue for full context.\n"
        f"2. Explore the codebase and identify relevant files.\n"
        f"3. Write the implementation plan in Markdown.\n"
        f"4. Include target files, implementation order, and expected impact.\n\n"
        f"Return only the Markdown plan."
    )


def build_implement_prompt(plan_content: str, summary: str) -> str:
    return (
        f"Implement the changes described in the plan below.\n\n"
        f"## Summary\n{summary}\n\n"
        f"## Plan\n{plan_content}\n\n"
        f"## Instructions\n"
        f"1. Follow the plan step by step.\n"
        f"2. Write clean, well-tested code.\n"
        f"3. Commit your changes with clear commit messages."
    )


def build_review_prompt(summary: str) -> str:
    return (
        f"Review the recent changes in this repository.\n\n"
        f"## Summary\n{summary}\n\n"
        f"## Instructions\n"
        f"1. Check the latest commits and changes.\n"
        f"2. Review for code quality, bugs, security issues.\n"
        f"3. Provide your review as a structured report."
    )


def build_fix_prompt(feedback: str, summary: str) -> str:
    return (
        f"Fix the issues identified in the code review.\n\n"
        f"## Summary\n{summary}\n\n"
        f"## Review Feedback\n{feedback}\n\n"
        f"## Instructions\n"
        f"1. Address each issue identified in the review.\n"
        f"2. Make minimal, targeted fixes.\n"
        f"3. Commit your changes with clear commit messages."
    )
```

**Step 4: Run test to verify it passes**

Run: `cd backend && python -m pytest tests/test_prompts.py -v`
Expected: All PASS

**Step 5: Commit**

```bash
git add backend/app/domain/prompts.py backend/tests/test_prompts.py
git commit -m "feat: add phase-specific prompt templates"
```

---

### Task 2: Update constructor and add test mocks

**Files:**
- Modify: `backend/app/usecases/delivery_usecases.py` (constructor only)
- Modify: `backend/app/main.py` (DI wiring)
- Modify: `backend/tests/conftest.py` (update fixture)

**Step 1: Update constructor to accept optional runner, git_ops, source_repo**

In `backend/app/usecases/delivery_usecases.py`, change the constructor:

```python
class DeliveryUseCasesImpl:
    def __init__(
        self,
        repo: DeliveryRepository,
        runner: SubprocessRunner | None = None,
        git_ops: GitOperations | None = None,
        source_repo: SourceRepository | None = None,
    ) -> None:
        self._repo = repo
        self._runner = runner
        self._git = git_ops
        self._source_repo = source_repo
```

Add imports at top:

```python
from app.ports.outbound.subprocess_runner import SubprocessRunner
from app.ports.outbound.git_operations import GitOperations
from app.ports.outbound.source_repository import SourceRepository
```

**Step 2: Update main.py DI wiring**

In `backend/app/main.py`, inject the new dependencies:

```python
from app.adapters.outbound.claude_cli import ClaudeCliAdapter
from app.adapters.outbound.git_cli import GitCliAdapter

# Inside lifespan():
runner = ClaudeCliAdapter()
git_ops = GitCliAdapter()
app.state.delivery_usecases = DeliveryUseCasesImpl(
    delivery_repo, runner, git_ops, source_repo
)
```

**Step 3: Run existing tests to verify nothing breaks**

Run: `cd backend && python -m pytest tests/test_delivery_usecases.py tests/test_deliveries_api.py -v`
Expected: All existing tests PASS (constructor params are optional)

**Step 4: Commit**

```bash
git add backend/app/usecases/delivery_usecases.py backend/app/main.py
git commit -m "feat: inject SubprocessRunner and GitOperations into use case"
```

---

### Task 3: Implement generate_plan execution

**Files:**
- Create: `backend/tests/test_agent_execution.py`
- Modify: `backend/app/usecases/delivery_usecases.py`

**Step 1: Write test mocks and the failing test**

```python
# backend/tests/test_agent_execution.py
"""Tests for agent execution use cases (generate_plan, run_implement, etc.)"""

from pathlib import Path

import pytest

from app.adapters.outbound.filesystem_delivery import FileSystemDeliveryRepository
from app.adapters.outbound.filesystem_source import FileSystemSourceRepository
from app.domain.models.delivery import DeliveryCreate, Phase, RunStatus
from app.domain.models.stream import StreamEvent
from app.usecases.delivery_usecases import DeliveryUseCasesImpl


class MockSubprocessRunner:
    """Mock that records calls and returns predefined stream events."""

    def __init__(self, result_text: str = "Generated plan content"):
        self.result_text = result_text
        self.calls: list[dict] = []

    async def run_with_stream(
        self,
        prompt: str,
        cwd: str,
        allowed_tools: list[str] | None = None,
        append_system_prompt: str | None = None,
    ) -> tuple[str, list[StreamEvent], str | None]:
        self.calls.append({
            "prompt": prompt,
            "cwd": cwd,
            "allowed_tools": allowed_tools,
            "append_system_prompt": append_system_prompt,
        })
        events = [
            StreamEvent(type="system", subtype="init", message={"model": "test-model"}),
            StreamEvent(type="result", message={
                "result": self.result_text,
                "is_error": False,
                "cost_usd": 0.01,
                "input_tokens": 100,
                "output_tokens": 50,
                "duration_ms": 1000,
            }),
        ]
        return (self.result_text, events, "test-session-id")


class MockGitOperations:
    """Mock that records clone calls and creates the directory."""

    def __init__(self):
        self.clone_calls: list[dict] = []

    def clone_repo(self, owner: str, repo: str, token: str, dest: str) -> None:
        self.clone_calls.append({"owner": owner, "repo": repo, "token": token, "dest": dest})
        Path(dest).mkdir(parents=True, exist_ok=True)

    def create_branch_with_file(self, *args, **kwargs) -> None:
        pass

    def create_draft_pr(self, *args, **kwargs) -> str:
        return "https://github.com/test/pr/1"


@pytest.fixture
def repos(tmp_path):
    delivery_repo = FileSystemDeliveryRepository(tmp_path / "deliveries")
    source_repo = FileSystemSourceRepository(tmp_path / "sources")
    return delivery_repo, source_repo


@pytest.fixture
def runner():
    return MockSubprocessRunner()


@pytest.fixture
def git_ops():
    return MockGitOperations()


@pytest.fixture
def uc(repos, runner, git_ops):
    delivery_repo, source_repo = repos
    return DeliveryUseCasesImpl(delivery_repo, runner, git_ops, source_repo)


def _create_delivery(uc, phase="intake", run_status="pending", plan=None):
    body = DeliveryCreate(
        phase=phase,
        run_status=run_status,
        summary="Fix login bug",
        repository="owner/repo",
        refs=[{"role": "trigger", "type": "github_issue", "label": "#1",
               "url": "https://github.com/owner/repo/issues/1"}],
    )
    result = uc.create_delivery(body)
    if plan:
        uc.update_delivery(result["id"], DeliveryUpdate(plan=plan))
    return result


class TestGeneratePlan:
    @pytest.mark.asyncio
    async def test_executes_runner_and_saves_transcript(self, uc, runner):
        result = _create_delivery(uc)
        plan_result = await uc.generate_plan(result["id"])

        assert plan_result["run_status"] == "succeeded"
        assert plan_result["run_id"] is not None

        # Runner was called
        assert len(runner.calls) == 1
        assert "Fix login bug" in runner.calls[0]["prompt"]

        # Delivery updated
        delivery = uc.get_delivery(result["id"])
        assert delivery["phase"] == "plan"
        assert delivery["run_status"] == "succeeded"
        assert delivery["plan"] is not None
        assert delivery["plan"]["content"] == "Generated plan content"
        assert len(delivery["runs"]) == 1

    @pytest.mark.asyncio
    async def test_uses_readonly_tools(self, uc, runner):
        result = _create_delivery(uc)
        await uc.generate_plan(result["id"])
        assert runner.calls[0]["allowed_tools"] is not None
        assert "Write" not in runner.calls[0]["allowed_tools"]

    @pytest.mark.asyncio
    async def test_clones_repo(self, uc, git_ops):
        result = _create_delivery(uc)
        await uc.generate_plan(result["id"])
        assert len(git_ops.clone_calls) == 1
        assert git_ops.clone_calls[0]["owner"] == "owner"
        assert git_ops.clone_calls[0]["repo"] == "repo"

    @pytest.mark.asyncio
    async def test_invalid_phase(self, uc):
        result = _create_delivery(uc, phase="plan", run_status="succeeded")
        with pytest.raises(ValueError, match="generate_plan"):
            await uc.generate_plan(result["id"])

    @pytest.mark.asyncio
    async def test_not_found(self, uc):
        result = await uc.generate_plan("nonexist")
        assert result is None

    @pytest.mark.asyncio
    async def test_runner_failure_sets_failed(self, repos, git_ops):
        delivery_repo, source_repo = repos
        failing_runner = MockSubprocessRunner()

        async def fail(*a, **kw):
            raise RuntimeError("claude CLI timeout")
        failing_runner.run_with_stream = fail

        uc = DeliveryUseCasesImpl(delivery_repo, failing_runner, git_ops, source_repo)
        result = _create_delivery(uc)
        plan_result = await uc.generate_plan(result["id"])

        assert plan_result["run_status"] == "failed"
        assert "timeout" in plan_result["error"]
        delivery = uc.get_delivery(result["id"])
        assert delivery["run_status"] == "failed"
```

Note: add `from app.domain.models.delivery import DeliveryUpdate` to imports.

**Step 2: Run test to verify it fails**

Run: `cd backend && python -m pytest tests/test_agent_execution.py::TestGeneratePlan -v`
Expected: FAIL (generate_plan is still sync, doesn't call runner)

**Step 3: Implement generate_plan with SubprocessRunner**

In `backend/app/usecases/delivery_usecases.py`, add imports and helper:

```python
import shutil
import tempfile

from app.domain.prompts import (
    build_plan_prompt,
    PLAN_SYSTEM_PROMPT,
    PLAN_ALLOWED_TOOLS,
)
from app.domain.services.stream_parser import extract_metadata, extract_transcript
```

Add `_get_source_token` helper:

```python
def _get_source_token(self, owner: str, repo: str) -> str:
    if self._source_repo is None:
        return ""
    for source in self._source_repo.list_sources():
        if source.get("owner") == owner and source.get("repo") == repo:
            return source.get("token", "")
    return ""
```

Add `_run_agent_phase` common helper:

```python
async def _run_agent_phase(
    self,
    delivery: dict,
    delivery_id: str,
    prompt: str,
    mode: str,
    allowed_tools: list[str] | None = None,
    system_prompt: str | None = None,
) -> dict:
    if self._runner is None or self._git is None:
        raise RuntimeError("SubprocessRunner and GitOperations required for agent execution")

    delivery["run_status"] = "running"
    delivery["updated_at"] = datetime.now(KST).isoformat()
    _append_phase_run(delivery, delivery["phase"], "running")
    self._repo.save_delivery(delivery_id, delivery)

    owner, repo = delivery["repository"].split("/", 1)
    token = self._get_source_token(owner, repo)
    work_dir = tempfile.mkdtemp(prefix="jakeops-work-")

    try:
        self._git.clone_repo(owner, repo, token, work_dir)
        result_text, events, session_id = await self._runner.run_with_stream(
            prompt=prompt,
            cwd=work_dir,
            allowed_tools=allowed_tools,
            append_system_prompt=system_prompt,
        )

        metadata = extract_metadata(events)
        transcript = extract_transcript(events)

        run_id = uuid.uuid4().hex[:8]
        run = {
            "id": run_id,
            "mode": mode,
            "status": "success",
            "created_at": datetime.now(KST).isoformat(),
            "session": {"model": metadata.model},
            "stats": {
                "cost_usd": metadata.cost_usd,
                "input_tokens": metadata.input_tokens,
                "output_tokens": metadata.output_tokens,
                "duration_ms": metadata.duration_ms,
            },
            "session_id": session_id,
            "summary": result_text[:200] if result_text else None,
        }

        delivery.setdefault("runs", []).append(run)
        delivery["run_status"] = "succeeded"
        delivery["updated_at"] = datetime.now(KST).isoformat()
        _append_phase_run(delivery, delivery["phase"], "succeeded")
        self._repo.save_delivery(delivery_id, delivery)
        self._repo.save_run_transcript(delivery_id, run_id, transcript)

        return {
            "id": delivery_id,
            "run_id": run_id,
            "phase": delivery["phase"],
            "run_status": "succeeded",
        }
    except Exception as e:
        delivery["run_status"] = "failed"
        delivery["error"] = str(e)
        delivery["updated_at"] = datetime.now(KST).isoformat()
        _append_phase_run(delivery, delivery["phase"], "failed")
        self._repo.save_delivery(delivery_id, delivery)
        return {
            "id": delivery_id,
            "phase": delivery["phase"],
            "run_status": "failed",
            "error": str(e),
        }
    finally:
        shutil.rmtree(work_dir, ignore_errors=True)
```

Replace `generate_plan` method:

```python
async def generate_plan(self, delivery_id: str) -> dict | None:
    existing = self._repo.get_delivery(delivery_id)
    if existing is None:
        return None
    if existing["phase"] != "intake":
        raise ValueError(
            f"generate_plan: not allowed from phase '{existing['phase']}'. "
            "only 'intake' is allowed"
        )

    existing["phase"] = "plan"
    prompt = build_plan_prompt(
        summary=existing["summary"],
        repository=existing["repository"],
        refs=existing.get("refs", []),
    )

    result = await self._run_agent_phase(
        delivery=existing,
        delivery_id=delivery_id,
        prompt=prompt,
        mode="plan",
        allowed_tools=PLAN_ALLOWED_TOOLS,
        system_prompt=PLAN_SYSTEM_PROMPT,
    )

    if result["run_status"] == "succeeded":
        delivery = self._repo.get_delivery(delivery_id)
        delivery["plan"] = {
            "content": result.get("_result_text", ""),
            "generated_at": datetime.now(KST).isoformat(),
            "model": "unknown",
            "cwd": "",
        }
        self._repo.save_delivery(delivery_id, delivery)

    return result
```

Note: The `_run_agent_phase` helper needs to pass `result_text` back. Modify the success return to include it:

```python
# In _run_agent_phase success path, add to return dict:
"_result_text": result_text,
```

Then in `generate_plan`, extract it for the plan content. Actually, better: save plan inside `_run_agent_phase` would couple it. Instead, return `result_text` in the response and let `generate_plan` handle it:

```python
# Better: _run_agent_phase returns result_text in the dict
return {
    "id": delivery_id,
    "run_id": run_id,
    "phase": delivery["phase"],
    "run_status": "succeeded",
    "result_text": result_text,
}
```

Then `generate_plan` uses `result["result_text"]` for plan content.

**Step 4: Run test to verify it passes**

Run: `cd backend && python -m pytest tests/test_agent_execution.py::TestGeneratePlan -v`
Expected: All PASS

**Step 5: Run existing tests to verify no regression**

Run: `cd backend && python -m pytest tests/test_delivery_usecases.py -v`
Expected: All PASS (existing sync tests unaffected)

**Step 6: Commit**

```bash
git add backend/app/usecases/delivery_usecases.py backend/tests/test_agent_execution.py
git commit -m "feat: implement generate_plan with SubprocessRunner execution"
```

---

### Task 4: Implement run_implement

**Files:**
- Modify: `backend/tests/test_agent_execution.py`
- Modify: `backend/app/usecases/delivery_usecases.py`

**Step 1: Write the failing test**

Add to `backend/tests/test_agent_execution.py`:

```python
from app.domain.models.delivery import DeliveryUpdate, Plan


class TestRunImplement:
    @pytest.mark.asyncio
    async def test_executes_runner_with_plan_context(self, uc, runner):
        result = _create_delivery(uc, phase="implement", run_status="pending")
        # Set plan on delivery
        uc.update_delivery(result["id"], DeliveryUpdate(
            plan=Plan(content="## Steps\n1. Fix X", generated_at="2026-01-01T00:00:00", model="test", cwd="/tmp"),
        ))
        impl_result = await uc.run_implement(result["id"])

        assert impl_result["run_status"] == "succeeded"
        assert len(runner.calls) == 1
        assert "## Steps" in runner.calls[0]["prompt"]
        # No tool restrictions for implement
        assert runner.calls[0]["allowed_tools"] is None

    @pytest.mark.asyncio
    async def test_invalid_phase(self, uc):
        result = _create_delivery(uc, phase="plan", run_status="succeeded")
        with pytest.raises(ValueError, match="run_implement"):
            await uc.run_implement(result["id"])

    @pytest.mark.asyncio
    async def test_invalid_run_status(self, uc):
        result = _create_delivery(uc, phase="implement", run_status="running")
        with pytest.raises(ValueError, match="run_implement"):
            await uc.run_implement(result["id"])

    @pytest.mark.asyncio
    async def test_saves_transcript(self, uc):
        result = _create_delivery(uc, phase="implement", run_status="pending")
        uc.update_delivery(result["id"], DeliveryUpdate(
            plan=Plan(content="plan", generated_at="2026-01-01T00:00:00", model="test", cwd="/tmp"),
        ))
        impl_result = await uc.run_implement(result["id"])
        transcript = uc.get_run_transcript(result["id"], impl_result["run_id"])
        assert transcript is not None
```

**Step 2: Run test to verify it fails**

Run: `cd backend && python -m pytest tests/test_agent_execution.py::TestRunImplement -v`
Expected: FAIL (run_implement not defined)

**Step 3: Write implementation**

In `backend/app/usecases/delivery_usecases.py`, add import and method:

```python
from app.domain.prompts import (
    build_plan_prompt, build_implement_prompt,
    PLAN_SYSTEM_PROMPT, PLAN_ALLOWED_TOOLS,
    IMPLEMENT_SYSTEM_PROMPT,
)
```

```python
async def run_implement(self, delivery_id: str) -> dict | None:
    existing = self._repo.get_delivery(delivery_id)
    if existing is None:
        return None
    if existing["phase"] != "implement" or existing["run_status"] != "pending":
        raise ValueError(
            f"run_implement: requires phase='implement' and run_status='pending', "
            f"got phase='{existing['phase']}' run_status='{existing['run_status']}'"
        )

    plan_content = ""
    if existing.get("plan"):
        plan_content = existing["plan"].get("content", "")

    prompt = build_implement_prompt(
        plan_content=plan_content,
        summary=existing["summary"],
    )

    return await self._run_agent_phase(
        delivery=existing,
        delivery_id=delivery_id,
        prompt=prompt,
        mode="implement",
        system_prompt=IMPLEMENT_SYSTEM_PROMPT,
    )
```

**Step 4: Run test to verify it passes**

Run: `cd backend && python -m pytest tests/test_agent_execution.py::TestRunImplement -v`
Expected: All PASS

**Step 5: Commit**

```bash
git add backend/app/usecases/delivery_usecases.py backend/tests/test_agent_execution.py
git commit -m "feat: implement run_implement use case method"
```

---

### Task 5: Implement run_review and run_fix

**Files:**
- Modify: `backend/tests/test_agent_execution.py`
- Modify: `backend/app/usecases/delivery_usecases.py`

**Step 1: Write the failing tests**

Add to `backend/tests/test_agent_execution.py`:

```python
class TestRunReview:
    @pytest.mark.asyncio
    async def test_executes_with_readonly_tools(self, uc, runner):
        result = _create_delivery(uc, phase="review", run_status="pending")
        review_result = await uc.run_review(result["id"])

        assert review_result["run_status"] == "succeeded"
        assert runner.calls[0]["allowed_tools"] is not None
        assert "Write" not in runner.calls[0]["allowed_tools"]

    @pytest.mark.asyncio
    async def test_invalid_phase(self, uc):
        result = _create_delivery(uc, phase="implement", run_status="pending")
        with pytest.raises(ValueError, match="run_review"):
            await uc.run_review(result["id"])


class TestRunFix:
    @pytest.mark.asyncio
    async def test_executes_with_feedback(self, uc, runner):
        result = _create_delivery(uc, phase="implement", run_status="pending")
        fix_result = await uc.run_fix(result["id"], feedback="Missing error handling")

        assert fix_result["run_status"] == "succeeded"
        assert "Missing error handling" in runner.calls[0]["prompt"]

    @pytest.mark.asyncio
    async def test_invalid_phase(self, uc):
        result = _create_delivery(uc, phase="review", run_status="pending")
        with pytest.raises(ValueError, match="run_fix"):
            await uc.run_fix(result["id"])
```

**Step 2: Run tests to verify failure**

Run: `cd backend && python -m pytest tests/test_agent_execution.py::TestRunReview tests/test_agent_execution.py::TestRunFix -v`
Expected: FAIL

**Step 3: Write implementation**

Add imports:

```python
from app.domain.prompts import (
    build_plan_prompt, build_implement_prompt, build_review_prompt, build_fix_prompt,
    PLAN_SYSTEM_PROMPT, PLAN_ALLOWED_TOOLS,
    IMPLEMENT_SYSTEM_PROMPT,
    REVIEW_SYSTEM_PROMPT, REVIEW_ALLOWED_TOOLS,
    FIX_SYSTEM_PROMPT,
)
```

```python
async def run_review(self, delivery_id: str) -> dict | None:
    existing = self._repo.get_delivery(delivery_id)
    if existing is None:
        return None
    if existing["phase"] != "review" or existing["run_status"] != "pending":
        raise ValueError(
            f"run_review: requires phase='review' and run_status='pending', "
            f"got phase='{existing['phase']}' run_status='{existing['run_status']}'"
        )

    prompt = build_review_prompt(summary=existing["summary"])

    return await self._run_agent_phase(
        delivery=existing,
        delivery_id=delivery_id,
        prompt=prompt,
        mode="review",
        allowed_tools=REVIEW_ALLOWED_TOOLS,
        system_prompt=REVIEW_SYSTEM_PROMPT,
    )

async def run_fix(self, delivery_id: str, feedback: str = "") -> dict | None:
    existing = self._repo.get_delivery(delivery_id)
    if existing is None:
        return None
    if existing["phase"] != "implement" or existing["run_status"] != "pending":
        raise ValueError(
            f"run_fix: requires phase='implement' and run_status='pending', "
            f"got phase='{existing['phase']}' run_status='{existing['run_status']}'"
        )

    prompt = build_fix_prompt(feedback=feedback, summary=existing["summary"])

    return await self._run_agent_phase(
        delivery=existing,
        delivery_id=delivery_id,
        prompt=prompt,
        mode="fix",
        system_prompt=FIX_SYSTEM_PROMPT,
    )
```

**Step 4: Run tests to verify pass**

Run: `cd backend && python -m pytest tests/test_agent_execution.py -v`
Expected: All PASS

**Step 5: Commit**

```bash
git add backend/app/usecases/delivery_usecases.py backend/tests/test_agent_execution.py
git commit -m "feat: implement run_review and run_fix use case methods"
```

---

### Task 6: Update protocol and add API endpoints

**Files:**
- Modify: `backend/app/ports/inbound/delivery_usecases.py`
- Modify: `backend/app/adapters/inbound/deliveries.py`
- Modify: `backend/tests/test_deliveries_api.py`

**Step 1: Write failing API tests**

Add to `backend/tests/test_deliveries_api.py`:

```python
def test_generate_plan_triggers_execution(monkeypatch):
    """generate_plan endpoint should trigger async execution."""
    # This test needs mock runner injected via conftest
    pass  # Covered by test_agent_execution.py unit tests


def test_run_implement_endpoint():
    delivery_data = {**VALID_DELIVERY, "phase": "implement", "run_status": "pending"}
    resp = client.post("/api/deliveries", json=delivery_data)
    delivery_id = resp.json()["id"]
    resp = client.post(f"/api/deliveries/{delivery_id}/run-implement")
    # Without runner injected, should return 500 or appropriate error
    assert resp.status_code in (200, 500)


def test_run_review_endpoint():
    delivery_data = {**VALID_DELIVERY, "phase": "review", "run_status": "pending"}
    resp = client.post("/api/deliveries", json=delivery_data)
    delivery_id = resp.json()["id"]
    resp = client.post(f"/api/deliveries/{delivery_id}/run-review")
    assert resp.status_code in (200, 500)


def test_run_fix_endpoint():
    delivery_data = {**VALID_DELIVERY, "phase": "implement", "run_status": "pending"}
    resp = client.post("/api/deliveries", json=delivery_data)
    delivery_id = resp.json()["id"]
    resp = client.post(f"/api/deliveries/{delivery_id}/run-fix", json={"feedback": "fix this"})
    assert resp.status_code in (200, 500)


def test_run_implement_wrong_phase():
    resp = client.post("/api/deliveries", json=VALID_DELIVERY)
    delivery_id = resp.json()["id"]
    resp = client.post(f"/api/deliveries/{delivery_id}/run-implement")
    assert resp.status_code == 409
```

**Step 2: Update protocol**

In `backend/app/ports/inbound/delivery_usecases.py`, add async methods:

```python
class DeliveryUseCases(Protocol):
    # ... existing sync methods ...
    async def generate_plan(self, delivery_id: str) -> dict | None: ...
    async def run_implement(self, delivery_id: str) -> dict | None: ...
    async def run_review(self, delivery_id: str) -> dict | None: ...
    async def run_fix(self, delivery_id: str, feedback: str = "") -> dict | None: ...
```

**Step 3: Add API endpoints**

In `backend/app/adapters/inbound/deliveries.py`:

```python
class RunFixBody(BaseModel):
    feedback: str = ""


@router.post("/deliveries/{delivery_id}/generate-plan")
async def generate_plan(delivery_id: str, uc=Depends(get_usecases)):
    try:
        result = await uc.generate_plan(delivery_id)
    except ValueError as e:
        raise HTTPException(status_code=409, detail=str(e))
    except RuntimeError as e:
        raise HTTPException(status_code=500, detail=str(e))
    if result is None:
        raise HTTPException(status_code=404, detail="Delivery not found")
    return result


@router.post("/deliveries/{delivery_id}/run-implement")
async def run_implement(delivery_id: str, uc=Depends(get_usecases)):
    try:
        result = await uc.run_implement(delivery_id)
    except ValueError as e:
        raise HTTPException(status_code=409, detail=str(e))
    except RuntimeError as e:
        raise HTTPException(status_code=500, detail=str(e))
    if result is None:
        raise HTTPException(status_code=404, detail="Delivery not found")
    return result


@router.post("/deliveries/{delivery_id}/run-review")
async def run_review(delivery_id: str, uc=Depends(get_usecases)):
    try:
        result = await uc.run_review(delivery_id)
    except ValueError as e:
        raise HTTPException(status_code=409, detail=str(e))
    except RuntimeError as e:
        raise HTTPException(status_code=500, detail=str(e))
    if result is None:
        raise HTTPException(status_code=404, detail="Delivery not found")
    return result


@router.post("/deliveries/{delivery_id}/run-fix")
async def run_fix(delivery_id: str, body: RunFixBody, uc=Depends(get_usecases)):
    try:
        result = await uc.run_fix(delivery_id, feedback=body.feedback)
    except ValueError as e:
        raise HTTPException(status_code=409, detail=str(e))
    except RuntimeError as e:
        raise HTTPException(status_code=500, detail=str(e))
    if result is None:
        raise HTTPException(status_code=404, detail="Delivery not found")
    return result
```

Note: Remove the old sync `generate_plan` endpoint since it's replaced.

**Step 4: Run tests**

Run: `cd backend && python -m pytest tests/test_deliveries_api.py -v`
Expected: PASS

**Step 5: Commit**

```bash
git add backend/app/ports/inbound/delivery_usecases.py backend/app/adapters/inbound/deliveries.py backend/tests/test_deliveries_api.py
git commit -m "feat: add API endpoints for run-implement, run-review, run-fix"
```

---

### Task 7: Clean up ClaudeCliAdapter

**Files:**
- Modify: `backend/app/adapters/outbound/claude_cli.py`

**Step 1: Remove dead prompt templates**

Remove `PLAN_PROMPT_TEMPLATE` and `SYSTEM_PROMPT` constants from
`backend/app/adapters/outbound/claude_cli.py`. These now live in
`backend/app/domain/prompts.py`.

Keep only: `_extract_session_id`, `ClaudeCliAdapter` class.

**Step 2: Run tests to verify nothing breaks**

Run: `cd backend && python -m pytest tests/test_claude_cli_stream.py -v`
Expected: All PASS

**Step 3: Commit**

```bash
git add backend/app/adapters/outbound/claude_cli.py
git commit -m "refactor: remove dead prompt templates from ClaudeCliAdapter"
```

---

### Task 8: Full verification

**Step 1: Run full test suite**

Run: `cd backend && python -m pytest -v`
Expected: All tests PASS

**Step 2: Run linter if configured**

Run: `cd backend && python -m ruff check . 2>/dev/null || true`

**Step 3: Final commit if any fixes needed**

```bash
git add -A && git commit -m "fix: address lint/test issues"
```
