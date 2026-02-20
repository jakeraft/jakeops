import { useEffect, useState, useCallback } from "react";
import { App, Spin, theme } from "antd";
import { WorkerStatusCards, type WorkerInfo } from "./WorkerStatusCards";
import { PipelineKanban, type PipelineIssue } from "./PipelineKanban";
import { apiFetch, apiPost } from "../../utils/api";

const POLL_INTERVAL = 30_000;

export const WorkerPage = () => {
  const { token } = theme.useToken();
  const { message } = App.useApp();
  const [workers, setWorkers] = useState<WorkerInfo[]>([]);
  const [issues, setIssues] = useState<PipelineIssue[]>([]);
  const [loading, setLoading] = useState(true);

  const fetchAll = useCallback(() => {
    Promise.all([
      apiFetch<{ workers: WorkerInfo[] }>("/api/worker/status"),
      apiFetch<PipelineIssue[]>("/api/issues"),
    ])
      .then(([ws, is]) => {
        setWorkers(ws.workers);
        const pipeline = is.filter((i) =>
          i.refs?.some((ref) => ref.type === "github_issue"),
        );
        setIssues(pipeline);
      })
      .catch(() => message.error("Failed to fetch data."))
      .finally(() => setLoading(false));
  }, [message]);

  useEffect(() => {
    fetchAll();
    const id = setInterval(fetchAll, POLL_INTERVAL);
    return () => clearInterval(id);
  }, [fetchAll]);

  const handleAction = (issueId: string, action: string) => {
    apiPost(`/api/issues/${issueId}/${action}`)
      .then(() => fetchAll())
      .catch(() => message.error("Failed to execute action."));
  };

  if (loading) return <Spin />;

  return (
    <div style={{ display: "flex", flexDirection: "column", gap: token.marginMD }}>
      <WorkerStatusCards workers={workers} />
      <PipelineKanban issues={issues} onAction={handleAction} />
    </div>
  );
};
