import json

import pytest

from app.adapters.outbound.filesystem_source import FileSystemSourceRepository


@pytest.fixture
def repo(tmp_path):
    return FileSystemSourceRepository(tmp_path / "sources")


def _make_source(source_id: str, created_at: str) -> dict:
    return {
        "id": source_id,
        "type": "github",
        "owner": "jakeraft",
        "repo": "jakeops",
        "created_at": created_at,
        "token": "",
        "active": True,
    }


class TestSaveAndGet:
    def test_save_and_get(self, repo):
        data = _make_source("src00001", "2026-02-20T10:00:00+09:00")
        repo.save_source("src00001", data)

        result = repo.get_source("src00001")
        assert result is not None
        assert result["id"] == "src00001"
        assert result["owner"] == "jakeraft"
        assert result["repo"] == "jakeops"


class TestGetNonexistent:
    def test_get_nonexistent(self, repo):
        result = repo.get_source("nonexistent")
        assert result is None


class TestListSources:
    def test_list_sources(self, repo):
        older = _make_source("src00001", "2026-02-19T10:00:00+09:00")
        newer = _make_source("src00002", "2026-02-20T10:00:00+09:00")

        repo.save_source("src00001", older)
        repo.save_source("src00002", newer)

        items = repo.list_sources()
        assert len(items) == 2
        # reverse created_at order: newer first
        assert items[0]["id"] == "src00002"
        assert items[1]["id"] == "src00001"


class TestDeleteSource:
    def test_delete_source(self, repo):
        data = _make_source("src00001", "2026-02-20T10:00:00+09:00")
        repo.save_source("src00001", data)

        result = repo.delete_source("src00001")
        assert result is True
        assert repo.get_source("src00001") is None

    def test_delete_nonexistent(self, repo):
        result = repo.delete_source("nonexistent")
        assert result is False


class TestCorruptedFile:
    def test_list_corrupted_file_skipped(self, repo, tmp_path):
        # save a valid file
        good = _make_source("good0001", "2026-02-20T10:00:00+09:00")
        repo.save_source("good0001", good)

        # create a corrupted JSON file directly
        bad_file = tmp_path / "sources" / "bad00001.json"
        bad_file.write_text("{invalid json", encoding="utf-8")

        items = repo.list_sources()
        assert len(items) == 1
        assert items[0]["id"] == "good0001"
