import json

import pytest
from pydantic import ValidationError

from app.domain.models.agent_output import ReviewOutput, PlanOutput
from app.domain.models.delivery import Verdict


class TestReviewOutput:
    def test_pass_verdict(self):
        output = ReviewOutput(
            verdict=Verdict.passed,
            summary="Code looks good",
        )
        assert output.verdict == Verdict.passed
        assert output.feedback == ""

    def test_not_pass_verdict_with_feedback(self):
        output = ReviewOutput(
            verdict=Verdict.not_passed,
            summary="Issues found",
            feedback="Missing error handling in auth module",
        )
        assert output.verdict == Verdict.not_passed
        assert output.feedback == "Missing error handling in auth module"

    def test_parse_from_json(self):
        raw = '{"verdict": "pass", "summary": "LGTM"}'
        output = ReviewOutput.model_validate_json(raw)
        assert output.verdict == Verdict.passed

    def test_parse_not_pass_from_json(self):
        raw = json.dumps({
            "verdict": "not_pass",
            "summary": "Needs work",
            "feedback": "Fix the SQL injection vulnerability",
        })
        output = ReviewOutput.model_validate_json(raw)
        assert output.verdict == Verdict.not_passed
        assert output.feedback == "Fix the SQL injection vulnerability"

    def test_missing_verdict_raises(self):
        with pytest.raises(ValidationError):
            ReviewOutput.model_validate_json('{"summary": "no verdict"}')

    def test_invalid_verdict_raises(self):
        with pytest.raises(ValidationError):
            ReviewOutput.model_validate_json(
                '{"verdict": "maybe", "summary": "invalid"}'
            )

    def test_not_pass_without_feedback_raises(self):
        with pytest.raises(ValidationError, match="feedback is required"):
            ReviewOutput(
                verdict=Verdict.not_passed,
                summary="Issues found",
            )

    def test_not_pass_with_blank_feedback_raises(self):
        with pytest.raises(ValidationError, match="feedback is required"):
            ReviewOutput(
                verdict=Verdict.not_passed,
                summary="Issues found",
                feedback="   ",
            )


class TestPlanOutput:
    def test_basic(self):
        output = PlanOutput(
            content="## Plan\n1. Do X\n2. Do Y",
            target_files=["src/auth.py", "tests/test_auth.py"],
        )
        assert "Do X" in output.content
        assert len(output.target_files) == 2

    def test_empty_target_files_default(self):
        output = PlanOutput(content="## Plan\nMinimal change")
        assert output.target_files == []

    def test_parse_from_json(self):
        raw = json.dumps({
            "content": "## Plan\nRefactor auth",
            "target_files": ["src/auth.py"],
        })
        output = PlanOutput.model_validate_json(raw)
        assert output.target_files == ["src/auth.py"]

    def test_missing_content_raises(self):
        with pytest.raises(ValidationError):
            PlanOutput.model_validate_json('{"target_files": []}')

    def test_empty_content_raises(self):
        with pytest.raises(ValidationError):
            PlanOutput(content="")
