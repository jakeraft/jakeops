import pytest
from pydantic import ValidationError


class TestIssueStatus:
    def test_all_values(self):
        from app.domain.models.issue import IssueStatus

        expected = [
            "new",
            "planned",
            "approved",
            "implemented",
            "ci_passed",
            "deployed",
            "done",
            "failed",
            "canceled",
        ]
        assert [s.value for s in IssueStatus] == expected

    def test_count(self):
        from app.domain.models.issue import IssueStatus

        assert len(IssueStatus) == 9


class TestIssueCreate:
    def test_minimal(self):
        from app.domain.models.issue import IssueCreate, IssueStatus, Ref, RefRole, RefType

        issue = IssueCreate(
            status=IssueStatus.new,
            summary="Fix login bug",
            repository="owner/repo",
            refs=[
                Ref(role=RefRole.trigger, type=RefType.jira, label="PROJ-123"),
            ],
        )
        assert issue.status == IssueStatus.new
        assert issue.summary == "Fix login bug"
        assert issue.repository == "owner/repo"
        assert len(issue.refs) == 1
        assert issue.id is None
        assert issue.created_at is None
        assert issue.schema_version is None

    def test_invalid_status(self):
        from app.domain.models.issue import IssueCreate

        with pytest.raises(ValidationError):
            IssueCreate(
                status="invalid_status",
                summary="test",
                repository="owner/repo",
                refs=[],
            )

    def test_extra_fields_ignored(self):
        from app.domain.models.issue import IssueCreate, IssueStatus

        issue = IssueCreate(
            status=IssueStatus.new,
            summary="test",
            repository="owner/repo",
            refs=[],
            unknown_field="should be ignored",
        )
        assert not hasattr(issue, "unknown_field")


class TestIssueUpdate:
    def test_partial_dump(self):
        from app.domain.models.issue import IssueStatus, IssueUpdate

        update = IssueUpdate(status=IssueStatus.planned)
        dumped = update.model_dump(exclude_none=True)
        assert dumped == {"status": "planned"}

    def test_with_error(self):
        from app.domain.models.issue import IssueStatus, IssueUpdate

        update = IssueUpdate(
            status=IssueStatus.failed,
            error="Build failed: exit code 1",
        )
        assert update.error == "Build failed: exit code 1"
        assert update.status == IssueStatus.failed


class TestRef:
    def test_url_optional(self):
        from app.domain.models.issue import Ref, RefRole, RefType

        ref = Ref(role=RefRole.trigger, type=RefType.jira, label="PROJ-123")
        assert ref.url is None

    def test_with_url(self):
        from app.domain.models.issue import Ref, RefRole, RefType

        ref = Ref(
            role=RefRole.output,
            type=RefType.pr,
            label="PR #42",
            url="https://github.com/owner/repo/pull/42",
        )
        assert ref.url == "https://github.com/owner/repo/pull/42"


class TestPlan:
    def test_creation(self):
        from app.domain.models.issue import Plan

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
        from app.domain.models.issue import ExecutionStats

        stats = ExecutionStats()
        assert stats.cost_usd == 0.0
        assert stats.input_tokens == 0
        assert stats.output_tokens == 0
        assert stats.duration_ms == 0
