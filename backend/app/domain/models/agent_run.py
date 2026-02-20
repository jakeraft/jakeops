from enum import Enum

from pydantic import BaseModel

from app.domain.models.delivery import ExecutionStats, Phase, Session


class AgentRunStatus(str, Enum):
    running = "running"
    success = "success"
    failed = "failed"


class AgentRun(BaseModel):
    id: str
    mode: Phase
    status: AgentRunStatus
    created_at: str
    session: Session
    stats: ExecutionStats
    error: str | None = None
    summary: str | None = None
    session_id: str | None = None
    prompt: str | None = None
    skills: list[str] = []
    used_skills: list[str] = []
    plugins: list[str] = []
    agents: list[str] = []
