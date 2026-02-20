from __future__ import annotations

import asyncio
import logging

from app.domain.models.stream import StreamEvent

logger = logging.getLogger(__name__)

PLAN_PROMPT_TEMPLATE = """\
Analyze the GitHub issue and generate an implementation plan.

## Issue
- Title: {issue_title}
- URL: {issue_url}
- Repository: {owner}/{repo}

## Issue Body
{issue_body}

## Instructions
1. Explore the codebase and identify files/structure relevant to the issue.
2. Write the implementation plan in Markdown.
3. Include target files, implementation order, and expected impact scope.

Return only the Markdown plan.\
"""

SYSTEM_PROMPT = (
    "You are an agent that analyzes this codebase and produces an implementation plan. "
    "Use read-only tools only."
)


def _extract_session_id(events: list[StreamEvent]) -> str | None:
    """Extract session_id from stream events."""
    for ev in events:
        if ev.session_id:
            return ev.session_id
    return None


class ClaudeCliAdapter:
    async def run_with_stream(
        self,
        prompt: str,
        cwd: str,
        allowed_tools: list[str] | None = None,
        append_system_prompt: str | None = None,
    ) -> tuple[str, list[StreamEvent], str | None]:
        from app.domain.services.stream_parser import parse_stream_lines, extract_metadata

        cmd = ["claude", "-p", prompt, "--output-format", "stream-json", "--verbose"]
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

        try:
            stdout, stderr = await asyncio.wait_for(proc.communicate(), timeout=600)
        except asyncio.TimeoutError:
            proc.kill()
            await proc.wait()
            raise RuntimeError("claude CLI timeout (exceeded 600s)")

        if proc.returncode != 0:
            raise RuntimeError(f"claude CLI failed: {stderr.decode().strip()}")

        lines = stdout.decode().strip().splitlines()
        events = parse_stream_lines(lines)
        session_id = _extract_session_id(events)
        metadata = extract_metadata(events)
        return (metadata.result_text, events, session_id)
