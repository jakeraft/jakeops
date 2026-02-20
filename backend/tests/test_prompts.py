from app.domain.prompts import (
    build_plan_prompt,
    build_implement_prompt,
    build_review_prompt,
    build_fix_prompt,
    PLAN_SYSTEM_PROMPT,
    PLAN_ALLOWED_TOOLS,
    REVIEW_ALLOWED_TOOLS,
)


class TestBuildPlanPrompt:
    def test_includes_summary(self):
        result = build_plan_prompt(
            summary="Fix login bug",
            repository="owner/repo",
            refs=[{"role": "trigger", "type": "github_issue", "label": "#1", "url": "https://github.com/owner/repo/issues/1"}],
        )
        assert "Fix login bug" in result

    def test_includes_trigger_url(self):
        result = build_plan_prompt(
            summary="Fix login bug",
            repository="owner/repo",
            refs=[{"role": "trigger", "type": "github_issue", "label": "#1", "url": "https://github.com/owner/repo/issues/1"}],
        )
        assert "https://github.com/owner/repo/issues/1" in result

    def test_no_trigger_url(self):
        result = build_plan_prompt(
            summary="Manual task",
            repository="owner/repo",
            refs=[],
        )
        assert "Manual task" in result


class TestBuildImplementPrompt:
    def test_includes_plan_and_summary(self):
        result = build_implement_prompt(plan_content="## Steps\n1. Fix X", summary="Fix login")
        assert "## Steps" in result
        assert "Fix login" in result


class TestBuildReviewPrompt:
    def test_includes_summary(self):
        result = build_review_prompt(summary="Fix login")
        assert "Fix login" in result


class TestBuildFixPrompt:
    def test_includes_feedback(self):
        result = build_fix_prompt(feedback="Missing error handling", summary="Fix login")
        assert "Missing error handling" in result


class TestConstants:
    def test_plan_tools_are_readonly(self):
        assert "Read" in PLAN_ALLOWED_TOOLS
        assert "Write" not in PLAN_ALLOWED_TOOLS

    def test_review_tools_are_readonly(self):
        assert "Read" in REVIEW_ALLOWED_TOOLS
        assert "Write" not in REVIEW_ALLOWED_TOOLS
