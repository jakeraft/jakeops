// Auto-generated from backend domain models. DO NOT EDIT.
// Run: python3 scripts/sync-types.py

export type Phase = "intake" | "plan" | "implement" | "review" | "verify" | "deploy" | "observe" | "close"
export const PHASES = ["intake", "plan", "implement", "review", "verify", "deploy", "observe", "close"] as const

export type RunStatus = "pending" | "running" | "succeeded" | "failed" | "blocked"
export const RUN_STATUSES = ["pending", "running", "succeeded", "failed", "blocked"] as const

export type ExecutorKind = "system" | "agent"
export const EXECUTOR_KINDS = ["system", "agent"] as const

export type Verdict = "pass" | "not_pass"
export const VERDICTS = ["pass", "not_pass"] as const

export type RefRole = "trigger" | "output" | "parent"
export const REF_ROLES = ["trigger", "output", "parent"] as const

export type RefType = "jira" | "verbal" | "pr" | "commit" | "repo" | "github_issue" | "pull_request" | "issue"
export const REF_TYPES = ["jira", "verbal", "pr", "commit", "repo", "github_issue", "pull_request", "issue"] as const
