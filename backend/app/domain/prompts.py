"""Phase-specific prompt templates for agent execution.

Prompts live here (not in adapters) because phase logic belongs in the
use case / domain layer. The executor (SubprocessRunner) is phase-agnostic.
"""

PLAN_SYSTEM_PROMPT = (
    "You are an agent that analyzes this codebase and produces an implementation plan. "
    "Use read-only tools only. "
    "You MUST end your response with a JSON block in this exact format:\n"
    "```json\n"
    '{"content": "full plan in Markdown", "target_files": ["path/to/file1.py", "path/to/file2.py"]}\n'
    "```"
)

PLAN_ALLOWED_TOOLS = ["Read", "Glob", "Grep", "LS"]

REVIEW_SYSTEM_PROMPT = (
    "You are a code review agent. Review changes for quality and correctness. "
    "Use read-only tools only. "
    "You MUST end your response with a JSON block in this exact format:\n"
    "```json\n"
    '{"verdict": "pass", "summary": "one-line summary", "feedback": ""}\n'
    "```\n"
    'verdict must be exactly "pass" or "not_pass". '
    "When verdict is not_pass, feedback must contain actionable feedback for the author."
)

REVIEW_ALLOWED_TOOLS = ["Read", "Glob", "Grep", "LS"]

IMPLEMENT_SYSTEM_PROMPT = (
    "You are a coding agent that implements changes based on a plan. "
    "Use all available tools to write and test code."
)

FIX_SYSTEM_PROMPT = (
    "You are a coding agent that fixes issues identified in code review. "
    "Make minimal, targeted changes to address the feedback."
)


def build_plan_prompt(summary: str, repository: str, refs: list[dict]) -> str:
    trigger_url = ""
    for ref in refs:
        if ref.get("role") == "trigger":
            trigger_url = ref.get("url", "")
            break

    url_line = f"\nURL: {trigger_url}" if trigger_url else ""

    return (
        f"Analyze the codebase and generate an implementation plan.\n\n"
        f"## Issue\n"
        f"{summary}{url_line}\n"
        f"Repository: {repository}\n\n"
        f"## Instructions\n"
        f"1. If a URL is provided, read the issue for full context.\n"
        f"2. Explore the codebase and identify relevant files.\n"
        f"3. Write the implementation plan in Markdown.\n"
        f"4. Include target files, implementation order, and expected impact.\n"
        f"5. End with a JSON block:\n"
        f"```json\n"
        f'{{"content": "full plan in Markdown", "target_files": ["path/to/file1.py", "path/to/file2.py"]}}\n'
        f"```"
    )


def build_implement_prompt(plan_content: str, summary: str) -> str:
    return (
        f"Implement the changes described in the plan below.\n\n"
        f"## Summary\n{summary}\n\n"
        f"## Plan\n{plan_content}\n\n"
        f"## Instructions\n"
        f"1. Follow the plan step by step.\n"
        f"2. Write clean, well-tested code.\n"
        f"3. Commit your changes with clear commit messages."
    )


def build_review_prompt(summary: str) -> str:
    return (
        f"Review the recent changes in this repository.\n\n"
        f"## Summary\n{summary}\n\n"
        f"## Instructions\n"
        f"1. Check the latest commits and changes.\n"
        f"2. Review for code quality, bugs, security issues.\n"
        f"3. End with a JSON block:\n"
        f"```json\n"
        f'{{"verdict": "pass", "summary": "one-line summary", "feedback": ""}}\n'
        f"```\n"
        f'verdict must be exactly "pass" or "not_pass". '
        f"When verdict is not_pass, feedback must contain actionable feedback."
    )


def build_fix_prompt(feedback: str, summary: str) -> str:
    return (
        f"Fix the issues identified in the code review.\n\n"
        f"## Summary\n{summary}\n\n"
        f"## Review Feedback\n{feedback}\n\n"
        f"## Instructions\n"
        f"1. Address each issue identified in the review.\n"
        f"2. Make minimal, targeted fixes.\n"
        f"3. Commit your changes with clear commit messages."
    )
