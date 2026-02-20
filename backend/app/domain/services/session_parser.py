"""Parse Claude session files (.jsonl).

Reads session files in `~/.claude/projects/<hash>/<session_id>.jsonl`
and converts them into StreamEvent lists.
Differences from stream-json: camelCase keys, no result event, noise event types.
"""

from __future__ import annotations

import json
import logging
from pathlib import Path

from app.domain.models.stream import StreamEvent

CLAUDE_PROJECTS_DIR = Path.home() / ".claude" / "projects"

logger = logging.getLogger(__name__)

NOISE_TYPES = {"progress", "file-history-snapshot"}


def synthesize_result_event(events: list[StreamEvent]) -> StreamEvent:
    """Synthesize a result event by aggregating assistant usage.

    Session files do not contain stream-json result events,
    so this creates one to make extract_metadata() work.

    Raises:
        ValueError: if no assistant message text exists
    """
    total_input = 0
    total_output = 0
    last_text = ""

    for ev in events:
        if ev.type != "assistant" or not ev.message:
            continue
        usage = ev.message.get("usage", {})
        total_input += usage.get("input_tokens", 0)
        total_output += usage.get("output_tokens", 0)
        for block in ev.message.get("content", []):
            if isinstance(block, dict) and block.get("type") == "text":
                last_text = block.get("text", "")

    if not last_text:
        raise ValueError("no assistant message text found — session file looks invalid")

    return StreamEvent(
        type="result",
        subtype="success",
        message={
            "result": last_text,
            "is_error": False,
            "cost_usd": 0.0,
            "input_tokens": total_input,
            "output_tokens": total_output,
            "duration_ms": 0,
        },
    )


def parse_session_lines(lines: list[str]) -> list[StreamEvent]:
    """Session JSONL -> StreamEvents with noise filtering and camelCase mapping."""
    events: list[StreamEvent] = []
    for idx, line in enumerate(lines):
        line = line.strip()
        if not line:
            continue
        try:
            data = json.loads(line)
        except json.JSONDecodeError as exc:
            logger.warning("Session JSONL parse failed (line %d): %s", idx, exc)
            continue

        event_type = data.get("type", "")
        if event_type in NOISE_TYPES:
            continue

        events.append(StreamEvent(
            type=event_type,
            subtype=data.get("subtype"),
            parent_tool_use_id=data.get("parentToolUseID"),
            message=data.get("message"),
            session_id=data.get("sessionId"),
        ))
    return events


def find_session_file(
    session_id: str,
    search_dirs: list[Path] | None = None,
) -> Path | None:
    """Find a session file under ~/.claude/projects/ recursively by project folder."""
    dirs = search_dirs or ([CLAUDE_PROJECTS_DIR] if CLAUDE_PROJECTS_DIR.exists() else [])
    for base in dirs:
        for project_dir in base.iterdir():
            if not project_dir.is_dir():
                continue
            candidate = project_dir / f"{session_id}.jsonl"
            if candidate.exists():
                return candidate
    return None
