import hashlib
import uuid
from datetime import datetime

from app.domain.constants import KST, SCHEMA_VERSION, ID_HEX_LENGTH
from app.domain.models.delivery import DeliveryCreate, DeliveryUpdate, Phase, RunStatus, ExecutorKind
from app.domain.services.session_parser import (
    find_session_file,
    parse_session_lines,
    synthesize_result_event,
)
from app.domain.services.stream_parser import extract_metadata, extract_transcript
from app.ports.outbound.delivery_repository import DeliveryRepository

FORWARD_TRANSITIONS: dict[str, str] = {
    "intake": "plan",
    "plan": "implement",
    "implement": "review",
    "review": "verify",
    "verify": "deploy",
    "deploy": "observe",
    "observe": "close",
}

GATE_PHASES = {"plan", "review", "deploy"}

REJECT_TRANSITIONS: dict[str, str] = {
    "plan": "intake",
    "review": "implement",
    "deploy": "verify",
}

DEFAULT_EXECUTOR: dict[str, str] = {
    "intake": "system",
    "plan": "agent",
    "implement": "agent",
    "review": "human",
    "verify": "system",
    "deploy": "system",
    "observe": "system",
    "close": "system",
}


def _append_phase_run(delivery: dict, phase: str, run_status: str, executor: str | None = None) -> None:
    now = datetime.now(KST).isoformat()
    if executor is None:
        executor = DEFAULT_EXECUTOR.get(phase, "system")
    run = {
        "phase": phase,
        "run_status": run_status,
        "executor": executor,
        "started_at": now,
        "ended_at": None,
    }
    delivery.setdefault("phase_runs", []).append(run)


class DeliveryUseCasesImpl:
    def __init__(self, repo: DeliveryRepository) -> None:
        self._repo = repo

    def list_deliveries(self) -> list[dict]:
        return self._repo.list_deliveries()

    def get_delivery(self, delivery_id: str) -> dict | None:
        return self._repo.get_delivery(delivery_id)

    def create_delivery(self, body: DeliveryCreate) -> dict:
        data = body.model_dump()
        now = datetime.now(KST)
        data["created_at"] = now.isoformat()
        data["updated_at"] = now.isoformat()
        data["schema_version"] = SCHEMA_VERSION
        data["runs"] = []
        data["phase_runs"] = []

        if data.get("exit_phase") is None:
            data["exit_phase"] = "deploy"

        trigger_label = ""
        for ref in data.get("refs", []):
            if ref.get("role") == "trigger":
                trigger_label = ref.get("label", "")
                break
        raw = f"{data['repository']}:{trigger_label}"
        data["id"] = hashlib.sha256(raw.encode()).hexdigest()[:ID_HEX_LENGTH]

        _append_phase_run(data, data["phase"], data["run_status"])

        self._repo.save_delivery(data["id"], data)
        return {"id": data["id"], "status": "created"}

    def update_delivery(self, delivery_id: str, body: DeliveryUpdate) -> dict | None:
        existing = self._repo.get_delivery(delivery_id)
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
        self._repo.save_delivery(delivery_id, existing)
        return {"id": delivery_id, "status": "updated"}

    def approve(self, delivery_id: str) -> dict | None:
        existing = self._repo.get_delivery(delivery_id)
        if existing is None:
            return None
        current_phase = existing["phase"]
        current_run_status = existing["run_status"]

        if current_phase not in GATE_PHASES:
            raise ValueError(f"approve: '{current_phase}' is not a gate phase")
        if current_run_status != "succeeded":
            raise ValueError(
                f"approve: run_status must be 'succeeded', got '{current_run_status}'"
            )

        exit_phase = existing.get("exit_phase", "deploy")
        if current_phase == exit_phase:
            next_phase = "close"
        else:
            next_phase = FORWARD_TRANSITIONS[current_phase]

        existing["phase"] = next_phase
        existing["run_status"] = "pending"
        existing["updated_at"] = datetime.now(KST).isoformat()
        _append_phase_run(existing, next_phase, "pending")
        self._repo.save_delivery(delivery_id, existing)
        return {"id": delivery_id, "phase": next_phase, "run_status": "pending"}

    def reject(self, delivery_id: str, reason: str) -> dict | None:
        existing = self._repo.get_delivery(delivery_id)
        if existing is None:
            return None
        current_phase = existing["phase"]
        if current_phase not in REJECT_TRANSITIONS:
            raise ValueError(f"reject: not allowed from phase '{current_phase}'")
        prev_phase = REJECT_TRANSITIONS[current_phase]
        existing["phase"] = prev_phase
        existing["run_status"] = "pending"
        existing["updated_at"] = datetime.now(KST).isoformat()
        _append_phase_run(existing, prev_phase, "pending")
        self._repo.save_delivery(delivery_id, existing)
        return {"id": delivery_id, "phase": prev_phase, "run_status": "pending"}

    def generate_plan(self, delivery_id: str) -> dict | None:
        existing = self._repo.get_delivery(delivery_id)
        if existing is None:
            return None
        if existing["phase"] != "intake":
            raise ValueError(
                f"generate_plan: not allowed from phase '{existing['phase']}'. only 'intake' is allowed"
            )
        return {"id": delivery_id, "phase": "intake", "run_status": existing["run_status"]}

    def retry(self, delivery_id: str) -> dict | None:
        existing = self._repo.get_delivery(delivery_id)
        if existing is None:
            return None
        if existing["run_status"] != "failed":
            raise ValueError(
                f"retry: not allowed when run_status is '{existing['run_status']}'. only 'failed' is allowed"
            )
        existing["run_status"] = "pending"
        existing["error"] = None
        existing["updated_at"] = datetime.now(KST).isoformat()
        _append_phase_run(existing, existing["phase"], "pending")
        self._repo.save_delivery(delivery_id, existing)
        return {"id": delivery_id, "phase": existing["phase"], "run_status": "pending"}

    def cancel(self, delivery_id: str) -> dict | None:
        existing = self._repo.get_delivery(delivery_id)
        if existing is None:
            return None
        existing["run_status"] = "canceled"
        existing["updated_at"] = datetime.now(KST).isoformat()
        _append_phase_run(existing, existing["phase"], "canceled")
        self._repo.save_delivery(delivery_id, existing)
        return {"id": delivery_id, "phase": existing["phase"], "run_status": "canceled"}

    def get_run_transcript(self, delivery_id: str, run_id: str) -> dict | None:
        return self._repo.get_run_transcript(delivery_id, run_id)

    def save_run_transcript(self, delivery_id: str, run_id: str, data: dict) -> None:
        self._repo.save_run_transcript(delivery_id, run_id, data)

    def collect_session(self, delivery_id: str, session_id: str) -> dict | None:
        existing = self._repo.get_delivery(delivery_id)
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
        self._repo.save_delivery(delivery_id, existing)
        self._repo.save_run_transcript(delivery_id, run_id, transcript)

        return {"id": delivery_id, "run_id": run_id, "status": "collected"}
