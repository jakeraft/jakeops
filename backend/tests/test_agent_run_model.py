class TestAgentRunMode:
    def test_values(self):
        from app.domain.models.agent_run import AgentRunMode

        assert AgentRunMode.plan == "plan"
        assert AgentRunMode.execution == "execution"
        assert AgentRunMode.fix == "fix"
        assert len(AgentRunMode) == 3


class TestAgentRunStatus:
    def test_values(self):
        from app.domain.models.agent_run import AgentRunStatus

        assert AgentRunStatus.success == "success"
        assert AgentRunStatus.failed == "failed"
        assert len(AgentRunStatus) == 2


class TestAgentRun:
    def test_success(self):
        from app.domain.models.agent_run import AgentRun, AgentRunMode, AgentRunStatus
        from app.domain.models.issue import ExecutionStats, Session

        run = AgentRun(
            id="abc123",
            mode=AgentRunMode.plan,
            status=AgentRunStatus.success,
            created_at="2026-02-20T10:00:00+09:00",
            session=Session(model="claude-opus-4-6"),
            stats=ExecutionStats(
                cost_usd=0.05,
                input_tokens=1000,
                output_tokens=500,
                duration_ms=3000,
            ),
            summary="Plan generated successfully",
        )
        assert run.id == "abc123"
        assert run.mode == AgentRunMode.plan
        assert run.status == AgentRunStatus.success
        assert run.error is None
        assert run.summary == "Plan generated successfully"
        assert run.stats.cost_usd == 0.05

    def test_failed_with_error(self):
        from app.domain.models.agent_run import AgentRun, AgentRunMode, AgentRunStatus
        from app.domain.models.issue import ExecutionStats, Session

        run = AgentRun(
            id="def456",
            mode=AgentRunMode.execution,
            status=AgentRunStatus.failed,
            created_at="2026-02-20T11:00:00+09:00",
            session=Session(model="claude-opus-4-6"),
            stats=ExecutionStats(duration_ms=1500),
            error="Command failed: git push",
        )
        assert run.status == AgentRunStatus.failed
        assert run.error == "Command failed: git push"
        assert run.summary is None

    def test_agent_run_with_session_id(self):
        from app.domain.models.agent_run import AgentRun
        from app.domain.models.issue import ExecutionStats, Session

        run = AgentRun(
            id="run-1",
            mode="plan",
            status="success",
            created_at="2026-02-20T12:00:00+09:00",
            session=Session(model="claude-opus-4-6"),
            stats=ExecutionStats(),
            session_id="sess-abc-123",
        )
        assert run.session_id == "sess-abc-123"

    def test_agent_run_session_id_optional(self):
        from app.domain.models.agent_run import AgentRun
        from app.domain.models.issue import ExecutionStats, Session

        run = AgentRun(
            id="run-1",
            mode="plan",
            status="success",
            created_at="2026-02-20T12:00:00+09:00",
            session=Session(model="claude-opus-4-6"),
            stats=ExecutionStats(),
        )
        assert run.session_id is None
