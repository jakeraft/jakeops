import json

import pytest

from app.adapters.outbound.filesystem_issue import FileSystemIssueRepository


@pytest.fixture
def repo(tmp_path):
    return FileSystemIssueRepository(tmp_path / "issues")


def _make_issue(issue_id: str, created_at: str) -> dict:
    return {
        "id": issue_id,
        "schema_version": 1,
        "status": "new",
        "summary": f"Issue {issue_id}",
        "repository": "owner/repo",
        "refs": [],
        "created_at": created_at,
    }


class TestSaveAndGet:
    def test_save_and_get(self, repo):
        data = _make_issue("abc12345", "2026-02-20T10:00:00+09:00")
        repo.save_issue("abc12345", data)

        result = repo.get_issue("abc12345")
        assert result is not None
        assert result["id"] == "abc12345"
        assert result["summary"] == "Issue abc12345"
        assert result["created_at"] == "2026-02-20T10:00:00+09:00"


class TestGetNonexistent:
    def test_get_nonexistent(self, repo):
        result = repo.get_issue("nonexistent")
        assert result is None


class TestListIssues:
    def test_list_issues(self, repo):
        older = _make_issue("issue001", "2026-02-19T10:00:00+09:00")
        newer = _make_issue("issue002", "2026-02-20T10:00:00+09:00")

        repo.save_issue("issue001", older)
        repo.save_issue("issue002", newer)

        items = repo.list_issues()
        assert len(items) == 2
        # reverse created_at order: newer first
        assert items[0]["id"] == "issue002"
        assert items[1]["id"] == "issue001"


class TestAtomicWrite:
    def test_atomic_write(self, repo, tmp_path):
        data = _make_issue("atomic01", "2026-02-20T12:00:00+09:00")
        repo.save_issue("atomic01", data)

        # verify the saved file is valid JSON
        file = tmp_path / "issues" / "atomic01" / "issue.json"
        assert file.exists()
        parsed = json.loads(file.read_text(encoding="utf-8"))
        assert parsed["id"] == "atomic01"


class TestTranscript:
    def test_save_and_get_transcript(self, repo):
        transcript_data = {
            "run_id": "run001",
            "messages": [{"role": "user", "content": "hello"}],
        }
        repo.save_run_transcript("issue001", "run001", transcript_data)

        result = repo.get_run_transcript("issue001", "run001")
        assert result is not None
        assert result["run_id"] == "run001"
        assert len(result["messages"]) == 1

    def test_get_run_transcript_not_found(self, repo):
        result = repo.get_run_transcript("issue001", "nonexistent")
        assert result is None


class TestCorruptedFile:
    def test_list_corrupted_file_skipped(self, repo, tmp_path):
        # save a valid file
        good = _make_issue("good0001", "2026-02-20T10:00:00+09:00")
        repo.save_issue("good0001", good)

        # create a corrupted JSON file directly
        bad_file = tmp_path / "issues" / "bad00001.json"
        bad_file.write_text("{invalid json", encoding="utf-8")

        items = repo.list_issues()
        assert len(items) == 1
        assert items[0]["id"] == "good0001"
