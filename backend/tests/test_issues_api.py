from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)

VALID_ISSUE = {
    "status": "new",
    "summary": "test issue",
    "repository": "jakeops",
    "refs": [{"role": "trigger", "type": "github_issue", "label": "#1"}],
}


def test_create_issue():
    resp = client.post("/api/issues", json=VALID_ISSUE)
    assert resp.status_code == 200
    assert len(resp.json()["id"]) == 12


def test_list_issues():
    client.post("/api/issues", json=VALID_ISSUE)
    resp = client.get("/api/issues")
    assert resp.status_code == 200
    assert len(resp.json()) >= 1


def test_get_issue():
    resp = client.post("/api/issues", json=VALID_ISSUE)
    issue_id = resp.json()["id"]
    resp = client.get(f"/api/issues/{issue_id}")
    assert resp.status_code == 200
    assert resp.json()["schema_version"] == 3


def test_get_issue_not_found():
    resp = client.get("/api/issues/nonexist")
    assert resp.status_code == 404


def test_update_issue():
    resp = client.post("/api/issues", json=VALID_ISSUE)
    issue_id = resp.json()["id"]
    resp = client.patch(f"/api/issues/{issue_id}", json={"summary": "updated"})
    assert resp.status_code == 200


def test_approve_planned():
    resp = client.post("/api/issues", json={**VALID_ISSUE, "status": "planned"})
    issue_id = resp.json()["id"]
    resp = client.post(f"/api/issues/{issue_id}/approve")
    assert resp.status_code == 200
    assert resp.json()["status"] == "approved"


def test_approve_invalid_state():
    resp = client.post("/api/issues", json=VALID_ISSUE)
    issue_id = resp.json()["id"]
    resp = client.post(f"/api/issues/{issue_id}/approve")
    assert resp.status_code == 409


def test_reject_planned():
    resp = client.post("/api/issues", json={**VALID_ISSUE, "status": "planned"})
    issue_id = resp.json()["id"]
    resp = client.post(f"/api/issues/{issue_id}/reject", json={"reason": "needs replanning"})
    assert resp.status_code == 200
    assert resp.json()["status"] == "new"


def test_cancel():
    resp = client.post("/api/issues", json=VALID_ISSUE)
    issue_id = resp.json()["id"]
    resp = client.post(f"/api/issues/{issue_id}/cancel")
    assert resp.status_code == 200
    assert resp.json()["status"] == "canceled"


def test_retry_from_failed():
    resp = client.post("/api/issues", json={**VALID_ISSUE, "status": "failed"})
    issue_id = resp.json()["id"]
    resp = client.post(f"/api/issues/{issue_id}/retry")
    assert resp.status_code == 200
    assert resp.json()["status"] == "new"


def test_generate_plan():
    resp = client.post("/api/issues", json=VALID_ISSUE)
    issue_id = resp.json()["id"]
    resp = client.post(f"/api/issues/{issue_id}/generate-plan")
    assert resp.status_code == 200


def test_get_schema():
    resp = client.get("/api/issues/schema")
    assert resp.status_code == 200
    assert "properties" in resp.json()
