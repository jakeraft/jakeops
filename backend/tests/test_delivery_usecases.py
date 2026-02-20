import pytest

from app.domain.models.delivery import DeliveryCreate, DeliveryUpdate, Phase, RunStatus


@pytest.fixture
def usecases(tmp_path):
    from app.adapters.outbound.filesystem_delivery import FileSystemDeliveryRepository
    from app.usecases.delivery_usecases import DeliveryUseCasesImpl
    repo = FileSystemDeliveryRepository(tmp_path / "deliveries")
    return DeliveryUseCasesImpl(repo)


def _create_delivery(usecases, phase="intake", run_status="pending", exit_phase=None):
    body = DeliveryCreate(
        phase=phase,
        run_status=run_status,
        exit_phase=exit_phase,
        summary="test",
        repository="jakeops",
        refs=[{"role": "trigger", "type": "github_issue", "label": "#1"}],
    )
    return usecases.create_delivery(body)


class TestCRUD:
    def test_create_delivery(self, usecases):
        result = _create_delivery(usecases)
        assert len(result["id"]) == 12
        assert result["status"] == "created"

    def test_create_delivery_sets_server_fields(self, usecases):
        result = _create_delivery(usecases)
        delivery = usecases.get_delivery(result["id"])
        assert delivery["schema_version"] == 5
        assert "+09:00" in delivery["created_at"]
        assert delivery["updated_at"] is not None
        assert delivery["runs"] == []
        assert delivery["phase"] == "intake"
        assert delivery["run_status"] == "pending"
        assert delivery["exit_phase"] == "deploy"
        assert len(delivery["phase_runs"]) == 1
        assert delivery["seq"] == 1

    def test_create_delivery_with_exit_phase(self, usecases):
        result = _create_delivery(usecases, exit_phase="verify")
        delivery = usecases.get_delivery(result["id"])
        assert delivery["exit_phase"] == "verify"

    def test_get_delivery(self, usecases):
        result = _create_delivery(usecases)
        delivery = usecases.get_delivery(result["id"])
        assert delivery["summary"] == "test"

    def test_get_delivery_not_found(self, usecases):
        assert usecases.get_delivery("nonexist") is None

    def test_list_deliveries(self, usecases):
        _create_delivery(usecases)
        items = usecases.list_deliveries()
        assert len(items) == 1

    def test_update_delivery(self, usecases):
        result = _create_delivery(usecases)
        updated = usecases.update_delivery(result["id"], DeliveryUpdate(summary="updated"))
        assert updated is not None
        delivery = usecases.get_delivery(result["id"])
        assert delivery["summary"] == "updated"

    def test_update_preserves_existing(self, usecases):
        result = _create_delivery(usecases)
        usecases.update_delivery(result["id"], DeliveryUpdate(summary="updated"))
        delivery = usecases.get_delivery(result["id"])
        assert delivery["repository"] == "jakeops"
        assert delivery["phase"] == "intake"
        assert delivery["run_status"] == "pending"


    def test_seq_auto_increments(self, usecases):
        r1 = _create_delivery(usecases)
        d1 = usecases.get_delivery(r1["id"])
        assert d1["seq"] == 1

        body2 = DeliveryCreate(
            summary="second",
            repository="jakeops",
            refs=[{"role": "trigger", "type": "github_issue", "label": "#2"}],
        )
        r2 = usecases.create_delivery(body2)
        d2 = usecases.get_delivery(r2["id"])
        assert d2["seq"] == 2

    def test_close_delivery(self, usecases):
        result = _create_delivery(usecases)
        closed = usecases.close_delivery(result["id"])
        assert closed["phase"] == "close"
        assert closed["run_status"] == "succeeded"
        delivery = usecases.get_delivery(result["id"])
        assert delivery["phase"] == "close"
        assert delivery["run_status"] == "succeeded"

    def test_close_delivery_not_found(self, usecases):
        assert usecases.close_delivery("nonexist") is None

    def test_close_delivery_appends_phase_run(self, usecases):
        result = _create_delivery(usecases)
        usecases.close_delivery(result["id"])
        delivery = usecases.get_delivery(result["id"])
        assert delivery["phase_runs"][-1]["phase"] == "close"
        assert delivery["phase_runs"][-1]["run_status"] == "succeeded"


class TestGateApprove:
    """approve: gate phase with run_status=succeeded advances to next phase"""

    def test_approve_plan_to_implement(self, usecases):
        result = _create_delivery(usecases, phase="plan", run_status="succeeded")
        approved = usecases.approve(result["id"])
        assert approved["phase"] == "implement"
        assert approved["run_status"] == "pending"
        delivery = usecases.get_delivery(result["id"])
        assert delivery["phase"] == "implement"

    def test_approve_review_to_verify(self, usecases):
        result = _create_delivery(usecases, phase="review", run_status="succeeded")
        approved = usecases.approve(result["id"])
        assert approved["phase"] == "verify"
        assert approved["run_status"] == "pending"

    def test_approve_deploy_to_observe(self, usecases):
        result = _create_delivery(usecases, phase="deploy", run_status="succeeded", exit_phase="observe")
        approved = usecases.approve(result["id"])
        assert approved["phase"] == "observe"
        assert approved["run_status"] == "pending"

    def test_approve_at_exit_phase_goes_to_close(self, usecases):
        result = _create_delivery(usecases, phase="deploy", run_status="succeeded", exit_phase="deploy")
        approved = usecases.approve(result["id"])
        assert approved["phase"] == "close"

    def test_approve_non_gate_phase(self, usecases):
        result = _create_delivery(usecases, phase="intake", run_status="succeeded")
        with pytest.raises(ValueError, match="not a gate phase"):
            usecases.approve(result["id"])

    def test_approve_not_succeeded(self, usecases):
        result = _create_delivery(usecases, phase="plan", run_status="pending")
        with pytest.raises(ValueError, match="run_status must be 'succeeded'"):
            usecases.approve(result["id"])

    def test_approve_not_found(self, usecases):
        assert usecases.approve("nonexist") is None

    def test_approve_appends_phase_run(self, usecases):
        result = _create_delivery(usecases, phase="plan", run_status="succeeded")
        usecases.approve(result["id"])
        delivery = usecases.get_delivery(result["id"])
        assert len(delivery["phase_runs"]) == 2
        assert delivery["phase_runs"][-1]["phase"] == "implement"
        assert delivery["phase_runs"][-1]["run_status"] == "pending"


class TestGateReject:
    """reject: gate phase sends delivery back to previous phase"""

    def test_reject_plan_to_intake(self, usecases):
        result = _create_delivery(usecases, phase="plan", run_status="succeeded")
        rejected = usecases.reject(result["id"], reason="Inadequate plan")
        assert rejected["phase"] == "intake"
        assert rejected["run_status"] == "pending"

    def test_reject_review_to_implement(self, usecases):
        result = _create_delivery(usecases, phase="review", run_status="succeeded")
        rejected = usecases.reject(result["id"], reason="Needs re-implementation")
        assert rejected["phase"] == "implement"
        assert rejected["run_status"] == "pending"

    def test_reject_deploy_to_verify(self, usecases):
        result = _create_delivery(usecases, phase="deploy", run_status="succeeded")
        rejected = usecases.reject(result["id"], reason="Deployment rollback")
        assert rejected["phase"] == "verify"
        assert rejected["run_status"] == "pending"

    def test_reject_non_gate_phase(self, usecases):
        result = _create_delivery(usecases, phase="intake", run_status="pending")
        with pytest.raises(ValueError, match="reject"):
            usecases.reject(result["id"], reason="x")

    def test_reject_appends_phase_run(self, usecases):
        result = _create_delivery(usecases, phase="plan", run_status="succeeded")
        usecases.reject(result["id"], reason="bad")
        delivery = usecases.get_delivery(result["id"])
        assert delivery["phase_runs"][-1]["phase"] == "intake"


class TestPhaseActions:
    """retry, cancel (generate_plan tests moved to test_agent_execution.py)"""

    def test_cancel(self, usecases):
        result = _create_delivery(usecases, phase="review", run_status="succeeded")
        canceled = usecases.cancel(result["id"])
        assert canceled["run_status"] == "canceled"
        assert canceled["phase"] == "review"

    def test_cancel_preserves_phase(self, usecases):
        result = _create_delivery(usecases, phase="implement", run_status="running")
        canceled = usecases.cancel(result["id"])
        assert canceled["phase"] == "implement"
        assert canceled["run_status"] == "canceled"

    def test_retry_from_failed(self, usecases):
        result = _create_delivery(usecases, phase="verify", run_status="failed")
        retried = usecases.retry(result["id"])
        assert retried["run_status"] == "pending"
        assert retried["phase"] == "verify"

    def test_retry_not_failed(self, usecases):
        result = _create_delivery(usecases)
        with pytest.raises(ValueError, match="retry"):
            usecases.retry(result["id"])

    def test_retry_appends_phase_run(self, usecases):
        result = _create_delivery(usecases, phase="verify", run_status="failed")
        usecases.retry(result["id"])
        delivery = usecases.get_delivery(result["id"])
        assert len(delivery["phase_runs"]) == 2
        assert delivery["phase_runs"][-1]["phase"] == "verify"
        assert delivery["phase_runs"][-1]["run_status"] == "pending"
