from fastapi import APIRouter, Depends, HTTPException, Request

from app.domain.models.source import SourceCreate, SourceUpdate

router = APIRouter()


def get_usecases(request: Request):
    return request.app.state.source_usecases


def get_issue_sync(request: Request):
    return request.app.state.issue_sync


@router.get("/sources")
def list_sources(uc=Depends(get_usecases)):
    return uc.list_sources()


@router.get("/sources/{source_id}")
def get_source(source_id: str, uc=Depends(get_usecases)):
    source = uc.get_source(source_id)
    if source is None:
        raise HTTPException(status_code=404, detail="Source not found")
    return source


@router.post("/sources")
def create_source(body: SourceCreate, uc=Depends(get_usecases)):
    result = uc.create_source(body)
    if "error" in result and result["error"] == "duplicate":
        raise HTTPException(status_code=409, detail="Source already exists")
    return result


@router.patch("/sources/{source_id}")
def update_source(source_id: str, body: SourceUpdate, uc=Depends(get_usecases)):
    result = uc.update_source(source_id, body)
    if result is None:
        raise HTTPException(status_code=404, detail="Source not found")
    return result


@router.delete("/sources/{source_id}")
def delete_source(source_id: str, uc=Depends(get_usecases)):
    deleted = uc.delete_source(source_id)
    if not deleted:
        raise HTTPException(status_code=404, detail="Source not found")
    return {"status": "deleted"}


@router.post("/sources/sync")
def sync_now(issue_sync=Depends(get_issue_sync)):
    return issue_sync.sync_once()
