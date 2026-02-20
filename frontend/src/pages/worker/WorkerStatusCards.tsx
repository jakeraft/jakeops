import { Card, Row, Col, Tag, Typography, theme } from "antd";

export interface WorkerInfo {
  name: string;
  label: string;
  enabled: boolean;
  interval_sec: number;
  last_poll_at: string | null;
  last_result: Record<string, unknown> | null;
  last_error: string | null;
}

const formatTimeAgo = (iso: string | null): string => {
  if (!iso) return "-";
  const diff = Math.floor((Date.now() - new Date(iso).getTime()) / 1000);
  if (diff < 60) return `${diff}s ago`;
  if (diff < 3600) return `${Math.floor(diff / 60)}m ago`;
  return `${Math.floor(diff / 3600)}h ago`;
};

export const WorkerStatusCards = ({ workers }: { workers: WorkerInfo[] }) => {
  const { token } = theme.useToken();

  if (workers.length === 0) return null;

  return (
    <Row gutter={[token.marginSM, token.marginSM]}>
      {workers.map((w) => (
        <Col key={w.name} xs={24} sm={8}>
          <Card
            size="small"
            title={w.label}
            extra={
              w.enabled
                ? <Tag color="success">Running</Tag>
                : <Tag>Disabled</Tag>
            }
          >
            <Typography.Text type="secondary">
              Last poll: {formatTimeAgo(w.last_poll_at)}
            </Typography.Text>
            {w.last_result && (
              <div style={{ marginTop: token.marginXS }}>
                <Typography.Text>
                  Result: {JSON.stringify(w.last_result)}
                </Typography.Text>
              </div>
            )}
            {w.last_error && (
              <div style={{ marginTop: token.marginXS }}>
                <Typography.Text type="danger">
                  Error: {w.last_error}
                </Typography.Text>
              </div>
            )}
          </Card>
        </Col>
      ))}
    </Row>
  );
};
