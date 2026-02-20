import { useCallback, useEffect, useState } from "react";
import { Table, Button, Modal, Input, Spin, Flex, App, Switch, theme } from "antd";
import { DeleteOutlined, EditOutlined } from "@ant-design/icons";
import { formatDateTime } from "../../utils/format";
import { apiFetch, apiPost, apiPatch, apiDelete } from "../../utils/api";
import type { Source } from "../../types";

export const SourceList = () => {
  const { message, modal } = App.useApp();
  const { token: designToken } = theme.useToken();
  const [data, setData] = useState<Source[]>([]);
  const [loading, setLoading] = useState(true);
  const [modalOpen, setModalOpen] = useState(false);
  const [owner, setOwner] = useState("");
  const [repo, setRepo] = useState("");
  const [pat, setPat] = useState("");
  const [refreshKey, setRefreshKey] = useState(0);
  const [editTokenId, setEditTokenId] = useState<string | null>(null);
  const [editTokenValue, setEditTokenValue] = useState("");

  const POLL_INTERVAL = 30_000;

  const fetchList = useCallback(() => {
    apiFetch<Source[]>("/api/sources")
      .then(setData)
      .finally(() => setLoading(false));
  }, []);

  const reload = useCallback(() => setRefreshKey((k) => k + 1), []);

  useEffect(() => {
    apiPost("/api/sources/sync").then(fetchList).catch(fetchList);
  }, [refreshKey, fetchList]);

  useEffect(() => {
    const id = setInterval(() => {
      apiPost("/api/sources/sync").then(fetchList).catch(fetchList);
    }, POLL_INTERVAL);
    return () => clearInterval(id);
  }, [fetchList]);

  const handleAdd = async () => {
    try {
      await apiPost("/api/sources", { type: "github", owner, repo, token: pat });
      message.success("Source added.");
      setModalOpen(false);
      setOwner("");
      setRepo("");
      setPat("");
      reload();
    } catch (e) {
      const msg = e instanceof Error ? e.message : "Failed to add source.";
      if (msg.includes("409")) {
        message.warning("This source already exists.");
      } else {
        message.error("Failed to add source.");
      }
    }
  };

  const handleUpdateToken = async () => {
    if (!editTokenId) return;
    try {
      await apiPatch(`/api/sources/${editTokenId}`, { token: editTokenValue });
      message.success("Token updated.");
      setEditTokenId(null);
      setEditTokenValue("");
      reload();
    } catch {
      message.error("Failed to update token.");
    }
  };

  const handleToggleActive = async (id: string, active: boolean) => {
    try {
      await apiPatch(`/api/sources/${id}`, { active });
      reload();
    } catch {
      message.error("Failed to update status.");
    }
  };

  const handleDelete = (id: string) => {
    modal.confirm({
      title: "Delete source",
      content: "Are you sure you want to delete this source?",
      okText: "Delete",
      okType: "danger",
      cancelText: "Cancel",
      onOk: async () => {
        try {
          await apiDelete(`/api/sources/${id}`);
          message.success("Source deleted.");
          reload();
        } catch {
          message.error("Failed to delete source.");
        }
      },
    });
  };

  if (loading) return <Spin />;

  return (
    <>
      <Flex justify="flex-end" style={{ marginBottom: designToken.marginMD }}>
        <Button type="primary" onClick={() => setModalOpen(true)}>
          Add Source
        </Button>
      </Flex>
      <Table dataSource={data} rowKey="id" size="small" bordered pagination={false} scroll={{ x: "max-content" }}>
        <Table.Column
          title="Active"
          render={(_, record: Source) => (
            <Switch
              size="small"
              checked={record.active}
              onChange={(checked) => handleToggleActive(record.id, checked)}
            />
          )}
        />
        <Table.Column title="Type" dataIndex="type" />
        <Table.Column title="Owner" dataIndex="owner" />
        <Table.Column title="Repo" dataIndex="repo" />
        <Table.Column
          title="Token"
          dataIndex="token"
          render={(token: string, record: Source) => (
            <Flex align="center" gap={designToken.marginXXS}>
              <span>{token || "-"}</span>
              <Button
                type="text"
                size="small"
                icon={<EditOutlined />}
                onClick={() => {
                  setEditTokenId(record.id);
                  setEditTokenValue("");
                }}
              />
            </Flex>
          )}
        />
        <Table.Column
          title="Last Polled"
          dataIndex="last_polled_at"
          render={(v: string) => (v ? formatDateTime(v) : "-")}
        />
        <Table.Column
          title=""
          align="center"
          render={(_, record: Source) => (
            <Button
              type="text"
              size="small"
              danger
              icon={<DeleteOutlined />}
              onClick={() => handleDelete(record.id)}
            />
          )}
        />
      </Table>
      <Modal
        title="Add Source"
        open={modalOpen}
        onOk={handleAdd}
        onCancel={() => setModalOpen(false)}
        okText="Add"
        cancelText="Cancel"
        okButtonProps={{ disabled: !owner || !repo }}
      >
        <Flex vertical gap={designToken.marginXS} style={{ marginTop: designToken.marginMD }}>
          <Input placeholder="Owner (e.g. jakeraft)" value={owner} onChange={(e) => setOwner(e.target.value)} />
          <Input placeholder="Repo (e.g. jakeops)" value={repo} onChange={(e) => setRepo(e.target.value)} />
          <Input.Password
            placeholder="GitHub PAT (optional)"
            value={pat}
            onChange={(e) => setPat(e.target.value)}
          />
        </Flex>
      </Modal>
      <Modal
        title="Update Token"
        open={editTokenId !== null}
        onOk={handleUpdateToken}
        onCancel={() => setEditTokenId(null)}
        okText="Update"
        cancelText="Cancel"
        okButtonProps={{ disabled: !editTokenValue }}
      >
        <Flex vertical gap={designToken.marginXS} style={{ marginTop: designToken.marginMD }}>
          <Input.Password
            placeholder="New GitHub PAT"
            value={editTokenValue}
            onChange={(e) => setEditTokenValue(e.target.value)}
          />
        </Flex>
      </Modal>
    </>
  );
};
