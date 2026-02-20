from typing import Protocol


class CodeExecutor(Protocol):
    def execute_plan(
        self,
        owner: str,
        repo: str,
        branch: str,
        plan_content: str,
        token: str = "",
    ) -> str:
        """Generate code from a plan and commit+push on a branch.
        Returns a result summary. Raise on failure.
        """
        ...
