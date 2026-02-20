import asyncio
import json

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, Request
from fastapi.responses import StreamingResponse
from pydantic import BaseModel

from app.domain.models.delivery import DeliveryCreate, DeliveryUpdate, RunStatus

router = APIRouter()


class RejectBody(BaseModel):
    reason: str = ""


class CollectBody(BaseModel):
    session_id: str



def get_usecases(request: Request):
    return request.app.state.delivery_usecases


def get_event_bus(request: Request):
    return request.app.state.event_bus


@router.get("/deliveries/{delivery_id}/stream")
async def stream_delivery(delivery_id: str, request: Request):
    event_bus = get_event_bus(request)

    async def event_generator():
        sub = event_bus.subscribe(delivery_id)
        try:
            while True:
                try:
                    event = await asyncio.wait_for(anext(sub), timeout=15)
                except StopAsyncIteration:
                    break
                except asyncio.TimeoutError:
                    if await request.is_disconnected():
                        break
                    yield ": heartbeat\n\n"
                    continue
                if await request.is_disconnected():
                    break
                yield f"data: {json.dumps(event)}\n\n"
        finally:
            await sub.aclose()
        yield "event: done\ndata: {}\n\n"

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )


@router.get("/deliveries")
def list_deliveries(uc=Depends(get_usecases)):
    return uc.list_deliveries()


@router.get("/deliveries/schema")
def get_schema():
    return DeliveryCreate.model_json_schema()


@router.get("/deliveries/{delivery_id}")
def get_delivery(delivery_id: str, uc=Depends(get_usecases)):
    delivery = uc.get_delivery(delivery_id)
    if delivery is None:
        raise HTTPException(status_code=404, detail="Delivery not found")
    return delivery


@router.post("/deliveries")
def create_delivery(body: DeliveryCreate, uc=Depends(get_usecases)):
    return uc.create_delivery(body)


@router.patch("/deliveries/{delivery_id}")
def update_delivery(delivery_id: str, body: DeliveryUpdate, uc=Depends(get_usecases)):
    result = uc.update_delivery(delivery_id, body)
    if result is None:
        raise HTTPException(status_code=404, detail="Delivery not found")
    return result


@router.post("/deliveries/{delivery_id}/approve")
async def approve(delivery_id: str, background: BackgroundTasks, uc=Depends(get_usecases)):
    try:
        result = uc.approve(delivery_id)
    except ValueError as e:
        raise HTTPException(status_code=409, detail=str(e))
    if result is None:
        raise HTTPException(status_code=404, detail="Delivery not found")
    if result.pop("_auto_trigger", False):
        background.add_task(uc.auto_trigger_phase, delivery_id)
    return result


@router.post("/deliveries/{delivery_id}/reject")
def reject(delivery_id: str, body: RejectBody, uc=Depends(get_usecases)):
    try:
        result = uc.reject(delivery_id, body.reason)
    except ValueError as e:
        raise HTTPException(status_code=409, detail=str(e))
    if result is None:
        raise HTTPException(status_code=404, detail="Delivery not found")
    return result


_AGENT_PHASE_REQUIREMENTS: dict[str, tuple[str, str]] = {
    "generate-plan": ("plan", "pending"),
    "run-implement": ("implement", "pending"),
    "run-review": ("review", "pending"),
}

def _validate_and_mark_running(delivery_id: str, action: str, uc) -> dict:
    """Validate delivery state and mark as running before background task starts."""
    existing = uc.get_delivery(delivery_id)
    if existing is None:
        raise HTTPException(status_code=404, detail="Delivery not found")
    required_phase, required_status = _AGENT_PHASE_REQUIREMENTS[action]
    if existing["phase"] != required_phase or existing["run_status"] != required_status:
        raise HTTPException(
            status_code=409,
            detail=(
                f"{action}: requires phase='{required_phase}' and "
                f"run_status='{required_status}', got phase='{existing['phase']}' "
                f"run_status='{existing['run_status']}'"
            ),
        )
    # Set running before 202 so polling sees the correct state immediately
    uc.update_delivery(delivery_id, DeliveryUpdate(run_status=RunStatus.running))
    return existing


@router.post("/deliveries/{delivery_id}/generate-plan", status_code=202)
async def generate_plan(
    delivery_id: str, background: BackgroundTasks, uc=Depends(get_usecases),
):
    existing = _validate_and_mark_running(delivery_id, "generate-plan", uc)
    background.add_task(uc.generate_plan, delivery_id)
    return {"id": delivery_id, "phase": existing["phase"], "run_status": "running"}


@router.post("/deliveries/{delivery_id}/run-implement", status_code=202)
async def run_implement(
    delivery_id: str, background: BackgroundTasks, uc=Depends(get_usecases),
):
    existing = _validate_and_mark_running(delivery_id, "run-implement", uc)
    background.add_task(uc.run_implement, delivery_id)
    return {"id": delivery_id, "phase": existing["phase"], "run_status": "running"}


@router.post("/deliveries/{delivery_id}/run-review", status_code=202)
async def run_review(
    delivery_id: str, background: BackgroundTasks, uc=Depends(get_usecases),
):
    existing = _validate_and_mark_running(delivery_id, "run-review", uc)
    background.add_task(uc.run_review, delivery_id)
    return {"id": delivery_id, "phase": existing["phase"], "run_status": "running"}



@router.post("/deliveries/{delivery_id}/retry")
def retry(delivery_id: str, uc=Depends(get_usecases)):
    try:
        result = uc.retry(delivery_id)
    except ValueError as e:
        raise HTTPException(status_code=409, detail=str(e))
    if result is None:
        raise HTTPException(status_code=404, detail="Delivery not found")
    return result


@router.post("/deliveries/{delivery_id}/cancel")
def cancel(delivery_id: str, uc=Depends(get_usecases)):
    try:
        result = uc.cancel(delivery_id)
    except ValueError as e:
        raise HTTPException(status_code=409, detail=str(e))
    if result is None:
        raise HTTPException(status_code=404, detail="Delivery not found")
    return result


@router.get("/deliveries/{delivery_id}/runs/{run_id}/transcript")
def get_run_transcript(delivery_id: str, run_id: str, uc=Depends(get_usecases)):
    transcript = uc.get_run_transcript(delivery_id, run_id)
    if transcript is None:
        raise HTTPException(status_code=404, detail="Transcript not found")
    return transcript


@router.get("/deliveries/{delivery_id}/runs/{run_id}/stream_log")
def get_stream_log(delivery_id: str, run_id: str, uc=Depends(get_usecases)):
    log = uc.get_stream_log(delivery_id, run_id)
    if log is None:
        raise HTTPException(status_code=404, detail="Stream log not found")
    return log


@router.post("/deliveries/{delivery_id}/collect")
def collect(delivery_id: str, body: CollectBody, uc=Depends(get_usecases)):
    try:
        result = uc.collect_session(delivery_id, body.session_id)
    except FileNotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e))
    if result is None:
        raise HTTPException(status_code=404, detail="Delivery not found")
    return result
