import hashlib
import logging
from datetime import datetime

from app.domain.constants import KST, ID_HEX_LENGTH
from app.domain.models.issue import Ref, RefRole, RefType, IssueCreate, IssueStatus, Session
from app.ports.outbound.github_repository import GitHubRepository
from app.ports.outbound.source_repository import SourceRepository
from app.ports.inbound.issue_usecases import IssueUseCases

logger = logging.getLogger(__name__)


class IssueSyncUseCase:
    def __init__(
        self,
        github_repo: GitHubRepository,
        source_repo: SourceRepository,
        issue_usecases: IssueUseCases,
    ) -> None:
        self._github = github_repo
        self._sources = source_repo
        self._issues = issue_usecases

    def sync_once(self) -> int:
        created = 0
        sources = self._sources.list_sources()
        for source in sources:
            if not source.get("active", True):
                continue
            owner, repo = source["owner"], source["repo"]
            try:
                gh_issues = self._github.list_open_issues(owner, repo, token=source.get("token", ""))
            except Exception as e:
                logger.error("Failed to fetch issues: %s/%s — %s", owner, repo, e)
                continue

            source["last_polled_at"] = datetime.now(KST).isoformat()
            self._sources.save_source(source["id"], source)

            for gh_issue in gh_issues:
                label = f"#{gh_issue.number}"
                raw = f"{owner}/{repo}:{label}"
                issue_id = hashlib.sha256(raw.encode()).hexdigest()[:ID_HEX_LENGTH]

                if self._issues.get_issue(issue_id):
                    continue

                body = IssueCreate(
                    status=IssueStatus.new,
                    summary=f"GitHub Issue #{gh_issue.number}: {gh_issue.title}",
                    repository=f"{owner}/{repo}",
                    refs=[
                        Ref(
                            role=RefRole.trigger,
                            type=RefType.github_issue,
                            label=label,
                            url=gh_issue.html_url,
                        )
                    ],
                )
                self._issues.create_issue(body)
                created += 1
                logger.info("Created issue: %s/%s %s", owner, repo, label)
        return created
