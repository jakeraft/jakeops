import hashlib

from app.domain.constants import ID_HEX_LENGTH
from app.domain.models.github import GitHubIssue
from app.domain.models.delivery import DeliveryCreate
from app.usecases.delivery_sync import DeliverySyncUseCase


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


class FakeDeliveryUseCases:
    def __init__(self):
        self.created: list[DeliveryCreate] = []
        self._deliveries: dict[str, dict] = {}

    def get_delivery(self, delivery_id: str) -> dict | None:
        return self._deliveries.get(delivery_id)

    def create_delivery(self, body: DeliveryCreate) -> dict:
        self.created.append(body)
        raw = f"{body.repository}:{body.refs[0].label}"
        delivery_id = hashlib.sha256(raw.encode()).hexdigest()[:ID_HEX_LENGTH]
        self._deliveries[delivery_id] = {"id": delivery_id}
        return {"id": delivery_id, "status": "created"}


def test_sync_creates_delivery_for_new_github_issue():
    issues = [GitHubIssue(number=1, title="Bug", html_url="https://github.com/o/r/issues/1", state="open")]
    github_repo = FakeGitHubRepo(issues)
    source_repo = FakeSourceRepo([{"id": "s1", "owner": "o", "repo": "r"}])
    delivery_uc = FakeDeliveryUseCases()

    uc = DeliverySyncUseCase(github_repo, source_repo, delivery_uc)
    uc.sync_once()

    assert len(delivery_uc.created) == 1
    body = delivery_uc.created[0]
    assert body.phase.value == "intake"
    assert body.run_status.value == "pending"
    assert body.refs[0].type.value == "github_issue"
    assert body.refs[0].label == "#1"
    assert body.repository == "o/r"


def test_sync_skips_existing_delivery():
    issues = [GitHubIssue(number=1, title="Bug", html_url="https://github.com/o/r/issues/1", state="open")]
    github_repo = FakeGitHubRepo(issues)
    source_repo = FakeSourceRepo([{"id": "s1", "owner": "o", "repo": "r"}])
    delivery_uc = FakeDeliveryUseCases()

    uc = DeliverySyncUseCase(github_repo, source_repo, delivery_uc)
    uc.sync_once()
    uc.sync_once()

    assert len(delivery_uc.created) == 1


def test_sync_multiple_sources():
    issues = [GitHubIssue(number=1, title="Bug", html_url="https://github.com/o/r/issues/1", state="open")]
    github_repo = FakeGitHubRepo(issues)
    source_repo = FakeSourceRepo([
        {"id": "s1", "owner": "o", "repo": "r"},
        {"id": "s2", "owner": "o", "repo": "r2"},
    ])
    delivery_uc = FakeDeliveryUseCases()

    uc = DeliverySyncUseCase(github_repo, source_repo, delivery_uc)
    uc.sync_once()

    assert len(delivery_uc.created) == 2


def test_sync_no_sources():
    github_repo = FakeGitHubRepo([])
    source_repo = FakeSourceRepo([])
    delivery_uc = FakeDeliveryUseCases()

    uc = DeliverySyncUseCase(github_repo, source_repo, delivery_uc)
    uc.sync_once()

    assert len(delivery_uc.created) == 0


def test_sync_skips_inactive_source():
    issues = [GitHubIssue(number=1, title="Bug", html_url="https://github.com/o/r/issues/1", state="open")]
    github_repo = FakeGitHubRepo(issues)
    source_repo = FakeSourceRepo([
        {"id": "s1", "owner": "o", "repo": "r", "active": False},
    ])
    delivery_uc = FakeDeliveryUseCases()

    uc = DeliverySyncUseCase(github_repo, source_repo, delivery_uc)
    created = uc.sync_once()

    assert created == 0
    assert len(delivery_uc.created) == 0


def test_sync_passes_source_token():
    issues = [GitHubIssue(number=1, title="Bug", html_url="https://github.com/o/r/issues/1", state="open")]
    github_repo = FakeGitHubRepo(issues)
    source_repo = FakeSourceRepo([
        {"id": "s1", "owner": "o", "repo": "r", "token": "ghp_abc123"},
    ])
    delivery_uc = FakeDeliveryUseCases()

    uc = DeliverySyncUseCase(github_repo, source_repo, delivery_uc)
    uc.sync_once()

    assert github_repo.last_token == "ghp_abc123"


def test_sync_legacy_source_without_token_and_active():
    """Works correctly even when legacy source data lacks token/active fields."""
    issues = [GitHubIssue(number=1, title="Bug", html_url="https://github.com/o/r/issues/1", state="open")]
    github_repo = FakeGitHubRepo(issues)
    source_repo = FakeSourceRepo([
        {"id": "s1", "owner": "o", "repo": "r"},
    ])
    delivery_uc = FakeDeliveryUseCases()

    uc = DeliverySyncUseCase(github_repo, source_repo, delivery_uc)
    created = uc.sync_once()

    assert created == 1
    assert github_repo.last_token == ""


def test_sync_uses_source_default_exit_phase():
    """Source with default_exit_phase passes it through to created deliveries."""
    issues = [GitHubIssue(number=1, title="Bug", html_url="https://github.com/o/r/issues/1", state="open")]
    github_repo = FakeGitHubRepo(issues)
    source_repo = FakeSourceRepo([
        {"id": "s1", "owner": "o", "repo": "r", "default_exit_phase": "verify"},
    ])
    delivery_uc = FakeDeliveryUseCases()

    uc = DeliverySyncUseCase(github_repo, source_repo, delivery_uc)
    uc.sync_once()

    body = delivery_uc.created[0]
    assert body.exit_phase.value == "verify"
