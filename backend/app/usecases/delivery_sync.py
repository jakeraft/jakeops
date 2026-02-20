import hashlib
from datetime import datetime

import structlog

from app.domain.constants import KST, ID_HEX_LENGTH
from app.domain.models.delivery import Ref, RefRole, RefType, DeliveryCreate, Phase, RunStatus, Session
from app.ports.outbound.github_repository import GitHubRepository
from app.ports.outbound.source_repository import SourceRepository
from app.ports.inbound.delivery_usecases import DeliveryUseCases

logger = structlog.get_logger()


class DeliverySyncUseCase:
    def __init__(
        self,
        github_repo: GitHubRepository,
        source_repo: SourceRepository,
        delivery_usecases: DeliveryUseCases,
    ) -> None:
        self._github = github_repo
        self._sources = source_repo
        self._deliveries = delivery_usecases

    def sync_once(self) -> dict:
        created = 0
        closed = 0
        sources = self._sources.list_sources()
        for source in sources:
            if not source.get("active", True):
                continue
            owner, repo = source["owner"], source["repo"]
            try:
                gh_issues = self._github.list_open_issues(owner, repo, token=source.get("token", ""))
            except Exception as e:
                logger.error("Failed to fetch issues", owner=owner, repo=repo, error=str(e))
                continue

            source["last_polled_at"] = datetime.now(KST).isoformat()
            self._sources.save_source(source["id"], source)

            default_endpoint = source.get("endpoint", "deploy")
            default_checkpoints = source.get("checkpoints", ["plan", "implement", "review"])

            for gh_issue in gh_issues:
                label = f"#{gh_issue.number}"
                raw = f"{owner}/{repo}:{label}"
                delivery_id = hashlib.sha256(raw.encode()).hexdigest()[:ID_HEX_LENGTH]

                if self._deliveries.get_delivery(delivery_id):
                    continue

                body = DeliveryCreate(
                    phase=Phase.intake,
                    run_status=RunStatus.pending,
                    endpoint=Phase(default_endpoint),
                    checkpoints=[Phase(cp) for cp in default_checkpoints],
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
                self._deliveries.create_delivery(body)
                created += 1
                logger.info("Created delivery", owner=owner, repo=repo, label=label)

            # Close deliveries whose trigger issues are no longer open
            open_numbers = {issue.number for issue in gh_issues}
            full_repo = f"{owner}/{repo}"
            all_deliveries = self._deliveries.list_deliveries()
            for delivery in all_deliveries:
                if delivery["phase"] == "close" or delivery["run_status"] == "canceled":
                    continue
                if delivery.get("repository") != full_repo:
                    continue

                trigger_ref = next(
                    (r for r in delivery.get("refs", [])
                     if r.get("role") == "trigger" and r.get("type") == "github_issue"),
                    None,
                )
                if trigger_ref is None:
                    continue

                label = trigger_ref.get("label", "")
                if not label.startswith("#"):
                    continue
                number = int(label[1:])

                if number not in open_numbers:
                    self._deliveries.close_delivery(delivery["id"])
                    closed += 1
                    logger.info("Closed delivery", owner=owner, repo=repo, number=number)

        return {"created": created, "closed": closed}
