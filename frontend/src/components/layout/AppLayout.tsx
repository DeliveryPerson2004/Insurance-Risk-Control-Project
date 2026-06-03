import { useEffect } from 'react';
import { Outlet } from 'react-router-dom';
import { Layout, Menu, Button } from 'antd';
import {
  DashboardOutlined,
  SearchOutlined,
  FileTextOutlined,
  SettingOutlined,
  LogoutOutlined,
} from '@ant-design/icons';
import { useNavigate, useLocation } from 'react-router-dom';
import { useAuth } from '../../hooks/useAuth';

const { Header, Sider, Content } = Layout;

export default function AppLayout() {
  const { user, isAuthenticated, logout, fetchMe } = useAuth();
  const navigate = useNavigate();
  const location = useLocation();

  // 页面刷新后恢复用户信息
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

  const selectedKey = location.pathname;

  return (
    <Layout style={{ minHeight: '100vh' }}>
      <Sider
        width={220}
        trigger={null}
        style={{
          background: '#EBE8E4',
          borderRight: '1px solid #D6D3D0',
        }}
      >
        <div
          style={{
            height: 48,
            margin: '16px 16px 8px',
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'center',
            fontWeight: 600,
            fontSize: 16,
            color: '#292524',
            letterSpacing: '-0.02em',
          }}
        >
          医保风控系统
        </div>
        <Menu
          mode="inline"
          selectedKeys={[selectedKey]}
          items={menuItems}
          onClick={({ key }) => navigate(key)}
          style={{
            background: 'transparent',
            borderInlineEnd: 'none',
          }}
        />
      </Sider>
      <Layout>
        <Header
          style={{
            padding: '0 24px',
            background: '#FAFAF9',
            display: 'flex',
            justifyContent: 'flex-end',
            alignItems: 'center',
            borderBottom: '1px solid #E7E5E2',
            height: 48,
            lineHeight: '48px',
          }}
        >
          <span style={{ marginRight: 16, fontSize: 13, color: '#44403C', fontWeight: 500 }}>
            {user?.display_name}
          </span>
          <Button
            type="text"
            icon={<LogoutOutlined />}
            onClick={logout}
            style={{ color: '#6B625D' }}
          >
            退出
          </Button>
        </Header>
        <Content style={{ padding: 32, background: '#FAFAF9' }}>
          <Outlet />
        </Content>
      </Layout>
    </Layout>
  );
}
