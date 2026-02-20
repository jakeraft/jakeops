"""Tests for agent execution use cases (generate_plan, run_implement, etc.)"""

from pathlib import Path

import pytest

from app.adapters.outbound.filesystem_delivery import FileSystemDeliveryRepository
from app.adapters.outbound.filesystem_source import FileSystemSourceRepository
from app.domain.models.delivery import DeliveryCreate, DeliveryUpdate, Plan
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


def _create_delivery(uc, phase="intake", run_status="pending"):
    body = DeliveryCreate(
        phase=phase,
        run_status=run_status,
        summary="Fix login bug",
        repository="owner/repo",
        refs=[{"role": "trigger", "type": "github_issue", "label": "#1",
               "url": "https://github.com/owner/repo/issues/1"}],
    )
    return uc.create_delivery(body)


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

        class FailingRunner:
            async def run_with_stream(
                self,
                prompt: str,
                cwd: str,
                allowed_tools: list[str] | None = None,
                append_system_prompt: str | None = None,
            ) -> tuple[str, list[StreamEvent], str | None]:
                raise RuntimeError("claude CLI timeout")

        uc = DeliveryUseCasesImpl(delivery_repo, FailingRunner(), git_ops, source_repo)
        result = _create_delivery(uc)
        plan_result = await uc.generate_plan(result["id"])

        assert plan_result["run_status"] == "failed"
        assert "timeout" in plan_result["error"]
        delivery = uc.get_delivery(result["id"])
        assert delivery["run_status"] == "failed"

    @pytest.mark.asyncio
    async def test_saves_transcript_file(self, uc):
        result = _create_delivery(uc)
        plan_result = await uc.generate_plan(result["id"])
        transcript = uc.get_run_transcript(result["id"], plan_result["run_id"])
        assert transcript is not None

    @pytest.mark.asyncio
    async def test_appends_phase_runs(self, uc):
        result = _create_delivery(uc)
        await uc.generate_plan(result["id"])
        delivery = uc.get_delivery(result["id"])
        # Should have: initial intake pending, plan running, plan succeeded
        phases = [(r["phase"], r["run_status"]) for r in delivery["phase_runs"]]
        assert ("plan", "running") in phases
        assert ("plan", "succeeded") in phases


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

    @pytest.mark.asyncio
    async def test_not_found(self, uc):
        result = await uc.run_implement("nonexist")
        assert result is None


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

    @pytest.mark.asyncio
    async def test_not_found(self, uc):
        result = await uc.run_review("nonexist")
        assert result is None

    @pytest.mark.asyncio
    async def test_saves_transcript(self, uc):
        result = _create_delivery(uc, phase="review", run_status="pending")
        review_result = await uc.run_review(result["id"])
        transcript = uc.get_run_transcript(result["id"], review_result["run_id"])
        assert transcript is not None


class TestRunFix:
    @pytest.mark.asyncio
    async def test_executes_with_feedback(self, uc, runner):
        result = _create_delivery(uc, phase="implement", run_status="pending")
        fix_result = await uc.run_fix(result["id"], feedback="Missing error handling")

        assert fix_result["run_status"] == "succeeded"
        assert "Missing error handling" in runner.calls[0]["prompt"]
        # fix gets all tools (no restrictions)
        assert runner.calls[0]["allowed_tools"] is None

    @pytest.mark.asyncio
    async def test_invalid_phase(self, uc):
        result = _create_delivery(uc, phase="review", run_status="pending")
        with pytest.raises(ValueError, match="run_fix"):
            await uc.run_fix(result["id"])

    @pytest.mark.asyncio
    async def test_not_found(self, uc):
        result = await uc.run_fix("nonexist")
        assert result is None
