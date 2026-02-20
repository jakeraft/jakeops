import json
import logging
import os
import tempfile
from pathlib import Path

logger = logging.getLogger(__name__)


class FileSystemIssueRepository:
    def __init__(self, data_dir: Path) -> None:
        self._dir = data_dir
        self._dir.mkdir(parents=True, exist_ok=True)

    def list_issues(self) -> list[dict]:
        items: list[dict] = []
        for issue_dir in self._dir.iterdir():
            if not issue_dir.is_dir():
                continue
            f = issue_dir / "issue.json"
            if not f.exists():
                continue
            try:
                data = json.loads(f.read_text(encoding="utf-8"))
                items.append(data)
            except (json.JSONDecodeError, ValueError):
                logger.warning("Skipping corrupted issue file: %s", f)
        items.sort(key=lambda x: x.get("created_at", ""), reverse=True)
        return items

    def get_issue(self, issue_id: str) -> dict | None:
        file = self._dir / issue_id / "issue.json"
        if not file.exists():
            return None
        return json.loads(file.read_text(encoding="utf-8"))

    def save_issue(self, issue_id: str, data: dict) -> None:
        issue_dir = self._dir / issue_id
        issue_dir.mkdir(parents=True, exist_ok=True)
        file = issue_dir / "issue.json"
        self._atomic_write(file, data)

    def get_run_transcript(self, issue_id: str, run_id: str) -> dict | None:
        file = self._dir / issue_id / f"run-{run_id}.transcript.json"
        if not file.exists():
            return None
        return json.loads(file.read_text(encoding="utf-8"))

    def save_run_transcript(self, issue_id: str, run_id: str, data: dict) -> None:
        issue_dir = self._dir / issue_id
        issue_dir.mkdir(parents=True, exist_ok=True)
        file = issue_dir / f"run-{run_id}.transcript.json"
        self._atomic_write(file, data)

    def _atomic_write(self, target: Path, data: dict) -> None:
        """Write JSON atomically: write to temp file, then rename."""
        content = json.dumps(data, ensure_ascii=False, indent=2)
        fd, tmp_path = tempfile.mkstemp(
            dir=target.parent, suffix=".tmp", prefix=".issue_"
        )
        closed = False
        try:
            os.write(fd, content.encode("utf-8"))
            os.close(fd)
            closed = True
            Path(tmp_path).replace(target)
        except BaseException:
            if not closed:
                os.close(fd)
            Path(tmp_path).unlink(missing_ok=True)
            raise
