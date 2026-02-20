"""Tests for agent execution use cases (generate_plan, run_implement, etc.)"""

from pathlib import Path

import pytest

from app.adapters.outbound.filesystem_delivery import FileSystemDeliveryRepository
from app.adapters.outbound.filesystem_source import FileSystemSourceRepository
from app.domain.models.delivery import DeliveryCreate, DeliveryUpdate, Plan
from app.usecases.delivery_usecases import DeliveryUseCasesImpl


class MockSubprocessRunner:
    """Mock that records calls and returns predefined result."""

    def __init__(self, result_text: str = "Generated plan content"):
        self.result_text = result_text
        self.calls: list[dict] = []

    async def run(
        self,
        prompt: str,
        cwd: str,
        allowed_tools: list[str] | None = None,
        append_system_prompt: str | None = None,
        delivery_id: str | None = None,
    ) -> tuple[str, str | None]:
        self.calls.append({
            "prompt": prompt,
            "cwd": cwd,
            "allowed_tools": allowed_tools,
            "append_system_prompt": append_system_prompt,
        })
        return (self.result_text, None)

    def kill(self, delivery_id: str) -> bool:
        return False


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
    async def test_executes_runner_and_saves_result(self, uc, runner):
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
            async def run(
                self, prompt, cwd, allowed_tools=None,
                append_system_prompt=None, delivery_id=None,
            ):
                raise RuntimeError("claude CLI timeout")

            def kill(self, delivery_id):
                return False

        uc = DeliveryUseCasesImpl(delivery_repo, FailingRunner(), git_ops, source_repo)
        result = _create_delivery(uc)
        plan_result = await uc.generate_plan(result["id"])

        assert plan_result["run_status"] == "failed"
        assert "timeout" in plan_result["error"]
        delivery = uc.get_delivery(result["id"])
        assert delivery["run_status"] == "failed"
        # Phase should be rolled back to intake so generate_plan can be retried
        assert delivery["phase"] == "intake"
        assert plan_result["phase"] == "intake"

    @pytest.mark.asyncio
    async def test_failure_does_not_mutate_caller_dict(self, repos, git_ops):
        """_run_agent_phase must not mutate the caller's delivery dict."""
        delivery_repo, source_repo = repos

        class FailingRunner:
            async def run(
                self, prompt, cwd, allowed_tools=None,
                append_system_prompt=None, delivery_id=None,
            ):
                raise RuntimeError("fail")

            def kill(self, delivery_id):
                return False

        uc = DeliveryUseCasesImpl(delivery_repo, FailingRunner(), git_ops, source_repo)
        result = _create_delivery(uc)
        delivery_before = uc.get_delivery(result["id"])
        original_run_status = delivery_before["run_status"]
        await uc.generate_plan(result["id"])
        # The local dict should not have been mutated by _run_agent_phase
        assert delivery_before["run_status"] == original_run_status

    @pytest.mark.asyncio
    async def test_run_without_session_file(self, uc):
        """When session_id is None, run succeeds without saving transcript."""
        result = _create_delivery(uc)
        plan_result = await uc.generate_plan(result["id"])
        assert plan_result["run_status"] == "succeeded"
        # No transcript saved (mock returns session_id=None)
        transcript = uc.get_run_transcript(result["id"], plan_result["run_id"])
        assert transcript is None

    @pytest.mark.asyncio
    async def test_session_parse_failure_does_not_fail_run(self, repos, git_ops):
        """If session file parsing raises, the run still succeeds."""
        delivery_repo, source_repo = repos

        class RunnerWithSessionId:
            async def run(self, prompt, cwd, allowed_tools=None, append_system_prompt=None, delivery_id=None):
                return ("Plan result", "bad-session-id")

            def kill(self, delivery_id):
                return False

        uc = DeliveryUseCasesImpl(
            delivery_repo, RunnerWithSessionId(), git_ops, source_repo,
        )
        result = _create_delivery(uc)
        plan_result = await uc.generate_plan(result["id"])
        # Session file won't be found, but run should still succeed
        assert plan_result["run_status"] == "succeeded"
        assert plan_result["result_text"] == "Plan result"

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
    async def test_not_found(self, uc):
        result = await uc.run_implement("nonexist")
        assert result is None


class TestRunReview:
    @pytest.mark.asyncio
    async def test_executes_runner(self, uc, runner):
        result = _create_delivery(uc, phase="review", run_status="pending")
        review_result = await uc.run_review(result["id"])

        assert review_result["run_status"] == "succeeded"
        assert len(runner.calls) == 1

    @pytest.mark.asyncio
    async def test_invalid_phase(self, uc):
        result = _create_delivery(uc, phase="implement", run_status="pending")
        with pytest.raises(ValueError, match="run_review"):
            await uc.run_review(result["id"])

    @pytest.mark.asyncio
    async def test_not_found(self, uc):
        result = await uc.run_review("nonexist")
        assert result is None


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
