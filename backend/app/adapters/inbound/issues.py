from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel

from app.domain.models.issue import IssueCreate, IssueUpdate

router = APIRouter()


class RejectBody(BaseModel):
    reason: str = ""


class CollectBody(BaseModel):
    session_id: str


def get_usecases(request: Request):
    return request.app.state.issue_usecases


@router.get("/issues")
def list_issues(uc=Depends(get_usecases)):
    return uc.list_issues()


@router.get("/issues/schema")
def get_schema():
    return IssueCreate.model_json_schema()


@router.get("/issues/{issue_id}")
def get_issue(issue_id: str, uc=Depends(get_usecases)):
    issue = uc.get_issue(issue_id)
    if issue is None:
        raise HTTPException(status_code=404, detail="Issue not found")
    return issue


@router.post("/issues")
def create_issue(body: IssueCreate, uc=Depends(get_usecases)):
    return uc.create_issue(body)


@router.patch("/issues/{issue_id}")
def update_issue(issue_id: str, body: IssueUpdate, uc=Depends(get_usecases)):
    result = uc.update_issue(issue_id, body)
    if result is None:
        raise HTTPException(status_code=404, detail="Issue not found")
    return result


@router.post("/issues/{issue_id}/approve")
def approve(issue_id: str, uc=Depends(get_usecases)):
    try:
        result = uc.approve(issue_id)
    except ValueError as e:
        raise HTTPException(status_code=409, detail=str(e))
    if result is None:
        raise HTTPException(status_code=404, detail="Issue not found")
    return result


@router.post("/issues/{issue_id}/reject")
def reject(issue_id: str, body: RejectBody, uc=Depends(get_usecases)):
    try:
        result = uc.reject(issue_id, body.reason)
    except ValueError as e:
        raise HTTPException(status_code=409, detail=str(e))
    if result is None:
        raise HTTPException(status_code=404, detail="Issue not found")
    return result


@router.post("/issues/{issue_id}/generate-plan")
def generate_plan(issue_id: str, uc=Depends(get_usecases)):
    try:
        result = uc.generate_plan(issue_id)
    except ValueError as e:
        raise HTTPException(status_code=409, detail=str(e))
    if result is None:
        raise HTTPException(status_code=404, detail="Issue not found")
    return result


@router.post("/issues/{issue_id}/retry")
def retry(issue_id: str, uc=Depends(get_usecases)):
    try:
        result = uc.retry(issue_id)
    except ValueError as e:
        raise HTTPException(status_code=409, detail=str(e))
    if result is None:
        raise HTTPException(status_code=404, detail="Issue not found")
    return result


@router.post("/issues/{issue_id}/cancel")
def cancel(issue_id: str, uc=Depends(get_usecases)):
    result = uc.cancel(issue_id)
    if result is None:
        raise HTTPException(status_code=404, detail="Issue not found")
    return result


@router.get("/issues/{issue_id}/runs/{run_id}/transcript")
def get_run_transcript(issue_id: str, run_id: str, uc=Depends(get_usecases)):
    transcript = uc.get_run_transcript(issue_id, run_id)
    if transcript is None:
        raise HTTPException(status_code=404, detail="Transcript not found")
    return transcript


@router.post("/issues/{issue_id}/collect")
def collect(issue_id: str, body: CollectBody, uc=Depends(get_usecases)):
    try:
        result = uc.collect_session(issue_id, body.session_id)
    except FileNotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e))
    if result is None:
        raise HTTPException(status_code=404, detail="Issue not found")
    return result
