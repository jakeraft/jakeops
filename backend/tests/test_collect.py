import json
from pathlib import Path

import pytest
from starlette.testclient import TestClient

from app.main import app


@pytest.fixture
def client():
    return TestClient(app)


@pytest.fixture
def delivery_id(client):
    body = {
        "phase": "intake",
        "run_status": "pending",
        "summary": "test delivery",
        "repository": "owner/repo",
        "refs": [{"role": "request", "type": "github_issue", "label": "#1"}],
    }
    resp = client.post("/api/deliveries", json=body)
    return resp.json()["id"]


@pytest.fixture
def session_dir(tmp_path, monkeypatch):
    project_dir = tmp_path / "proj-hash"
    project_dir.mkdir()
    monkeypatch.setattr(
        "app.domain.services.session_parser.CLAUDE_PROJECTS_DIR",
        tmp_path,
    )
    return project_dir


def _write_session_file(session_dir: Path, session_id: str) -> Path:
    lines = [
        json.dumps({
            "type": "system", "subtype": "init",
            "sessionId": session_id,
            "message": {"model": "claude-opus-4-6", "cwd": "/tmp/repo"},
        }),
        json.dumps({
            "type": "user", "sessionId": session_id,
            "message": {"role": "user", "content": "implement this"},
        }),
        json.dumps({
            "type": "assistant", "sessionId": session_id,
            "message": {
                "role": "assistant",
                "content": [{"type": "text", "text": "Implementation complete."}],
                "usage": {"input_tokens": 500, "output_tokens": 200},
            },
        }),
    ]
    f = session_dir / f"{session_id}.jsonl"
    f.write_text("\n".join(lines))
    return f


class TestCollectEndpoint:
    def test_collect_success(self, client, delivery_id, session_dir):
        _write_session_file(session_dir, "sess-abc")
        resp = client.post(
            f"/api/deliveries/{delivery_id}/collect",
            json={"session_id": "sess-abc"},
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["status"] == "collected"

        delivery = client.get(f"/api/deliveries/{delivery_id}").json()
        assert len(delivery["runs"]) == 1
        assert delivery["runs"][0]["session_id"] == "sess-abc"
        assert delivery["runs"][0]["session"]["model"] == "claude-opus-4-6"

    def test_collect_not_found_delivery(self, client, session_dir):
        _write_session_file(session_dir, "sess-abc")
        resp = client.post(
            "/api/deliveries/nonexistent/collect",
            json={"session_id": "sess-abc"},
        )
        assert resp.status_code == 404

    def test_collect_session_file_not_found(self, client, delivery_id, session_dir):
        resp = client.post(
            f"/api/deliveries/{delivery_id}/collect",
            json={"session_id": "nonexistent"},
        )
        assert resp.status_code == 404
        assert "Session file not found" in resp.json()["detail"]
