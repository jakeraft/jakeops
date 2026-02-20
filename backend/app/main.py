import asyncio
import logging
import os
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.adapters.inbound import deliveries, sources, worker
from app.domain.services.worker_registry import WorkerRegistry
from app.adapters.outbound.filesystem_delivery import FileSystemDeliveryRepository
from app.adapters.outbound.filesystem_source import FileSystemSourceRepository
from app.adapters.outbound.github_api import GitHubApiAdapter
from app.usecases.delivery_usecases import DeliveryUseCasesImpl
from app.usecases.source_usecases import SourceUseCasesImpl
from app.usecases.delivery_sync import DeliverySyncUseCase

logger = logging.getLogger(__name__)

PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent

DELIVERIES_DIR = Path(os.environ.get("JAKEOPS_DATA_DIR", PROJECT_ROOT / "deliveries"))
SOURCES_DIR = Path(os.environ.get("JAKEOPS_SOURCES_DIR", PROJECT_ROOT / "sources"))

GITHUB_POLL_INTERVAL = int(os.environ.get("GITHUB_POLL_INTERVAL", "60"))
CORS_ORIGINS = os.environ.get("JAKEOPS_CORS_ORIGINS", "*").split(",")


async def _poll_loop(
    delivery_sync: DeliverySyncUseCase,
    interval: int,
    registry: WorkerRegistry,
    runner_name: str,
) -> None:
    while True:
        try:
            created = await asyncio.to_thread(delivery_sync.sync_once)
            registry.record_success(runner_name, {"created": created})
            if created:
                logger.info("Delivery sync: created %d deliveries", created)
        except Exception as e:
            registry.record_error(runner_name, str(e))
            logger.error("Delivery sync failed: %s", e)
        await asyncio.sleep(interval)


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Outbound Adapters
    delivery_repo = FileSystemDeliveryRepository(DELIVERIES_DIR)
    source_repo = FileSystemSourceRepository(SOURCES_DIR)

    # Use Cases
    app.state.delivery_usecases = DeliveryUseCasesImpl(delivery_repo)
    app.state.source_usecases = SourceUseCasesImpl(source_repo)

    # Runner Registry
    registry = WorkerRegistry()
    registry.register(
        "delivery_sync", label="Delivery Sync",
        interval_sec=GITHUB_POLL_INTERVAL, enabled=True,
    )
    app.state.worker_registry = registry

    # Delivery Sync
    github_adapter = GitHubApiAdapter()
    delivery_sync = DeliverySyncUseCase(
        github_repo=github_adapter,
        source_repo=source_repo,
        delivery_usecases=app.state.delivery_usecases,
    )
    app.state.delivery_sync = delivery_sync
    poll_task = asyncio.create_task(
        _poll_loop(delivery_sync, GITHUB_POLL_INTERVAL, registry, "delivery_sync")
    )
    logger.info("Delivery polling started (interval: %ds)", GITHUB_POLL_INTERVAL)

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
app.include_router(deliveries.router, prefix="/api")
app.include_router(sources.router, prefix="/api")
app.include_router(worker.router, prefix="/api")
