"""Verify method signatures of the GitOperations Protocol."""
import inspect


def test_git_operations_protocol_has_create_branch_with_file():
    from app.ports.outbound.git_operations import GitOperations

    method = getattr(GitOperations, "create_branch_with_file", None)
    assert method is not None, "create_branch_with_file method must exist"

    sig = inspect.signature(method)
    param_names = list(sig.parameters.keys())
    assert param_names == [
        "self",
        "repo_url",
        "branch",
        "file_path",
        "content",
        "commit_message",
        "token",
    ]
    assert sig.parameters["token"].default == ""
    assert sig.return_annotation is None


def test_git_operations_protocol_has_create_draft_pr():
    from app.ports.outbound.git_operations import GitOperations

    method = getattr(GitOperations, "create_draft_pr", None)
    assert method is not None, "create_draft_pr method must exist"

    sig = inspect.signature(method)
    param_names = list(sig.parameters.keys())
    assert param_names == [
        "self",
        "owner",
        "repo",
        "branch",
        "title",
        "body",
        "token",
    ]
    assert sig.parameters["token"].default == ""
    assert sig.return_annotation is str


def test_git_operations_is_protocol():
    from typing import runtime_checkable, Protocol

    from app.ports.outbound.git_operations import GitOperations

    assert issubclass(GitOperations, Protocol)
