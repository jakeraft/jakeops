import { useState } from "react";
import { Card, Tag, Button, Space, Row, Col, Select, Typography, theme } from "antd";
import type { Ref } from "../../types";

export interface PipelineIssue {
  id: string;
  summary: string;
  status: string;
  repository: string;
  refs: Ref[];
}

const STATUS_COLUMNS = [
  { key: "new", label: "New", color: "default" },
  { key: "planned", label: "Planned", color: "processing" },
  { key: "approved", label: "Approved", color: "cyan" },
  { key: "implemented", label: "Implemented", color: "blue" },
  { key: "ci_passed", label: "CI Passed", color: "green" },
  { key: "deployed", label: "Deployed", color: "purple" },
  { key: "done", label: "Done", color: "success" },
  { key: "failed", label: "Failed", color: "error" },
] as const;

interface Props {
  issues: PipelineIssue[];
  onAction: (id: string, action: string) => void;
}

export const PipelineKanban = ({ issues, onAction }: Props) => {
  const { token } = theme.useToken();
  const [repoFilter, setRepoFilter] = useState<string | undefined>(undefined);

  const repos = [...new Set(issues.map((r) => r.repository))];
  const filtered = repoFilter
    ? issues.filter((r) => r.repository === repoFilter)
    : issues;

  return (
    <div style={{ display: "flex", flexDirection: "column", gap: token.marginSM }}>
      <Select
        allowClear
        placeholder="Filter by repository"
        value={repoFilter}
        onChange={setRepoFilter}
        options={repos.map((r) => ({ label: r, value: r }))}
        style={{ maxWidth: 300 }}
      />
      <div style={{ overflowX: "auto" }}>
        <Row gutter={[token.marginXS, token.marginXS]} wrap={false}>
          {STATUS_COLUMNS.map((col) => {
            const items = filtered.filter((r) => r.status === col.key);
            return (
              <Col key={col.key} flex="1 1 0" style={{ minWidth: 180 }}>
                <Card
                  size="small"
                  title={
                    <>
                      <Tag color={col.color}>{col.label}</Tag>
                      <Typography.Text type="secondary">{items.length}</Typography.Text>
                    </>
                  }
                  styles={{
                    body: {
                      display: "flex",
                      flexDirection: "column",
                      gap: token.marginXS,
                    },
                  }}
                >
                  {items.map((r) => {
                    const repoShort = r.repository.split("/").pop();
                    const issueRef = r.refs.find((ref) => ref.type === "github_issue");
                    const prRef = r.refs.find((ref) => ref.type === "pull_request");

                    return (
                      <Card key={r.id} size="small" hoverable>
                        <Space direction="vertical" size="small" style={{ width: "100%" }}>
                          <Space>
                            <Tag>{repoShort}</Tag>
                            {issueRef && (
                              <a href={issueRef.url} target="_blank" rel="noreferrer">
                                {issueRef.label}
                              </a>
                            )}
                          </Space>
                          <Typography.Text ellipsis style={{ fontSize: token.fontSizeSM }}>
                            {r.summary}
                          </Typography.Text>
                          {prRef && (
                            <a
                              href={prRef.url}
                              target="_blank"
                              rel="noreferrer"
                              style={{ fontSize: token.fontSizeSM }}
                            >
                              PR: {prRef.label}
                            </a>
                          )}
                          {r.status === "new" && (
                            <Button
                              size="small"
                              type="primary"
                              onClick={() => onAction(r.id, "generate-plan")}
                            >
                              Generate Plan
                            </Button>
                          )}
                          {r.status === "planned" && (
                            <Space size="small">
                              <Button
                                size="small"
                                type="primary"
                                onClick={() => onAction(r.id, "approve")}
                              >
                                Approve
                              </Button>
                              <Button
                                size="small"
                                danger
                                onClick={() => onAction(r.id, "reject")}
                              >
                                Reject
                              </Button>
                            </Space>
                          )}
                          {r.status === "failed" && (
                            <Button
                              size="small"
                              type="primary"
                              onClick={() => onAction(r.id, "retry")}
                            >
                              Retry
                            </Button>
                          )}
                        </Space>
                      </Card>
                    );
                  })}
                  {items.length === 0 && (
                    <Typography.Text type="secondary" style={{ fontSize: token.fontSizeSM }}>
                      None
                    </Typography.Text>
                  )}
                </Card>
              </Col>
            );
          })}
        </Row>
      </div>
    </div>
  );
};
