from enum import Enum

from pydantic import BaseModel, Field


class IssueStatus(str, Enum):
    new = "new"
    planned = "planned"
    approved = "approved"
    implemented = "implemented"
    ci_passed = "ci_passed"
    deployed = "deployed"
    done = "done"
    failed = "failed"
    canceled = "canceled"


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


class IssueCreate(BaseModel, extra="ignore"):
    schema_version: int | None = None
    id: str | None = None
    created_at: str | None = None
    status: IssueStatus
    summary: str
    repository: str
    refs: list[Ref]


class IssueUpdate(BaseModel):
    status: IssueStatus | None = None
    summary: str | None = None
    plan: Plan | None = None
    refs: list[Ref] | None = None
    error: str | None = None
