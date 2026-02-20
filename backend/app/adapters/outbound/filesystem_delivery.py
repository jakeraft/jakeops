import json
import logging
import os
import tempfile
from pathlib import Path

logger = logging.getLogger(__name__)


class FileSystemDeliveryRepository:
    def __init__(self, data_dir: Path) -> None:
        self._dir = data_dir
        self._dir.mkdir(parents=True, exist_ok=True)

    def list_deliveries(self) -> list[dict]:
        items: list[dict] = []
        for delivery_dir in self._dir.iterdir():
            if not delivery_dir.is_dir():
                continue
            f = delivery_dir / "delivery.json"
            if not f.exists():
                continue
            try:
                data = json.loads(f.read_text(encoding="utf-8"))
                items.append(data)
            except (json.JSONDecodeError, ValueError):
                logger.warning("Skipping corrupted delivery file: %s", f)
        items.sort(key=lambda x: x.get("created_at", ""), reverse=True)
        return items

    def get_delivery(self, delivery_id: str) -> dict | None:
        file = self._dir / delivery_id / "delivery.json"
        if not file.exists():
            return None
        return json.loads(file.read_text(encoding="utf-8"))

    def save_delivery(self, delivery_id: str, data: dict) -> None:
        delivery_dir = self._dir / delivery_id
        delivery_dir.mkdir(parents=True, exist_ok=True)
        file = delivery_dir / "delivery.json"
        self._atomic_write(file, data)

    def get_run_transcript(self, delivery_id: str, run_id: str) -> dict | None:
        file = self._dir / delivery_id / f"run-{run_id}.transcript.json"
        if not file.exists():
            return None
        return json.loads(file.read_text(encoding="utf-8"))

    def save_run_transcript(self, delivery_id: str, run_id: str, data: dict) -> None:
        delivery_dir = self._dir / delivery_id
        delivery_dir.mkdir(parents=True, exist_ok=True)
        file = delivery_dir / f"run-{run_id}.transcript.json"
        self._atomic_write(file, data)

    def _atomic_write(self, target: Path, data: dict) -> None:
        """Write JSON atomically: write to temp file, then rename."""
        content = json.dumps(data, ensure_ascii=False, indent=2)
        fd, tmp_path = tempfile.mkstemp(
            dir=target.parent, suffix=".tmp", prefix=".delivery_"
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
