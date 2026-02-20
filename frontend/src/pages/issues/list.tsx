import { useEffect, useState } from "react";
import { Table, Spin, Tag } from "antd";
import { useNavigate } from "react-router";
import { formatDateTime } from "../../utils/format";
import { apiFetch } from "../../utils/api";
import { STATUS_COLOR, type Ref, type Issue } from "../../types";

type IssueItem = Pick<Issue, "id" | "summary" | "status" | "repository" | "created_at" | "refs">;

const RefLink = ({ refs, role, urlOnly }: { refs: Ref[]; role: string; urlOnly?: boolean }) => {
  const matched = refs.filter((r) => r.role === role);
  if (urlOnly) {
    const withUrl = matched.filter((r) => r.url);
    if (withUrl.length === 0) return <>-</>;
    return (
      <>
        {withUrl.map((r, i) => (
          <span key={i}>
            {i > 0 && ", "}
            <a href={r.url} target="_blank" rel="noreferrer" onClick={(e) => e.stopPropagation()}>
              {r.label}
            </a>
          </span>
        ))}
      </>
    );
  }
  if (matched.length === 0) return <>-</>;
  return (
    <>
      {matched.map((r, i) => (
        <span key={i}>
          {i > 0 && ", "}
          {r.url ? (
            <a href={r.url} target="_blank" rel="noreferrer" onClick={(e) => e.stopPropagation()}>
              {r.label}
            </a>
          ) : (
            r.type
          )}
        </span>
      ))}
    </>
  );
};

export const IssueList = () => {
  const navigate = useNavigate();
  const [data, setData] = useState<IssueItem[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    apiFetch<IssueItem[]>("/api/issues")
      .then(setData)
      .finally(() => setLoading(false));
  }, []);

  if (loading) return <Spin />;

  return (
    <Table
      dataSource={data}
      rowKey="id"
      size="small"
      bordered
      pagination={false}
      scroll={{ x: "max-content" }}
      onRow={(record) => ({
        onClick: () => navigate(`/issues/show/${record.id}`),
        style: { cursor: "pointer" },
      })}
    >
      <Table.Column title="Created" dataIndex="created_at" render={(v: string) => formatDateTime(v)} />
      <Table.Column title="Summary" dataIndex="summary" ellipsis />
      <Table.Column
        title="Status"
        dataIndex="status"
        filters={[
          { text: "new", value: "new" },
          { text: "planned", value: "planned" },
          { text: "approved", value: "approved" },
          { text: "implemented", value: "implemented" },
          { text: "ci_passed", value: "ci_passed" },
          { text: "deployed", value: "deployed" },
          { text: "done", value: "done" },
          { text: "failed", value: "failed" },
          { text: "canceled", value: "canceled" },
        ]}
        onFilter={(value, record) => (record as IssueItem).status === value}
        render={(s: string) => <Tag color={STATUS_COLOR[s] ?? "default"}>{s}</Tag>}
      />
      <Table.Column title="Repository" dataIndex="repository" />
      <Table.Column
        title="Trigger"
        dataIndex="refs"
        render={(refs: Ref[]) => <RefLink refs={refs ?? []} role="trigger" />}
      />
      <Table.Column
        title="Output"
        dataIndex="refs"
        render={(refs: Ref[]) => <RefLink refs={refs ?? []} role="output" />}
      />
    </Table>
  );
};
