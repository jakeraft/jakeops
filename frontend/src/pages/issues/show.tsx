import { useEffect, useState } from "react";
import { useParams } from "react-router";
import { Spin, Descriptions, Tabs, Typography, Button, Space, Tag, Timeline, theme, Modal, Input } from "antd";
import { CodeOutlined } from "@ant-design/icons";
import { formatDateTime } from "../../utils/format";
import { apiFetch, apiPost } from "../../utils/api";
import { STATUS_COLOR, type Issue, type AgentRun, type Ref } from "../../types";
import { messageToText, type TranscriptMessage } from "../../utils/transcript";

const RefList = ({ refs }: { refs: Ref[] }) => {
  if (refs.length === 0) return <>-</>;
  return (
    <>
      {refs.map((r, i) => (
        <span key={i}>
          {i > 0 && ", "}
          [{r.type}]{" "}
          {r.url ? (
            <a href={r.url} target="_blank" rel="noreferrer">
              {r.label}
            </a>
          ) : (
            r.label
          )}
        </span>
      ))}
    </>
  );
};

const RunTranscript = ({ issueId, runId }: { issueId: string; runId: string }) => {
  const { token } = theme.useToken();
  const [messages, setMessages] = useState<TranscriptMessage[] | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    apiFetch<TranscriptMessage[]>(`/api/issues/${issueId}/runs/${runId}/transcript`)
      .then(setMessages)
      .catch(() => setMessages(null))
      .finally(() => setLoading(false));
  }, [issueId, runId]);

  if (loading) return <Spin size="small" />;
  if (!messages) return <Typography.Text type="secondary">No transcript available.</Typography.Text>;

  return (
    <pre style={{
      whiteSpace: "pre-wrap",
      margin: 0,
      fontSize: token.fontSizeSM,
      maxHeight: 600,
      overflow: "auto",
    }}>
      {messages.map(messageToText).join("\n\n")}
    </pre>
  );
};

const RunTimeline = ({ runs, issueId }: { runs: AgentRun[]; issueId: string }) => {
  const { token } = theme.useToken();
  const [expandedRun, setExpandedRun] = useState<string | null>(null);

  if (runs.length === 0) {
    return <Typography.Text type="secondary">No runs yet.</Typography.Text>;
  }

  const sorted = [...runs].sort((a, b) => new Date(b.created_at).getTime() - new Date(a.created_at).getTime());

  return (
    <Timeline
      items={sorted.map((run) => ({
        color: run.status === "completed" ? "green" : run.status === "failed" ? "red" : "blue",
        children: (
          <div style={{ display: "flex", flexDirection: "column", gap: token.marginXXS }}>
            <Space>
              <Tag color={run.status === "completed" ? "success" : run.status === "failed" ? "error" : "processing"}>
                {run.status}
              </Tag>
              <Typography.Text type="secondary">{run.mode}</Typography.Text>
              <Typography.Text type="secondary">{formatDateTime(run.created_at)}</Typography.Text>
            </Space>
            {run.summary && <Typography.Text>{run.summary}</Typography.Text>}
            {run.error && <Typography.Text type="danger">{run.error}</Typography.Text>}
            <Space>
              <Typography.Text type="secondary" style={{ fontSize: token.fontSizeSM }}>
                {run.session.model} | ${run.stats.cost_usd.toFixed(4)} | {(run.stats.duration_ms / 1000).toFixed(1)}s
              </Typography.Text>
              <Button type="link" size="small" onClick={() => setExpandedRun(expandedRun === run.id ? null : run.id)}>
                {expandedRun === run.id ? "Hide" : "Transcript"}
              </Button>
            </Space>
            {expandedRun === run.id && <RunTranscript issueId={issueId} runId={run.id} />}
          </div>
        ),
      }))}
    />
  );
};

export const IssueShow = () => {
  const { id } = useParams();
  const [record, setRecord] = useState<Issue | null>(null);
  const [loading, setLoading] = useState(true);
  const [actionLoading, setActionLoading] = useState(false);
  const [collectModalOpen, setCollectModalOpen] = useState(false);

  const refetchIssue = () => {
    if (!id) return;
    apiFetch<Issue>(`/api/issues/${id}`).then(setRecord);
  };

  const gateAction = (action: string) => {
    if (!id) return;
    setActionLoading(true);
    apiPost(`/api/issues/${id}/${action}`)
      .then(() => refetchIssue())
      .finally(() => setActionLoading(false));
  };

  useEffect(() => {
    if (!id) return;
    apiFetch<Issue>(`/api/issues/${id}`)
      .then(setRecord)
      .finally(() => setLoading(false));
  }, [id]);

  if (loading) return <Spin />;
  if (!record) return null;

  const triggerRefs = record.refs.filter((r) => r.role === "trigger");
  const outputRefs = record.refs.filter((r) => r.role === "output");
  const prRefs = record.refs.filter((r) => r.role === "output" && r.type === "pull_request");

  return (
    <>
    <Tabs
      defaultActiveKey="ref"
      items={[
        {
          key: "ref",
          label: "References",
          children: (
            <Descriptions column={1} size="small" bordered>
              <Descriptions.Item label="Created">{formatDateTime(record.created_at)}</Descriptions.Item>
              <Descriptions.Item label="Summary">{record.summary}</Descriptions.Item>
              <Descriptions.Item label="Status">
                <Tag color={STATUS_COLOR[record.status] ?? "default"}>{record.status}</Tag>
              </Descriptions.Item>
              {record.error && (
                <Descriptions.Item label="Error">
                  <Typography.Text type="danger">{record.error}</Typography.Text>
                </Descriptions.Item>
              )}
              <Descriptions.Item label="Actions">
                <Space>
                  {record.status === "new" && (
                    <Button type="primary" loading={actionLoading} onClick={() => gateAction("generate-plan")}>
                      Generate Plan
                    </Button>
                  )}
                  {record.status === "planned" && (
                    <>
                      <Button type="primary" loading={actionLoading} onClick={() => gateAction("approve")}>
                        Approve
                      </Button>
                      <Button danger loading={actionLoading} onClick={() => gateAction("reject")}>
                        Reject
                      </Button>
                    </>
                  )}
                  {record.status === "approved" && (
                    <Button
                      icon={<CodeOutlined />}
                      onClick={() => setCollectModalOpen(true)}
                    >
                      Run Locally
                    </Button>
                  )}
                  {record.status === "ci_passed" && (
                    <>
                      <Button type="primary" loading={actionLoading} onClick={() => gateAction("approve")}>
                        Deploy
                      </Button>
                      <Button danger loading={actionLoading} onClick={() => gateAction("reject")}>
                        Reject
                      </Button>
                    </>
                  )}
                  {record.status === "deployed" && (
                    <>
                      <Button type="primary" loading={actionLoading} onClick={() => gateAction("approve")}>
                        Complete
                      </Button>
                      <Button danger loading={actionLoading} onClick={() => gateAction("reject")}>
                        Roll Back
                      </Button>
                    </>
                  )}
                  {record.status === "failed" && (
                    <Button type="primary" loading={actionLoading} onClick={() => gateAction("retry")}>
                      Retry
                    </Button>
                  )}
                  <Button loading={actionLoading} onClick={() => gateAction("cancel")}>
                    Cancel
                  </Button>
                </Space>
              </Descriptions.Item>
              <Descriptions.Item label="Repository">{record.repository}</Descriptions.Item>
              <Descriptions.Item label="Trigger">
                <RefList refs={triggerRefs} />
              </Descriptions.Item>
              {prRefs.length > 0 && (
                <Descriptions.Item label="Draft PR">
                  {prRefs.map((r, i) => (
                    <span key={i}>
                      {i > 0 && ", "}
                      <a href={r.url} target="_blank" rel="noreferrer" style={{ fontWeight: "bold" }}>
                        {r.label}
                      </a>
                    </span>
                  ))}
                </Descriptions.Item>
              )}
              <Descriptions.Item label="Output">
                <RefList refs={outputRefs} />
              </Descriptions.Item>
              <Descriptions.Item label="Model">{record.runs[0]?.session.model ?? "-"}</Descriptions.Item>
            </Descriptions>
          ),
        },
        {
          key: "plan",
          label: "Plan",
          children: record.plan ? (
            <Descriptions column={1} size="small" bordered>
              <Descriptions.Item label="Generated">{formatDateTime(record.plan.generated_at)}</Descriptions.Item>
              <Descriptions.Item label="Model">{record.plan.model}</Descriptions.Item>
              <Descriptions.Item label="CWD">{record.plan.cwd}</Descriptions.Item>
              <Descriptions.Item label="Content">
                <pre style={{ whiteSpace: "pre-wrap", margin: 0 }}>{record.plan.content}</pre>
              </Descriptions.Item>
            </Descriptions>
          ) : (
            <Typography.Text type="secondary">No plan available.</Typography.Text>
          ),
        },
        {
          key: "runs",
          label: "Run History",
          children: id ? <RunTimeline runs={record.runs} issueId={id} /> : null,
        },
      ]}
    />
    <Modal
      title="Run Locally"
      open={collectModalOpen}
      onCancel={() => setCollectModalOpen(false)}
      footer={null}
      width={640}
    >
      <Typography.Paragraph>
        Run the command below in your terminal.
        Results will be collected automatically after the Claude session exits.
      </Typography.Paragraph>
      <Input.TextArea
        readOnly
        autoSize
        value={`claude --resume SESSION_ID; curl -s -X POST ${window.location.origin}/api/issues/${id}/collect -H 'Content-Type: application/json' -d '{"session_id":"SESSION_ID"}'`}
        style={{ fontFamily: "monospace", fontSize: 12 }}
      />
      <Typography.Text type="secondary" style={{ display: "block", marginTop: 8 }}>
        Replace SESSION_ID with the session ID assigned during plan generation.
        Auto-fill support is planned.
      </Typography.Text>
    </Modal>
    </>
  );
};
