import { useState, useEffect } from 'react';
import { Outlet } from 'react-router-dom';
import { Layout, Menu, Button, theme } from 'antd';
import {
  DashboardOutlined,
  SearchOutlined,
  FileTextOutlined,
  SettingOutlined,
  LogoutOutlined,
  MenuFoldOutlined,
  MenuUnfoldOutlined,
} from '@ant-design/icons';
import { useNavigate, useLocation } from 'react-router-dom';
import { useAuth } from '../../hooks/useAuth';

const { Header, Sider, Content } = Layout;

export default function AppLayout() {
  const [collapsed, setCollapsed] = useState(false);
  const { user, isAuthenticated, logout, fetchMe } = useAuth();
  const navigate = useNavigate();
  const location = useLocation();
  const { token: themeToken } = theme.useToken();

  // Bug #1 修复: 页面刷新后恢复用户信息
  useEffect(() => {
    if (isAuthenticated && !user) {
      fetchMe();
    }
  }, [isAuthenticated, user, fetchMe]);

  const menuItems = [
    { key: '/', icon: <DashboardOutlined />, label: '仪表盘' },
    { key: '/predict/single', icon: <SearchOutlined />, label: '单条预测' },
    { key: '/predict/batch', icon: <FileTextOutlined />, label: '批量预测' },
    { key: '/cases', icon: <FileTextOutlined />, label: '案件管理' },
    ...(user?.user_role === 'admin'
      ? [{ key: '/admin', icon: <SettingOutlined />, label: '管理面板' }]
      : []),
  ];

  // Bug #2 修复: 使用完整路径匹配（非 split 首段），确保二级路由正确高亮
  const selectedKey = location.pathname;

  return (
    <Layout style={{ minHeight: '100vh' }}>
      <Sider trigger={null} collapsible collapsed={collapsed}>
        <div
          style={{
            height: 32,
            margin: 16,
            color: '#fff',
            fontWeight: 'bold',
            textAlign: 'center',
            lineHeight: '32px',
            overflow: 'hidden',
          }}
        >
          {collapsed ? '风控' : '医保风控系统'}
        </div>
        <Menu
          theme="dark"
          mode="inline"
          selectedKeys={[selectedKey]}
          items={menuItems}
          onClick={({ key }) => navigate(key)}
        />
      </Sider>
      <Layout>
        <Header
          style={{
            padding: '0 24px',
            background: themeToken.colorBgContainer,
            display: 'flex',
            justifyContent: 'space-between',
            alignItems: 'center',
          }}
        >
          <Button
            type="text"
            icon={collapsed ? <MenuUnfoldOutlined /> : <MenuFoldOutlined />}
            onClick={() => setCollapsed(!collapsed)}
          />
          <div>
            <span style={{ marginRight: 12 }}>{user?.display_name}</span>
            <Button
              type="text"
              icon={<LogoutOutlined />}
              onClick={logout}
            >
              退出
            </Button>
          </div>
        </Header>
        <Content style={{ margin: 24 }}>
          <Outlet />
        </Content>
      </Layout>
    </Layout>
  );
}
