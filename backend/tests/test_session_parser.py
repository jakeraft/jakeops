import json

import pytest

from app.domain.models.stream import StreamEvent
from app.domain.services.session_parser import find_session_file, parse_session_lines, synthesize_result_event
from app.domain.services.stream_parser import extract_metadata


class TestParseSessionLines:
    def test_maps_camelcase_to_snake_case(self):
        lines = [
            json.dumps({
                "type": "system", "subtype": "init",
                "sessionId": "sess-abc",
                "parentToolUseID": None,
                "message": {"model": "claude-opus-4-6"},
            }),
        ]
        events = parse_session_lines(lines)
        assert len(events) == 1
        assert events[0].session_id == "sess-abc"
        assert events[0].parent_tool_use_id is None

    def test_filters_noise_types(self):
        lines = [
            json.dumps({"type": "progress", "data": {}}),
            json.dumps({"type": "file-history-snapshot", "snapshot": {}}),
            json.dumps({
                "type": "user", "sessionId": "s1",
                "message": {"role": "user", "content": "hello"},
            }),
        ]
        events = parse_session_lines(lines)
        assert len(events) == 1
        assert events[0].type == "user"

    def test_extracts_parent_tool_use_id(self):
        lines = [
            json.dumps({
                "type": "assistant",
                "parentToolUseID": "tool-xyz",
                "sessionId": "s1",
                "message": {"role": "assistant", "content": [{"type": "text", "text": "r"}]},
            }),
        ]
        events = parse_session_lines(lines)
        assert events[0].parent_tool_use_id == "tool-xyz"

    def test_skips_invalid_json(self):
        lines = ["not json", json.dumps({"type": "user", "message": {}})]
        events = parse_session_lines(lines)
        assert len(events) == 1


class TestSynthesizeResultEvent:
    def test_aggregates_usage_from_assistant_messages(self):
        lines = [
            json.dumps({
                "type": "system", "subtype": "init",
                "sessionId": "s1",
                "message": {"model": "claude-opus-4-6", "cwd": "/repo"},
            }),
            json.dumps({
                "type": "assistant", "sessionId": "s1",
                "message": {
                    "role": "assistant",
                    "content": [{"type": "text", "text": "intermediate response"}],
                    "usage": {"input_tokens": 100, "output_tokens": 50},
                },
            }),
            json.dumps({
                "type": "assistant", "sessionId": "s1",
                "message": {
                    "role": "assistant",
                    "content": [{"type": "text", "text": "final response"}],
                    "usage": {"input_tokens": 200, "output_tokens": 100},
                },
            }),
        ]
        events = parse_session_lines(lines)
        result_event = synthesize_result_event(events)

        assert result_event.type == "result"
        assert result_event.subtype == "success"
        assert result_event.message["result"] == "final response"
        assert result_event.message["input_tokens"] == 300
        assert result_event.message["output_tokens"] == 150
        assert result_event.message["is_error"] is False

    def test_works_with_extract_metadata(self):
        """synthesize_result_event output can be passed directly to extract_metadata."""
        lines = [
            json.dumps({
                "type": "system", "subtype": "init",
                "sessionId": "s1",
                "message": {"model": "claude-opus-4-6"},
            }),
            json.dumps({
                "type": "assistant", "sessionId": "s1",
                "message": {
                    "role": "assistant",
                    "content": [{"type": "text", "text": "plan content"}],
                    "usage": {"input_tokens": 500, "output_tokens": 300},
                },
            }),
        ]
        events = parse_session_lines(lines)
        result_event = synthesize_result_event(events)
        all_events = events + [result_event]

        meta = extract_metadata(all_events)
        assert meta.model == "claude-opus-4-6"
        assert meta.result_text == "plan content"
        assert meta.input_tokens == 500
        assert meta.output_tokens == 300
        assert meta.is_success is True

    def test_empty_assistant_raises(self):
        events = [
            StreamEvent(type="system", subtype="init", message={"model": "m"}),
            StreamEvent(type="user", message={"role": "user", "content": "q"}),
        ]
        with pytest.raises(ValueError, match="no assistant message text found"):
            synthesize_result_event(events)


class TestFindSessionFile:
    def test_finds_session_file(self, tmp_path):
        project_dir = tmp_path / "proj-hash"
        project_dir.mkdir()
        session_file = project_dir / "sess-abc.jsonl"
        session_file.write_text('{"type":"user"}')

        result = find_session_file("sess-abc", search_dirs=[tmp_path])
        assert result == session_file

    def test_returns_none_when_not_found(self, tmp_path):
        result = find_session_file("nonexistent", search_dirs=[tmp_path])
        assert result is None
