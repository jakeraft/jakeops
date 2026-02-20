from app.domain.models.stream import StreamEvent, StreamMetadata


class TestStreamEvent:
    def test_minimal_event(self):
        ev = StreamEvent(type="assistant")
        assert ev.type == "assistant"
        assert ev.subtype is None
        assert ev.parent_tool_use_id is None
        assert ev.message is None
        assert ev.session_id is None

    def test_full_event(self):
        ev = StreamEvent(
            type="system", subtype="init",
            parent_tool_use_id=None,
            message={"model": "claude-opus-4-6"},
            session_id="sess-123",
        )
        assert ev.subtype == "init"
        assert ev.message["model"] == "claude-opus-4-6"

    def test_subagent_event(self):
        ev = StreamEvent(
            type="assistant",
            parent_tool_use_id="tool-abc-123",
            message={"role": "assistant", "content": [{"type": "text", "text": "hello"}]},
        )
        assert ev.parent_tool_use_id == "tool-abc-123"


class TestStreamMetadata:
    def test_defaults(self):
        meta = StreamMetadata()
        assert meta.model == "unknown"
        assert meta.cwd is None
        assert meta.skills == []
        assert meta.plugins == []
        assert meta.cost_usd == 0.0
        assert meta.input_tokens == 0
        assert meta.output_tokens == 0
        assert meta.duration_ms == 0
        assert meta.is_success is False
        assert meta.result_text == ""

    def test_full_metadata(self):
        meta = StreamMetadata(
            model="claude-opus-4-6", cwd="/tmp/repo",
            skills=["Read", "Glob"], plugins=[],
            cost_usd=0.05, input_tokens=1000, output_tokens=500,
            duration_ms=30000, is_success=True, result_text="Plan generated",
        )
        assert meta.model == "claude-opus-4-6"
        assert meta.cost_usd == 0.05
        assert meta.is_success is True
