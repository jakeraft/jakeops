import asyncio
import json

import pytest

from app.adapters.outbound.claude_cli import ClaudeCliAdapter


class TestRun:
    @pytest.fixture
    def adapter(self):
        return ClaudeCliAdapter()

    def test_parses_json_output(self, adapter, monkeypatch):
        result_json = json.dumps({
            "result": "Generated plan",
            "session_id": "sess-abc",
            "cost_usd": 0.03,
            "is_error": False,
        })

        async def fake_create_subprocess_exec(*args, **kwargs):
            class FakeProc:
                returncode = 0
                async def communicate(self):
                    return result_json.encode(), b""
            return FakeProc()

        monkeypatch.setattr("asyncio.create_subprocess_exec", fake_create_subprocess_exec)

        result_text, session_id = asyncio.run(adapter.run("prompt", "/tmp"))
        assert result_text == "Generated plan"
        assert session_id == "sess-abc"

    def test_raises_on_nonzero_exit(self, adapter, monkeypatch):
        async def fake_create_subprocess_exec(*args, **kwargs):
            class FakeProc:
                returncode = 1
                async def communicate(self):
                    return b"", b"error message"
            return FakeProc()

        monkeypatch.setattr("asyncio.create_subprocess_exec", fake_create_subprocess_exec)

        with pytest.raises(RuntimeError, match="claude CLI failed"):
            asyncio.run(adapter.run("prompt", "/tmp"))

    def test_raises_on_cli_error_result(self, adapter, monkeypatch):
        result_json = json.dumps({
            "result": "Something went wrong",
            "is_error": True,
        })

        async def fake_create_subprocess_exec(*args, **kwargs):
            class FakeProc:
                returncode = 0
                async def communicate(self):
                    return result_json.encode(), b""
            return FakeProc()

        monkeypatch.setattr("asyncio.create_subprocess_exec", fake_create_subprocess_exec)

        with pytest.raises(RuntimeError, match="claude CLI returned error"):
            asyncio.run(adapter.run("prompt", "/tmp"))

    def test_passes_allowed_tools(self, adapter, monkeypatch):
        captured_args = []

        async def fake_create_subprocess_exec(*args, **kwargs):
            captured_args.extend(args)
            class FakeProc:
                returncode = 0
                async def communicate(self):
                    return json.dumps({"result": "ok", "is_error": False}).encode(), b""
            return FakeProc()

        monkeypatch.setattr("asyncio.create_subprocess_exec", fake_create_subprocess_exec)

        asyncio.run(adapter.run("p", "/tmp", allowed_tools=["Read", "Glob"]))
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
                    return json.dumps({"result": "ok", "is_error": False}).encode(), b""
            return FakeProc()

        monkeypatch.setattr("asyncio.create_subprocess_exec", fake_create_subprocess_exec)

        asyncio.run(adapter.run("p", "/tmp", append_system_prompt="You are a bot"))
        assert "--append-system-prompt" in captured_args
        idx = captured_args.index("--append-system-prompt")
        assert captured_args[idx + 1] == "You are a bot"

    def test_uses_json_output_format(self, adapter, monkeypatch):
        captured_args = []

        async def fake_create_subprocess_exec(*args, **kwargs):
            captured_args.extend(args)
            class FakeProc:
                returncode = 0
                async def communicate(self):
                    return json.dumps({"result": "ok", "is_error": False}).encode(), b""
            return FakeProc()

        monkeypatch.setattr("asyncio.create_subprocess_exec", fake_create_subprocess_exec)

        asyncio.run(adapter.run("p", "/tmp"))
        assert "--output-format" in captured_args
        idx = captured_args.index("--output-format")
        assert captured_args[idx + 1] == "json"

    def test_returns_session_id(self, adapter, monkeypatch):
        result_json = json.dumps({
            "result": "ok",
            "session_id": "sess-123",
            "is_error": False,
        })

        async def fake_create_subprocess_exec(*args, **kwargs):
            class FakeProc:
                returncode = 0
                async def communicate(self):
                    return result_json.encode(), b""
            return FakeProc()

        monkeypatch.setattr("asyncio.create_subprocess_exec", fake_create_subprocess_exec)

        result_text, session_id = asyncio.run(adapter.run("prompt", "/tmp"))
        assert session_id == "sess-123"
        assert result_text == "ok"

    def test_returns_none_session_id_when_missing(self, adapter, monkeypatch):
        result_json = json.dumps({
            "result": "ok",
            "is_error": False,
        })

        async def fake_create_subprocess_exec(*args, **kwargs):
            class FakeProc:
                returncode = 0
                async def communicate(self):
                    return result_json.encode(), b""
            return FakeProc()

        monkeypatch.setattr("asyncio.create_subprocess_exec", fake_create_subprocess_exec)

        result_text, session_id = asyncio.run(adapter.run("prompt", "/tmp"))
        assert session_id is None
        assert result_text == "ok"
