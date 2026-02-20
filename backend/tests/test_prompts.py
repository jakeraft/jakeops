from app.domain.prompts import (
    build_plan_prompt,
    build_implement_prompt,
    build_review_prompt,
    _collect_ref_urls,
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


class TestCollectRefUrls:
    def test_all_urls(self):
        d = _delivery(refs=[
            {"role": "trigger", "url": "https://a"},
            {"role": "output", "type": "pr", "url": "https://b"},
        ])
        assert _collect_ref_urls(d) == ["https://a", "https://b"]

    def test_filter_by_role(self):
        d = _delivery(refs=[
            {"role": "trigger", "url": "https://a"},
            {"role": "output", "type": "pr", "url": "https://b"},
        ])
        assert _collect_ref_urls(d, role="trigger") == ["https://a"]

    def test_skips_empty_urls(self):
        d = _delivery(refs=[{"role": "trigger"}])
        assert _collect_ref_urls(d) == []


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
        assert "References" not in result

    def test_only_trigger_urls(self):
        d = _delivery(refs=[
            {"role": "trigger", "url": "https://issue"},
            {"role": "output", "type": "pr", "url": "https://pr"},
        ])
        result = build_plan_prompt(d)
        assert "https://issue" in result
        assert "https://pr" not in result


class TestBuildImplementPrompt:
    def test_includes_plan_and_summary(self):
        d = _delivery(plan={"content": "## Steps\n1. Fix X", "generated_at": "", "model": "", "cwd": ""})
        result = build_implement_prompt(d)
        assert "## Steps" in result
        assert "Fix login bug" in result

    def test_includes_reject_reason(self):
        d = _delivery(
            plan={"content": "plan", "generated_at": "", "model": "", "cwd": ""},
            reject_reason="Missing error handling",
        )
        result = build_implement_prompt(d)
        assert "Missing error handling" in result
        assert "Review Feedback" in result

    def test_no_reject_reason(self):
        d = _delivery(plan={"content": "plan", "generated_at": "", "model": "", "cwd": ""})
        result = build_implement_prompt(d)
        assert "Review Feedback" not in result

    def test_includes_all_ref_urls(self):
        d = _delivery(
            plan={"content": "plan", "generated_at": "", "model": "", "cwd": ""},
            refs=[
                {"role": "trigger", "url": "https://issue"},
                {"role": "output", "type": "pr", "url": "https://pr"},
            ],
        )
        result = build_implement_prompt(d)
        assert "https://issue" in result
        assert "https://pr" in result


class TestBuildReviewPrompt:
    def test_includes_summary(self):
        result = build_review_prompt(_delivery())
        assert "Fix login bug" in result

    def test_includes_all_ref_urls(self):
        d = _delivery(refs=[
            {"role": "trigger", "url": "https://issue"},
            {"role": "output", "type": "pr", "url": "https://pr"},
        ])
        result = build_review_prompt(d)
        assert "https://issue" in result
        assert "https://pr" in result
