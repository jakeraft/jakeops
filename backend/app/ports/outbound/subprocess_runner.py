from __future__ import annotations

from collections.abc import AsyncGenerator
from typing import Any, Protocol


class SubprocessRunner(Protocol):
    async def run(
        self,
        prompt: str,
        cwd: str,
        allowed_tools: list[str] | None = None,
        append_system_prompt: str | None = None,
        delivery_id: str | None = None,
    ) -> tuple[str, str | None]:
        """Run `claude -p --output-format json`.
        Returns: (result_text, session_id)
        """
        ...

    def run_stream(
        self,
        prompt: str,
        cwd: str,
        allowed_tools: list[str] | None = None,
        append_system_prompt: str | None = None,
        delivery_id: str | None = None,
    ) -> AsyncGenerator[dict[str, Any], None]:
        """Run `claude -p --output-format stream-json`.
        Yields parsed JSON events line by line.
        """
        ...

    def kill(self, delivery_id: str) -> bool:
        """Kill a running subprocess by delivery_id.
        Returns True if process was found and killed.
        """
        ...
