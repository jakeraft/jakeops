import pytest

from app.domain.models.issue import IssueCreate, IssueUpdate, IssueStatus


@pytest.fixture
def usecases(tmp_path):
    from app.adapters.outbound.filesystem_issue import FileSystemIssueRepository
    from app.usecases.issue_usecases import IssueUseCasesImpl
    repo = FileSystemIssueRepository(tmp_path / "issues")
    return IssueUseCasesImpl(repo)


def _create_issue(usecases, status="new"):
    body = IssueCreate(
        status=status,
        summary="test",
        repository="jakeops",
        refs=[{"role": "trigger", "type": "github_issue", "label": "#1"}],
    )
    return usecases.create_issue(body)


class TestCRUD:
    def test_create_issue(self, usecases):
        result = _create_issue(usecases)
        assert len(result["id"]) == 12
        assert result["status"] == "created"

    def test_create_issue_sets_server_fields(self, usecases):
        result = _create_issue(usecases)
        issue = usecases.get_issue(result["id"])
        assert issue["schema_version"] == 3
        assert "+09:00" in issue["created_at"]
        assert issue["updated_at"] is not None
        assert issue["runs"] == []

    def test_get_issue(self, usecases):
        result = _create_issue(usecases)
        issue = usecases.get_issue(result["id"])
        assert issue["summary"] == "test"

    def test_get_issue_not_found(self, usecases):
        assert usecases.get_issue("nonexist") is None

    def test_list_issues(self, usecases):
        _create_issue(usecases)
        items = usecases.list_issues()
        assert len(items) == 1

    def test_update_issue(self, usecases):
        result = _create_issue(usecases)
        updated = usecases.update_issue(result["id"], IssueUpdate(summary="updated"))
        assert updated is not None
        issue = usecases.get_issue(result["id"])
        assert issue["summary"] == "updated"

    def test_update_preserves_existing(self, usecases):
        result = _create_issue(usecases)
        usecases.update_issue(result["id"], IssueUpdate(summary="updated"))
        issue = usecases.get_issue(result["id"])
        assert issue["repository"] == "jakeops"
        assert issue["status"] == "new"


class TestGateApprove:
    """approve: transition from current gate to next state"""

    def test_approve_planned_to_approved(self, usecases):
        result = _create_issue(usecases, status="planned")
        approved = usecases.approve(result["id"])
        assert approved["status"] == "approved"
        issue = usecases.get_issue(result["id"])
        assert issue["status"] == "approved"

    def test_approve_ci_passed_to_deployed(self, usecases):
        result = _create_issue(usecases, status="ci_passed")
        approved = usecases.approve(result["id"])
        assert approved["status"] == "deployed"

    def test_approve_deployed_to_done(self, usecases):
        result = _create_issue(usecases, status="deployed")
        approved = usecases.approve(result["id"])
        assert approved["status"] == "done"

    def test_approve_invalid_state(self, usecases):
        result = _create_issue(usecases, status="new")
        with pytest.raises(ValueError, match="approve"):
            usecases.approve(result["id"])

    def test_approve_not_found(self, usecases):
        assert usecases.approve("nonexist") is None


class TestGateReject:
    """reject: transition from current gate to previous state"""

    def test_reject_planned_to_new(self, usecases):
        result = _create_issue(usecases, status="planned")
        rejected = usecases.reject(result["id"], reason="Inadequate plan")
        assert rejected["status"] == "new"

    def test_reject_ci_passed_to_implemented(self, usecases):
        result = _create_issue(usecases, status="ci_passed")
        rejected = usecases.reject(result["id"], reason="Needs re-execution")
        assert rejected["status"] == "implemented"

    def test_reject_deployed_to_ci_passed(self, usecases):
        result = _create_issue(usecases, status="deployed")
        rejected = usecases.reject(result["id"], reason="Deployment rollback")
        assert rejected["status"] == "ci_passed"

    def test_reject_invalid_state(self, usecases):
        result = _create_issue(usecases, status="new")
        with pytest.raises(ValueError, match="reject"):
            usecases.reject(result["id"], reason="x")


class TestGateSpecial:
    """generate_plan, retry, cancel"""

    def test_generate_plan_from_new(self, usecases):
        """generate_plan keeps status as new (AgentRunner handles transition)"""
        result = _create_issue(usecases, status="new")
        triggered = usecases.generate_plan(result["id"])
        assert triggered is not None

    def test_generate_plan_invalid_state(self, usecases):
        result = _create_issue(usecases, status="planned")
        with pytest.raises(ValueError, match="generate_plan"):
            usecases.generate_plan(result["id"])

    def test_cancel(self, usecases):
        result = _create_issue(usecases, status="approved")
        canceled = usecases.cancel(result["id"])
        assert canceled["status"] == "canceled"

    def test_retry_from_failed(self, usecases):
        """retry: failed -> restore to pre-failure state (default: new)"""
        result = _create_issue(usecases, status="failed")
        retried = usecases.retry(result["id"])
        assert retried["status"] == "new"

    def test_retry_not_failed(self, usecases):
        result = _create_issue(usecases, status="new")
        with pytest.raises(ValueError, match="retry"):
            usecases.retry(result["id"])
