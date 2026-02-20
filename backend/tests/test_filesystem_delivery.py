import json

import pytest

from app.adapters.outbound.filesystem_delivery import FileSystemDeliveryRepository


@pytest.fixture
def repo(tmp_path):
    return FileSystemDeliveryRepository(tmp_path / "deliveries")


def _make_delivery(delivery_id: str, created_at: str) -> dict:
    return {
        "id": delivery_id,
        "schema_version": 4,
        "phase": "intake",
        "run_status": "pending",
        "summary": f"Delivery {delivery_id}",
        "repository": "owner/repo",
        "refs": [],
        "created_at": created_at,
    }


class TestSaveAndGet:
    def test_save_and_get(self, repo):
        data = _make_delivery("abc12345", "2026-02-20T10:00:00+09:00")
        repo.save_delivery("abc12345", data)

        result = repo.get_delivery("abc12345")
        assert result is not None
        assert result["id"] == "abc12345"
        assert result["summary"] == "Delivery abc12345"
        assert result["created_at"] == "2026-02-20T10:00:00+09:00"


class TestGetNonexistent:
    def test_get_nonexistent(self, repo):
        result = repo.get_delivery("nonexistent")
        assert result is None


class TestListDeliveries:
    def test_list_deliveries(self, repo):
        older = _make_delivery("dlv00001", "2026-02-19T10:00:00+09:00")
        newer = _make_delivery("dlv00002", "2026-02-20T10:00:00+09:00")

        repo.save_delivery("dlv00001", older)
        repo.save_delivery("dlv00002", newer)

        items = repo.list_deliveries()
        assert len(items) == 2
        # reverse created_at order: newer first
        assert items[0]["id"] == "dlv00002"
        assert items[1]["id"] == "dlv00001"


class TestAtomicWrite:
    def test_atomic_write(self, repo, tmp_path):
        data = _make_delivery("atomic01", "2026-02-20T12:00:00+09:00")
        repo.save_delivery("atomic01", data)

        # verify the saved file is valid JSON
        file = tmp_path / "deliveries" / "atomic01" / "delivery.json"
        assert file.exists()
        parsed = json.loads(file.read_text(encoding="utf-8"))
        assert parsed["id"] == "atomic01"


class TestTranscript:
    def test_save_and_get_transcript(self, repo):
        transcript_data = {
            "run_id": "run001",
            "messages": [{"role": "user", "content": "hello"}],
        }
        repo.save_run_transcript("dlv00001", "run001", transcript_data)

        result = repo.get_run_transcript("dlv00001", "run001")
        assert result is not None
        assert result["run_id"] == "run001"
        assert len(result["messages"]) == 1

    def test_get_run_transcript_not_found(self, repo):
        result = repo.get_run_transcript("dlv00001", "nonexistent")
        assert result is None


class TestCorruptedFile:
    def test_list_corrupted_file_skipped(self, repo, tmp_path):
        # save a valid file
        good = _make_delivery("good0001", "2026-02-20T10:00:00+09:00")
        repo.save_delivery("good0001", good)

        # create a corrupted JSON file directly
        bad_file = tmp_path / "deliveries" / "bad00001.json"
        bad_file.write_text("{invalid json", encoding="utf-8")

        items = repo.list_deliveries()
        assert len(items) == 1
        assert items[0]["id"] == "good0001"
