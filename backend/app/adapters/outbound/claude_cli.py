from __future__ import annotations

import asyncio
import json

import structlog

logger = structlog.get_logger()


class ClaudeCliAdapter:
    def __init__(self) -> None:
        self._processes: dict[str, asyncio.subprocess.Process] = {}

    async def run(
        self,
        prompt: str,
        cwd: str,
        allowed_tools: list[str] | None = None,
        append_system_prompt: str | None = None,
        delivery_id: str | None = None,
    ) -> tuple[str, str | None]:
        cmd = ["claude", "-p", prompt, "--output-format", "json"]
        if allowed_tools:
            cmd += ["--allowedTools", ",".join(allowed_tools)]
        if append_system_prompt:
            cmd += ["--append-system-prompt", append_system_prompt]

        proc = await asyncio.create_subprocess_exec(
            *cmd,
            cwd=cwd,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )

        if delivery_id:
            self._processes[delivery_id] = proc

        try:
            stdout, stderr = await asyncio.wait_for(proc.communicate(), timeout=600)
        except asyncio.TimeoutError:
            proc.kill()
            await proc.wait()
            raise RuntimeError("claude CLI timeout (exceeded 600s)")
        finally:
            if delivery_id:
                self._processes.pop(delivery_id, None)

        if proc.returncode != 0:
            raise RuntimeError(f"claude CLI failed: {stderr.decode().strip()}")

        data = json.loads(stdout.decode())
        result_text = data.get("result", "")
        session_id = data.get("session_id")

        if data.get("is_error", False):
            raise RuntimeError(f"claude CLI returned error: {result_text}")

        return (result_text, session_id)

    def kill(self, delivery_id: str) -> bool:
        proc = self._processes.pop(delivery_id, None)
        if proc is None:
            return False
        proc.kill()
        return True
