"""Phase-specific prompt templates for agent execution.

JakeOps prompts follow a minimal principle: only pass the context that
the system knows (issue summary, URL, plan content, feedback). Never
tell the agent HOW to do its job — the agent's own capabilities and the
user's usage handle that. This preserves the user's agent experience
as if they invoked the agent directly.

All builders take `delivery: dict` as the single source of context.
Extra params (e.g. feedback) are for data that comes from the API call,
not from the stored delivery.
"""

PLAN_SYSTEM_PROMPT = "Analyze this codebase and produce an implementation plan."

REVIEW_SYSTEM_PROMPT = "Review the recent changes in this repository."

IMPLEMENT_SYSTEM_PROMPT = "Implement the changes described in the plan."

FIX_SYSTEM_PROMPT = "Fix the issues identified in the code review feedback."


def _trigger_url(delivery: dict) -> str:
    for ref in delivery.get("refs", []):
        if ref.get("role") == "trigger":
            return ref.get("url", "")
    return ""


def build_plan_prompt(delivery: dict) -> str:
    url = _trigger_url(delivery)
    url_line = f"\nURL: {url}" if url else ""
    return f"{delivery['summary']}{url_line}"


def build_implement_prompt(delivery: dict) -> str:
    plan_content = ""
    if delivery.get("plan"):
        plan_content = delivery["plan"].get("content", "")
    return f"## Summary\n{delivery['summary']}\n\n## Plan\n{plan_content}"


def build_review_prompt(delivery: dict) -> str:
    return delivery["summary"]


def build_fix_prompt(delivery: dict, feedback: str = "") -> str:
    return f"## Summary\n{delivery['summary']}\n\n## Feedback\n{feedback}"
