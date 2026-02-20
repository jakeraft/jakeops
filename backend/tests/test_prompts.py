from app.domain.prompts import build_prompt, _collect_ref_urls


def _delivery(**overrides) -> dict:
    base = {
        "summary": "Fix login bug",
        "repository": "owner/repo",
        "refs": [{"role": "request", "type": "github_issue", "label": "#1",
                  "url": "https://github.com/owner/repo/issues/1"}],
    }
    base.update(overrides)
    return base


class TestCollectRefUrls:
    def test_all_urls(self):
        d = _delivery(refs=[
            {"role": "request", "url": "https://a"},
            {"role": "work", "type": "pr", "url": "https://b"},
        ])
        assert _collect_ref_urls(d) == ["https://a", "https://b"]

    def test_filter_by_role(self):
        d = _delivery(refs=[
            {"role": "request", "url": "https://a"},
            {"role": "work", "type": "pr", "url": "https://b"},
        ])
        assert _collect_ref_urls(d, role="request") == ["https://a"]

    def test_skips_empty_urls(self):
        d = _delivery(refs=[{"role": "request"}])
        assert _collect_ref_urls(d) == []


class TestBuildPrompt:
    def test_includes_summary(self):
        result = build_prompt(_delivery())
        assert "Fix login bug" in result

    def test_includes_ref_url(self):
        result = build_prompt(_delivery())
        assert "https://github.com/owner/repo/issues/1" in result

    def test_no_refs(self):
        result = build_prompt(_delivery(refs=[]))
        assert "Fix login bug" in result
        assert "References" not in result

    def test_includes_all_ref_urls(self):
        d = _delivery(refs=[
            {"role": "request", "url": "https://issue"},
            {"role": "work", "type": "pr", "url": "https://pr"},
        ])
        result = build_prompt(d)
        assert "https://issue" in result
        assert "https://pr" in result

    def test_ignores_plan_content(self):
        d = _delivery(plan={"content": "SECRET_PLAN", "generated_at": "", "model": "", "cwd": ""})
        result = build_prompt(d)
        assert "SECRET_PLAN" not in result

    def test_ignores_reject_reason(self):
        d = _delivery(reject_reason="Missing error handling")
        result = build_prompt(d)
        assert "Missing error handling" not in result
