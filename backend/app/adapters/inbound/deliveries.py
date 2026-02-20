from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, Request
from pydantic import BaseModel

from app.domain.models.delivery import DeliveryCreate, DeliveryUpdate

router = APIRouter()


class RejectBody(BaseModel):
    reason: str = ""


class CollectBody(BaseModel):
    session_id: str



def get_usecases(request: Request):
    return request.app.state.delivery_usecases


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


@router.post("/deliveries/{delivery_id}/generate-plan")
async def generate_plan(delivery_id: str, uc=Depends(get_usecases)):
    try:
        result = await uc.generate_plan(delivery_id)
    except ValueError as e:
        raise HTTPException(status_code=409, detail=str(e))
    except RuntimeError as e:
        raise HTTPException(status_code=500, detail=str(e))
    if result is None:
        raise HTTPException(status_code=404, detail="Delivery not found")
    return result


@router.post("/deliveries/{delivery_id}/run-implement")
async def run_implement(delivery_id: str, uc=Depends(get_usecases)):
    try:
        result = await uc.run_implement(delivery_id)
    except ValueError as e:
        raise HTTPException(status_code=409, detail=str(e))
    except RuntimeError as e:
        raise HTTPException(status_code=500, detail=str(e))
    if result is None:
        raise HTTPException(status_code=404, detail="Delivery not found")
    return result


@router.post("/deliveries/{delivery_id}/run-review")
async def run_review(delivery_id: str, uc=Depends(get_usecases)):
    try:
        result = await uc.run_review(delivery_id)
    except ValueError as e:
        raise HTTPException(status_code=409, detail=str(e))
    except RuntimeError as e:
        raise HTTPException(status_code=500, detail=str(e))
    if result is None:
        raise HTTPException(status_code=404, detail="Delivery not found")
    return result



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


@router.post("/deliveries/{delivery_id}/collect")
def collect(delivery_id: str, body: CollectBody, uc=Depends(get_usecases)):
    try:
        result = uc.collect_session(delivery_id, body.session_id)
    except FileNotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e))
    if result is None:
        raise HTTPException(status_code=404, detail="Delivery not found")
    return result
