from __future__ import annotations

import asyncio
import json
from collections.abc import AsyncGenerator
from typing import Any

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

    async def run_stream(
        self,
        prompt: str,
        cwd: str,
        allowed_tools: list[str] | None = None,
        append_system_prompt: str | None = None,
        delivery_id: str | None = None,
    ) -> AsyncGenerator[dict[str, Any], None]:
        cmd = ["claude", "-p", prompt, "--output-format", "stream-json"]
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
            assert proc.stdout is not None
            while True:
                try:
                    line = await asyncio.wait_for(proc.stdout.readline(), timeout=600)
                except asyncio.TimeoutError:
                    proc.kill()
                    await proc.wait()
                    raise RuntimeError("claude CLI streaming timeout (exceeded 600s)")
                if not line:
                    break
                text = line.decode().strip()
                if not text:
                    continue
                try:
                    yield json.loads(text)
                except json.JSONDecodeError:
                    logger.warning("skipping non-JSON line", line=text)
            await proc.wait()
            if proc.returncode != 0:
                stderr_data = await proc.stderr.read() if proc.stderr else b""
                raise RuntimeError(
                    f"claude CLI failed (exit {proc.returncode}): "
                    f"{stderr_data.decode().strip()}"
                )
        finally:
            if delivery_id:
                self._processes.pop(delivery_id, None)

    def kill(self, delivery_id: str) -> bool:
        proc = self._processes.pop(delivery_id, None)
        if proc is None:
            return False
        proc.kill()
        return True
