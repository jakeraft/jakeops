import hashlib

from app.domain.constants import ID_HEX_LENGTH
from app.domain.models.github import GitHubIssue
from app.domain.models.issue import IssueCreate
from app.usecases.issue_sync import IssueSyncUseCase


class FakeGitHubRepo:
    def __init__(self, issues: list[GitHubIssue] | None = None):
        self._issues = issues or []
        self.last_token: str | None = None

    def list_open_issues(self, owner: str, repo: str, token: str = "") -> list[GitHubIssue]:
        self.last_token = token
        return self._issues


class FakeSourceRepo:
    def __init__(self, sources: list[dict] | None = None):
        self._sources = sources or []
        self.saved: dict[str, dict] = {}

    def list_sources(self) -> list[dict]:
        return self._sources

    def save_source(self, source_id: str, data: dict) -> None:
        self.saved[source_id] = data


class FakeIssueUseCases:
    def __init__(self):
        self.created: list[IssueCreate] = []
        self._issues: dict[str, dict] = {}

    def get_issue(self, issue_id: str) -> dict | None:
        return self._issues.get(issue_id)

    def create_issue(self, body: IssueCreate) -> dict:
        self.created.append(body)
        raw = f"{body.repository}:{body.refs[0].label}"
        issue_id = hashlib.sha256(raw.encode()).hexdigest()[:ID_HEX_LENGTH]
        self._issues[issue_id] = {"id": issue_id}
        return {"id": issue_id, "status": "created"}


def test_sync_creates_issue_for_new_github_issue():
    issues = [GitHubIssue(number=1, title="Bug", html_url="https://github.com/o/r/issues/1", state="open")]
    github_repo = FakeGitHubRepo(issues)
    source_repo = FakeSourceRepo([{"id": "s1", "owner": "o", "repo": "r"}])
    issue_uc = FakeIssueUseCases()

    uc = IssueSyncUseCase(github_repo, source_repo, issue_uc)
    uc.sync_once()

    assert len(issue_uc.created) == 1
    body = issue_uc.created[0]
    assert body.status.value == "new"
    assert body.refs[0].type.value == "github_issue"
    assert body.refs[0].label == "#1"
    assert body.repository == "o/r"


def test_sync_skips_existing_issue():
    issues = [GitHubIssue(number=1, title="Bug", html_url="https://github.com/o/r/issues/1", state="open")]
    github_repo = FakeGitHubRepo(issues)
    source_repo = FakeSourceRepo([{"id": "s1", "owner": "o", "repo": "r"}])
    issue_uc = FakeIssueUseCases()

    uc = IssueSyncUseCase(github_repo, source_repo, issue_uc)
    uc.sync_once()
    uc.sync_once()

    assert len(issue_uc.created) == 1


def test_sync_multiple_sources():
    issues = [GitHubIssue(number=1, title="Bug", html_url="https://github.com/o/r/issues/1", state="open")]
    github_repo = FakeGitHubRepo(issues)
    source_repo = FakeSourceRepo([
        {"id": "s1", "owner": "o", "repo": "r"},
        {"id": "s2", "owner": "o", "repo": "r2"},
    ])
    issue_uc = FakeIssueUseCases()

    uc = IssueSyncUseCase(github_repo, source_repo, issue_uc)
    uc.sync_once()

    assert len(issue_uc.created) == 2


def test_sync_no_sources():
    github_repo = FakeGitHubRepo([])
    source_repo = FakeSourceRepo([])
    issue_uc = FakeIssueUseCases()

    uc = IssueSyncUseCase(github_repo, source_repo, issue_uc)
    uc.sync_once()

    assert len(issue_uc.created) == 0


def test_sync_skips_inactive_source():
    issues = [GitHubIssue(number=1, title="Bug", html_url="https://github.com/o/r/issues/1", state="open")]
    github_repo = FakeGitHubRepo(issues)
    source_repo = FakeSourceRepo([
        {"id": "s1", "owner": "o", "repo": "r", "active": False},
    ])
    issue_uc = FakeIssueUseCases()

    uc = IssueSyncUseCase(github_repo, source_repo, issue_uc)
    created = uc.sync_once()

    assert created == 0
    assert len(issue_uc.created) == 0


def test_sync_passes_source_token():
    issues = [GitHubIssue(number=1, title="Bug", html_url="https://github.com/o/r/issues/1", state="open")]
    github_repo = FakeGitHubRepo(issues)
    source_repo = FakeSourceRepo([
        {"id": "s1", "owner": "o", "repo": "r", "token": "ghp_abc123"},
    ])
    issue_uc = FakeIssueUseCases()

    uc = IssueSyncUseCase(github_repo, source_repo, issue_uc)
    uc.sync_once()

    assert github_repo.last_token == "ghp_abc123"


def test_sync_legacy_source_without_token_and_active():
    """Works correctly even when legacy source data lacks token/active fields."""
    issues = [GitHubIssue(number=1, title="Bug", html_url="https://github.com/o/r/issues/1", state="open")]
    github_repo = FakeGitHubRepo(issues)
    source_repo = FakeSourceRepo([
        {"id": "s1", "owner": "o", "repo": "r"},
    ])
    issue_uc = FakeIssueUseCases()

    uc = IssueSyncUseCase(github_repo, source_repo, issue_uc)
    created = uc.sync_once()

    assert created == 1
    assert github_repo.last_token == ""
