from fastapi import APIRouter, Request

from app.domain.models.worker import WorkerStatusResponse
from app.domain.services.worker_registry import WorkerRegistry

router = APIRouter()


@router.get("/worker/status", response_model=WorkerStatusResponse)
def get_worker_status(request: Request) -> WorkerStatusResponse:
    registry: WorkerRegistry = request.app.state.worker_registry
    return WorkerStatusResponse(workers=registry.get_all())
