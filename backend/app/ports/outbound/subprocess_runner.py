from __future__ import annotations

from typing import Protocol

from app.domain.models.stream import StreamEvent


class SubprocessRunner(Protocol):
    async def run_with_stream(
        self,
        prompt: str,
        cwd: str,
        allowed_tools: list[str] | None = None,
        append_system_prompt: str | None = None,
    ) -> tuple[str, list[StreamEvent], str | None]:
        """Run `claude -p --output-format stream-json`.
        Returns: (result_text, stream_events, session_id)
        """
        ...
