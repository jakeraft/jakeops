"""Extract metadata and transcript from StreamEvent lists.

`extract_metadata` and `extract_transcript` are consumed by the delivery
pipeline. Events are produced by `session_parser.parse_session_lines` (from
local session JSONL files under ~/.claude/projects/).

`parse_stream_lines` is retained for testing but is no longer used in the
production flow (the adapter now uses `--output-format json`).
"""

from __future__ import annotations

import json
from typing import Any

import structlog

from app.domain.models.stream import StreamEvent, StreamMetadata

logger = structlog.get_logger()


def extract_metadata(events: list[StreamEvent]) -> StreamMetadata:
    """Extract metadata from init + result events.

    When a result event is missing (e.g. CLI cancelled or crashed),
    falls back to assembling result_text from assistant text blocks.
    """
    meta = StreamMetadata()
    has_result = False

    for ev in events:
        if ev.type == "system" and ev.subtype == "init" and ev.message:
            meta.model = ev.message.get("model", "unknown")
            meta.cwd = ev.message.get("cwd")
            meta.skills = ev.message.get("tools", [])
            meta.plugins = ev.message.get("mcp_servers", [])
        elif ev.type == "result" and ev.message:
            has_result = True
            meta.result_text = ev.message.get("result", "")
            meta.cost_usd = ev.message.get("cost_usd", 0.0)
            meta.input_tokens = ev.message.get("input_tokens", 0)
            meta.output_tokens = ev.message.get("output_tokens", 0)
            meta.duration_ms = ev.message.get("duration_ms", 0)
            meta.is_success = not ev.message.get("is_error", True)

    if not has_result:
        logger.warning(
            "stream has no result event — falling back to assistant text",
            event_count=len(events),
            event_types=[ev.type for ev in events[-5:]],
        )
        meta.result_text = _assemble_result_text(events)
        meta.is_success = bool(meta.result_text)

    if not meta.result_text:
        meta.result_text = "(no output captured)"

    return meta


def _assemble_result_text(events: list[StreamEvent]) -> str:
    """Build result_text from the last assistant message text blocks."""
    parts: list[str] = []
    for ev in reversed(events):
        if ev.type != "assistant" or not ev.message:
            continue
        content = ev.message.get("content")
        if not isinstance(content, list):
            continue
        for block in content:
            if isinstance(block, dict) and block.get("type") == "text":
                text = block.get("text", "")
                if text:
                    parts.append(text)
        if parts:
            break
    return "\n".join(reversed(parts))


def extract_transcript(events: list[StreamEvent]) -> dict[str, Any]:
    """Build transcript structure grouped by parent_tool_use_id."""
    SKIP_TYPES = {"system", "result", "progress", "file-history-snapshot"}

    buckets: dict[str, list[dict]] = {"leader": []}
    agent_models: dict[str, str] = {}

    for ev in events:
        if ev.type == "system" and ev.subtype == "init" and ev.message:
            agent_models["leader"] = ev.message.get("model", "unknown")
            break
    if "leader" not in agent_models:
        agent_models["leader"] = "unknown"

    for ev in events:
        if ev.type in SKIP_TYPES:
            continue

        msg = ev.message or {}
        role = msg.get("role") or ev.type
        content = _transform_content(msg.get("content"))

        entry = {
            "role": role,
            "content": content,
        }

        if ev.parent_tool_use_id is None:
            buckets["leader"].append(entry)
        else:
            key = f"subagent_{ev.parent_tool_use_id}"
            if key not in buckets:
                buckets[key] = []
            buckets[key].append(entry)
            if key not in agent_models and msg.get("model"):
                agent_models[key] = msg["model"]

    agents_meta: dict[str, dict] = {}
    for agent_key in buckets:
        agents_meta[agent_key] = {
            "model": agent_models.get(agent_key, "unknown"),
        }

    result: dict[str, Any] = {
        "meta": {"agents": agents_meta},
    }
    for agent_key, messages in buckets.items():
        result[agent_key] = messages

    return result


def _transform_content(content: Any) -> Any:
    """Transform content blocks to the minimal required fields."""
    if not isinstance(content, list):
        return content

    transformed = []
    for block in content:
        block_type = block.get("type", "")
        if block_type == "text":
            transformed.append({"type": "text", "text": block.get("text", "")})
        elif block_type == "thinking":
            transformed.append({"type": "thinking", "thinking": block.get("thinking", "")})
        elif block_type == "tool_use":
            transformed.append({
                "type": "tool_use",
                "name": block.get("name", ""),
                "input": block.get("input", {}),
            })
        elif block_type == "tool_result":
            transformed.append({
                "type": "tool_result",
                "content": block.get("content"),
                "tool_use_id": block.get("tool_use_id", ""),
            })
        else:
            transformed.append(block)
    return transformed


def parse_stream_lines(lines: list[str]) -> list[StreamEvent]:
    """Convert JSONL lines to StreamEvents; skip malformed lines with warning."""
    events: list[StreamEvent] = []
    for idx, line in enumerate(lines):
        line = line.strip()
        if not line:
            continue
        try:
            data = json.loads(line)
        except json.JSONDecodeError as exc:
            logger.warning("JSONL parse failed", line_number=idx, error=str(exc), content=line[:200])
            continue
        events.append(StreamEvent(
            type=data.get("type", ""),
            subtype=data.get("subtype"),
            parent_tool_use_id=data.get("parent_tool_use_id"),
            message=data.get("message"),
            session_id=data.get("session_id"),
        ))
    return events
