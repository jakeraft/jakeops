import json
from pathlib import Path

import pytest
from starlette.testclient import TestClient

from app.main import app


@pytest.fixture
def client():
    return TestClient(app)


@pytest.fixture
def issue_id(client):
    body = {
        "status": "approved",
        "summary": "test issue",
        "repository": "owner/repo",
        "refs": [{"role": "trigger", "type": "github_issue", "label": "#1"}],
    }
    resp = client.post("/api/issues", json=body)
    iid = resp.json()["id"]
    # change to approved status
    client.patch(f"/api/issues/{iid}", json={"status": "approved"})
    return iid


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
    def test_collect_success(self, client, issue_id, session_dir):
        _write_session_file(session_dir, "sess-abc")
        resp = client.post(
            f"/api/issues/{issue_id}/collect",
            json={"session_id": "sess-abc"},
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["status"] == "collected"

        issue = client.get(f"/api/issues/{issue_id}").json()
        assert len(issue["runs"]) == 1
        assert issue["runs"][0]["session_id"] == "sess-abc"
        assert issue["runs"][0]["session"]["model"] == "claude-opus-4-6"

    def test_collect_not_found_issue(self, client, session_dir):
        _write_session_file(session_dir, "sess-abc")
        resp = client.post(
            "/api/issues/nonexistent/collect",
            json={"session_id": "sess-abc"},
        )
        assert resp.status_code == 404

    def test_collect_session_file_not_found(self, client, issue_id, session_dir):
        resp = client.post(
            f"/api/issues/{issue_id}/collect",
            json={"session_id": "nonexistent"},
        )
        assert resp.status_code == 404
        assert "Session file not found" in resp.json()["detail"]
