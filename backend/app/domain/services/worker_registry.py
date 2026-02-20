from __future__ import annotations

from datetime import datetime, timezone

from app.domain.models.worker import WorkerStatus


class WorkerRegistry:
    """In-memory worker status registry."""

    def __init__(self) -> None:
        self._workers: dict[str, WorkerStatus] = {}

    def register(
        self,
        name: str,
        *,
        label: str,
        interval_sec: int,
        enabled: bool,
    ) -> None:
        self._workers[name] = WorkerStatus(
            name=name,
            label=label,
            enabled=enabled,
            interval_sec=interval_sec,
        )

    def record_success(self, name: str, result: dict) -> None:
        if name not in self._workers:
            return
        w = self._workers[name]
        self._workers[name] = w.model_copy(update={
            "last_poll_at": datetime.now(timezone.utc).isoformat(),
            "last_result": result,
            "last_error": None,
        })

    def record_error(self, name: str, error: str) -> None:
        if name not in self._workers:
            return
        w = self._workers[name]
        self._workers[name] = w.model_copy(update={
            "last_poll_at": datetime.now(timezone.utc).isoformat(),
            "last_error": error,
            "last_result": None,
        })

    def get_all(self) -> list[WorkerStatus]:
        return list(self._workers.values())
