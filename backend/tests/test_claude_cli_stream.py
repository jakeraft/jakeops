import asyncio
import json

import pytest

from app.adapters.outbound.claude_cli import ClaudeCliAdapter


class TestRunWithStream:
    @pytest.fixture
    def adapter(self):
        return ClaudeCliAdapter()

    def test_parses_stream_output(self, adapter, monkeypatch):
        init_line = json.dumps({
            "type": "system", "subtype": "init",
            "message": {"model": "claude-opus-4-6", "cwd": "/tmp"},
        })
        assistant_line = json.dumps({
            "type": "assistant",
            "message": {"role": "assistant", "content": [{"type": "text", "text": "plan"}]},
        })
        result_line = json.dumps({
            "type": "result", "subtype": "success",
            "message": {
                "result": "Generated plan", "cost_usd": 0.03,
                "input_tokens": 800, "output_tokens": 400,
                "duration_ms": 20000, "is_error": False,
            },
        })
        stdout = f"{init_line}\n{assistant_line}\n{result_line}\n"

        async def fake_create_subprocess_exec(*args, **kwargs):
            class FakeProc:
                returncode = 0
                async def communicate(self):
                    return stdout.encode(), b""
            return FakeProc()

        monkeypatch.setattr("asyncio.create_subprocess_exec", fake_create_subprocess_exec)

        result_text, events, _ = asyncio.run(adapter.run_with_stream("prompt", "/tmp"))
        assert result_text == "Generated plan"
        assert len(events) == 3
        assert events[0].type == "system"
        assert events[0].subtype == "init"

    def test_raises_on_nonzero_exit(self, adapter, monkeypatch):
        async def fake_create_subprocess_exec(*args, **kwargs):
            class FakeProc:
                returncode = 1
                async def communicate(self):
                    return b"", b"error message"
            return FakeProc()

        monkeypatch.setattr("asyncio.create_subprocess_exec", fake_create_subprocess_exec)

        with pytest.raises(RuntimeError, match="claude CLI failed"):
            asyncio.run(adapter.run_with_stream("prompt", "/tmp"))

    def test_passes_allowed_tools(self, adapter, monkeypatch):
        captured_args = []

        async def fake_create_subprocess_exec(*args, **kwargs):
            captured_args.extend(args)
            class FakeProc:
                returncode = 0
                async def communicate(self):
                    result_line = json.dumps({
                        "type": "result", "subtype": "success",
                        "message": {"result": "ok", "is_error": False},
                    })
                    return result_line.encode(), b""
            return FakeProc()

        monkeypatch.setattr("asyncio.create_subprocess_exec", fake_create_subprocess_exec)

        asyncio.run(adapter.run_with_stream("p", "/tmp", allowed_tools=["Read", "Glob"]))
        assert "--allowedTools" in captured_args
        idx = captured_args.index("--allowedTools")
        assert captured_args[idx + 1] == "Read,Glob"

    def test_passes_system_prompt(self, adapter, monkeypatch):
        captured_args = []

        async def fake_create_subprocess_exec(*args, **kwargs):
            captured_args.extend(args)
            class FakeProc:
                returncode = 0
                async def communicate(self):
                    result_line = json.dumps({
                        "type": "result", "subtype": "success",
                        "message": {"result": "ok", "is_error": False},
                    })
                    return result_line.encode(), b""
            return FakeProc()

        monkeypatch.setattr("asyncio.create_subprocess_exec", fake_create_subprocess_exec)

        asyncio.run(adapter.run_with_stream("p", "/tmp", append_system_prompt="You are a bot"))
        assert "--append-system-prompt" in captured_args
        idx = captured_args.index("--append-system-prompt")
        assert captured_args[idx + 1] == "You are a bot"

    def test_returns_session_id(self, adapter, monkeypatch):
        init_line = json.dumps({
            "type": "system", "subtype": "init",
            "session_id": "sess-123",
            "message": {"model": "claude-opus-4-6"},
        })
        result_line = json.dumps({
            "type": "result", "subtype": "success",
            "message": {"result": "ok", "is_error": False},
        })
        stdout = f"{init_line}\n{result_line}\n"

        async def fake_create_subprocess_exec(*args, **kwargs):
            class FakeProc:
                returncode = 0
                async def communicate(self):
                    return stdout.encode(), b""
            return FakeProc()

        monkeypatch.setattr("asyncio.create_subprocess_exec", fake_create_subprocess_exec)

        result_text, events, session_id = asyncio.run(
            adapter.run_with_stream("prompt", "/tmp")
        )
        assert session_id == "sess-123"
        assert result_text == "ok"
