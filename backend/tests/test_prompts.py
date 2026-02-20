from app.domain.prompts import (
    build_plan_prompt,
    build_implement_prompt,
    build_review_prompt,
    build_fix_prompt,
)


def _delivery(**overrides) -> dict:
    base = {
        "summary": "Fix login bug",
        "repository": "owner/repo",
        "refs": [{"role": "trigger", "type": "github_issue", "label": "#1",
                  "url": "https://github.com/owner/repo/issues/1"}],
    }
    base.update(overrides)
    return base


class TestBuildPlanPrompt:
    def test_includes_summary(self):
        result = build_plan_prompt(_delivery())
        assert "Fix login bug" in result

    def test_includes_trigger_url(self):
        result = build_plan_prompt(_delivery())
        assert "https://github.com/owner/repo/issues/1" in result

    def test_no_trigger_url(self):
        result = build_plan_prompt(_delivery(refs=[]))
        assert "Fix login bug" in result


class TestBuildImplementPrompt:
    def test_includes_plan_and_summary(self):
        d = _delivery(plan={"content": "## Steps\n1. Fix X", "generated_at": "", "model": "", "cwd": ""})
        result = build_implement_prompt(d)
        assert "## Steps" in result
        assert "Fix login bug" in result


class TestBuildReviewPrompt:
    def test_includes_summary(self):
        result = build_review_prompt(_delivery())
        assert "Fix login bug" in result


class TestBuildFixPrompt:
    def test_includes_feedback(self):
        result = build_fix_prompt(_delivery(), feedback="Missing error handling")
        assert "Missing error handling" in result
