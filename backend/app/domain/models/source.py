from enum import Enum

from pydantic import BaseModel


class SourceType(str, Enum):
    github = "github"


class Source(BaseModel):
    id: str
    type: SourceType
    owner: str
    repo: str
    created_at: str
    token: str = ""
    active: bool = True
    default_exit_phase: str = "deploy"


class SourceCreate(BaseModel):
    type: SourceType
    owner: str
    repo: str
    token: str = ""
    default_exit_phase: str = "deploy"


class SourceUpdate(BaseModel):
    token: str | None = None
    active: bool | None = None
    default_exit_phase: str | None = None
