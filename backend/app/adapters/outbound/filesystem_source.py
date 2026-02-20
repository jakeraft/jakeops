import json
import logging
import os
import tempfile
from pathlib import Path

logger = logging.getLogger(__name__)


class FileSystemSourceRepository:
    def __init__(self, data_dir: Path) -> None:
        self._dir = data_dir
        self._dir.mkdir(parents=True, exist_ok=True)

    def list_sources(self) -> list[dict]:
        items: list[dict] = []
        for f in self._dir.glob("*.json"):
            try:
                data = json.loads(f.read_text(encoding="utf-8"))
                items.append(data)
            except (json.JSONDecodeError, ValueError):
                logger.warning("Skipping corrupted source file: %s", f)
        items.sort(key=lambda x: x.get("created_at", ""), reverse=True)
        return items

    def get_source(self, source_id: str) -> dict | None:
        file = self._dir / f"{source_id}.json"
        if not file.exists():
            return None
        return json.loads(file.read_text(encoding="utf-8"))

    def save_source(self, source_id: str, data: dict) -> None:
        file = self._dir / f"{source_id}.json"
        self._atomic_write(file, data)

    def delete_source(self, source_id: str) -> bool:
        file = self._dir / f"{source_id}.json"
        if not file.exists():
            return False
        file.unlink()
        return True

    def _atomic_write(self, target: Path, data: dict) -> None:
        """Write JSON atomically: write to temp file, then rename."""
        content = json.dumps(data, ensure_ascii=False, indent=2)
        fd, tmp_path = tempfile.mkstemp(
            dir=target.parent, suffix=".tmp", prefix=".source_"
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
