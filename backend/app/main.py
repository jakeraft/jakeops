import asyncio
import os
from contextlib import asynccontextmanager
from pathlib import Path

import structlog
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.logging import configure_logging
from app.middleware.logging import RequestLoggingMiddleware
from app.adapters.inbound import deliveries, sources
from app.adapters.outbound.filesystem_delivery import FileSystemDeliveryRepository
from app.adapters.outbound.filesystem_source import FileSystemSourceRepository
from app.adapters.outbound.github_api import GitHubApiAdapter
from app.adapters.outbound.claude_cli import ClaudeCliAdapter
from app.adapters.outbound.git_cli import GitCliAdapter
from app.domain.services.event_bus import EventBus
from app.usecases.delivery_usecases import DeliveryUseCasesImpl
from app.usecases.source_usecases import SourceUseCasesImpl
from app.usecases.delivery_sync import DeliverySyncUseCase

configure_logging()

logger = structlog.get_logger()

PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent

DELIVERIES_DIR = Path(os.environ.get("JAKEOPS_DATA_DIR", PROJECT_ROOT / "deliveries"))
SOURCES_DIR = Path(os.environ.get("JAKEOPS_SOURCES_DIR", PROJECT_ROOT / "sources"))

GITHUB_POLL_INTERVAL = int(os.environ.get("GITHUB_POLL_INTERVAL", "60"))
CORS_ORIGINS = os.environ.get("JAKEOPS_CORS_ORIGINS", "*").split(",")


async def _poll_loop(
    delivery_sync: DeliverySyncUseCase,
    interval: int,
) -> None:
    while True:
        try:
            result = await asyncio.to_thread(delivery_sync.sync_once)
            if result["created"] or result["closed"]:
                logger.info("Delivery sync completed", created=result["created"], closed=result["closed"])
        except Exception as e:
            logger.error("Delivery sync failed", error=str(e))
        await asyncio.sleep(interval)


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Outbound Adapters
    delivery_repo = FileSystemDeliveryRepository(DELIVERIES_DIR)
    source_repo = FileSystemSourceRepository(SOURCES_DIR)

    # Use Cases
    runner = ClaudeCliAdapter()
    git_ops = GitCliAdapter()
    event_bus = EventBus()
    app.state.delivery_usecases = DeliveryUseCasesImpl(
        delivery_repo, runner, git_ops, source_repo, event_bus=event_bus
    )
    app.state.event_bus = event_bus
    app.state.source_usecases = SourceUseCasesImpl(source_repo)

    # Delivery Sync
    github_adapter = GitHubApiAdapter()
    delivery_sync = DeliverySyncUseCase(
        github_repo=github_adapter,
        source_repo=source_repo,
        delivery_usecases=app.state.delivery_usecases,
    )
    app.state.delivery_sync = delivery_sync
    poll_task = asyncio.create_task(
        _poll_loop(delivery_sync, GITHUB_POLL_INTERVAL)
    )
    logger.info("Delivery polling started", interval_sec=GITHUB_POLL_INTERVAL)

    yield
    poll_task.cancel()


app = FastAPI(title="jakeops", version="0.3.0", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=CORS_ORIGINS,
    allow_methods=["*"],
    allow_headers=["*"],
)
app.add_middleware(RequestLoggingMiddleware)

# Inbound Adapters (Routers)
app.include_router(deliveries.router, prefix="/api")
app.include_router(sources.router, prefix="/api")
