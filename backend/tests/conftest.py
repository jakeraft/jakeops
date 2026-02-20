import pytest

from app.main import app
from app.adapters.outbound.filesystem_delivery import FileSystemDeliveryRepository
from app.adapters.outbound.filesystem_source import FileSystemSourceRepository
from app.usecases.delivery_usecases import DeliveryUseCasesImpl
from app.usecases.source_usecases import SourceUseCasesImpl
from app.domain.services.worker_registry import WorkerRegistry


@pytest.fixture(autouse=True)
def _test_storage(tmp_path):
    """Replace Use Case + Repository with temp directory for each test."""
    delivery_repo = FileSystemDeliveryRepository(tmp_path / "deliveries")
    source_repo = FileSystemSourceRepository(tmp_path / "sources")

    app.state.delivery_usecases = DeliveryUseCasesImpl(delivery_repo)
    app.state.source_usecases = SourceUseCasesImpl(source_repo)

    app.state.worker_registry = WorkerRegistry()
    yield tmp_path
