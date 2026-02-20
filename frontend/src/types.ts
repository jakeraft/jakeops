export interface Ref {
  role: string;
  type: string;
  label: string;
  url?: string;
}

export interface AgentRun {
  id: string;
  mode: string;
  status: string;
  created_at: string;
  summary?: string;
  error?: string;
  session: { model: string };
  stats: { cost_usd: number; input_tokens: number; output_tokens: number; duration_ms: number };
  session_id?: string;
}

export interface Issue {
  schema_version: number;
  id: string;
  created_at: string;
  updated_at: string;
  status: string;
  summary: string;
  repository: string;
  refs: Ref[];
  runs: AgentRun[];
  plan?: { content: string; generated_at: string; model: string; cwd: string };
  error?: string;
}

export interface Source {
  id: string;
  type: string;
  owner: string;
  repo: string;
  created_at: string;
  token: string;
  active: boolean;
  last_polled_at?: string;
}

export type IssueStatus = "new" | "planned" | "approved" | "implemented" | "ci_passed" | "deployed" | "done" | "failed" | "canceled";

export const STATUS_COLOR: Record<string, string> = {
  new: "default",
  planned: "processing",
  approved: "cyan",
  implemented: "blue",
  ci_passed: "green",
  deployed: "purple",
  done: "success",
  failed: "error",
  canceled: "default",
};
