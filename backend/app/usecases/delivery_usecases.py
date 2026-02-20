import copy
import hashlib
import shutil
import tempfile
import uuid
from datetime import datetime

from app.domain.constants import KST, SCHEMA_VERSION, ID_HEX_LENGTH
from app.domain.models.delivery import DeliveryCreate, DeliveryUpdate, Phase, RunStatus, ExecutorKind
from app.domain.models.source import DEFAULT_CHECKPOINTS
from app.domain.prompts import (
    build_plan_prompt,
    build_implement_prompt,
    build_review_prompt,
    build_fix_prompt,
    PLAN_SYSTEM_PROMPT,
    PLAN_ALLOWED_TOOLS,
    IMPLEMENT_SYSTEM_PROMPT,
    REVIEW_SYSTEM_PROMPT,
    REVIEW_ALLOWED_TOOLS,
    FIX_SYSTEM_PROMPT,
)
from app.domain.services.session_parser import (
    find_session_file,
    parse_session_lines,
    synthesize_result_event,
)
from app.domain.services.stream_parser import extract_metadata, extract_transcript
from app.ports.outbound.delivery_repository import DeliveryRepository
from app.ports.outbound.subprocess_runner import SubprocessRunner
from app.ports.outbound.git_operations import GitOperations
from app.ports.outbound.source_repository import SourceRepository

FORWARD_TRANSITIONS: dict[str, str] = {
    "intake": "plan",
    "plan": "implement",
    "implement": "review",
    "review": "verify",
    "verify": "deploy",
    "deploy": "observe",
    "observe": "close",
}

REJECT_TRANSITIONS: dict[str, str] = {
    "plan": "intake",
    "implement": "plan",
    "review": "implement",
}

# Phases that support human actions (approve/reject/retry)
ACTION_PHASES = {"plan", "implement", "review"}

DEFAULT_EXECUTOR: dict[str, str] = {
    "intake": "system",
    "plan": "agent",
    "implement": "agent",
    "review": "agent",
    "verify": "system",
    "deploy": "system",
    "observe": "system",
    "close": "system",
}


def _append_phase_run(
    delivery: dict,
    phase: str,
    run_status: str,
    executor: str | None = None,
    verdict: str | None = None,
) -> None:
    now = datetime.now(KST).isoformat()
    if executor is None:
        executor = DEFAULT_EXECUTOR.get(phase, "system")
    run = {
        "phase": phase,
        "run_status": run_status,
        "executor": executor,
        "verdict": verdict,
        "started_at": now,
        "ended_at": None,
    }
    delivery.setdefault("phase_runs", []).append(run)


class DeliveryUseCasesImpl:
    def __init__(
        self,
        repo: DeliveryRepository,
        runner: SubprocessRunner | None = None,
        git_ops: GitOperations | None = None,
        source_repo: SourceRepository | None = None,
    ) -> None:
        self._repo = repo
        self._runner = runner
        self._git = git_ops
        self._source_repo = source_repo

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

        if data.get("endpoint") is None:
            data["endpoint"] = "deploy"
        if data.get("checkpoints") is None:
            data["checkpoints"] = list(DEFAULT_CHECKPOINTS)

        trigger_label = ""
        for ref in data.get("refs", []):
            if ref.get("role") == "trigger":
                trigger_label = ref.get("label", "")
                break
        raw = f"{data['repository']}:{trigger_label}"
        data["id"] = hashlib.sha256(raw.encode()).hexdigest()[:ID_HEX_LENGTH]
        data["seq"] = self._repo.next_seq()

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

    def close_delivery(self, delivery_id: str) -> dict | None:
        existing = self._repo.get_delivery(delivery_id)
        if existing is None:
            return None
        existing["phase"] = "close"
        existing["run_status"] = "succeeded"
        existing["updated_at"] = datetime.now(KST).isoformat()
        _append_phase_run(existing, "close", "succeeded")
        self._repo.save_delivery(delivery_id, existing)
        return {"id": delivery_id, "phase": "close", "run_status": "succeeded"}

    def approve(self, delivery_id: str) -> dict | None:
        existing = self._repo.get_delivery(delivery_id)
        if existing is None:
            return None
        current_phase = existing["phase"]
        current_run_status = existing["run_status"]
        # TODO: use checkpoints for auto-advance logic
        # checkpoints = existing.get("checkpoints", list(DEFAULT_CHECKPOINTS))

        if current_phase not in ACTION_PHASES:
            raise ValueError(f"approve: '{current_phase}' is not an action phase")
        if current_run_status != "succeeded":
            raise ValueError(
                f"approve: run_status must be 'succeeded', got '{current_run_status}'"
            )

        endpoint = existing.get("endpoint", "deploy")
        if current_phase == endpoint:
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
        existing["reject_reason"] = reason
        existing["updated_at"] = datetime.now(KST).isoformat()
        _append_phase_run(existing, prev_phase, "pending")
        self._repo.save_delivery(delivery_id, existing)
        return {"id": delivery_id, "phase": prev_phase, "run_status": "pending"}

    def _get_source_token(self, owner: str, repo: str) -> str:
        if self._source_repo is None:
            return ""
        for source in self._source_repo.list_sources():
            if source.get("owner") == owner and source.get("repo") == repo:
                return source.get("token", "")
        return ""

    async def _run_agent_phase(
        self,
        delivery: dict,
        delivery_id: str,
        prompt: str,
        mode: str,
        allowed_tools: list[str] | None = None,
        system_prompt: str | None = None,
    ) -> dict:
        if self._runner is None or self._git is None:
            raise RuntimeError("SubprocessRunner and GitOperations required for agent execution")

        delivery = copy.deepcopy(delivery)
        delivery["run_status"] = "running"
        delivery["updated_at"] = datetime.now(KST).isoformat()
        _append_phase_run(delivery, delivery["phase"], "running")
        self._repo.save_delivery(delivery_id, delivery)

        owner, repo_name = delivery["repository"].split("/", 1)
        token = self._get_source_token(owner, repo_name)
        work_dir = tempfile.mkdtemp(prefix="jakeops-work-")

        try:
            self._git.clone_repo(owner, repo_name, token, work_dir)
            result_text, events, session_id = await self._runner.run_with_stream(
                prompt=prompt,
                cwd=work_dir,
                allowed_tools=allowed_tools,
                append_system_prompt=system_prompt,
            )

            metadata = extract_metadata(events)
            transcript = extract_transcript(events)

            run_id = uuid.uuid4().hex[:8]
            run = {
                "id": run_id,
                "mode": mode,
                "status": "success",
                "created_at": datetime.now(KST).isoformat(),
                "session": {"model": metadata.model},
                "stats": {
                    "cost_usd": metadata.cost_usd,
                    "input_tokens": metadata.input_tokens,
                    "output_tokens": metadata.output_tokens,
                    "duration_ms": metadata.duration_ms,
                },
                "session_id": session_id,
                "summary": result_text[:200] if result_text else None,
            }

            delivery.setdefault("runs", []).append(run)
            delivery["run_status"] = "succeeded"
            delivery["updated_at"] = datetime.now(KST).isoformat()
            _append_phase_run(delivery, delivery["phase"], "succeeded")
            self._repo.save_delivery(delivery_id, delivery)
            self._repo.save_run_transcript(delivery_id, run_id, transcript)

            return {
                "id": delivery_id,
                "run_id": run_id,
                "phase": delivery["phase"],
                "run_status": "succeeded",
                "result_text": result_text,
            }
        except Exception as e:
            delivery["run_status"] = "failed"
            delivery["error"] = str(e)
            delivery["updated_at"] = datetime.now(KST).isoformat()
            _append_phase_run(delivery, delivery["phase"], "failed")
            self._repo.save_delivery(delivery_id, delivery)
            return {
                "id": delivery_id,
                "phase": delivery["phase"],
                "run_status": "failed",
                "error": str(e),
            }
        finally:
            shutil.rmtree(work_dir, ignore_errors=True)

    async def generate_plan(self, delivery_id: str) -> dict | None:
        existing = self._repo.get_delivery(delivery_id)
        if existing is None:
            return None
        if existing["phase"] != "intake":
            raise ValueError(
                f"generate_plan: not allowed from phase '{existing['phase']}'. "
                "only 'intake' is allowed"
            )

        existing["phase"] = "plan"
        prompt = build_plan_prompt(
            summary=existing["summary"],
            repository=existing["repository"],
            refs=existing.get("refs", []),
        )

        result = await self._run_agent_phase(
            delivery=existing,
            delivery_id=delivery_id,
            prompt=prompt,
            mode="plan",
            allowed_tools=PLAN_ALLOWED_TOOLS,
            system_prompt=PLAN_SYSTEM_PROMPT,
        )

        if result["run_status"] == "failed":
            delivery = self._repo.get_delivery(delivery_id)
            delivery["phase"] = "intake"
            self._repo.save_delivery(delivery_id, delivery)
            result["phase"] = "intake"
        elif result["run_status"] == "succeeded":
            delivery = self._repo.get_delivery(delivery_id)
            delivery["plan"] = {
                "content": result.get("result_text", ""),
                "generated_at": datetime.now(KST).isoformat(),
                "model": "unknown",
                "cwd": "",
            }
            self._repo.save_delivery(delivery_id, delivery)

        return result

    async def run_implement(self, delivery_id: str) -> dict | None:
        existing = self._repo.get_delivery(delivery_id)
        if existing is None:
            return None
        if existing["phase"] != "implement" or existing["run_status"] != "pending":
            raise ValueError(
                f"run_implement: requires phase='implement' and run_status='pending', "
                f"got phase='{existing['phase']}' run_status='{existing['run_status']}'"
            )

        plan_content = ""
        if existing.get("plan"):
            plan_content = existing["plan"].get("content", "")

        prompt = build_implement_prompt(
            plan_content=plan_content,
            summary=existing["summary"],
        )

        return await self._run_agent_phase(
            delivery=existing,
            delivery_id=delivery_id,
            prompt=prompt,
            mode="implement",
            system_prompt=IMPLEMENT_SYSTEM_PROMPT,
        )

    async def run_review(self, delivery_id: str) -> dict | None:
        existing = self._repo.get_delivery(delivery_id)
        if existing is None:
            return None
        if existing["phase"] != "review" or existing["run_status"] != "pending":
            raise ValueError(
                f"run_review: requires phase='review' and run_status='pending', "
                f"got phase='{existing['phase']}' run_status='{existing['run_status']}'"
            )

        prompt = build_review_prompt(summary=existing["summary"])

        return await self._run_agent_phase(
            delivery=existing,
            delivery_id=delivery_id,
            prompt=prompt,
            mode="review",
            allowed_tools=REVIEW_ALLOWED_TOOLS,
            system_prompt=REVIEW_SYSTEM_PROMPT,
        )

    async def run_fix(self, delivery_id: str, feedback: str = "") -> dict | None:
        existing = self._repo.get_delivery(delivery_id)
        if existing is None:
            return None
        if existing["phase"] != "implement" or existing["run_status"] != "pending":
            raise ValueError(
                f"run_fix: requires phase='implement' and run_status='pending', "
                f"got phase='{existing['phase']}' run_status='{existing['run_status']}'"
            )

        prompt = build_fix_prompt(feedback=feedback, summary=existing["summary"])

        return await self._run_agent_phase(
            delivery=existing,
            delivery_id=delivery_id,
            prompt=prompt,
            mode="fix",
            system_prompt=FIX_SYSTEM_PROMPT,
        )

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
