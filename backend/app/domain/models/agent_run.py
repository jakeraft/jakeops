from enum import Enum

from pydantic import BaseModel

from app.domain.models.issue import ExecutionStats, Session


class AgentRunMode(str, Enum):
    plan = "plan"
    execution = "execution"
    fix = "fix"


class AgentRunStatus(str, Enum):
    success = "success"
    failed = "failed"


class AgentRun(BaseModel):
    id: str
    mode: AgentRunMode
    status: AgentRunStatus
    created_at: str
    session: Session
    stats: ExecutionStats
    error: str | None = None
    summary: str | None = None
    session_id: str | None = None
