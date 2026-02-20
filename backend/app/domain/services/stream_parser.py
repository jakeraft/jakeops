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
    used_skills: list[str] = []

    for ev in events:
        if ev.type == "system" and ev.subtype == "init" and ev.message:
            meta.model = ev.message.get("model", "unknown")
            meta.cwd = ev.message.get("cwd")
            meta.tools = ev.message.get("tools", [])
            meta.skills = ev.message.get("skills", [])
            raw_plugins = ev.message.get("plugins", [])
            meta.plugins = [
                p["name"] if isinstance(p, dict) else p
                for p in raw_plugins
            ]
            meta.agents = ev.message.get("agents", [])
        elif ev.type == "result" and ev.message:
            has_result = True
            msg = ev.message
            meta.result_text = msg.get("result", "")
            meta.cost_usd = msg.get("cost_usd") or msg.get("total_cost_usd", 0.0)
            usage = msg.get("usage", {})
            meta.input_tokens = msg.get("input_tokens") or usage.get("input_tokens", 0)
            meta.output_tokens = msg.get("output_tokens") or usage.get("output_tokens", 0)
            meta.duration_ms = msg.get("duration_ms", 0)
            meta.is_success = not msg.get("is_error", True)

        # Collect Skill tool invocations from assistant messages
        if ev.type == "assistant" and ev.message:
            content = ev.message.get("content")
            if isinstance(content, list):
                for block in content:
                    if (
                        isinstance(block, dict)
                        and block.get("type") == "tool_use"
                        and block.get("name") == "Skill"
                    ):
                        skill_name = (block.get("input") or {}).get("skill", "")
                        if skill_name:
                            used_skills.append(skill_name)

    # Deduplicate while preserving invocation order
    seen: set[str] = set()
    meta.used_skills = [s for s in used_skills if not (s in seen or seen.add(s))]

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


def extract_agent_buckets(events: list[StreamEvent]) -> list[dict]:
    """Extract agent bucket metadata for UI dropdown.

    Scans events (skipping system/result) to collect unique
    parent_tool_use_id values, then matches them to Task tool_use
    blocks to build human-readable labels.
    """
    SKIP_TYPES = {"system", "result"}

    ordered_parent_ids: list[str] = []
    seen_parent_ids: set[str] = set()
    has_leader = False

    for ev in events:
        if ev.type in SKIP_TYPES:
            continue
        if ev.parent_tool_use_id:
            pid = ev.parent_tool_use_id
            if pid not in seen_parent_ids:
                ordered_parent_ids.append(pid)
                seen_parent_ids.add(pid)
        else:
            has_leader = True

    # Build label lookup from Task tool_use blocks
    task_labels: dict[str, str] = {}
    for ev in events:
        if ev.type != "assistant" or not ev.message:
            continue
        content = ev.message.get("content")
        if not isinstance(content, list):
            continue
        for block in content:
            if not isinstance(block, dict):
                continue
            if (
                block.get("type") == "tool_use"
                and block.get("name") == "Task"
                and block.get("id")
            ):
                bid = block["id"]
                if bid in seen_parent_ids and bid not in task_labels:
                    inp = block.get("input") or {}
                    desc = inp.get("description", "")
                    agent_type = inp.get("subagent_type", "")
                    label = f"{agent_type}: {desc}" if agent_type else desc
                    if label:
                        task_labels[bid] = label

    buckets: list[dict] = []
    if has_leader:
        buckets.append({"id": "leader", "label": "Leader"})

    for pid in ordered_parent_ids:
        label = task_labels.get(pid, pid[:8])
        buckets.append({"id": pid, "label": label})

    return buckets


class StreamMetaTracker:
    """Incrementally track model and agent_buckets from streaming events.

    Call ``push(event)`` for each incoming ``StreamEvent``.  When internal
    state changes, ``push`` returns a ``meta`` dict suitable for SSE
    broadcast; otherwise it returns ``None`` (no-op).
    """

    _SKIP_TYPES = frozenset({"system", "result"})

    def __init__(self) -> None:
        self.model: str | None = None
        self._has_leader = False
        self._ordered_parent_ids: list[str] = []
        self._seen_parent_ids: set[str] = set()
        self._task_labels: dict[str, str] = {}
        self._used_skills: list[str] = []
        self._seen_skills: set[str] = set()

    def push(self, ev: StreamEvent) -> dict | None:
        changed = False

        # Extract model from init event
        if ev.type == "system" and ev.subtype == "init" and ev.message:
            model = ev.message.get("model")
            if model and model != self.model:
                self.model = model
                changed = True

        # Track leader / subagent presence
        if ev.type not in self._SKIP_TYPES:
            if ev.parent_tool_use_id:
                pid = ev.parent_tool_use_id
                if pid not in self._seen_parent_ids:
                    self._ordered_parent_ids.append(pid)
                    self._seen_parent_ids.add(pid)
                    changed = True
            else:
                if not self._has_leader:
                    self._has_leader = True
                    changed = True

        # Extract tool_use metadata (Task labels, Skill invocations)
        if ev.type == "assistant" and ev.message:
            content = ev.message.get("content")
            if isinstance(content, list):
                for block in content:
                    if not isinstance(block, dict):
                        continue
                    if block.get("type") != "tool_use":
                        continue
                    name = block.get("name", "")
                    if name == "Task" and block.get("id"):
                        bid = block["id"]
                        if bid in self._seen_parent_ids and bid not in self._task_labels:
                            inp = block.get("input") or {}
                            desc = inp.get("description", "")
                            agent_type = inp.get("subagent_type", "")
                            label = f"{agent_type}: {desc}" if agent_type else desc
                            if label:
                                self._task_labels[bid] = label
                                changed = True
                    elif name == "Skill":
                        skill = (block.get("input") or {}).get("skill", "")
                        if skill and skill not in self._seen_skills:
                            self._used_skills.append(skill)
                            self._seen_skills.add(skill)
                            changed = True

        if not changed:
            return None
        return self._snapshot()

    def _snapshot(self) -> dict:
        buckets: list[dict] = []
        if self._has_leader:
            buckets.append({"id": "leader", "label": "Leader"})
        for pid in self._ordered_parent_ids:
            buckets.append({"id": pid, "label": self._task_labels.get(pid, pid[:8])})
        return {
            "model": self.model,
            "agent_buckets": buckets,
            "used_skills": list(self._used_skills),
        }


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
