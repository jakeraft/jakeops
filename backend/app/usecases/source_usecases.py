import hashlib
from datetime import datetime

from app.domain.constants import KST, ID_HEX_LENGTH
from app.domain.models.source import SourceCreate, SourceUpdate
from app.ports.outbound.source_repository import SourceRepository


def mask_token(token: str) -> str:
    if not token:
        return ""
    if len(token) <= 8:
        return "****"
    return token[:4] + "****" + token[-4:]


class SourceUseCasesImpl:
    def __init__(self, repo: SourceRepository) -> None:
        self._repo = repo

    def _mask_source(self, source: dict) -> dict:
        masked = dict(source)
        masked["token"] = mask_token(masked.get("token", ""))
        return masked

    def list_sources(self) -> list[dict]:
        return [self._mask_source(s) for s in self._repo.list_sources()]

    def get_source(self, source_id: str) -> dict | None:
        source = self._repo.get_source(source_id)
        if source is None:
            return None
        return self._mask_source(source)

    def create_source(self, body: SourceCreate) -> dict:
        raw = f"{body.owner}/{body.repo}"
        source_id = hashlib.sha256(raw.encode()).hexdigest()[:ID_HEX_LENGTH]

        if self._repo.get_source(source_id):
            return {"error": "duplicate", "id": source_id}

        data = {
            "id": source_id,
            "type": body.type.value,
            "owner": body.owner,
            "repo": body.repo,
            "created_at": datetime.now(KST).isoformat(),
            "token": body.token,
            "active": True,
            "default_exit_phase": body.default_exit_phase,
        }
        self._repo.save_source(source_id, data)
        return self._mask_source(data)

    def update_source(self, source_id: str, body: SourceUpdate) -> dict | None:
        existing = self._repo.get_source(source_id)
        if not existing:
            return None

        if body.token is not None:
            existing["token"] = body.token
        if body.active is not None:
            existing["active"] = body.active
        if body.default_exit_phase is not None:
            existing["default_exit_phase"] = body.default_exit_phase

        self._repo.save_source(source_id, existing)
        return self._mask_source(existing)

    def delete_source(self, source_id: str) -> bool:
        return self._repo.delete_source(source_id)
