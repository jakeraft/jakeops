from typing import Protocol

from app.domain.models.github import GitHubIssue


class GitHubRepository(Protocol):
    def list_open_issues(self, owner: str, repo: str, token: str = "") -> list[GitHubIssue]: ...
    def get_issue(self, owner: str, repo: str, number: int, token: str = "") -> GitHubIssue | None: ...
