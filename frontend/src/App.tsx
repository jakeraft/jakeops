import { useState } from "react";
import { BrowserRouter, Routes, Route, useNavigate, useLocation } from "react-router";
import { ConfigProvider, App as AntApp, Layout, Menu, Grid, theme } from "antd";
import { FileTextOutlined, GithubOutlined, RocketOutlined, MenuOutlined } from "@ant-design/icons";

import { IssueList } from "./pages/issues/list";
import { IssueShow } from "./pages/issues/show";
import { SourceList } from "./pages/sources/list";
import { WorkerPage } from "./pages/worker";

const pageTitles: Record<string, string> = {
  "/issues": "Issues",
  "/sources": "Sources",
  "/worker": "Runner Dashboard",
};

const AppLayout = () => {
  const navigate = useNavigate();
  const location = useLocation();
  const { token } = theme.useToken();
  const screens = Grid.useBreakpoint();
  const [collapsed, setCollapsed] = useState(false);

  const selectedKey = Object.keys(pageTitles).find((k) => location.pathname.startsWith(k)) ?? "/issues";
  const pageTitle = pageTitles[selectedKey] ?? "";

  return (
    <Layout style={{ minHeight: "100vh" }}>
      <Layout.Sider
        width={200}
        breakpoint="md"
        collapsedWidth={0}
        trigger={null}
        collapsed={collapsed}
        onBreakpoint={(broken) => setCollapsed(broken)}
      >
        <div
          style={{ height: 64, display: "flex", alignItems: "center", padding: "0 16px", cursor: "pointer" }}
          onClick={() => navigate("/issues")}
        >
          <span style={{ fontSize: token.fontSizeLG, fontWeight: 600, color: "rgba(255,255,255,0.85)" }}>jakeops</span>
        </div>
        <Menu
          theme="dark"
          mode="inline"
          selectedKeys={[selectedKey]}
          items={[
            { key: "/issues", icon: <FileTextOutlined />, label: "Issues" },
            { key: "/sources", icon: <GithubOutlined />, label: "Sources" },
            { key: "/worker", icon: <RocketOutlined />, label: "Runner" },
          ]}
          onClick={({ key }) => {
            navigate(key);
            if (!screens.md) setCollapsed(true);
          }}
        />
      </Layout.Sider>
      <Layout>
        <Layout.Header style={{ display: "flex", alignItems: "center", gap: token.marginXS }}>
          {collapsed && (
            <MenuOutlined
              onClick={() => setCollapsed(false)}
              style={{ color: "rgba(255,255,255,0.85)", fontSize: token.fontSizeLG }}
            />
          )}
          <span style={{ fontSize: token.fontSizeLG, fontWeight: 600, color: "rgba(255,255,255,0.85)" }}>{pageTitle}</span>
        </Layout.Header>
        <Layout.Content style={{ padding: token.paddingLG }}>
          <Routes>
            <Route index element={<IssueList />} />
            <Route path="/issues" element={<IssueList />} />
            <Route path="/issues/show/:id" element={<IssueShow />} />
            <Route path="/sources" element={<SourceList />} />
            <Route path="/worker" element={<WorkerPage />} />
          </Routes>
        </Layout.Content>
      </Layout>
    </Layout>
  );
};

function App() {
  return (
    <BrowserRouter>
      <ConfigProvider
        theme={{
          token: { borderRadius: 0, colorBorderSecondary: "#ccc" },
          components: {
            Layout: { bodyBg: "#fff", headerPadding: "0 24px" },
          },
        }}
      >
        <AntApp>
          <AppLayout />
        </AntApp>
      </ConfigProvider>
    </BrowserRouter>
  );
}

export default App;
