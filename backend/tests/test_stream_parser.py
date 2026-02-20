import json
import logging

import pytest

from app.domain.models.stream import StreamEvent
from app.domain.services.stream_parser import (
    extract_metadata,
    extract_transcript,
    parse_stream_lines,
)


class TestParseStreamLines:
    def test_parses_valid_lines(self):
        lines = [
            json.dumps({"type": "system", "subtype": "init", "session_id": "s1"}),
            json.dumps({"type": "assistant", "message": {"role": "assistant"}}),
        ]
        events = parse_stream_lines(lines)
        assert len(events) == 2
        assert events[0].type == "system"
        assert events[0].subtype == "init"
        assert events[1].type == "assistant"

    def test_skips_invalid_json(self):
        lines = ["not valid json", json.dumps({"type": "user"}), "{broken"]
        events = parse_stream_lines(lines)
        assert len(events) == 1
        assert events[0].type == "user"

    def test_skips_empty_lines(self):
        lines = ["", "  ", json.dumps({"type": "result", "subtype": "success"})]
        events = parse_stream_lines(lines)
        assert len(events) == 1

    def test_extracts_parent_tool_use_id(self):
        lines = [json.dumps({"type": "assistant", "parent_tool_use_id": "tool-123", "message": {}})]
        events = parse_stream_lines(lines)
        assert events[0].parent_tool_use_id == "tool-123"

    def test_preserves_message_dict(self):
        msg = {"role": "assistant", "content": [{"type": "text", "text": "hi"}]}
        lines = [json.dumps({"type": "assistant", "message": msg})]
        events = parse_stream_lines(lines)
        assert events[0].message == msg


class TestExtractMetadata:
    def test_extracts_from_init_event(self):
        events = [
            StreamEvent(type="system", subtype="init", message={
                "model": "claude-opus-4-6", "cwd": "/tmp/repo",
                "tools": ["Read", "Glob", "Grep"], "mcp_servers": [],
            }, session_id="sess-1"),
            StreamEvent(type="assistant", message={"role": "assistant"}),
            StreamEvent(type="result", subtype="success", message={
                "result": "done", "is_error": False,
            }),
        ]
        meta = extract_metadata(events)
        assert meta.model == "claude-opus-4-6"
        assert meta.cwd == "/tmp/repo"
        assert meta.skills == ["Read", "Glob", "Grep"]

    def test_extracts_from_result_event(self):
        events = [
            StreamEvent(type="system", subtype="init", message={"model": "claude-opus-4-6"}),
            StreamEvent(type="result", subtype="success", message={
                "result": "Plan generated successfully",
                "cost_usd": 0.05, "input_tokens": 1000, "output_tokens": 500,
                "duration_ms": 30000, "is_error": False,
            }),
        ]
        meta = extract_metadata(events)
        assert meta.is_success is True
        assert meta.result_text == "Plan generated successfully"
        assert meta.cost_usd == 0.05
        assert meta.input_tokens == 1000
        assert meta.output_tokens == 500
        assert meta.duration_ms == 30000

    def test_raises_when_no_result_event(self):
        """Raises ValueError when no result event is present."""
        events = [StreamEvent(type="assistant", message={})]
        with pytest.raises(ValueError, match="stream has no result event"):
            extract_metadata(events)

    def test_error_result(self):
        events = [
            StreamEvent(type="result", subtype="error", message={
                "result": "Error occurred", "is_error": True, "cost_usd": 0.01,
            }),
        ]
        meta = extract_metadata(events)
        assert meta.is_success is False
        assert meta.result_text == "Error occurred"
        assert meta.cost_usd == 0.01

    def test_raises_when_result_text_empty(self):
        """Raises ValueError when result_text is an empty string."""
        events = [
            StreamEvent(type="result", subtype="success", message={
                "result": "", "is_error": False,
            }),
        ]
        with pytest.raises(ValueError, match="result_text is empty"):
            extract_metadata(events)


class TestParseStreamLinesWarning:
    def test_logs_warning_on_invalid_json(self, caplog):
        """Invalid JSON lines produce a warning log."""
        lines = ["not valid json", json.dumps({"type": "user"})]
        with caplog.at_level(logging.WARNING, logger="app.domain.services.stream_parser"):
            events = parse_stream_lines(lines)
        assert len(events) == 1
        assert "JSONL parse failed" in caplog.text
        assert "not valid json" in caplog.text

    def test_logs_warning_with_line_number(self, caplog):
        """Warning log includes the line number."""
        lines = [json.dumps({"type": "system"}), "{broken", json.dumps({"type": "user"})]
        with caplog.at_level(logging.WARNING, logger="app.domain.services.stream_parser"):
            events = parse_stream_lines(lines)
        assert len(events) == 2
        assert "line 1" in caplog.text


class TestExtractTranscript:
    def test_leader_only(self):
        events = [
            StreamEvent(type="system", subtype="init", message={"model": "claude-opus-4-6"}),
            StreamEvent(type="user", message={"role": "user", "content": "question"}),
            StreamEvent(type="assistant", message={
                "role": "assistant", "content": [{"type": "text", "text": "answer"}],
                "model": "claude-opus-4-6",
            }),
        ]
        result = extract_transcript(events)
        assert "leader" in result
        assert len(result["leader"]) == 2
        assert result["leader"][0]["role"] == "user"
        assert result["leader"][1]["role"] == "assistant"
        assert result["meta"]["agents"]["leader"]["model"] == "claude-opus-4-6"

    def test_subagent_grouping(self):
        events = [
            StreamEvent(type="user", message={"role": "user", "content": "leader message"}),
            StreamEvent(type="assistant", parent_tool_use_id="tool-aaa",
                message={"role": "assistant", "content": [{"type": "text", "text": "sub1 response"}]}),
            StreamEvent(type="user", parent_tool_use_id="tool-aaa",
                message={"role": "user", "content": "sub1 input"}),
            StreamEvent(type="assistant", parent_tool_use_id="tool-bbb",
                message={"role": "assistant", "content": [{"type": "text", "text": "sub2 response"}]}),
        ]
        result = extract_transcript(events)
        assert len(result["leader"]) == 1
        assert "subagent_tool-aaa" in result
        assert len(result["subagent_tool-aaa"]) == 2
        assert "subagent_tool-bbb" in result
        assert len(result["subagent_tool-bbb"]) == 1

    def test_filters_system_events(self):
        events = [
            StreamEvent(type="system", subtype="init", message={"model": "m"}),
            StreamEvent(type="system", subtype="task_started", message={}),
            StreamEvent(type="user", message={"role": "user", "content": "hello"}),
            StreamEvent(type="result", subtype="success", message={"result": "ok"}),
        ]
        result = extract_transcript(events)
        assert len(result["leader"]) == 1

    def test_filters_progress_events(self):
        events = [
            StreamEvent(type="user", message={"role": "user", "content": "hi"}),
            StreamEvent(type="progress", message={}),
            StreamEvent(type="assistant", message={
                "role": "assistant", "content": [{"type": "text", "text": "bye"}]}),
        ]
        result = extract_transcript(events)
        assert len(result["leader"]) == 2

    def test_content_block_transform(self):
        events = [
            StreamEvent(type="assistant", message={
                "role": "assistant",
                "content": [
                    {"type": "text", "text": "hello", "extra": "noise"},
                    {"type": "tool_use", "name": "Read", "input": {"path": "/tmp"}, "id": "tool-1"},
                    {"type": "thinking", "thinking": "hmm", "signature": "xxx"},
                ],
            }),
        ]
        result = extract_transcript(events)
        blocks = result["leader"][0]["content"]
        assert blocks[0] == {"type": "text", "text": "hello"}
        assert blocks[1] == {"type": "tool_use", "name": "Read", "input": {"path": "/tmp"}}
        assert "id" not in blocks[1]
        assert blocks[2] == {"type": "thinking", "thinking": "hmm"}
        assert "signature" not in blocks[2]

    def test_meta_agents(self):
        events = [
            StreamEvent(type="system", subtype="init", message={"model": "claude-opus-4-6"}),
            StreamEvent(type="user", message={"role": "user", "content": "q"}),
            StreamEvent(type="assistant", parent_tool_use_id="tool-x",
                message={"role": "assistant", "model": "claude-haiku-4-5",
                    "content": [{"type": "text", "text": "r"}]}),
        ]
        result = extract_transcript(events)
        assert result["meta"]["agents"]["leader"]["model"] == "claude-opus-4-6"
        assert result["meta"]["agents"]["subagent_tool-x"]["model"] == "claude-haiku-4-5"
