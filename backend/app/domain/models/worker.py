from __future__ import annotations

from pydantic import BaseModel


class WorkerStatus(BaseModel):
    name: str
    label: str
    enabled: bool
    interval_sec: int
    last_poll_at: str | None = None
    last_result: dict | None = None
    last_error: str | None = None


class WorkerStatusResponse(BaseModel):
    workers: list[WorkerStatus]
