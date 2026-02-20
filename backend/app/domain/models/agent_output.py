"""Structured output schemas for agent phases.

These models define the contract between the system and the agent.
Agents MUST return JSON conforming to these schemas. The use case layer
parses agent output with these models, rejecting malformed responses.
"""

from pydantic import BaseModel, Field, model_validator

from app.domain.models.delivery import Verdict


class ReviewOutput(BaseModel):
    """Agent output for the review phase."""

    verdict: Verdict = Field(
        description="pass if code meets quality standards, not_pass otherwise"
    )
    summary: str = Field(
        description="One-line summary of the review outcome"
    )
    feedback: str = Field(
        default="",
        description="Actionable feedback for the author. Required when verdict is not_pass",
    )

    @model_validator(mode="after")
    def feedback_required_when_not_pass(self) -> "ReviewOutput":
        if self.verdict == Verdict.not_passed and not self.feedback.strip():
            raise ValueError("feedback is required when verdict is not_pass")
        return self


class PlanOutput(BaseModel):
    """Agent output for the plan phase."""

    content: str = Field(
        min_length=1,
        description="Full implementation plan in Markdown",
    )
    target_files: list[str] = Field(
        default_factory=list,
        description="Files expected to be created or modified",
    )
