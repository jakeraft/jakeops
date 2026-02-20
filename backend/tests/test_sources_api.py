from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)


def test_list_sources_empty():
    resp = client.get("/api/sources")
    assert resp.status_code == 200
    assert resp.json() == []


def test_create_source():
    resp = client.post("/api/sources", json={"type": "github", "owner": "jakeraft", "repo": "jakeops"})
    assert resp.status_code == 200
    data = resp.json()
    assert len(data["id"]) == 12
    assert data["owner"] == "jakeraft"
    assert data["repo"] == "jakeops"
    assert data["type"] == "github"
    assert data["active"] is True
    assert data["token"] == ""


def test_create_source_with_token():
    resp = client.post(
        "/api/sources",
        json={"type": "github", "owner": "tokenowner", "repo": "tokenrepo", "token": "ghp_abcdefgh1234"},
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["token"] == "ghp_****1234"


def test_create_source_duplicate():
    client.post("/api/sources", json={"type": "github", "owner": "dup", "repo": "same"})
    resp = client.post("/api/sources", json={"type": "github", "owner": "dup", "repo": "same"})
    assert resp.status_code == 409


def test_get_source():
    resp = client.post("/api/sources", json={"type": "github", "owner": "getsrc", "repo": "r"})
    source_id = resp.json()["id"]
    resp = client.get(f"/api/sources/{source_id}")
    assert resp.status_code == 200
    assert resp.json()["owner"] == "getsrc"


def test_get_source_not_found():
    resp = client.get("/api/sources/nonexist")
    assert resp.status_code == 404


def test_patch_toggle_active():
    resp = client.post("/api/sources", json={"type": "github", "owner": "toggle", "repo": "repo"})
    source_id = resp.json()["id"]
    resp = client.patch(f"/api/sources/{source_id}", json={"active": False})
    assert resp.status_code == 200
    assert resp.json()["active"] is False


def test_patch_update_token():
    resp = client.post("/api/sources", json={"type": "github", "owner": "tokupd", "repo": "repo"})
    source_id = resp.json()["id"]
    resp = client.patch(f"/api/sources/{source_id}", json={"token": "ghp_newtoken5678"})
    assert resp.status_code == 200
    assert resp.json()["token"] == "ghp_****5678"


def test_patch_not_found():
    resp = client.patch("/api/sources/nonexist", json={"active": False})
    assert resp.status_code == 404


def test_delete_source():
    resp = client.post("/api/sources", json={"type": "github", "owner": "del", "repo": "repo"})
    source_id = resp.json()["id"]
    resp = client.delete(f"/api/sources/{source_id}")
    assert resp.status_code == 200


def test_delete_source_not_found():
    resp = client.delete("/api/sources/nonexist")
    assert resp.status_code == 404
