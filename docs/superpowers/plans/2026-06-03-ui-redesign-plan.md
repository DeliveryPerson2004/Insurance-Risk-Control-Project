# UI 重设计 · 实施计划

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 将现有 Ant Design 默认风格系统替换为 Warm Slate + Olive 设计系统，纯视觉重构，无功能变更。

**Architecture:** 自底向上：先字体自托管 + 全局 Token（ConfigProvider theme + CSS 变量），再改布局骨架，最后逐页面重构。每页改动独立，无跨页依赖。

**Tech Stack:** React 18 + TypeScript + Ant Design 5 + @antv/g2 + Vite 5

---

## File Map

| 层 | 文件 | 职责 |
|----|------|------|
| 字体 | `public/fonts/inter-*.woff2` | Inter 自托管字体文件 |
| 全局 | `index.css` | @font-face + CSS 变量 + 全局重置 |
| 全局 | `App.tsx` | ConfigProvider theme token 注入 |
| 布局 | `AppLayout.tsx` | 侧边栏/Header/Content 骨架 |
| 仪表盘 | `DashboardPage.tsx` | Editorial 双栏布局 |
| 仪表盘 | `StatsCards.tsx` | 4 指标卡片 |
| 仪表盘 | `RiskTrendChart.tsx` | @antv/g2 趋势图 |
| 仪表盘 | `HighRiskTable.tsx` | 高风险案件表格 |
| 预测 | `PredictionPage.tsx` | 预测结果展示 |
| 预测 | `PredictionForm.tsx` | 2 列网格表单 |
| 批量 | `BatchPredictPage.tsx` | 批量预测页面 |
| 批量 | `BatchUpload.tsx` | 拖拽上传区 |
| 批量 | `BatchProgress.tsx` | 进度条 + 下载 |
| 案件 | `CaseListPage.tsx` | 筛选 + 列表 |
| 案件 | `CaseTable.tsx` | 案件表格 |
| 案件详情 | `CaseDetailPage.tsx` | 详情分区布局 |
| 案件详情 | `CaseDetail.tsx` | 子卡片组件 |
| 案件详情 | `AdjudicateModal.tsx` | 判定弹窗 |
| 管理 | `AdminPage.tsx` | Tab 容器 |
| 管理 | `UserManagement.tsx` | 用户表格 |
| 管理 | `DataUpload.tsx` | 数据上传 + 任务列表 |
| 通用 | `Skeleton.tsx` | 骨架屏 |
| 通用 | `EmptyState.tsx` | 空状态 |
| 通用 | `ErrorBoundary.tsx` | 错误边界 |

---

### Task 1: 下载 Inter 字体 (woff2)

**Files:**
- Create: `frontend/public/fonts/inter-latin-300.woff2`
- Create: `frontend/public/fonts/inter-latin-400.woff2`
- Create: `frontend/public/fonts/inter-latin-500.woff2`
- Create: `frontend/public/fonts/inter-latin-600.woff2`
- Create: `frontend/public/fonts/inter-latin-700.woff2`

- [ ] **Step 1: 从 Google Fonts CDN 下载 5 个 weight 的 woff2 文件**

从 https://fonts.google.com/download?family=Inter 下载 Inter 字体包，或使用 google-webfonts-helper (https://gwfh.mranftl.com/fonts/inter) 下载 latin subset 的 woff2 文件（300, 400, 500, 600, 700），放入 `frontend/public/fonts/`。

```bash
mkdir -p frontend/public/fonts
# 手动下载 5 个 woff2 文件到此目录，命名为:
# inter-latin-300.woff2
# inter-latin-400.woff2
# inter-latin-500.woff2
# inter-latin-600.woff2
# inter-latin-700.woff2
```

> 注：在中国大陆可访问 https://gwfh.mranftl.com/fonts/inter 下载，或从其他 CDN 镜像获取。

---

### Task 2: 全局 CSS 变量 + @font-face + 重置

**Files:**
- Modify: `frontend/src/index.css` (全文替换)

- [ ] **Step 1: 重写 index.css**

将 `frontend/src/index.css` 全文替换为：

```css
/* === Inter 自托管 === */
@font-face {
  font-family: 'Inter';
  font-style: normal;
  font-weight: 300;
  font-display: swap;
  src: url('/fonts/inter-latin-300.woff2') format('woff2');
}
@font-face {
  font-family: 'Inter';
  font-style: normal;
  font-weight: 400;
  font-display: swap;
  src: url('/fonts/inter-latin-400.woff2') format('woff2');
}
@font-face {
  font-family: 'Inter';
  font-style: normal;
  font-weight: 500;
  font-display: swap;
  src: url('/fonts/inter-latin-500.woff2') format('woff2');
}
@font-face {
  font-family: 'Inter';
  font-style: normal;
  font-weight: 600;
  font-display: swap;
  src: url('/fonts/inter-latin-600.woff2') format('woff2');
}
@font-face {
  font-family: 'Inter';
  font-style: normal;
  font-weight: 700;
  font-display: swap;
  src: url('/fonts/inter-latin-700.woff2') format('woff2');
}

/* === CSS 变量（作为非 Ant Design 场景的补充） === */
:root {
  --color-content-bg: #FAFAF9;
  --color-sidebar-bg: #EBE8E4;
  --color-surface: #FFFFFF;
  --color-border: #E7E5E2;
  --color-divider: #D6D3D0;
  --color-foreground: #292524;
  --color-secondary: #44403C;
  --color-muted: #6B625D;
  --color-placeholder: #A8A29E;
  --color-olive: #4A5630;
  --color-olive-hover: #3B4526;
  --color-olive-light: #EDF0E7;
  --color-danger: #DC2626;
  --color-danger-light: #FEF2F2;
  --color-warning: #947008;
  --color-warning-light: #FFF8EB;
  --color-success-surface: #F2F7ED;

  --font-family: 'Inter', system-ui, -apple-system, 'Microsoft YaHei', sans-serif;
  --radius: 6px;
  --radius-sm: 4px;
}

/* === 全局重置 === */
*,
*::before,
*::after {
  box-sizing: border-box;
}

body {
  margin: 0;
  font-family: var(--font-family);
  -webkit-font-smoothing: antialiased;
  -moz-osx-font-smoothing: grayscale;
  color: var(--color-foreground);
  background: var(--color-content-bg);
}

/* 全局 h2 重设计 */
h2 {
  font-family: var(--font-family);
  font-weight: 600;
  font-size: 24px;
  letter-spacing: -0.02em;
  color: var(--color-foreground);
  margin: 0 0 8px 0;
}

/* 全局 h4 重设计 */
h4 {
  font-family: var(--font-family);
  font-weight: 600;
  font-size: 14px;
  color: var(--color-secondary);
  margin: 0 0 12px 0;
}
```

- [ ] **Step 2: 提交**

```bash
git add frontend/src/index.css frontend/public/fonts/
git commit -m "feat: self-hosted Inter font + CSS variables + global reset"
```

---

### Task 3: ConfigProvider 全局 Theme Token

**Files:**
- Modify: `frontend/src/App.tsx`

- [ ] **Step 1: 替换 ConfigProvider theme 配置**

将 `App.tsx` 中的 ConfigProvider 的 `theme` prop 替换为完整的 design token：

```tsx
// 找到 App.tsx 第 50-57 行，替换 ConfigProvider 的 theme prop
<ConfigProvider
  locale={zhCN}
  theme={{
    token: {
      // 品牌色
      colorPrimary: '#4A5630',
      colorPrimaryHover: '#3B4526',
      colorPrimaryActive: '#3B4526',
      colorPrimaryBg: '#EDF0E7',
      colorPrimaryBgHover: '#E3E7DA',
      // 中性色
      colorText: '#292524',
      colorTextSecondary: '#44403C',
      colorTextTertiary: '#6B625D',
      colorTextQuaternary: '#A8A29E',
      colorBorder: '#E7E5E2',
      colorBorderSecondary: '#D6D3D0',
      colorFill: '#E7E5E2',
      colorFillSecondary: '#EDF0E7',
      colorFillTertiary: '#F5F3F0',
      colorFillQuaternary: '#FAFAF9',
      // 背景
      colorBgContainer: '#FFFFFF',
      colorBgElevated: '#FFFFFF',
      colorBgLayout: '#FAFAF9',
      colorBgSpotlight: '#292524',
      // 语义色
      colorSuccess: '#4A5630',
      colorWarning: '#947008',
      colorError: '#DC2626',
      colorInfo: '#6B625D',
      colorSuccessBg: '#F2F7ED',
      colorWarningBg: '#FFF8EB',
      colorErrorBg: '#FEF2F2',
      colorInfoBg: '#EDF0E7',
      colorSuccessBorder: '#4A5630',
      colorWarningBorder: '#947008',
      colorErrorBorder: '#DC2626',
      // 字体
      fontFamily: "'Inter', system-ui, -apple-system, 'Microsoft YaHei', sans-serif",
      fontSize: 14,
      fontSizeHeading1: 32,
      fontSizeHeading2: 24,
      fontSizeHeading3: 18,
      fontSizeHeading4: 16,
      fontSizeHeading5: 14,
      lineHeight: 1.6,
      // 圆角
      borderRadius: 6,
      borderRadiusLG: 8,
      borderRadiusSM: 4,
      // 阴影 (Ant Design 用 boxShadow 衍生)
      boxShadow: '0 1px 2px rgba(0,0,0,0.04)',
      boxShadowSecondary: '0 4px 12px rgba(0,0,0,0.08)',
      // 间距
      padding: 16,
      paddingLG: 24,
      paddingXS: 8,
      margin: 16,
      marginLG: 24,
      // 其他
      controlHeight: 36,
      controlHeightLG: 44,
      wireframe: false,
    },
    components: {
      Layout: {
        bodyBg: '#FAFAF9',
        headerBg: '#FAFAF9',
        siderBg: '#EBE8E4',
        triggerBg: '#EBE8E4',
        triggerColor: '#44403C',
      },
      Menu: {
        itemBg: 'transparent',
        itemColor: '#44403C',
        itemHoverBg: '#D6D3D0',
        itemSelectedBg: '#EDF0E7',
        itemSelectedColor: '#4A5630',
        subMenuItemBg: 'transparent',
      },
      Card: {
        paddingLG: 24,
      },
      Table: {
        headerBg: '#FAFAF9',
        headerColor: '#6B625D',
        rowHoverBg: '#EDF0E7',
        borderColor: '#E7E5E2',
      },
      Tag: {
        defaultBg: '#F5F3F0',
        defaultColor: '#44403C',
      },
      Tabs: {
        inkBarColor: '#4A5630',
        itemActiveColor: '#4A5630',
        itemHoverColor: '#3B4526',
        itemSelectedColor: '#4A5630',
      },
      Modal: {
        boxShadow: '0 8px 24px rgba(0,0,0,0.10)',
      },
    },
  }}
>
```

- [ ] **Step 2: 提交**

```bash
git add frontend/src/App.tsx
git commit -m "feat: apply Warm Slate + Olive theme tokens to ConfigProvider"
```

---

### Task 4: AppLayout 骨架重构

**Files:**
- Modify: `frontend/src/components/layout/AppLayout.tsx`

- [ ] **Step 1: 重写 AppLayout 为浅色侧边栏 + 干净 Header**

将 `AppLayout.tsx` 全文替换为：

```tsx
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
```


- [ ] **Step 2: 提交**

```bash
git add frontend/src/components/layout/AppLayout.tsx
git commit -m "refactor: light sidebar + clean header in Warm Slate style"
```

---

### Task 5: 通用组件重设计 (Skeleton, EmptyState, ErrorBoundary)

**Files:**
- Modify: `frontend/src/components/common/Skeleton.tsx`
- Modify: `frontend/src/components/common/EmptyState.tsx`
- Modify: `frontend/src/components/common/ErrorBoundary.tsx`

- [ ] **Step 5.1: Skeleton — 替换占位色**

以 `Skeleton.tsx` 的 `ChartSkeleton` 为例，将 `#fafafa` 替换为 `#F5F3F0`，`#ccc` 替换为 `#D6D3D0`：

```tsx
// ChartSkeleton 中的 background 和 color
<div
  style={{
    height,
    background: '#F5F3F0',
    borderRadius: 8,
    display: 'flex',
    alignItems: 'center',
    justifyContent: 'center',
    color: '#A8A29E',
    marginTop: 8,
  }}
>
  加载中...
</div>
```

其余 Skeleton 组件无需代码变更——ConfigProvider token 已自动接管 Ant Design Skeleton 的配色。

- [ ] **Step 5.2: EmptyState — 替换颜色**

```tsx
export default function EmptyState({ description = '暂无数据', image, action }: Props) {
  return (
    <Empty
      image={image || Empty.PRESENTED_IMAGE_SIMPLE}
      description={<span style={{ color: '#6B625D' }}>{description}</span>}
      style={{ padding: '60px 0' }}
    >
      {action}
    </Empty>
  );
}
```

- [ ] **Step 5.3: ErrorBoundary — 无需代码变更**

ConfigProvider token 自动接管 Result 组件的配色，无需修改。

- [ ] **Step 5.4: 提交**

```bash
git add frontend/src/components/common/
git commit -m "refactor: update Skeleton/EmptyState colors for Warm Slate"
```

---

### Task 6: 登录页重构

**Files:**
- Modify: `frontend/src/pages/LoginPage.tsx`

- [ ] **Step 1: 去掉紫色渐变，改为水平横幅布局**

将 `LoginPage.tsx` 全文替换为：

```tsx
import { useState } from 'react';
import { Button, Form, Input, message, Tabs } from 'antd';
import { UserOutlined, LockOutlined } from '@ant-design/icons';
import { useAuth } from '../hooks/useAuth';
import type { LoginRequest, RegisterRequest } from '../types';

export default function LoginPage() {
  const { login, register } = useAuth();
  const [loading, setLoading] = useState(false);
  const [activeTab, setActiveTab] = useState('login');

  const handleLogin = async (values: LoginRequest) => {
    setLoading(true);
    try {
      await login(values);
      message.success('登录成功');
    } catch (err: unknown) {
      const msg =
        (err as { response?: { data?: { message?: string } } })?.response?.data
          ?.message || '登录失败';
      message.error(msg);
    } finally {
      setLoading(false);
    }
  };

  const handleRegister = async (values: RegisterRequest) => {
    setLoading(true);
    try {
      await register(values);
      message.success('注册成功');
    } catch (err: unknown) {
      const msg =
        (err as { response?: { data?: { message?: string } } })?.response?.data
          ?.message || '注册失败';
      message.error(msg);
    } finally {
      setLoading(false);
    }
  };

  return (
    <div style={{
      minHeight: '100vh',
      display: 'flex',
      flexDirection: 'column',
      background: '#FAFAF9',
    }}>
      {/* 品牌条 */}
      <div style={{
        background: '#EBE8E4',
        textAlign: 'center',
        padding: '16px 24px',
        borderBottom: '1px solid #D6D3D0',
      }}>
        <div style={{
          fontSize: 18,
          fontWeight: 600,
          color: '#292524',
          letterSpacing: '-0.02em',
        }}>
          医疗保险欺诈检测系统
        </div>
      </div>

      {/* 表单区 */}
      <div style={{
        flex: 1,
        display: 'flex',
        justifyContent: 'center',
        alignItems: 'center',
        padding: 24,
      }}>
        <div style={{
          width: 400,
          background: '#FFFFFF',
          border: '1px solid #E7E5E2',
          borderRadius: 8,
          padding: 32,
          boxShadow: '0 1px 2px rgba(0,0,0,0.04)',
        }}>
          <Tabs
            activeKey={activeTab}
            onChange={setActiveTab}
            centered
            items={[
              {
                key: 'login',
                label: '登录',
                children: (
                  <Form onFinish={handleLogin} size="large">
                    <Form.Item name="username" rules={[{ required: true, message: '请输入用户名' }]}>
                      <Input prefix={<UserOutlined />} placeholder="用户名" />
                    </Form.Item>
                    <Form.Item name="password" rules={[{ required: true, message: '请输入密码' }]}>
                      <Input.Password prefix={<LockOutlined />} placeholder="密码" />
                    </Form.Item>
                    <Form.Item>
                      <Button type="primary" htmlType="submit" loading={loading} block>
                        登录
                      </Button>
                    </Form.Item>
                  </Form>
                ),
              },
              {
                key: 'register',
                label: '注册',
                children: (
                  <Form onFinish={handleRegister} size="large">
                    <Form.Item name="username" rules={[{ required: true, message: '请输入用户名' }]}>
                      <Input prefix={<UserOutlined />} placeholder="用户名" />
                    </Form.Item>
                    <Form.Item name="password" rules={[{ required: true, min: 6, message: '密码至少6位' }]}>
                      <Input.Password prefix={<LockOutlined />} placeholder="密码" />
                    </Form.Item>
                    <Form.Item name="display_name">
                      <Input placeholder="显示名称（可选）" />
                    </Form.Item>
                    <Form.Item>
                      <Button type="primary" htmlType="submit" loading={loading} block>
                        注册
                      </Button>
                    </Form.Item>
                  </Form>
                ),
              },
            ]}
          />
        </div>
      </div>
    </div>
  );
}
```

- [ ] **Step 2: 提交**

```bash
git add frontend/src/pages/LoginPage.tsx
git commit -m "refactor: login page — horizontal banner + card, remove purple gradient"
```

---

### Task 7: 仪表盘重构

**Files:**
- Modify: `frontend/src/pages/DashboardPage.tsx`
- Modify: `frontend/src/components/dashboard/StatsCards.tsx`
- Modify: `frontend/src/components/dashboard/RiskTrendChart.tsx`
- Modify: `frontend/src/components/dashboard/HighRiskTable.tsx`

- [ ] **Step 7.1: DashboardPage — Editorial 双栏布局 (Spec 对齐)**

将 `DashboardPage.tsx` 全文替换为：

```tsx
import { useEffect, useState } from 'react';
import StatsCards from '../components/dashboard/StatsCards';
import RiskTrendChart from '../components/dashboard/RiskTrendChart';
import HighRiskTable from '../components/dashboard/HighRiskTable';

function DateHeader() {
  const [dateStr, setDateStr] = useState('');
  useEffect(() => {
    const today = new Date();
    const weekdays = ['星期日', '星期一', '星期二', '星期三', '星期四', '星期五', '星期六'];
    setDateStr(`${today.getFullYear()}-${String(today.getMonth() + 1).padStart(2, '0')}-${String(today.getDate()).padStart(2, '0')} · ${weekdays[today.getDay()]}`);
  }, []);
  return <span style={{ color: '#A8A29E' }}>{dateStr}</span>;
}

export default function DashboardPage() {
  return (
    <div>
      <h2>Dashboard</h2>
      <p style={{ color: '#6B625D', fontSize: 13, marginBottom: 24 }}>
        欺诈检测概览 · <DateHeader />
      </p>

      {/* 核心区: 趋势图 60% + 右侧 4 卡片 40% */}
      <div style={{ display: 'flex', gap: 12, marginBottom: 24 }}>
        <div style={{
          flex: '60%',
          background: '#FFFFFF',
          border: '1px solid #E7E5E2',
          borderRadius: 6,
          padding: '20px 24px',
          boxShadow: '0 1px 2px rgba(0,0,0,0.04)',
        }}>
          <RiskTrendChart />
        </div>
        <div style={{ flex: '40%' }}>
          <StatsCards />
        </div>
      </div>

      {/* 高风险表格 — 全宽 */}
      <div>
        <HighRiskTable />
      </div>
    </div>
  );
}
```

- [ ] **Step 7.2: StatsCards — 4 指标右侧竖排**

将 `StatsCards.tsx` 全文替换为：

```tsx
import { useEffect, useState } from 'react';
import type { CSSProperties } from 'react';
import {
  ClockCircleOutlined,
  WarningOutlined,
  CheckCircleOutlined,
  DatabaseOutlined,
} from '@ant-design/icons';
import { fetchStats } from '../../api/dashboard';
import type { DashboardStats } from '../../types';
import { CardSkeleton } from '../common/Skeleton';

const CARD_STYLE: CSSProperties = {
  background: '#FFFFFF',
  border: '1px solid #E7E5E2',
  borderRadius: 6,
  padding: '16px 20px',
  boxShadow: '0 1px 2px rgba(0,0,0,0.04)',
};

const statProps = (color: string) => ({
  valueStyle: {
    fontSize: 28,
    fontWeight: 600 as const,
    color,
    fontFamily: "'Inter', sans-serif",
    fontFeatureSettings: "'tnum'",
  },
});

const titleStyle: CSSProperties = { fontSize: 12, color: '#6B625D', fontWeight: 400 };

export default function StatsCards() {
  const [stats, setStats] = useState<DashboardStats | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    fetchStats().then(setStats).catch(() => {}).finally(() => setLoading(false));
    const interval = setInterval(() => { fetchStats().then(setStats).catch(() => {}); }, 60_000);
    return () => clearInterval(interval);
  }, []);

  if (loading) return <CardSkeleton count={4} />;

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: 12, height: '100%' }}>
      <div style={{ flex: 1, ...CARD_STYLE }}>
        <div style={titleStyle}>待审核</div>
        <div style={{ fontSize: 32, fontWeight: 600, color: '#292524', fontFeatureSettings: "'tnum'", marginTop: 4 }}>
          <ClockCircleOutlined style={{ fontSize: 18, color: '#6B625D', marginRight: 8 }} />
          {stats?.today_pending ?? 0}
        </div>
      </div>
      <div style={{ flex: 1, ...CARD_STYLE, borderLeft: '3px solid #DC2626' }}>
        <div style={titleStyle}>高风险</div>
        <div style={{ fontSize: 32, fontWeight: 600, color: '#DC2626', fontFeatureSettings: "'tnum'", marginTop: 4 }}>
          <WarningOutlined style={{ fontSize: 18, color: '#DC2626', marginRight: 8 }} />
          {stats?.today_high_risk ?? 0}
        </div>
      </div>
      <div style={{ flex: 1, ...CARD_STYLE }}>
        <div style={titleStyle}>已处理</div>
        <div style={{ fontSize: 28, fontWeight: 600, color: '#292524', fontFeatureSettings: "'tnum'", marginTop: 4 }}>
          <CheckCircleOutlined style={{ fontSize: 16, color: '#4A5630', marginRight: 8 }} />
          {stats?.today_processed ?? 0}
        </div>
      </div>
      <div style={{ flex: 1, ...CARD_STYLE }}>
        <div style={titleStyle}>累计检测量</div>
        <div style={{ fontSize: 28, fontWeight: 600, color: '#292524', fontFeatureSettings: "'tnum'", marginTop: 4 }}>
          <DatabaseOutlined style={{ fontSize: 16, color: '#6B625D', marginRight: 8 }} />
          {stats?.total_detected ?? 0}
        </div>
      </div>
    </div>
  );
}
```

- [ ] **Step 7.3: HighRiskTable — 概率纯数字 + 颜色**

将 `HighRiskTable.tsx` 全文替换为：

```tsx
import { useEffect, useState } from 'react';
import { Table } from 'antd';
import type { ColumnsType } from 'antd/es/table';
import { fetchHighRisk } from '../../api/dashboard';
import type { HighRiskItem } from '../../types';
import { TableSkeleton } from '../common/Skeleton';

const probColor = (v: number): string => {
  if (v >= 0.7) return '#DC2626';
  if (v >= 0.3) return '#947008';
  return '#4A5630';
};

const columns: ColumnsType<HighRiskItem> = [
  {
    title: '案件ID',
    dataIndex: 'policy_id',
    key: 'policy_id',
    width: 180,
    render: (v: string) => <span style={{ fontFamily: "'Inter', sans-serif", fontWeight: 500 }}>{v}</span>,
  },
  {
    title: '欺诈概率',
    dataIndex: 'fraud_prob',
    key: 'fraud_prob',
    width: 100,
    render: (v: number) => (
      <span style={{ fontWeight: 600, color: probColor(v), fontFamily: "'Inter', sans-serif", fontFeatureSettings: "'tnum'" }}>
        {(v * 100).toFixed(1)}%
      </span>
    ),
  },
  {
    title: '风险等级',
    dataIndex: 'risk_level',
    key: 'risk_level',
    width: 80,
    render: (v: string) => {
      const color = v === 'high' ? '#DC2626' : '#947008';
      return (
        <span style={{ display: 'inline-flex', alignItems: 'center', gap: 4, fontSize: 12 }}>
          <span style={{ width: 6, height: 6, borderRadius: '50%', background: color, display: 'inline-block' }} />
          <span style={{ color }}>{v === 'high' ? '高风险' : '中风险'}</span>
        </span>
      );
    },
  },
  {
    title: '理赔金额',
    dataIndex: 'claim_amount',
    key: 'claim_amount',
    width: 100,
    render: (v: number | null) => (
      <span style={{ fontFamily: "'Inter', sans-serif", fontFeatureSettings: "'tnum'" }}>
        {v != null ? `¥${v.toLocaleString()}` : '-'}
      </span>
    ),
  },
];

export default function HighRiskTable() {
  const [items, setItems] = useState<HighRiskItem[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    fetchHighRisk(5)
      .then(setItems)
      .catch(() => {})
      .finally(() => setLoading(false));

    const interval = setInterval(() => {
      fetchHighRisk(5).then(setItems).catch(() => {});
    }, 60_000);
    return () => clearInterval(interval);
  }, []);

  return (
    <div style={{
      background: '#FFFFFF',
      border: '1px solid #E7E5E2',
      borderRadius: 6,
      padding: '20px 24px',
      boxShadow: '0 1px 2px rgba(0,0,0,0.04)',
    }}>
      <h4 style={{ marginBottom: 16 }}>高风险案件 Top 5</h4>
      {loading ? (
        <TableSkeleton rows={5} />
      ) : (
        <Table
          columns={columns}
          dataSource={items}
          rowKey="id"
          size="small"
          pagination={false}
        />
      )}
    </div>
  );
}
```

- [ ] **Step 7.4: RiskTrendChart — 更新 G2 图表的颜色**

修改 `RiskTrendChart.tsx` 中的两处硬编码颜色：

```tsx
// 第 44 行: .style('fill', '#1677ff') 改为
.style('fill', '#4A5630')

// 第 56 行: .style('stroke', '#ff4d4f') 改为
.style('stroke', '#DC2626')
```

同时也更新标题区域的样式（第 79 行）：
```tsx
<span style={{ fontWeight: 600, fontSize: 14, color: '#292524' }}>
```

去掉 `#666` 的硬编码颜色。

- [ ] **Step 7.5: 提交**

```bash
git add frontend/src/pages/DashboardPage.tsx frontend/src/components/dashboard/
git commit -m "refactor: dashboard — editorial 60/40 layout, 4 metrics, olive+red colors"
```

---

### Task 8: 单条预测重构

**Files:**
- Modify: `frontend/src/components/predict/PredictionForm.tsx`
- Modify: `frontend/src/pages/PredictionPage.tsx`

- [ ] **Step 8.1: PredictionForm — 去掉折叠/向导，改为 2 列网格**

将 `PredictionForm.tsx` 全文替换为：

```tsx
import { useState, useEffect, useCallback } from 'react';
import { Form, Select, InputNumber, Input, Button, message, Spin, Row, Col } from 'antd';
import type { FieldOption } from '../../types';
import { getFieldOptions } from '../../api/predict';

interface Props {
  onResult: (result: any) => void;
  loading: boolean;
}

export default function PredictionForm({ onResult, loading }: Props) {
  const [form] = Form.useForm();
  const [fields, setFields] = useState<FieldOption[]>([]);
  const [groups, setGroups] = useState<string[]>([]);
  const [fetching, setFetching] = useState(true);

  useEffect(() => {
    getFieldOptions()
      .then((data) => {
        setFields(data.fields);
        setGroups(data.groups);
      })
      .catch(() => message.error('获取字段配置失败'))
      .finally(() => setFetching(false));
  }, []);

  const getFieldsByGroup = useCallback(
    (group: string) => fields.filter((f) => f.group === group),
    [fields],
  );

  const renderField = (field: FieldOption) => {
    const normOptions = (field.options || []).map((o) =>
      typeof o === 'string' ? { value: o, label: o } : o,
    );

    if (field.type === 'select') {
      return (
        <Form.Item
          key={field.name}
          name={field.name}
          label={<span style={{ fontSize: 12, color: '#6B625D' }}>{field.label}</span>}
          rules={[{ required: field.required, message: `请选择${field.label}` }]}
        >
          <Select
            showSearch
            placeholder={field.placeholder || `请选择${field.label}`}
            options={normOptions}
          />
        </Form.Item>
      );
    }

    // field.type === 'number' — InputNumber
    return (
      <Form.Item
        key={field.name}
        name={field.name}
        label={<span style={{ fontSize: 12, color: '#6B625D' }}>{field.label}</span>}
        rules={[{ required: field.required, message: `请输入${field.label}` }]}
      >
        <InputNumber
          style={{ width: '100%' }}
          min={field.min}
          max={field.max}
          step={field.step}
          placeholder={field.placeholder}
        />
      </Form.Item>
    );
  };

  if (fetching) {
    return <Spin tip="加载字段配置..." style={{ display: 'block', textAlign: 'center', padding: 48 }} />;
  }

  return (
    <Form
      form={form}
      layout="vertical"
      onFinish={(values) => onResult(values)}
    >
      {/* 被保险人 ID — 全宽 */}
      <div style={{
        background: '#FFFFFF',
        border: '1px solid #E7E5E2',
        borderRadius: 6,
        padding: '16px 24px',
        marginBottom: 16,
      }}>
        <Form.Item
          name="insuree_id"
          label={<span style={{ fontSize: 12, color: '#6B625D' }}>被保险人 ID</span>}
          rules={[{ required: true, message: '请输入被保险人 ID' }]}
          style={{ marginBottom: 0 }}
        >
          <Input placeholder="请输入被保险人 ID" />
        </Form.Item>
      </div>

      {/* 字段分组 — 2 列网格 */}
      <Row gutter={[16, 0]}>
        {groups.map((group) => (
          <Col span={12} key={group}>
            <div style={{
              background: '#FFFFFF',
              border: '1px solid #E7E5E2',
              borderRadius: 6,
              padding: '16px 24px',
              marginBottom: 16,
            }}>
              <h4 style={{ marginBottom: 12 }}>
                {group}
                <span style={{ fontWeight: 400, fontSize: 11, color: '#A8A29E', marginLeft: 8 }}>
                  {getFieldsByGroup(group).length} 字段
                </span>
              </h4>
              {getFieldsByGroup(group).map(renderField)}
            </div>
          </Col>
        ))}
      </Row>

      {/* 操作按钮 */}
      <div style={{ display: 'flex', justifyContent: 'flex-end', gap: 12, marginTop: 8 }}>
        <Button onClick={() => form.resetFields()}>重置</Button>
        <Button type="primary" htmlType="submit" loading={loading}>
          提交预测
        </Button>
      </div>
    </Form>
  );
}
```

- [ ] **Step 8.2: PredictionPage — 去掉硬编码颜色 + 删除 Phase 3 过期占位按钮**

将 `PredictionPage.tsx` 全文替换为：

```tsx
import { useState } from 'react';
import { message, Card } from 'antd';
import PredictionForm from '../components/predict/PredictionForm';
import RiskGauge from '../components/predict/RiskGauge';
import ShapExplanation from '../components/predict/ShapExplanation';
import { postSinglePredict } from '../api/predict';
import type { PredictSingleResponse } from '../types';

export default function PredictionPage() {
  const [result, setResult] = useState<PredictSingleResponse | null>(null);
  const [loading, setLoading] = useState(false);

  const handleSubmit = async (values: Record<string, any>) => {
    setLoading(true);
    try {
      const res = await postSinglePredict(values as any);
      setResult(res);
      message.success('预测完成');
    } catch {
      message.error('预测失败，请检查输入');
    } finally {
      setLoading(false);
    }
  };

  return (
    <div>
      <h2>单条预测</h2>
      <p style={{ color: '#6B625D', fontSize: 13, marginBottom: 24 }}>
        理赔风险评估 · 填写以下字段后提交，即刻返回欺诈概率
      </p>

      <PredictionForm onResult={handleSubmit} loading={loading} />

      {result && (
        <Card style={{ marginTop: 24 }} title="预测结果">
          <div style={{
            marginBottom: 16,
            padding: '10px 16px',
            background: '#F5F3F0',
            borderRadius: 6,
            fontSize: 13,
            color: '#44403C',
          }}>
            保单号：<strong style={{ color: '#292524' }}>{result.policy_id}</strong>
          </div>
          <div style={{ display: 'flex', gap: 24, alignItems: 'flex-start' }}>
            <div style={{ flex: '240px 0 0' }}>
              <RiskGauge
                fraudProb={result.fraud_prob}
                riskLevel={result.risk_level}
                threshold={result.threshold_used}
              />
            </div>
            <div style={{ flex: 1 }}>
              <ShapExplanation items={result.shap_top10} />
            </div>
          </div>
        </Card>
      )}
    </div>
  );
}
```

- [ ] **Step 8.3: 提交**

```bash
git add frontend/src/components/predict/PredictionForm.tsx frontend/src/pages/PredictionPage.tsx
git commit -m "refactor: prediction form — 2-column grid, remove wizard/collapse, clean result card"
```

---

### Task 9: 批量预测重构

**Files:**
- Modify: `frontend/src/components/batch/BatchUpload.tsx`
- Modify: `frontend/src/components/batch/BatchProgress.tsx`
- Modify: `frontend/src/pages/BatchPredictPage.tsx`

- [ ] **Step 9.1: BatchUpload — 自定义拖拽样式**

将 `BatchUpload.tsx` 全文替换为：

```tsx
import { Upload, message } from 'antd';
import { InboxOutlined } from '@ant-design/icons';
import type { UploadProps } from 'antd';

const { Dragger } = Upload;

interface Props {
  onUpload: (file: File) => void;
  disabled?: boolean;
}

export default function BatchUpload({ onUpload, disabled }: Props) {
  const props: UploadProps = {
    name: 'file',
    multiple: false,
    accept: '.csv,.xlsx,.xls',
    disabled,
    beforeUpload: (file) => {
      const isAllowed =
        file.name.endsWith('.csv') ||
        file.name.endsWith('.xlsx') ||
        file.name.endsWith('.xls');
      if (!isAllowed) {
        message.error('仅支持 CSV 和 Excel 文件');
        return Upload.LIST_IGNORE;
      }
      onUpload(file);
      return false;
    },
    showUploadList: false,
  };

  return (
    <Dragger
      {...props}
      style={{
        border: '2px dashed #D6D3D0',
        borderRadius: 6,
        background: '#FAFAF9',
        padding: '32px 24px',
      }}
    >
      <p className="ant-upload-drag-icon">
        <InboxOutlined style={{ color: '#A8A29E', fontSize: 32 }} />
      </p>
      <p style={{ color: '#44403C', fontSize: 14, marginBottom: 4, fontWeight: 500 }}>
        点击或拖拽 CSV/Excel 文件到此处上传
      </p>
      <p style={{ color: '#A8A29E', fontSize: 12, margin: 0 }}>
        支持 .csv / .xlsx / .xls 格式，最大 100MB
      </p>
    </Dragger>
  );
}
```

- [ ] **Step 9.2: BatchProgress — 替换颜色**

将 `BatchProgress.tsx` 全文替换为：

```tsx
import { Progress, Button, Space } from 'antd';
import { DownloadOutlined } from '@ant-design/icons';
import type { BatchTaskStatus } from '../../types';

interface Props {
  status: BatchTaskStatus;
  onDownload: () => void;
}

const STATUS_DOT: Record<string, string> = {
  pending: '#A8A29E',
  processing: '#4A5630',
  completed: '#4A5630',
  failed: '#DC2626',
};

const STATUS_LABEL: Record<string, string> = {
  pending: '等待中',
  processing: '处理中',
  completed: '已完成',
  failed: '失败',
};

export default function BatchProgress({ status, onDownload }: Props) {
  const percent =
    status.total > 0
      ? Math.round(((status.processed || 0) / status.total) * 100)
      : 0;

  return (
    <div style={{ padding: '16px 0' }}>
      <Space direction="vertical" style={{ width: '100%' }} size="middle">
        <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
          <span style={{
            width: 8,
            height: 8,
            borderRadius: '50%',
            background: STATUS_DOT[status.status] || '#A8A29E',
            display: 'inline-block',
            flexShrink: 0,
          }} />
          <span style={{ fontSize: 13, color: '#44403C', fontWeight: 500 }}>
            {STATUS_LABEL[status.status] || status.status}
          </span>
          <span style={{ fontSize: 12, color: '#6B625D', marginLeft: 4 }}>
            {status.status === 'processing'
              ? `${status.processed} / ${status.total}`
              : status.status === 'completed'
                ? `${status.success} 成功, ${status.failed} 失败`
                : status.status === 'failed'
                  ? '处理失败'
                  : '等待中...'}
          </span>
        </div>

        <Progress
          percent={percent}
          status={status.status === 'failed' ? 'exception' : status.status === 'completed' ? 'success' : 'active'}
          strokeColor={status.status === 'failed' ? '#DC2626' : '#4A5630'}
        />

        {status.status === 'completed' && (
          <Button type="primary" icon={<DownloadOutlined />} onClick={onDownload}>
            下载结果
          </Button>
        )}

        {status.status === 'failed' && status.error_message && (
          <div style={{ fontSize: 12, color: '#DC2626', background: '#FEF2F2', padding: '8px 12px', borderRadius: 4 }}>
            {status.error_message}
          </div>
        )}
      </Space>
    </div>
  );
}
```

- [ ] **Step 9.3: BatchPredictPage — 更新布局样式**

将 `BatchPredictPage.tsx` 中的页面标题和描述风格化。找到原来的 `<Title level={4}>` 和 Card 包装，替换为：

```tsx
// 顶部
<div>
  <h2>批量预测</h2>
  <p style={{ color: '#6B625D', fontSize: 13, marginBottom: 24 }}>
    文件上传 · 支持 CSV / Excel，上传后台异步处理，结果可下载
  </p>

  <div style={{
    background: '#FFFFFF',
    border: '1px solid #E7E5E2',
    borderRadius: 6,
    padding: 24,
    marginBottom: 24,
    boxShadow: '0 1px 2px rgba(0,0,0,0.04)',
  }}>
    <BatchUpload onUpload={handleUpload} disabled={loading || currentTask?.status === 'processing'} />
  </div>

  {currentTask && (
    <div style={{
      background: '#FFFFFF',
      border: '1px solid #E7E5E2',
      borderRadius: 6,
      padding: 24,
      marginBottom: 24,
      boxShadow: '0 1px 2px rgba(0,0,0,0.04)',
    }}>
      <BatchProgress status={currentTask} onDownload={handleDownload} />
    </div>
  )}

  <div style={{
    background: '#FFFFFF',
    border: '1px solid #E7E5E2',
    borderRadius: 6,
    padding: 24,
    boxShadow: '0 1px 2px rgba(0,0,0,0.04)',
  }}>
    <h4>历史任务</h4>
    {/* 表格... */}
  </div>
</div>
```

- [ ] **Step 9.4: 提交**

```bash
git add frontend/src/components/batch/ frontend/src/pages/BatchPredictPage.tsx
git commit -m "refactor: batch prediction — custom drag zone, dot status, flow layout"
```

---

### Task 10: 案件管理重构

**Files:**
- Modify: `frontend/src/pages/CaseListPage.tsx`
- Modify: `frontend/src/components/cases/CaseTable.tsx`

- [ ] **Step 10.1: CaseListPage — 去掉 Card 包裹的筛选栏**

将 `CaseListPage.tsx` 全文替换为（保留全部逻辑，仅改样式结构）：

```tsx
import { useState, useCallback, useEffect, useRef } from 'react';
import {
  Select,
  DatePicker,
  Input,
  Row,
  Col,
  Space,
  message,
} from 'antd';
import { SearchOutlined } from '@ant-design/icons';
import CaseTable from '../components/cases/CaseTable';
import { fetchCases } from '../api/cases';
import type { CaseListItem } from '../types';
import { TableSkeleton } from '../components/common/Skeleton';
import EmptyState from '../components/common/EmptyState';

const { RangePicker } = DatePicker;

export default function CaseListPage() {
  const [data, setData] = useState<CaseListItem[]>([]);
  const [total, setTotal] = useState(0);
  const [loading, setLoading] = useState(false);
  const [page, setPage] = useState(1);
  const [pageSize, setPageSize] = useState(20);
  const [riskLevel, setRiskLevel] = useState<string | undefined>(undefined);
  const [manualResult, setManualResult] = useState<string | undefined>(undefined);
  const [dateRange, setDateRange] = useState<[string, string] | null>(null);
  const [keyword, setKeyword] = useState('');

  const loadData = useCallback(async (
    p?: number, s?: number, rl?: string, mr?: string,
    dr?: [string, string] | undefined, kw?: string,
  ) => {
    const pageNum = p ?? 1;
    const sizeNum = s ?? 20;
    setPage(pageNum);
    setPageSize(sizeNum);
    setLoading(true);
    try {
      const res = await fetchCases({
        page: pageNum, size: sizeNum,
        risk_level: rl !== undefined ? rl : riskLevel,
        manual_result: mr !== undefined ? mr : manualResult,
        date_from: dr !== undefined ? dr?.[0] : dateRange?.[0],
        date_to: dr !== undefined ? dr?.[1] : dateRange?.[1],
        keyword: kw !== undefined ? kw || undefined : keyword || undefined,
      });
      setData(res.items);
      setTotal(res.total);
    } catch {
      message.error('加载案件列表失败');
    } finally {
      setLoading(false);
    }
  }, [riskLevel, manualResult, dateRange, keyword]);

  const initialLoadDone = useRef(false);
  useEffect(() => {
    if (!initialLoadDone.current) { initialLoadDone.current = true; loadData(); }
  }, [loadData]);

  const handlePageChange = (p: number, ps: number) => { loadData(p, ps); };
  const handleSearch = () => { loadData(1, pageSize, undefined, undefined, undefined, keyword); };

  return (
    <div>
      <h2>案件管理</h2>
      <p style={{ color: '#6B625D', fontSize: 13, marginBottom: 16 }}>
        审核工作台 · 共 {total} 条记录
      </p>

      {/* 筛选栏 — 无 Card 外框 */}
      <div style={{
        background: '#FFFFFF',
        border: '1px solid #E7E5E2',
        borderRadius: 6,
        padding: '12px 16px',
        marginBottom: 16,
        boxShadow: '0 1px 2px rgba(0,0,0,0.04)',
      }}>
        <Row gutter={[12, 12]} align="middle">
          <Col>
            <Select
              placeholder="风险等级"
              allowClear
              style={{ width: 130 }}
              value={riskLevel}
              onChange={(v) => { setRiskLevel(v); loadData(1, pageSize, v, undefined, undefined, undefined); }}
              options={[
                { label: '高风险', value: 'high' },
                { label: '中风险', value: 'medium' },
                { label: '低风险', value: 'low' },
              ]}
            />
          </Col>
          <Col>
            <Select
              placeholder="人工判定"
              allowClear
              style={{ width: 130 }}
              value={manualResult}
              onChange={(v) => { setManualResult(v); loadData(1, pageSize, undefined, v, undefined, undefined); }}
              options={[
                { label: '通过', value: 'pass' },
                { label: '拒绝', value: 'reject' },
                { label: '调查中', value: 'investigate' },
              ]}
            />
          </Col>
          <Col>
            <RangePicker
              placeholder={['开始日期', '结束日期']}
              onChange={(dates) => {
                if (dates && dates[0] && dates[1]) {
                  const dr: [string, string] = [dates[0].format('YYYY-MM-DD'), dates[1].format('YYYY-MM-DD')];
                  setDateRange(dr);
                  loadData(1, pageSize, undefined, undefined, dr, undefined);
                } else {
                  setDateRange(null);
                  loadData(1, pageSize, undefined, undefined, undefined, undefined);
                }
              }}
            />
          </Col>
          <Col flex="auto">
            <Space.Compact style={{ width: '100%' }}>
              <Input
                placeholder="搜索保单号..."
                value={keyword}
                onChange={(e) => setKeyword(e.target.value)}
                onPressEnter={handleSearch}
                allowClear
              />
              <SearchOutlined
                onClick={handleSearch}
                style={{
                  padding: '0 12px', fontSize: 16, cursor: 'pointer',
                  display: 'flex', alignItems: 'center',
                  border: '1px solid #E7E5E2', borderRadius: '0 6px 6px 0',
                  background: '#FAFAF9', color: '#6B625D',
                }}
              />
            </Space.Compact>
          </Col>
        </Row>
      </div>

      {/* 表格容器 */}
      <div style={{
        background: '#FFFFFF',
        border: '1px solid #E7E5E2',
        borderRadius: 6,
        padding: 24,
        boxShadow: '0 1px 2px rgba(0,0,0,0.04)',
      }}>
        {loading ? (
          <TableSkeleton />
        ) : data.length === 0 ? (
          <EmptyState description="暂无案件" />
        ) : (
          <CaseTable
            data={data}
            loading={false}
            pagination={{ current: page, pageSize, total }}
            onPageChange={handlePageChange}
          />
        )}
      </div>
    </div>
  );
}
```

- [ ] **Step 10.2: CaseTable — 概率纯数字颜色 + 状态圆点**

替换 `CaseTable.tsx` 中的颜色映射和渲染逻辑。关键改动：

```tsx
// 风险等级颜色（概率驱动，不是 level 字符串）
const probColor = (v: number): string => {
  if (v >= 0.7) return '#DC2626';
  if (v >= 0.3) return '#947008';
  return '#4A5630';
};

const riskDotColor: Record<string, string> = {
  high: '#DC2626',
  medium: '#947008',
  low: '#4A5630',
};

const riskLabelMap: Record<string, string> = {
  high: '高风险',
  medium: '中风险',
  low: '低风险',
};

// 在 columns 中：
// 欺诈概率列: 纯数字 + 颜色
{
  title: '欺诈概率',
  dataIndex: 'fraud_prob',
  key: 'fraud_prob',
  width: 120,
  render: (v: number) => (
    <span style={{ fontWeight: 600, color: probColor(v), fontFamily: "'Inter', sans-serif", fontFeatureSettings: "'tnum'" }}>
      {(v * 100).toFixed(1)}%
    </span>
  ),
},
// 风险等级列: 圆点 + 文字（非 Tag）
{
  title: '风险等级',
  dataIndex: 'risk_level',
  key: 'risk_level',
  width: 100,
  render: (level: string) => (
    <span style={{ display: 'inline-flex', alignItems: 'center', gap: 4, fontSize: 12 }}>
      <span style={{ width: 6, height: 6, borderRadius: '50%', background: riskDotColor[level] || '#A8A29E', display: 'inline-block' }} />
      <span style={{ color: riskDotColor[level] || '#A8A29E' }}>{riskLabelMap[level] || level}</span>
    </span>
  ),
},
// 人工判定列: 也改用圆点
{
  title: '人工判定',
  dataIndex: 'manual_result',
  key: 'manual_result',
  width: 110,
  render: (v: string | null) => {
    if (!v) return <span style={{ color: '#A8A29E', fontSize: 12 }}>待处理</span>;
    const c: Record<string, string> = { pass: '#4A5630', reject: '#DC2626', investigate: '#947008' };
    const lbl: Record<string, string> = { pass: '通过', reject: '拒绝', investigate: '调查中' };
    return (
      <span style={{ display: 'inline-flex', alignItems: 'center', gap: 4, fontSize: 12 }}>
        <span style={{ width: 6, height: 6, borderRadius: '50%', background: c[v] || '#A8A29E', display: 'inline-block' }} />
        <span style={{ color: c[v] || '#A8A29E' }}>{lbl[v] || v}</span>
      </span>
    );
  },
},
```

- [ ] **Step 10.3: 提交**

```bash
git add frontend/src/pages/CaseListPage.tsx frontend/src/components/cases/CaseTable.tsx
git commit -m "refactor: case list — flat filter bar, dot status, probability color-only"
```

---

### Task 11: 案件详情重构

**Files:**
- Modify: `frontend/src/pages/CaseDetailPage.tsx`
- Modify: `frontend/src/components/cases/CaseDetail.tsx`
- Modify: `frontend/src/components/cases/AdjudicateModal.tsx`

- [ ] **Step 11.1: CaseDetailPage — 分区布局 + 去硬编码**

将 `CaseDetailPage.tsx` 全文替换为（保留全部逻辑）：

```tsx
import { useState, useEffect, useCallback } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import { Card, Button, Space, message } from 'antd';
import { DetailSkeleton } from '../components/common/Skeleton';
import EmptyState from '../components/common/EmptyState';
import {
  ArrowLeftOutlined,
  AuditOutlined,
  RobotOutlined,
} from '@ant-design/icons';
import {
  InsureeCard,
  PolicyCard,
  ClaimCard,
  PredictionCard,
  ShapCard,
  HistoryTimeline,
} from '../components/cases/CaseDetail';
import AdjudicateModal from '../components/cases/AdjudicateModal';
import { fetchCaseDetail, adjudicateCase } from '../api/cases';
import { analyzeCase } from '../api/agent';
import type { CaseDetailResponse } from '../types';

export default function CaseDetailPage() {
  const { id } = useParams<{ id: string }>();
  const navigate = useNavigate();
  const [detail, setDetail] = useState<CaseDetailResponse | null>(null);
  const [loading, setLoading] = useState(false);
  const [adjudicating, setAdjudicating] = useState(false);
  const [analyzing, setAnalyzing] = useState(false);
  const [agentReport, setAgentReport] = useState<{
    report_text: string; model_used: string; generated_at: string;
  } | null>(null);
  const [modalOpen, setModalOpen] = useState(false);

  const loadDetail = useCallback(async () => {
    if (!id) return;
    setLoading(true);
    try {
      const data = await fetchCaseDetail(Number(id));
      setDetail(data);
    } catch { message.error('加载案件详情失败'); }
    finally { setLoading(false); }
  }, [id]);

  useEffect(() => { loadDetail(); }, [loadDetail]);

  useEffect(() => {
    if (detail?.agent_report) setAgentReport(detail.agent_report);
  }, [detail]);

  const handleAnalyze = useCallback(async () => {
    if (!id) return;
    setAnalyzing(true);
    try {
      const isRefresh = !!agentReport;
      const res = await analyzeCase(Number(id), isRefresh);
      if (res.fallback) { message.warning('AI 分析暂时不可用，请稍后重试'); }
      else if (res.report) {
        setAgentReport({
          report_text: res.report,
          model_used: res.model_used || 'unknown',
          generated_at: new Date().toISOString(),
        });
        message.success(res.cached ? '命中缓存' : '分析报告已生成');
      }
    } catch { message.error('AI 分析请求失败'); }
    finally { setAnalyzing(false); }
  }, [id, agentReport]);

  const handleAdjudicate = useCallback(async (values: { manual_result: 'pass' | 'reject' | 'investigate'; remark?: string }) => {
    if (!id) return;
    setAdjudicating(true);
    try {
      await adjudicateCase(Number(id), { manual_result: values.manual_result, remark: values.remark });
      message.success('人工判定成功');
      setModalOpen(false);
      loadDetail();
    } catch { message.error('人工判定失败'); }
    finally { setAdjudicating(false); }
  }, [id, loadDetail]);

  if (loading) return <DetailSkeleton cards={4} />;
  if (!detail) return <EmptyState description="案件不存在" />;

  const riskLabel = detail.risk_level === 'high' ? '高风险' : detail.risk_level === 'medium' ? '中风险' : '低风险';
  const riskColor = detail.risk_level === 'high' ? '#DC2626' : detail.risk_level === 'medium' ? '#947008' : '#4A5630';

  return (
    <div>
      {/* 顶部导航 */}
      <div style={{ display: 'flex', alignItems: 'flex-start', marginBottom: 24 }}>
        <Button
          icon={<ArrowLeftOutlined />}
          onClick={() => navigate('/cases')}
          type="text"
          style={{ color: '#6B625D', marginRight: 8, marginTop: 2 }}
        />
        <div style={{ flex: 1 }}>
          <h2 style={{ marginBottom: 4 }}>
            案件 {detail.policy_id}
          </h2>
          <p style={{ color: '#6B625D', fontSize: 13, margin: 0 }}>
            创建于 {detail.detect_time ? new Date(detail.detect_time).toLocaleString() : '-'}
            <span style={{ display: 'inline-flex', alignItems: 'center', gap: 4, marginLeft: 12 }}>
              <span style={{ width: 6, height: 6, borderRadius: '50%', background: riskColor, display: 'inline-block' }} />
              <span style={{ color: riskColor, fontWeight: 500 }}>{riskLabel}</span>
            </span>
          </p>
        </div>
        <Space>
          <Button icon={<RobotOutlined />} onClick={handleAnalyze} loading={analyzing}>
            {agentReport ? '刷新 AI 分析' : 'AI 分析'}
          </Button>
          <Button type="primary" icon={<AuditOutlined />} onClick={() => setModalOpen(true)}>
            人工判定
          </Button>
        </Space>
      </div>

      {/* AI 分析报告 */}
      {agentReport && (
        <Card title="AI 分析报告" size="small" style={{ marginBottom: 16 }}>
          <div style={{ whiteSpace: 'pre-wrap', color: '#44403C' }}>{agentReport.report_text}</div>
          <p style={{ color: '#A8A29E', fontSize: 12, marginTop: 8 }}>
            模型: {agentReport.model_used} | 生成时间: {new Date(agentReport.generated_at).toLocaleString()}
          </p>
        </Card>
      )}

      {/* 概览 */}
      <Card style={{ marginBottom: 16 }} title="预测概览">
        <PredictionCard detail={detail} />
      </Card>

      {/* 详细特征 */}
      <InsureeCard insuree={detail.insuree} featureValues={detail.feature_values} />
      <PolicyCard policy={detail.policy} featureValues={detail.feature_values} />
      <ClaimCard claim={detail.accident_claim} featureValues={detail.feature_values} />

      {/* SHAP 解释 */}
      <Card style={{ marginBottom: 16 }} title="SHAP 特征贡献">
        <ShapCard shapValues={detail.shap_values} />
      </Card>

      {/* 审核历史 */}
      <Card style={{ marginBottom: 16 }} title="审核历史">
        <HistoryTimeline history={detail.case_history} />
      </Card>

      {/* 判定弹窗 */}
      <AdjudicateModal
        open={modalOpen}
        onOk={handleAdjudicate}
        onCancel={() => setModalOpen(false)}
        loading={adjudicating}
      />
    </div>
  );
}
```

- [ ] **Step 11.2: CaseDetail 子组件 — 全部 6 组件颜色更新**

`CaseDetail.tsx` 中 6 个具名导出组件的颜色硬编码清除。逐个更新：

**InsureeCard**: 无硬编码颜色——ConfigProvider token 覆盖了 Descriptions/Tag 配色，无需代码变更。

**PolicyCard**: 同 InsureeCard，逻辑不变，无需代码变更。

**ClaimCard**: 将 `is_fraud` 的 "欺诈"/"正常" 文字颜色化：
```tsx
<Descriptions.Item label="是否欺诈">
  {claim.is_fraud != null ? (
    <span style={{ fontWeight: 500, color: claim.is_fraud ? '#DC2626' : '#4A5630' }}>
      {claim.is_fraud ? '欺诈' : '正常'}
    </span>
  ) : '-'}
</Descriptions.Item>
```

**PredictionCard**: 将 `<Tag>` 替换为圆点+颜色（去 Tag，去 Ant Design 默认 riskColorMap）：
```tsx
export function PredictionCard({ detail }: { detail: CaseDetailResponse }) {
  const prob = detail.fraud_prob * 100;
  const pc = prob >= 70 ? '#DC2626' : prob >= 30 ? '#947008' : '#4A5630';
  const rl = detail.risk_level;
  const rc = rl === 'high' ? '#DC2626' : rl === 'medium' ? '#947008' : '#4A5630';
  const rlabel = rl === 'high' ? '高风险' : rl === 'medium' ? '中风险' : '低风险';

  const resultColor: Record<string, string> = { pass: '#4A5630', reject: '#DC2626', investigate: '#947008' };
  const resultLabel: Record<string, string> = { pass: '通过', reject: '拒绝', investigate: '调查中' };

  return (
    <Descriptions column={2} bordered size="small">
      <Descriptions.Item label="欺诈概率">
        <span style={{ fontWeight: 700, fontSize: 24, color: pc, fontFamily: "'Inter', sans-serif", fontFeatureSettings: "'tnum'" }}>
          {prob.toFixed(1)}%
        </span>
      </Descriptions.Item>
      <Descriptions.Item label="风险等级">
        <span style={{ display: 'inline-flex', alignItems: 'center', gap: 6 }}>
          <span style={{ width: 8, height: 8, borderRadius: '50%', background: rc, display: 'inline-block' }} />
          <span style={{ fontWeight: 500, color: rc }}>{rlabel}</span>
        </span>
      </Descriptions.Item>
      <Descriptions.Item label="原始概率">
        {detail.raw_prob != null ? `${(detail.raw_prob * 100).toFixed(1)}%` : '-'}
      </Descriptions.Item>
      <Descriptions.Item label="阈值">
        {detail.threshold_used != null ? `${(detail.threshold_used * 100).toFixed(1)}%` : '-'}
      </Descriptions.Item>
      <Descriptions.Item label="人工判定">
        {detail.manual_result ? (
          <span style={{ display: 'inline-flex', alignItems: 'center', gap: 4, fontSize: 12 }}>
            <span style={{ width: 6, height: 6, borderRadius: '50%', background: resultColor[detail.manual_result] || '#A8A29E', display: 'inline-block' }} />
            <span style={{ color: resultColor[detail.manual_result] || '#A8A29E', fontWeight: 500 }}>
              {resultLabel[detail.manual_result] || detail.manual_result}
            </span>
          </span>
        ) : (
          <span style={{ color: '#A8A29E', fontSize: 12 }}>待处理</span>
        )}
      </Descriptions.Item>
      <Descriptions.Item label="检测时间">
        {detail.detect_time ? new Date(detail.detect_time).toLocaleString() : '-'}
      </Descriptions.Item>
    </Descriptions>
  );
}
```

**ShapCard**: Timeline 颜色更新：
```tsx
export function ShapCard({ shapValues }: { shapValues: Record<string, number> | null }) {
  if (!shapValues || Object.keys(shapValues).length === 0) return null;

  const sorted = Object.entries(shapValues)
    .map(([feature, value]) => ({ feature, value }))
    .sort((a, b) => Math.abs(b.value) - Math.abs(a.value))
    .slice(0, 10);

  return (
    <div>
      <Timeline
        items={sorted.map((item) => ({
          color: item.value >= 0 ? '#DC2626' : '#4A5630',
          children: (
            <span>
              <strong>{item.feature}</strong>: {item.value >= 0 ? '+' : ''}
              {item.value.toFixed(4)} {item.value >= 0 ? '(推高欺诈概率)' : '(降低欺诈概率)'}
            </span>
          ),
        }))}
      />
    </div>
  );
}
```

**HistoryTimeline**: 颜色 + Tag 替换：
```tsx
export function HistoryTimeline({ history }: { history: CaseDetailResponse['case_history'] }) {
  if (!history || history.length === 0) {
    return <p style={{ color: '#6B625D' }}>暂无审核记录</p>;
  }

  const dotColor: Record<string, string> = { pass: '#4A5630', reject: '#DC2626', investigate: '#947008' };
  const lbl: Record<string, string> = { pass: '通过', reject: '拒绝', investigate: '调查中' };

  return (
    <Timeline
      items={history.map((item) => ({
        color: dotColor[item.manual_result ?? ''] || '#A8A29E',
        children: (
          <div>
            <div>
              <strong>{item.reviewer_name ?? '系统'}</strong>
              {item.manual_result && (
                <span style={{
                  display: 'inline-flex', alignItems: 'center', gap: 4,
                  marginLeft: 8, fontSize: 12,
                  color: dotColor[item.manual_result] || '#A8A29E',
                }}>
                  <span style={{ width: 6, height: 6, borderRadius: '50%', background: dotColor[item.manual_result] || '#A8A29E', display: 'inline-block' }} />
                  {lbl[item.manual_result] || item.manual_result}
                </span>
              )}
              <span style={{ marginLeft: 8, color: '#A8A29E', fontSize: 12 }}>
                {item.operate_time ? new Date(item.operate_time).toLocaleString() : '-'}
              </span>
            </div>
            {item.remark && (
              <div style={{ marginTop: 4, color: '#6B625D' }}>{item.remark}</div>
            )}
          </div>
        ),
      }))}
    />
  );
}
```

- [ ] **Step 11.3: AdjudicateModal — 无需大改**

ConfigProvider token 已接管颜色。可去掉 Ant Design 默认的 Modal 样式说明。

- [ ] **Step 11.4: 提交**

```bash
git add frontend/src/pages/CaseDetailPage.tsx frontend/src/components/cases/
git commit -m "refactor: case detail — zoned layout, probability color, dot indicators"
```

---

### Task 12: 管理面板重构

**Files:**
- Modify: `frontend/src/pages/AdminPage.tsx`
- Modify: `frontend/src/components/admin/UserManagement.tsx`
- Modify: `frontend/src/components/admin/DataUpload.tsx`

- [ ] **Step 12.1: AdminPage — 去掉 Tab 中的 icon 内联**

```tsx
// AdminPage.tsx: 去掉 <span> 包裹，直接使用 label 字符串
<Tabs
  defaultActiveKey="users"
  items={[
    { key: 'users', label: '用户管理', children: <UserManagement /> },
    { key: 'data', label: '数据管理', children: <DataUpload /> },
  ]}
/>
```

- [ ] **Step 12.2: UserManagement — 状态改为圆点**

将 `<Text type={v ? 'success' : 'secondary'}>` 替换为：

```tsx
// 状态列 render:
render: (v: boolean, record: User) => {
  const isSelf = record.user_id === currentUser?.user_id;
  return (
    <Space>
      <Switch
        size="small"
        checked={v}
        disabled={isSelf}
        onChange={(checked) => handleActiveChange(record.user_id, checked)}
      />
      <span style={{ display: 'inline-flex', alignItems: 'center', gap: 4, fontSize: 12 }}>
        <span style={{ width: 6, height: 6, borderRadius: '50%', background: v ? '#4A5630' : '#A8A29E', display: 'inline-block' }} />
        <span style={{ color: v ? '#4A5630' : '#A8A29E' }}>{v ? '启用' : '停用'}</span>
      </span>
    </Space>
  );
},
```

角色 Tag 颜色也更新：
```tsx
const ROLE_COLOR: Record<string, string> = {
  admin: '#44403C',
  reviewer: '#4A5630',
};
```

- [ ] **Step 12.3: DataUpload — 同步 BatchUpload 样式**

将 DataUpload 中的 Dragger 样式与 BatchUpload 同步（虚线边框 + 暖色），并将状态 Tag 改为圆点：

```tsx
// Dragger 添加 style prop:
<Dragger
  accept=".xlsx,.xls"
  maxCount={1}
  customRequest={handleUpload}
  disabled={uploading}
  showUploadList={false}
  style={{
    border: '2px dashed #D6D3D0',
    borderRadius: 6,
    background: '#FAFAF9',
    padding: '32px 24px',
    marginBottom: 24,
  }}
>
  <p className="ant-upload-drag-icon">
    <InboxOutlined style={{ color: '#A8A29E', fontSize: 32 }} />
  </p>
  <p style={{ color: '#44403C', fontSize: 14, marginBottom: 4, fontWeight: 500 }}>
    点击或拖拽上传原始 Excel 文件
  </p>
  <p style={{ color: '#A8A29E', fontSize: 12, margin: 0 }}>
    支持 .xlsx / .xls 格式，最大 100MB
  </p>
</Dragger>
```

状态列改用圆点：
```tsx
const STATUS_DOT: Record<string, string> = {
  pending: '#A8A29E',
  processing: '#4A5630',
  completed: '#4A5630',
  failed: '#DC2626',
};

// render:
render: (s: string) => (
  <span style={{ display: 'inline-flex', alignItems: 'center', gap: 4, fontSize: 12 }}>
    <span style={{ width: 6, height: 6, borderRadius: '50%', background: STATUS_DOT[s] || '#A8A29E', display: 'inline-block' }} />
    <span style={{ color: STATUS_DOT[s] || '#A8A29E' }}>{STATUS_LABEL[s] || s}</span>
  </span>
),
```

- [ ] **Step 12.4: 提交**

```bash
git add frontend/src/pages/AdminPage.tsx frontend/src/components/admin/
git commit -m "refactor: admin panel — dot status, unified upload style, removed icons from tabs"
```

---

### Task 13: 验证与清理

- [ ] **Step 1: 硬编码色值扫描**

```bash
cd frontend
grep -rE '#[0-9a-fA-F]{3}([0-9a-fA-F]{3})?' src/ --include='*.tsx' --include='*.css'
```

应该只看到 CSS 变量定义 (index.css) 和设计 Token 颜色（在组件 style prop 中）。不应出现旧颜色 `#1677ff`、`#667eea`、`#764ba2`、`#cf1322`、`#3f8600`、`#ff4d4f`、`#666`、`#999`、`#f6f8fa`、`#fafafa`、`#52c41a`、`#faad14`、`#d9d9d9`。

- [ ] **Step 2: 旧颜色关键词扫描**

```bash
grep -r '1677ff\|667eea\|764ba2\|cf1322\|3f8600\|52c41a\|faad14' frontend/src/
```

预期：空输出。

- [ ] **Step 3: TypeScript 检查**

```bash
cd frontend && npx tsc --noEmit
```

预期：无错误。如有类型错误，逐个修复。

- [ ] **Step 4: 确认字体文件存在**

```bash
ls frontend/public/fonts/inter-latin-*.woff2
```

预期：5 个文件。

- [ ] **Step 5: 提交**

```bash
git add -A
git commit -m "chore: verification — color cleanup, tsc pass, fonts present"
```
