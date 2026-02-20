import pytest
from pydantic import ValidationError


class TestPhaseEnum:
    def test_all_values(self):
        from app.domain.models.delivery import Phase

        expected = [
            "intake", "plan", "implement", "review",
            "verify", "deploy", "observe", "close",
        ]
        assert [p.value for p in Phase] == expected

    def test_count(self):
        from app.domain.models.delivery import Phase

        assert len(Phase) == 8


class TestRunStatusEnum:
    def test_all_values(self):
        from app.domain.models.delivery import RunStatus

        expected = ["pending", "running", "succeeded", "failed", "blocked"]
        assert [s.value for s in RunStatus] == expected

    def test_count(self):
        from app.domain.models.delivery import RunStatus

        assert len(RunStatus) == 5


class TestExecutorKindEnum:
    def test_all_values(self):
        from app.domain.models.delivery import ExecutorKind

        expected = ["system", "agent"]
        assert [e.value for e in ExecutorKind] == expected


class TestVerdictEnum:
    def test_all_values(self):
        from app.domain.models.delivery import Verdict

        expected = ["pass", "not_pass"]
        assert [v.value for v in Verdict] == expected


class TestPhaseRun:
    def test_creation(self):
        from app.domain.models.delivery import PhaseRun, Phase, RunStatus, ExecutorKind

        run = PhaseRun(
            phase=Phase.verify,
            run_status=RunStatus.succeeded,
            executor=ExecutorKind.system,
            started_at="2026-02-20T15:00:00+09:00",
            ended_at="2026-02-20T15:03:00+09:00",
        )
        assert run.phase == Phase.verify
        assert run.run_status == RunStatus.succeeded
        assert run.executor == ExecutorKind.system

    def test_optional_timestamps(self):
        from app.domain.models.delivery import PhaseRun, Phase, RunStatus, ExecutorKind

        run = PhaseRun(
            phase=Phase.intake,
            run_status=RunStatus.pending,
            executor=ExecutorKind.system,
        )
        assert run.started_at is None
        assert run.ended_at is None
        assert run.verdict is None

    def test_with_verdict(self):
        from app.domain.models.delivery import PhaseRun, Phase, RunStatus, ExecutorKind, Verdict

        run = PhaseRun(
            phase=Phase.review,
            run_status=RunStatus.succeeded,
            executor=ExecutorKind.agent,
            verdict=Verdict.passed,
        )
        assert run.verdict == Verdict.passed


class TestDeliveryCreate:
    def test_defaults(self):
        from app.domain.models.delivery import DeliveryCreate, Phase, RunStatus, Ref, RefRole, RefType

        delivery = DeliveryCreate(
            summary="Fix login bug",
            repository="owner/repo",
            refs=[
                Ref(role=RefRole.trigger, type=RefType.jira, label="PROJ-123"),
            ],
        )
        assert delivery.phase == Phase.intake
        assert delivery.run_status == RunStatus.pending
        assert delivery.endpoint is None
        assert delivery.summary == "Fix login bug"
        assert delivery.repository == "owner/repo"
        assert len(delivery.refs) == 1
        assert delivery.id is None
        assert delivery.created_at is None
        assert delivery.schema_version is None

    def test_with_explicit_phase(self):
        from app.domain.models.delivery import DeliveryCreate, Phase, RunStatus

        delivery = DeliveryCreate(
            phase=Phase.plan,
            run_status=RunStatus.succeeded,
            endpoint=Phase.verify,
            summary="test",
            repository="owner/repo",
            refs=[],
        )
        assert delivery.phase == Phase.plan
        assert delivery.run_status == RunStatus.succeeded
        assert delivery.endpoint == Phase.verify

    def test_invalid_phase(self):
        from app.domain.models.delivery import DeliveryCreate

        with pytest.raises(ValidationError):
            DeliveryCreate(
                phase="invalid_phase",
                summary="test",
                repository="owner/repo",
                refs=[],
            )

    def test_extra_fields_ignored(self):
        from app.domain.models.delivery import DeliveryCreate

        delivery = DeliveryCreate(
            summary="test",
            repository="owner/repo",
            refs=[],
            unknown_field="should be ignored",
        )
        assert not hasattr(delivery, "unknown_field")


class TestDeliveryUpdate:
    def test_partial_dump_phase(self):
        from app.domain.models.delivery import Phase, DeliveryUpdate

        update = DeliveryUpdate(phase=Phase.plan)
        dumped = update.model_dump(exclude_none=True)
        assert dumped == {"phase": "plan"}

    def test_partial_dump_run_status(self):
        from app.domain.models.delivery import RunStatus, DeliveryUpdate

        update = DeliveryUpdate(run_status=RunStatus.failed)
        dumped = update.model_dump(exclude_none=True)
        assert dumped == {"run_status": "failed"}

    def test_with_error(self):
        from app.domain.models.delivery import RunStatus, DeliveryUpdate

        update = DeliveryUpdate(
            run_status=RunStatus.failed,
            error="Build failed: exit code 1",
        )
        assert update.error == "Build failed: exit code 1"
        assert update.run_status == RunStatus.failed


class TestRef:
    def test_url_optional(self):
        from app.domain.models.delivery import Ref, RefRole, RefType

        ref = Ref(role=RefRole.trigger, type=RefType.jira, label="PROJ-123")
        assert ref.url is None

    def test_with_url(self):
        from app.domain.models.delivery import Ref, RefRole, RefType

        ref = Ref(
            role=RefRole.output,
            type=RefType.pr,
            label="PR #42",
            url="https://github.com/owner/repo/pull/42",
        )
        assert ref.url == "https://github.com/owner/repo/pull/42"


class TestPlan:
    def test_creation(self):
        from app.domain.models.delivery import Plan

        plan = Plan(
            content="## Plan\n- Step 1\n- Step 2",
            generated_at="2026-02-20T10:00:00+09:00",
            model="claude-opus-4-6",
            cwd="/workspace/repo",
        )
        assert plan.content.startswith("## Plan")
        assert plan.model == "claude-opus-4-6"
        assert plan.cwd == "/workspace/repo"


class TestExecutionStats:
    def test_defaults(self):
        from app.domain.models.delivery import ExecutionStats

        stats = ExecutionStats()
        assert stats.cost_usd == 0.0
        assert stats.input_tokens == 0
        assert stats.output_tokens == 0
        assert stats.duration_ms == 0
