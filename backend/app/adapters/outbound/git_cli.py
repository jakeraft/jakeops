import os
import subprocess
import tempfile
from pathlib import Path

import structlog

logger = structlog.get_logger()


class GitCliAdapter:
    def clone_repo(self, owner: str, repo: str, token: str, dest: str) -> None:
        if token:
            clone_url = f"https://x-access-token:{token}@github.com/{owner}/{repo}.git"
        else:
            clone_url = f"https://github.com/{owner}/{repo}.git"
        self._run_git(["git", "clone", "--depth=1", clone_url, dest], "clone", token=token)

    def create_branch_with_file(
        self,
        repo_url: str,
        branch: str,
        file_path: str,
        content: str,
        commit_message: str,
        token: str = "",
    ) -> None:
        with tempfile.TemporaryDirectory(prefix="jakeops-git-") as tmpdir:
            if token:
                clone_url = repo_url.replace("https://", f"https://x-access-token:{token}@")
            else:
                clone_url = repo_url

            self._run_git(["git", "clone", "--depth=1", clone_url, tmpdir], "clone", token=token)
            self._run_git(["git", "checkout", "-b", branch], "checkout", cwd=tmpdir)

            target = Path(tmpdir) / file_path
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_text(content, encoding="utf-8")

            self._run_git(["git", "add", file_path], "add", cwd=tmpdir)
            self._run_git(
                ["git", "commit", "-m", commit_message],
                "commit",
                cwd=tmpdir,
                env_override={
                    "GIT_AUTHOR_NAME": "jakeops",
                    "GIT_COMMITTER_NAME": "jakeops",
                    "GIT_AUTHOR_EMAIL": "jakeops@noreply",
                    "GIT_COMMITTER_EMAIL": "jakeops@noreply",
                },
            )
            self._run_git(["git", "push", "-u", "origin", branch], "push", cwd=tmpdir, token=token)

    def create_draft_pr(
        self,
        owner: str,
        repo: str,
        branch: str,
        title: str,
        body: str,
        token: str = "",
    ) -> str:
        cmd = [
            "gh", "pr", "create",
            "--repo", f"{owner}/{repo}",
            "--head", branch,
            "--title", title,
            "--body", body,
            "--draft",
        ]
        env_override = {}
        if token:
            env_override["GH_TOKEN"] = token

        result = self._run_subprocess(cmd, env_override=env_override or None)
        if result.returncode != 0:
            raise RuntimeError(f"Failed to create draft PR: {owner}/{repo} — {result.stderr.strip()}")
        return result.stdout.strip()

    def _run_git(
        self,
        cmd: list[str],
        label: str,
        cwd: str | None = None,
        env_override: dict[str, str] | None = None,
        token: str = "",
    ) -> None:
        result = self._run_subprocess(cmd, cwd=cwd, env_override=env_override)
        if result.returncode != 0:
            safe_stderr = result.stderr.replace(token, "***") if token else result.stderr
            raise RuntimeError(f"git {label} failed: {safe_stderr.strip()}")

    @staticmethod
    def _run_subprocess(
        cmd: list[str],
        cwd: str | None = None,
        env_override: dict[str, str] | None = None,
    ) -> subprocess.CompletedProcess:
        env = None
        if env_override:
            env = {**os.environ, **env_override}
        return subprocess.run(
            cmd, capture_output=True, text=True, timeout=120, cwd=cwd, env=env,
        )
