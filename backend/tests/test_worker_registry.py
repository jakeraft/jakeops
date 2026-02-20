from app.domain.services.worker_registry import WorkerRegistry


def test_register_and_get_status():
    registry = WorkerRegistry()
    registry.register("plan_worker", label="Plan Worker", interval_sec=30, enabled=True)
    statuses = registry.get_all()
    assert len(statuses) == 1
    assert statuses[0].name == "plan_worker"
    assert statuses[0].label == "Plan Worker"
    assert statuses[0].enabled is True
    assert statuses[0].interval_sec == 30
    assert statuses[0].last_poll_at is None
    assert statuses[0].last_result is None
    assert statuses[0].last_error is None


def test_record_success():
    registry = WorkerRegistry()
    registry.register("plan_worker", label="Plan Worker", interval_sec=30, enabled=True)
    registry.record_success("plan_worker", {"processed": 2})
    statuses = registry.get_all()
    assert statuses[0].last_result == {"processed": 2}
    assert statuses[0].last_poll_at is not None
    assert statuses[0].last_error is None


def test_record_success_clears_previous_error():
    registry = WorkerRegistry()
    registry.register("plan_worker", label="Plan Worker", interval_sec=30, enabled=True)
    registry.record_error("plan_worker", "timeout")
    registry.record_success("plan_worker", {"processed": 1})
    statuses = registry.get_all()
    assert statuses[0].last_error is None
    assert statuses[0].last_result == {"processed": 1}


def test_record_error():
    registry = WorkerRegistry()
    registry.register("plan_worker", label="Plan Worker", interval_sec=30, enabled=True)
    registry.record_error("plan_worker", "timeout")
    statuses = registry.get_all()
    assert statuses[0].last_error == "timeout"
    assert statuses[0].last_poll_at is not None


def test_unregistered_worker_ignored():
    registry = WorkerRegistry()
    registry.record_success("unknown", {"x": 1})  # no error
    registry.record_error("unknown", "fail")  # no error
    assert registry.get_all() == []


def test_multiple_workers():
    registry = WorkerRegistry()
    registry.register("issue_sync", label="Issue Sync", interval_sec=60, enabled=True)
    registry.register("plan_worker", label="Plan Worker", interval_sec=30, enabled=True)
    registry.register("exec_worker", label="Execution Worker", interval_sec=30, enabled=False)
    statuses = registry.get_all()
    assert len(statuses) == 3
    names = [s.name for s in statuses]
    assert names == ["issue_sync", "plan_worker", "exec_worker"]
