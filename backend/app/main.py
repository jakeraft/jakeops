import asyncio
import logging
import os
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.adapters.inbound import issues, sources, worker
from app.domain.services.worker_registry import WorkerRegistry
from app.adapters.outbound.filesystem_issue import FileSystemIssueRepository
from app.adapters.outbound.filesystem_source import FileSystemSourceRepository
from app.adapters.outbound.github_api import GitHubApiAdapter
from app.usecases.issue_usecases import IssueUseCasesImpl
from app.usecases.source_usecases import SourceUseCasesImpl
from app.usecases.issue_sync import IssueSyncUseCase

logger = logging.getLogger(__name__)

PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent

ISSUES_DIR = Path(os.environ.get("JAKEOPS_DATA_DIR", PROJECT_ROOT / "issues"))
SOURCES_DIR = Path(os.environ.get("JAKEOPS_SOURCES_DIR", PROJECT_ROOT / "sources"))

GITHUB_POLL_INTERVAL = int(os.environ.get("GITHUB_POLL_INTERVAL", "60"))
CORS_ORIGINS = os.environ.get("JAKEOPS_CORS_ORIGINS", "*").split(",")


async def _poll_loop(
    issue_sync: IssueSyncUseCase,
    interval: int,
    registry: WorkerRegistry,
    runner_name: str,
) -> None:
    while True:
        try:
            created = await asyncio.to_thread(issue_sync.sync_once)
            registry.record_success(runner_name, {"created": created})
            if created:
                logger.info("Issue sync: created %d issues", created)
        except Exception as e:
            registry.record_error(runner_name, str(e))
            logger.error("Issue sync failed: %s", e)
        await asyncio.sleep(interval)


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Outbound Adapters
    issue_repo = FileSystemIssueRepository(ISSUES_DIR)
    source_repo = FileSystemSourceRepository(SOURCES_DIR)

    # Use Cases
    app.state.issue_usecases = IssueUseCasesImpl(issue_repo)
    app.state.source_usecases = SourceUseCasesImpl(source_repo)

    # Runner Registry
    registry = WorkerRegistry()
    registry.register(
        "issue_sync", label="Issue Sync",
        interval_sec=GITHUB_POLL_INTERVAL, enabled=True,
    )
    app.state.worker_registry = registry

    # Issue Sync
    github_adapter = GitHubApiAdapter()
    issue_sync = IssueSyncUseCase(
        github_repo=github_adapter,
        source_repo=source_repo,
        issue_usecases=app.state.issue_usecases,
    )
    app.state.issue_sync = issue_sync
    poll_task = asyncio.create_task(
        _poll_loop(issue_sync, GITHUB_POLL_INTERVAL, registry, "issue_sync")
    )
    logger.info("Issue polling started (interval: %ds)", GITHUB_POLL_INTERVAL)

    yield
    poll_task.cancel()


app = FastAPI(title="jakeops", version="0.3.0", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=CORS_ORIGINS,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Inbound Adapters (Routers)
app.include_router(issues.router, prefix="/api")
app.include_router(sources.router, prefix="/api")
app.include_router(worker.router, prefix="/api")
