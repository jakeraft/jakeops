"""Unit tests for GitCliAdapter — verify via mocked subprocess.run."""
import subprocess
from unittest.mock import patch, call

import pytest


def _ok_result(**overrides) -> subprocess.CompletedProcess:
    """Helper to create a CompletedProcess with returncode=0."""
    defaults = {"returncode": 0, "stdout": "", "stderr": ""}
    defaults.update(overrides)
    return subprocess.CompletedProcess(args=[], **defaults)


def _fail_result(**overrides) -> subprocess.CompletedProcess:
    """Helper to create a CompletedProcess with returncode=1."""
    defaults = {"returncode": 1, "stdout": "", "stderr": "fatal error"}
    defaults.update(overrides)
    return subprocess.CompletedProcess(args=[], **defaults)


# ── create_branch_with_file ──────────────────────────────────────────


def test_creates_branch_and_pushes():
    """subprocess is called in order: clone, checkout, add, commit, push."""
    from app.adapters.outbound.git_cli import GitCliAdapter

    adapter = GitCliAdapter()

    with patch("app.adapters.outbound.git_cli.subprocess.run", return_value=_ok_result()) as mock_run:
        adapter.create_branch_with_file(
            repo_url="https://github.com/owner/repo.git",
            branch="feat/test",
            file_path="plans/plan.md",
            content="# Plan",
            commit_message="feat: add plan",
        )

    # at least 5 calls: clone, checkout, add, commit, push
    assert mock_run.call_count == 5

    cmds = [c.args[0] for c in mock_run.call_args_list]
    assert cmds[0][:3] == ["git", "clone", "--depth=1"]
    assert cmds[1] == ["git", "checkout", "-b", "feat/test"]
    assert cmds[2] == ["git", "add", "plans/plan.md"]
    assert cmds[3][:3] == ["git", "commit", "-m"]
    assert cmds[4] == ["git", "push", "-u", "origin", "feat/test"]


def test_uses_token_in_clone_url():
    """Clone URL includes x-access-token when a token is provided."""
    from app.adapters.outbound.git_cli import GitCliAdapter

    adapter = GitCliAdapter()

    with patch("app.adapters.outbound.git_cli.subprocess.run", return_value=_ok_result()) as mock_run:
        adapter.create_branch_with_file(
            repo_url="https://github.com/owner/repo.git",
            branch="feat/token-test",
            file_path="f.txt",
            content="hello",
            commit_message="test",
            token="ghp_secret123",
        )

    clone_cmd = mock_run.call_args_list[0].args[0]
    clone_url = clone_cmd[3]  # git clone --depth=1 <URL> <dir>
    assert "x-access-token:ghp_secret123@" in clone_url
    assert clone_url.startswith("https://x-access-token:ghp_secret123@github.com/")


def test_raises_on_clone_failure():
    """Raises RuntimeError when clone fails."""
    from app.adapters.outbound.git_cli import GitCliAdapter

    adapter = GitCliAdapter()

    with patch("app.adapters.outbound.git_cli.subprocess.run", return_value=_fail_result()):
        with pytest.raises(RuntimeError, match="git clone failed"):
            adapter.create_branch_with_file(
                repo_url="https://github.com/owner/repo.git",
                branch="feat/fail",
                file_path="f.txt",
                content="x",
                commit_message="test",
            )


def test_masks_token_in_error_message():
    """Token is masked in the stderr error message."""
    from app.adapters.outbound.git_cli import GitCliAdapter

    adapter = GitCliAdapter()
    token = "ghp_secret123"
    stderr_with_token = f"fatal: could not read from https://x-access-token:{token}@github.com/o/r.git"

    with patch(
        "app.adapters.outbound.git_cli.subprocess.run",
        return_value=_fail_result(stderr=stderr_with_token),
    ):
        with pytest.raises(RuntimeError) as exc_info:
            adapter.create_branch_with_file(
                repo_url="https://github.com/owner/repo.git",
                branch="feat/fail",
                file_path="f.txt",
                content="x",
                commit_message="test",
                token=token,
            )
    assert token not in str(exc_info.value)
    assert "***" in str(exc_info.value)


# ── create_draft_pr ──────────────────────────────────────────────────


def test_creates_pr_and_returns_url():
    """Returns stdout (PR URL) after calling gh pr create --draft."""
    from app.adapters.outbound.git_cli import GitCliAdapter

    adapter = GitCliAdapter()
    pr_url = "https://github.com/owner/repo/pull/42"

    with patch(
        "app.adapters.outbound.git_cli.subprocess.run",
        return_value=_ok_result(stdout=f"  {pr_url}  \n"),
    ) as mock_run:
        result = adapter.create_draft_pr(
            owner="owner",
            repo="repo",
            branch="feat/test",
            title="Draft: plan",
            body="auto-generated",
        )

    assert result == pr_url

    cmd = mock_run.call_args.args[0]
    assert cmd[0:3] == ["gh", "pr", "create"]
    assert "--draft" in cmd
    assert "--repo" in cmd
    idx = cmd.index("--repo")
    assert cmd[idx + 1] == "owner/repo"


def test_pr_uses_token_as_gh_token_env():
    """Token is passed as GH_TOKEN environment variable."""
    from app.adapters.outbound.git_cli import GitCliAdapter

    adapter = GitCliAdapter()

    with patch(
        "app.adapters.outbound.git_cli.subprocess.run",
        return_value=_ok_result(stdout="https://github.com/o/r/pull/1"),
    ) as mock_run:
        adapter.create_draft_pr(
            owner="o",
            repo="r",
            branch="feat/x",
            title="t",
            body="b",
            token="ghp_tok",
        )

    call_kwargs = mock_run.call_args.kwargs
    assert call_kwargs["env"] is not None
    assert call_kwargs["env"]["GH_TOKEN"] == "ghp_tok"


def test_raises_on_pr_failure():
    """Raises RuntimeError when PR creation fails."""
    from app.adapters.outbound.git_cli import GitCliAdapter

    adapter = GitCliAdapter()

    with patch(
        "app.adapters.outbound.git_cli.subprocess.run",
        return_value=_fail_result(stderr="could not create PR"),
    ):
        with pytest.raises(RuntimeError, match="Failed to create draft PR"):
            adapter.create_draft_pr(
                owner="owner",
                repo="repo",
                branch="feat/broken",
                title="t",
                body="b",
            )
