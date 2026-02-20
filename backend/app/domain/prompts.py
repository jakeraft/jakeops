"""Phase-specific prompt templates for agent execution.

JakeOps prompts follow a minimal principle:
- system prompt: what to do (one-liner role)
- user prompt: summary + refs URLs (agent reads full context from GitHub)
- cwd: cloned repo + user's CLAUDE.md

Never tell the agent HOW to do its job.
"""

_NON_INTERACTIVE = (
    "You are running non-interactively in a CI pipeline. "
    "Do NOT ask questions, request clarification, or present options. "
    "Complete the task fully and return the result directly."
)

PLAN_SYSTEM_PROMPT = (
    "Analyze this codebase and produce an implementation plan. "
    "Write the plan directly in your response — do NOT create a file for it. "
    f"{_NON_INTERACTIVE}"
)

REVIEW_SYSTEM_PROMPT = (
    f"Review the recent changes in this repository. {_NON_INTERACTIVE}"
)

IMPLEMENT_SYSTEM_PROMPT = (
    f"Implement the changes described in the plan. {_NON_INTERACTIVE}"
)


def _collect_ref_urls(delivery: dict, role: str | None = None) -> list[str]:
    """Extract URLs from refs, optionally filtered by role."""
    urls = []
    for ref in delivery.get("refs", []):
        if role and ref.get("role") != role:
            continue
        url = ref.get("url", "")
        if url:
            urls.append(url)
    return urls


def _refs_section(urls: list[str]) -> str:
    if not urls:
        return ""
    lines = "\n".join(f"- {url}" for url in urls)
    return f"\n\n## References\n{lines}"


def build_prompt(delivery: dict) -> str:
    """Unified prompt builder — summary + all ref URLs.

    Agent reads full context (plan, review feedback, etc.)
    directly from GitHub issue/PR threads via the URLs.
    """
    urls = _collect_ref_urls(delivery)
    return f"{delivery['summary']}{_refs_section(urls)}"
