from enum import Enum

from pydantic import BaseModel, Field


class Phase(str, Enum):
    intake = "intake"
    plan = "plan"
    implement = "implement"
    review = "review"
    verify = "verify"
    deploy = "deploy"
    observe = "observe"
    close = "close"


class RunStatus(str, Enum):
    pending = "pending"
    running = "running"
    succeeded = "succeeded"
    failed = "failed"
    blocked = "blocked"
    canceled = "canceled"


class ExecutorKind(str, Enum):
    system = "system"
    agent = "agent"
    human = "human"


class PhaseRun(BaseModel):
    phase: Phase
    run_status: RunStatus
    executor: ExecutorKind
    started_at: str | None = None
    ended_at: str | None = None


class RefRole(str, Enum):
    trigger = "trigger"
    output = "output"
    parent = "parent"


class RefType(str, Enum):
    jira = "jira"
    verbal = "verbal"
    pr = "pr"
    commit = "commit"
    repo = "repo"
    github_issue = "github_issue"
    pull_request = "pull_request"
    issue = "issue"


class Ref(BaseModel):
    role: RefRole
    type: RefType
    label: str
    url: str | None = Field(default=None)


class Session(BaseModel):
    model: str = Field(examples=["claude-opus-4-6"])


class Plan(BaseModel):
    content: str
    generated_at: str
    model: str
    cwd: str


class ExecutionStats(BaseModel):
    cost_usd: float = 0.0
    input_tokens: int = 0
    output_tokens: int = 0
    duration_ms: int = 0


class DeliveryCreate(BaseModel, extra="ignore"):
    schema_version: int | None = None
    id: str | None = None
    created_at: str | None = None
    phase: Phase = Phase.intake
    run_status: RunStatus = RunStatus.pending
    exit_phase: Phase | None = None
    summary: str
    repository: str
    refs: list[Ref]


class DeliveryUpdate(BaseModel):
    phase: Phase | None = None
    run_status: RunStatus | None = None
    summary: str | None = None
    plan: Plan | None = None
    refs: list[Ref] | None = None
    error: str | None = None
