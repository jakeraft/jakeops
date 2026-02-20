from fastapi.testclient import TestClient

from app.main import app
from app.domain.services.worker_registry import WorkerRegistry

client = TestClient(app)


def test_worker_status_returns_registered_workers():
    registry = WorkerRegistry()
    registry.register("issue_sync", label="Issue Sync", interval_sec=60, enabled=True)
    registry.register("plan_worker", label="Plan Worker", interval_sec=30, enabled=True)
    app.state.worker_registry = registry

    resp = client.get("/api/worker/status")
    assert resp.status_code == 200
    data = resp.json()
    assert len(data["workers"]) == 2
    assert data["workers"][0]["name"] == "issue_sync"
    assert data["workers"][1]["name"] == "plan_worker"


def test_worker_status_empty():
    app.state.worker_registry = WorkerRegistry()
    resp = client.get("/api/worker/status")
    assert resp.status_code == 200
    assert resp.json()["workers"] == []


def test_worker_status_with_result():
    registry = WorkerRegistry()
    registry.register("plan_worker", label="Plan Worker", interval_sec=30, enabled=True)
    registry.record_success("plan_worker", {"processed": 3})
    app.state.worker_registry = registry

    resp = client.get("/api/worker/status")
    assert resp.status_code == 200
    worker = resp.json()["workers"][0]
    assert worker["last_result"] == {"processed": 3}
    assert worker["last_poll_at"] is not None
    assert worker["last_error"] is None
