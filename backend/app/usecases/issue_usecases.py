import hashlib
import uuid
from datetime import datetime

from app.domain.constants import KST, SCHEMA_VERSION, ID_HEX_LENGTH
from app.domain.models.issue import IssueCreate, IssueUpdate
from app.domain.services.session_parser import (
    find_session_file,
    parse_session_lines,
    synthesize_result_event,
)
from app.domain.services.stream_parser import extract_metadata, extract_transcript
from app.ports.outbound.issue_repository import IssueRepository

# Gate transition map: next state on approve
APPROVE_TRANSITIONS: dict[str, str] = {
    "planned": "approved",
    "ci_passed": "deployed",
    "deployed": "done",
}

# Gate transition map: previous state on reject
REJECT_TRANSITIONS: dict[str, str] = {
    "planned": "new",
    "ci_passed": "implemented",
    "deployed": "ci_passed",
}


class IssueUseCasesImpl:
    def __init__(self, repo: IssueRepository) -> None:
        self._repo = repo

    def list_issues(self) -> list[dict]:
        return self._repo.list_issues()

    def get_issue(self, issue_id: str) -> dict | None:
        return self._repo.get_issue(issue_id)

    def create_issue(self, body: IssueCreate) -> dict:
        data = body.model_dump()
        now = datetime.now(KST)
        data["created_at"] = now.isoformat()
        data["updated_at"] = now.isoformat()
        data["schema_version"] = SCHEMA_VERSION
        data["runs"] = []

        trigger_label = ""
        for ref in data.get("refs", []):
            if ref.get("role") == "trigger":
                trigger_label = ref.get("label", "")
                break
        raw = f"{data['repository']}:{trigger_label}"
        data["id"] = hashlib.sha256(raw.encode()).hexdigest()[:ID_HEX_LENGTH]

        self._repo.save_issue(data["id"], data)
        return {"id": data["id"], "status": "created"}

    def update_issue(self, issue_id: str, body: IssueUpdate) -> dict | None:
        existing = self._repo.get_issue(issue_id)
        if existing is None:
            return None
        update_data = body.model_dump(exclude_none=True)
        if "refs" in update_data:
            new_refs = update_data.pop("refs")
            existing_refs = existing.get("refs", [])
            for new_ref in new_refs:
                if new_ref.get("role") == "output":
                    existing_refs = [
                        r for r in existing_refs
                        if not (r.get("role") == "output" and r.get("type") == new_ref.get("type"))
                    ]
            existing["refs"] = existing_refs + new_refs
        existing.update(update_data)
        existing["updated_at"] = datetime.now(KST).isoformat()
        self._repo.save_issue(issue_id, existing)
        return {"id": issue_id, "status": "updated"}

    def approve(self, issue_id: str) -> dict | None:
        existing = self._repo.get_issue(issue_id)
        if existing is None:
            return None
        current = existing["status"]
        if current not in APPROVE_TRANSITIONS:
            raise ValueError(f"approve: not allowed from '{current}'")
        next_status = APPROVE_TRANSITIONS[current]
        existing["status"] = next_status
        existing["updated_at"] = datetime.now(KST).isoformat()
        self._repo.save_issue(issue_id, existing)
        return {"id": issue_id, "status": next_status}

    def reject(self, issue_id: str, reason: str) -> dict | None:
        existing = self._repo.get_issue(issue_id)
        if existing is None:
            return None
        current = existing["status"]
        if current not in REJECT_TRANSITIONS:
            raise ValueError(f"reject: not allowed from '{current}'")
        prev_status = REJECT_TRANSITIONS[current]
        existing["status"] = prev_status
        existing["updated_at"] = datetime.now(KST).isoformat()
        self._repo.save_issue(issue_id, existing)
        return {"id": issue_id, "status": prev_status}

    def generate_plan(self, issue_id: str) -> dict | None:
        existing = self._repo.get_issue(issue_id)
        if existing is None:
            return None
        if existing["status"] != "new":
            raise ValueError(
                f"generate_plan: not allowed from '{existing['status']}'. only 'new' is allowed"
            )
        return {"id": issue_id, "status": "new"}

    def retry(self, issue_id: str) -> dict | None:
        existing = self._repo.get_issue(issue_id)
        if existing is None:
            return None
        if existing["status"] != "failed":
            raise ValueError(
                f"retry: not allowed from '{existing['status']}'. only 'failed' is allowed"
            )
        existing["status"] = "new"
        existing["error"] = None
        existing["updated_at"] = datetime.now(KST).isoformat()
        self._repo.save_issue(issue_id, existing)
        return {"id": issue_id, "status": "new"}

    def cancel(self, issue_id: str) -> dict | None:
        existing = self._repo.get_issue(issue_id)
        if existing is None:
            return None
        existing["status"] = "canceled"
        existing["updated_at"] = datetime.now(KST).isoformat()
        self._repo.save_issue(issue_id, existing)
        return {"id": issue_id, "status": "canceled"}

    def get_run_transcript(self, issue_id: str, run_id: str) -> dict | None:
        return self._repo.get_run_transcript(issue_id, run_id)

    def save_run_transcript(self, issue_id: str, run_id: str, data: dict) -> None:
        self._repo.save_run_transcript(issue_id, run_id, data)

    def collect_session(self, issue_id: str, session_id: str) -> dict | None:
        existing = self._repo.get_issue(issue_id)
        if existing is None:
            return None

        session_file = find_session_file(session_id)
        if session_file is None:
            raise FileNotFoundError(f"Session file not found: {session_id}")

        lines = session_file.read_text(encoding="utf-8").strip().splitlines()
        events = parse_session_lines(lines)
        result_event = synthesize_result_event(events)
        all_events = events + [result_event]

        metadata = extract_metadata(all_events)
        transcript = extract_transcript(all_events)

        run_id = uuid.uuid4().hex[:8]
        run = {
            "id": run_id,
            "mode": "execution",
            "status": "success" if metadata.is_success else "failed",
            "created_at": datetime.now(KST).isoformat(),
            "session": {"model": metadata.model},
            "stats": {
                "cost_usd": metadata.cost_usd,
                "input_tokens": metadata.input_tokens,
                "output_tokens": metadata.output_tokens,
                "duration_ms": metadata.duration_ms,
            },
            "session_id": session_id,
            "summary": metadata.result_text[:200] if metadata.result_text else None,
        }

        existing.setdefault("runs", []).append(run)
        existing["updated_at"] = datetime.now(KST).isoformat()
        self._repo.save_issue(issue_id, existing)
        self._repo.save_run_transcript(issue_id, run_id, transcript)

        return {"id": issue_id, "run_id": run_id, "status": "collected"}
