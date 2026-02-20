from enum import Enum

from pydantic import BaseModel, Field


class SourceType(str, Enum):
    github = "github"


DEFAULT_CHECKPOINTS: list[str] = ["plan", "implement", "review"]


class Source(BaseModel):
    id: str
    type: SourceType
    owner: str
    repo: str
    created_at: str
    token: str = ""
    active: bool = True
    endpoint: str = "deploy"
    checkpoints: list[str] = Field(default_factory=lambda: list(DEFAULT_CHECKPOINTS))
    last_polled_at: str | None = None


class SourceCreate(BaseModel):
    type: SourceType
    owner: str
    repo: str
    token: str = ""
    endpoint: str = "deploy"
    checkpoints: list[str] = Field(default_factory=lambda: list(DEFAULT_CHECKPOINTS))


class SourceUpdate(BaseModel):
    token: str | None = None
    active: bool | None = None
    endpoint: str | None = None
    checkpoints: list[str] | None = None
