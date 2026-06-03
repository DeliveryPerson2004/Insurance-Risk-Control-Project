# Phase 4 模块 3: 打磨 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 新增 3 个共用组件（ErrorBoundary / EmptyState / Skeleton），接入 5 个页面替换 loading spinner 和空状态

**Architecture:** 所有组件置于 `frontend/src/components/common/`，纯展示组件无业务逻辑依赖。ErrorBoundary 在 App.tsx 最外层包裹；Skeleton + EmptyState 各页面按需引入

**Tech Stack:** React 18 + TypeScript + Ant Design 5 (Result, Empty, Skeleton)

**范围说明:**
- 本次打磨仅覆盖 **React 渲染层**（ErrorBoundary / Skeleton / EmptyState）
- **API 层全局异常处理**（Axios interceptor 统一 toast、403/500 降级）不在此次范围内，当前各组件 `catch` 中 `message.error()` 已可接受
- DashboardPage 的 StatsCards 加载优化（空白卡片→CardSkeleton）作为已知改进项记录，本次不阻塞

---

### Task 1: ErrorBoundary + App.tsx 接入

**Files:**
- Create: `frontend/src/components/common/ErrorBoundary.tsx`
- Modify: `frontend/src/App.tsx`

- [ ] **Step 1: 创建 ErrorBoundary**

```bash
mkdir -p frontend/src/components/common
```

创建 `frontend/src/components/common/ErrorBoundary.tsx`:

```typescript
import { Component, type ReactNode } from 'react';
import { Result, Button } from 'antd';

interface Props {
  children: ReactNode;
}

interface State {
  hasError: boolean;
  error: Error | null;
}

export default class ErrorBoundary extends Component<Props, State> {
  state: State = { hasError: false, error: null };

  static getDerivedStateFromError(error: Error): State {
    return { hasError: true, error };
  }

  handleRefresh = () => {
    window.location.reload();
  };

  render() {
    if (this.state.hasError) {
      return (
        <Result
          status="error"
          title="页面出现异常"
          subTitle={this.state.error?.message || '未知错误'}
          extra={
            <Button type="primary" onClick={this.handleRefresh}>
              刷新页面
            </Button>
          }
        />
      );
    }
    return this.props.children;
  }
}
```

- [ ] **Step 2: App.tsx 包裹 ErrorBoundary**

修改 `frontend/src/App.tsx`:

在文件顶部 import 区域添加:
```typescript
import ErrorBoundary from './components/common/ErrorBoundary';
```

在 `<AntApp>` 内部包裹 `<ErrorBoundary>`:
```typescript
// 修改前:
<AntApp>
  <BrowserRouter>
    ...
  </BrowserRouter>
</AntApp>

// 修改后:
<AntApp>
  <ErrorBoundary>
    <BrowserRouter>
      ...
    </BrowserRouter>
  </ErrorBoundary>
</AntApp>
```

- [ ] **Step 3: 验证**

```bash
cd frontend && npx tsc --noEmit
```

- [ ] **Step 4: Commit**

```bash
git add frontend/src/components/common/ErrorBoundary.tsx frontend/src/App.tsx
git commit -m "feat: add ErrorBoundary with antd Result, wrap App root"
```

---

### Task 2: EmptyState 组件

**Files:**
- Create: `frontend/src/components/common/EmptyState.tsx`

- [ ] **Step 1: 创建 EmptyState**

```typescript
import { Empty } from 'antd';
import type { ReactNode } from 'react';

interface Props {
  description?: string;
  image?: ReactNode;  // 与 antd Empty.image 命名一致，传入的是插图
  action?: ReactNode;
}

export default function EmptyState({ description = '暂无数据', image, action }: Props) {
  return (
    <Empty
      image={image || Empty.PRESENTED_IMAGE_SIMPLE}
      description={description}
      style={{ padding: '60px 0' }}
    >
      {action}
    </Empty>
  );
}
```

- [ ] **Step 2: 验证**

```bash
cd frontend && npx tsc --noEmit
```

- [ ] **Step 3: Commit**

```bash
git add frontend/src/components/common/EmptyState.tsx
git commit -m "feat: add EmptyState common component wrapping antd Empty"
```

---

### Task 3: Skeleton 组件

**Files:**
- Create: `frontend/src/components/common/Skeleton.tsx`

- [ ] **Step 1: 创建 Skeleton 预设模板**

```typescript
import { Skeleton as AntSkeleton, Card, Row, Col } from 'antd';

/** 模拟表格: 表头 + 5 行 */
export function TableSkeleton({ rows = 5 }: { rows?: number }) {
  return (
    <Card>
      <AntSkeleton active title={{ width: '30%' }} paragraph={{ rows: 1 }} />
      {Array.from({ length: rows }, (_, i) => (
        <AntSkeleton
          key={i}
          active
          avatar={{ shape: 'square', size: 'small' }}
          paragraph={{ rows: 1 }}
          title={false}
        />
      ))}
    </Card>
  );
}

/** 模拟统计卡片: 1 行 × 4 列 */
export function CardSkeleton({ count = 4 }: { count?: number }) {
  return (
    <Row gutter={16}>
      {Array.from({ length: count }, (_, i) => (
        <Col key={i} span={6}>
          <Card>
            <AntSkeleton active paragraph={{ rows: 2 }} title={{ width: '60%' }} />
          </Card>
        </Col>
      ))}
    </Row>
  );
}

/** 模拟详情页: 多个信息卡片 */
export function DetailSkeleton({ cards = 4 }: { cards?: number }) {
  return (
    <div>
      <AntSkeleton active paragraph={{ rows: 0 }} title={{ width: '40%' }} />
      {Array.from({ length: cards }, (_, i) => (
        <Card key={i} style={{ marginTop: 16 }}>
          <AntSkeleton active paragraph={{ rows: 3 }} title={{ width: '50%' }} />
        </Card>
      ))}
    </div>
  );
}
```

- [ ] **Step 2: 验证**

```bash
cd frontend && npx tsc --noEmit
```

- [ ] **Step 3: Commit**

```bash
git add frontend/src/components/common/Skeleton.tsx
git commit -m "feat: add Skeleton presets: TableSkeleton, CardSkeleton, DetailSkeleton"
```

---

### Task 4: 接入各页面

**Files:**
- Modify: `frontend/src/pages/DashboardPage.tsx`
- Modify: `frontend/src/pages/CaseListPage.tsx`
- Modify: `frontend/src/pages/CaseDetailPage.tsx`
- Modify: `frontend/src/pages/BatchPredictPage.tsx`
- Modify: `frontend/src/components/admin/UserManagement.tsx`

- [ ] **Step 1: DashboardPage — 本次跳过**

DashboardPage 无需修改。StatsCards 组件内部自行获取数据，初始渲染先显示 4 张空白统计卡片（value 为 0），API 返回后更新数据——无骨架屏过渡。这是第一个登录后看到的页面，是已知 UX 改进项，建议后续给 StatsCards 加显式 `loading` state 并在此处用 `<CardSkeleton />` 替换。本次不阻塞。

- [ ] **Step 2: CaseListPage — TableSkeleton + EmptyState**

在 `CaseListPage.tsx` 中:

导入区域添加:
```typescript
import { TableSkeleton } from '../components/common/Skeleton';
import EmptyState from '../components/common/EmptyState';
```

**只替换表格区域，筛选栏始终可见**（不用早期 return，避免筛选项消失）:

找到 return 中的 `<CaseTable ... />` 行，替换为:
```typescript
{loading ? (
  <TableSkeleton />
) : data.length === 0 ? (
  <EmptyState description="暂无案件" />
) : (
  <CaseTable
    data={data}
    total={total}
    loading={false}
    page={page}
    pageSize={pageSize}
    onPageChange={(p, ps) => { setPage(p); setPageSize(ps); }}
    // ... 其余 props 保持不变
  />
)}
```

筛选栏（风险等级 Select + 判定状态 Select + 日期 RangePicker + 关键词 Input）在 return 中始终渲染，不受 loading/empty 影响。

- [ ] **Step 3: CaseDetailPage — DetailSkeleton 替换 Spin**

在 `CaseDetailPage.tsx` 中:

导入:
```typescript
import { DetailSkeleton } from '../components/common/Skeleton';
import EmptyState from '../components/common/EmptyState';
```

替换 lines 112-122:
```typescript
// 修改前:
if (loading) {
  return (
    <div style={{ textAlign: 'center', padding: 100 }}>
      <Spin size="large" />
    </div>
  );
}
if (!detail) {
  return <div>案件不存在</div>;
}

// 修改后:
if (loading) {
  return <DetailSkeleton cards={4} />;
}
if (!detail) {
  return <EmptyState description="案件不存在" />;
}
```

并移除 `Spin` 从 antd import 中（如不再使用）。

- [ ] **Step 4: BatchPredictPage — EmptyState 空任务列表**

在 `BatchPredictPage.tsx` 中:

导入:
```typescript
import EmptyState from '../components/common/EmptyState';
```

将历史任务 Table 替换为:
```typescript
<Card title="历史任务">
  {taskList.length === 0 ? (
    <EmptyState description="暂无批量预测任务" />
  ) : (
    <Table
      columns={columns}
      dataSource={taskList}
      rowKey="task_id"
      pagination={{ pageSize: 20, size: 'small' }}
      size="small"
    />
  )}
</Card>
```

- [ ] **Step 5: UserManagement — EmptyState 空用户列表**

在 `UserManagement.tsx` 中:

导入:
```typescript
import EmptyState from '../common/EmptyState';
```

在 Table 渲染处加条件:
```typescript
// 修改前:
<Table rowKey="user_id" ... />

// 修改后:
{!loading && users.length === 0 ? (
  <EmptyState description="暂无用户" />
) : (
  <Table rowKey="user_id" ... />
)}
```

- [ ] **Step 6: 验证**

```bash
cd frontend && npx tsc --noEmit
```

- [ ] **Step 7: Commit**

```bash
git add frontend/src/pages/CaseListPage.tsx frontend/src/pages/CaseDetailPage.tsx frontend/src/pages/BatchPredictPage.tsx frontend/src/components/admin/UserManagement.tsx
git commit -m "feat: integrate Skeleton and EmptyState into all pages"
```

---

### Task 5: 验证

- [ ] **Step 1: TypeScript + Build**

```bash
cd frontend && npx tsc --noEmit && npx vite build
```

- [ ] **Step 2: 视觉验证（手动，需浏览器）**

```bash
cd frontend && npm run dev
# 浏览器访问 localhost:5173
```

逐项验证并勾选:
- [ ] 案件列表: 首次加载是否闪现 TableSkeleton → 数据展示
- [ ] 案件列表: 空数据（username 搜不存在的值）→ EmptyState "暂无案件"
- [ ] 案件详情: 点击某条记录加载 → DetailSkeleton → 详情展示
- [ ] 批量预测: 历史任务列表为空 → EmptyState "暂无批量预测任务"
- [ ] 用户管理: 用户列表为空 → EmptyState "暂无用户"
- [ ] ErrorBoundary: 在任意页面控制台执行 `throw new Error('test')` → 显示 Result 错误页 + "刷新页面" 按钮 → 点击刷新恢复正常

> 注: DashboardPage 骨架屏暂不验证（StatsCards 内部自行加载，已知改进项）

- [ ] **Step 3: Commit（如有修复）**

```bash
git status
# 如有修复，commit
```
