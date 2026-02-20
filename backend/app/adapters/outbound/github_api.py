import httpx
import structlog

from app.domain.models.github import GitHubIssue

logger = structlog.get_logger()


class GitHubApiAdapter:
    def list_open_issues(self, owner: str, repo: str, token: str = "") -> list[GitHubIssue]:
        url = f"https://api.github.com/repos/{owner}/{repo}/issues"
        headers: dict[str, str] = {"Accept": "application/vnd.github+json"}
        if token:
            headers["Authorization"] = f"Bearer {token}"
        params = {"state": "open", "per_page": 100}

        try:
            resp = httpx.get(url, headers=headers, params=params, timeout=30)
            resp.raise_for_status()
        except httpx.HTTPStatusError as e:
            if e.response.status_code == 404:
                logger.warning("GitHub repository not found", owner=owner, repo=repo)
                return []
            raise
        except httpx.HTTPError:
            raise

        issues = []
        for item in resp.json():
            if item.get("pull_request"):
                continue
            issues.append(GitHubIssue(
                number=item["number"],
                title=item["title"],
                html_url=item["html_url"],
                state=item["state"],
            ))
        return issues

    def get_issue(self, owner: str, repo: str, number: int, token: str = "") -> GitHubIssue | None:
        url = f"https://api.github.com/repos/{owner}/{repo}/issues/{number}"
        headers: dict[str, str] = {"Accept": "application/vnd.github+json"}
        if token:
            headers["Authorization"] = f"Bearer {token}"

        try:
            resp = httpx.get(url, headers=headers, timeout=30)
            resp.raise_for_status()
        except httpx.HTTPStatusError as e:
            if e.response.status_code == 404:
                logger.warning("GitHub issue not found", owner=owner, repo=repo, number=number)
                return None
            raise
        except httpx.HTTPError:
            raise

        item = resp.json()
        return GitHubIssue(
            number=item["number"],
            title=item["title"],
            html_url=item["html_url"],
            state=item["state"],
            body=item.get("body") or "",
        )
