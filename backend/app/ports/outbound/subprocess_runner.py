from __future__ import annotations

from typing import Protocol


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

    def kill(self, delivery_id: str) -> bool:
        """Kill a running subprocess by delivery_id.
        Returns True if process was found and killed.
        """
        ...
