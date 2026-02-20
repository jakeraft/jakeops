"""Phase-specific prompt templates for agent execution.

JakeOps prompts follow a minimal principle:
- system prompt: what to do (one-liner role)
- user prompt: refs URLs (accumulated context)
- cwd: cloned repo + user's CLAUDE.md

Never tell the agent HOW to do its job.
All builders take `delivery: dict` as the single source of context.
"""

_NON_INTERACTIVE = (
    "You are running non-interactively in a CI pipeline. "
    "Do NOT ask questions, request clarification, or present options. "
    "Complete the task fully and return the result directly."
)

PLAN_SYSTEM_PROMPT = (
    f"Analyze this codebase and produce an implementation plan. {_NON_INTERACTIVE}"
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


def build_plan_prompt(delivery: dict) -> str:
    urls = _collect_ref_urls(delivery, role="trigger")
    return f"{delivery['summary']}{_refs_section(urls)}"


def build_implement_prompt(delivery: dict) -> str:
    urls = _collect_ref_urls(delivery)
    plan_content = ""
    if delivery.get("plan"):
        plan_content = delivery["plan"].get("content", "")

    parts = [f"## Summary\n{delivery['summary']}"]
    parts.append(f"\n\n## Plan\n{plan_content}")

    reject_reason = delivery.get("reject_reason")
    if reject_reason:
        parts.append(f"\n\n## Review Feedback\n{reject_reason}")

    ref_section = _refs_section(urls)
    if ref_section:
        parts.append(ref_section)

    return "".join(parts)


def build_review_prompt(delivery: dict) -> str:
    urls = _collect_ref_urls(delivery)
    return f"{delivery['summary']}{_refs_section(urls)}"
