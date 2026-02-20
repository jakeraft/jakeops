# backend/tests/test_streaming_integration.py
import pytest
from app.adapters.outbound.filesystem_delivery import FileSystemDeliveryRepository
from app.adapters.outbound.filesystem_source import FileSystemSourceRepository
from app.domain.models.delivery import DeliveryCreate
from app.domain.services.event_bus import EventBus
from app.usecases.delivery_usecases import DeliveryUseCasesImpl


class MockStreamingRunner:
    def __init__(self, result_text: str = "Generated plan content"):
        self.result_text = result_text
        self.calls: list[dict] = []

    async def run(self, prompt, cwd, allowed_tools=None, append_system_prompt=None, delivery_id=None):
        self.calls.append({"prompt": prompt, "cwd": cwd})
        return (self.result_text, None)

    async def run_stream(self, prompt, cwd, allowed_tools=None, append_system_prompt=None, delivery_id=None):
        self.calls.append({"prompt": prompt, "cwd": cwd})
        events = [
            {"type": "system", "subtype": "init", "message": {"model": "test-model", "cwd": cwd}},
            {"type": "assistant", "message": {"role": "assistant", "content": [{"type": "text", "text": self.result_text}], "usage": {"input_tokens": 10, "output_tokens": 5}}},
            {"type": "result", "subtype": "success", "message": {"result": self.result_text, "is_error": False, "cost_usd": 0.01, "input_tokens": 10, "output_tokens": 5, "duration_ms": 100}},
        ]
        for event in events:
            yield event

    def kill(self, delivery_id):
        return False


class MockGitOperations:
    def __init__(self):
        self.clone_calls = []

    def clone_repo(self, owner, repo, token, dest):
        self.clone_calls.append({"owner": owner, "repo": repo})
        from pathlib import Path
        Path(dest).mkdir(parents=True, exist_ok=True)

    def checkout_branch(self, cwd, branch):
        pass

    def create_branch_with_file(self, *args, **kwargs):
        pass

    def create_draft_pr(self, *args, **kwargs):
        return "https://github.com/test/pr/1"


@pytest.fixture
def full_uc(tmp_path):
    delivery_repo = FileSystemDeliveryRepository(tmp_path / "deliveries")
    source_repo = FileSystemSourceRepository(tmp_path / "sources")
    runner = MockStreamingRunner()
    git_ops = MockGitOperations()
    event_bus = EventBus()
    uc = DeliveryUseCasesImpl(delivery_repo, runner, git_ops, source_repo, event_bus=event_bus)
    return uc, event_bus


class TestStreamingIntegration:
    @pytest.mark.asyncio
    async def test_plan_streams_events_and_saves_transcript(self, full_uc):
        uc, event_bus = full_uc
        body = DeliveryCreate(
            phase="plan", run_status="pending",
            summary="Test", repository="owner/repo",
            refs=[{"role": "trigger", "type": "github_issue", "label": "#1",
                   "url": "https://github.com/owner/repo/issues/1"}],
        )
        result = uc.create_delivery(body)
        delivery_id = result["id"]

        plan_result = await uc.generate_plan(delivery_id)
        assert plan_result["run_status"] == "succeeded"

        # Transcript should have been saved
        run_id = plan_result["run_id"]
        transcript = uc.get_run_transcript(delivery_id, run_id)
        assert transcript is not None
        assert "leader" in transcript

        # EventBus should be cleaned up
        assert not event_bus.is_active(delivery_id)

    @pytest.mark.asyncio
    async def test_metadata_extracted_correctly(self, full_uc):
        uc, event_bus = full_uc
        body = DeliveryCreate(
            phase="plan", run_status="pending",
            summary="Test metadata", repository="owner/repo",
            refs=[{"role": "trigger", "type": "github_issue", "label": "#2",
                   "url": "https://github.com/owner/repo/issues/2"}],
        )
        result = uc.create_delivery(body)
        delivery_id = result["id"]

        plan_result = await uc.generate_plan(delivery_id)
        delivery = uc.get_delivery(delivery_id)

        run = delivery["runs"][-1]
        assert run["stats"]["cost_usd"] == 0.01
        assert run["stats"]["input_tokens"] == 10
        assert run["stats"]["output_tokens"] == 5
        assert run["session"]["model"] == "test-model"
