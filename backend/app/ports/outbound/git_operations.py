from typing import Protocol


class GitOperations(Protocol):
    def create_branch_with_file(
        self,
        repo_url: str,
        branch: str,
        file_path: str,
        content: str,
        commit_message: str,
        token: str = "",
    ) -> None:
        """Create a branch on remote repo and commit+push a file. Raise on failure."""
        ...

    def clone_repo(self, owner: str, repo: str, token: str, dest: str) -> None:
        """Shallow-clone repository to destination path."""
        ...

    def checkout_branch(self, cwd: str, branch: str) -> None:
        """Fetch and checkout a remote branch. Raise on failure."""
        ...

    def create_draft_pr(
        self,
        owner: str,
        repo: str,
        branch: str,
        title: str,
        body: str,
        token: str = "",
    ) -> str:
        """Create a draft PR and return PR URL. Raise on failure."""
        ...
