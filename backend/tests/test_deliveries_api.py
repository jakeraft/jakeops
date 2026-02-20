from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)

VALID_DELIVERY = {
    "phase": "intake",
    "run_status": "pending",
    "summary": "test delivery",
    "repository": "jakeops",
    "refs": [{"role": "trigger", "type": "github_issue", "label": "#1"}],
}


def test_create_delivery():
    resp = client.post("/api/deliveries", json=VALID_DELIVERY)
    assert resp.status_code == 200
    assert len(resp.json()["id"]) == 12


def test_list_deliveries():
    client.post("/api/deliveries", json=VALID_DELIVERY)
    resp = client.get("/api/deliveries")
    assert resp.status_code == 200
    assert len(resp.json()) >= 1


def test_get_delivery():
    resp = client.post("/api/deliveries", json=VALID_DELIVERY)
    delivery_id = resp.json()["id"]
    resp = client.get(f"/api/deliveries/{delivery_id}")
    assert resp.status_code == 200
    assert resp.json()["schema_version"] == 4
    assert resp.json()["phase"] == "intake"
    assert resp.json()["run_status"] == "pending"


def test_get_delivery_not_found():
    resp = client.get("/api/deliveries/nonexist")
    assert resp.status_code == 404


def test_update_delivery():
    resp = client.post("/api/deliveries", json=VALID_DELIVERY)
    delivery_id = resp.json()["id"]
    resp = client.patch(f"/api/deliveries/{delivery_id}", json={"summary": "updated"})
    assert resp.status_code == 200


def test_approve_gate_phase():
    delivery_data = {**VALID_DELIVERY, "phase": "plan", "run_status": "succeeded"}
    resp = client.post("/api/deliveries", json=delivery_data)
    delivery_id = resp.json()["id"]
    resp = client.post(f"/api/deliveries/{delivery_id}/approve")
    assert resp.status_code == 200
    assert resp.json()["phase"] == "implement"
    assert resp.json()["run_status"] == "pending"


def test_approve_non_gate_phase():
    resp = client.post("/api/deliveries", json=VALID_DELIVERY)
    delivery_id = resp.json()["id"]
    resp = client.post(f"/api/deliveries/{delivery_id}/approve")
    assert resp.status_code == 409


def test_reject_gate_phase():
    delivery_data = {**VALID_DELIVERY, "phase": "plan", "run_status": "succeeded"}
    resp = client.post("/api/deliveries", json=delivery_data)
    delivery_id = resp.json()["id"]
    resp = client.post(f"/api/deliveries/{delivery_id}/reject", json={"reason": "needs replanning"})
    assert resp.status_code == 200
    assert resp.json()["phase"] == "intake"
    assert resp.json()["run_status"] == "pending"


def test_cancel():
    resp = client.post("/api/deliveries", json=VALID_DELIVERY)
    delivery_id = resp.json()["id"]
    resp = client.post(f"/api/deliveries/{delivery_id}/cancel")
    assert resp.status_code == 200
    assert resp.json()["run_status"] == "canceled"


def test_retry_from_failed():
    delivery_data = {**VALID_DELIVERY, "phase": "verify", "run_status": "failed"}
    resp = client.post("/api/deliveries", json=delivery_data)
    delivery_id = resp.json()["id"]
    resp = client.post(f"/api/deliveries/{delivery_id}/retry")
    assert resp.status_code == 200
    assert resp.json()["run_status"] == "pending"
    assert resp.json()["phase"] == "verify"


def test_get_schema():
    resp = client.get("/api/deliveries/schema")
    assert resp.status_code == 200
    assert "properties" in resp.json()
