import pytest

from app.main import app
from app.adapters.outbound.filesystem_issue import FileSystemIssueRepository
from app.adapters.outbound.filesystem_source import FileSystemSourceRepository
from app.usecases.issue_usecases import IssueUseCasesImpl
from app.usecases.source_usecases import SourceUseCasesImpl
from app.domain.services.worker_registry import WorkerRegistry


@pytest.fixture(autouse=True)
def _test_storage(tmp_path):
    """Replace Use Case + Repository with temp directory for each test."""
    issue_repo = FileSystemIssueRepository(tmp_path / "issues")
    source_repo = FileSystemSourceRepository(tmp_path / "sources")

    app.state.issue_usecases = IssueUseCasesImpl(issue_repo)
    app.state.source_usecases = SourceUseCasesImpl(source_repo)

    app.state.worker_registry = WorkerRegistry()
    yield tmp_path
