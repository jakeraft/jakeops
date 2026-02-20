from unittest.mock import patch, MagicMock

import httpx
import pytest

from app.adapters.outbound.github_api import GitHubApiAdapter


def test_list_open_issues():
    adapter = GitHubApiAdapter()
    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_response.json.return_value = [
        {
            "number": 1,
            "title": "Bug report",
            "html_url": "https://github.com/owner/repo/issues/1",
            "state": "open",
        },
        {
            "number": 2,
            "title": "Feature request",
            "html_url": "https://github.com/owner/repo/issues/2",
            "state": "open",
        },
    ]
    mock_response.raise_for_status = MagicMock()

    with patch("httpx.get", return_value=mock_response) as mock_get:
        issues = adapter.list_open_issues("owner", "repo", token="fake-token")

    assert len(issues) == 2
    assert issues[0].number == 1
    assert issues[0].title == "Bug report"
    mock_get.assert_called_once()


def test_list_open_issues_filters_pull_requests():
    adapter = GitHubApiAdapter()
    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_response.json.return_value = [
        {
            "number": 1,
            "title": "Bug report",
            "html_url": "https://github.com/owner/repo/issues/1",
            "state": "open",
        },
        {
            "number": 2,
            "title": "PR title",
            "html_url": "https://github.com/owner/repo/pull/2",
            "state": "open",
            "pull_request": {"url": "..."},
        },
    ]
    mock_response.raise_for_status = MagicMock()

    with patch("httpx.get", return_value=mock_response):
        issues = adapter.list_open_issues("owner", "repo", token="fake-token")

    assert len(issues) == 1
    assert issues[0].number == 1


def test_list_open_issues_no_token():
    """Can fetch issues from a public repo without a token."""
    adapter = GitHubApiAdapter()
    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_response.json.return_value = [
        {
            "number": 1,
            "title": "Public issue",
            "html_url": "https://github.com/owner/repo/issues/1",
            "state": "open",
        },
    ]
    mock_response.raise_for_status = MagicMock()

    with patch("httpx.get", return_value=mock_response) as mock_get:
        issues = adapter.list_open_issues("owner", "repo")

    assert len(issues) == 1
    # Authorization header should not be present
    call_headers = mock_get.call_args.kwargs.get("headers", {})
    assert "Authorization" not in call_headers


def test_get_issue():
    """Get a single issue — includes body."""
    adapter = GitHubApiAdapter()
    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_response.json.return_value = {
        "number": 42,
        "title": "Feature request",
        "html_url": "https://github.com/o/r/issues/42",
        "state": "open",
        "body": "## Requirements\nNeed to add feature",
    }
    mock_response.raise_for_status = MagicMock()

    with patch("httpx.get", return_value=mock_response) as mock_get:
        issue = adapter.get_issue("o", "r", 42, token="ghp_test")

    assert issue is not None
    assert issue.number == 42
    assert issue.body == "## Requirements\nNeed to add feature"
    mock_get.assert_called_once()


def test_get_issue_not_found():
    """Non-existent issue — returns None."""
    adapter = GitHubApiAdapter()
    mock_response = MagicMock()
    mock_response.raise_for_status.side_effect = httpx.HTTPStatusError(
        "Not Found", request=MagicMock(), response=MagicMock(status_code=404)
    )

    with patch("httpx.get", return_value=mock_response):
        issue = adapter.get_issue("o", "r", 999)

    assert issue is None


def test_list_open_issues_not_found_returns_empty():
    """Returns empty list on 404 response."""
    adapter = GitHubApiAdapter()
    mock_response = MagicMock()
    mock_response.raise_for_status.side_effect = httpx.HTTPStatusError(
        "Not Found", request=MagicMock(), response=MagicMock(status_code=404)
    )

    with patch("httpx.get", return_value=mock_response):
        issues = adapter.list_open_issues("owner", "nonexistent")

    assert issues == []


def test_list_open_issues_server_error_raises():
    """Propagates exception on 500 error."""
    adapter = GitHubApiAdapter()
    mock_response = MagicMock()
    mock_response.raise_for_status.side_effect = httpx.HTTPStatusError(
        "Internal Server Error", request=MagicMock(), response=MagicMock(status_code=500)
    )

    with patch("httpx.get", return_value=mock_response):
        with pytest.raises(httpx.HTTPStatusError):
            adapter.list_open_issues("owner", "repo")


def test_get_issue_server_error_raises():
    """Propagates exception on 500 error."""
    adapter = GitHubApiAdapter()
    mock_response = MagicMock()
    mock_response.raise_for_status.side_effect = httpx.HTTPStatusError(
        "Internal Server Error", request=MagicMock(), response=MagicMock(status_code=500)
    )

    with patch("httpx.get", return_value=mock_response):
        with pytest.raises(httpx.HTTPStatusError):
            adapter.get_issue("o", "r", 42)


def test_list_open_issues_rate_limit_raises():
    """Propagates exception on 403 Rate Limit."""
    adapter = GitHubApiAdapter()
    mock_response = MagicMock()
    mock_response.raise_for_status.side_effect = httpx.HTTPStatusError(
        "Forbidden", request=MagicMock(), response=MagicMock(status_code=403)
    )

    with patch("httpx.get", return_value=mock_response):
        with pytest.raises(httpx.HTTPStatusError):
            adapter.list_open_issues("owner", "repo")
