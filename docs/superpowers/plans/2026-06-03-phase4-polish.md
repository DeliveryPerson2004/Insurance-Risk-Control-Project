# Phase 4 模块 3: 打磨 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 新增 3 个共用组件（ErrorBoundary / EmptyState / Skeleton），接入 5 个页面替换 loading spinner 和空状态

**Architecture:** 所有组件置于 `frontend/src/components/common/`，纯展示组件无业务逻辑依赖。ErrorBoundary 在 App.tsx 最外层包裹；Skeleton + EmptyState 各页面按需引入

**Tech Stack:** React 18 + TypeScript + Ant Design 5 (Result, Empty, Skeleton)

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
  icon?: ReactNode;
  action?: ReactNode;
}

export default function EmptyState({ description = '暂无数据', icon, action }: Props) {
  return (
    <Empty
      image={icon || Empty.PRESENTED_IMAGE_SIMPLE}
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

- [ ] **Step 1: DashboardPage — CardSkeleton 替换 StatsCards 加载态**

`DashboardPage.tsx` 不涉及数据获取（StatsCards 内部自行加载），但可以为未来扩展预留。当前 StatsCards 组件已自行处理 loading，跳过修改。DashboardPage 无需改动。

- [ ] **Step 2: CaseListPage — TableSkeleton + EmptyState**

在 `CaseListPage.tsx` 中:

导入区域添加:
```typescript
import { TableSkeleton } from '../components/common/Skeleton';
import EmptyState from '../components/common/EmptyState';
```

将 `<CaseTable>` 包裹替换现有的 loading 处理。找到 CaseTable 渲染处，改为条件渲染:

```typescript
// 修改前（在 return 中）:
<CaseTable ... />

// 修改后:
if (loading) {
  return <TableSkeleton />;
}
if (!loading && data.length === 0) {
  return <EmptyState description="暂无案件" />;
}
```

注意: 需要把 loading/data 提取到 return 之前做条件判断，然后将原来的 return JSX 放在 else 分支或 main return 中。

更简洁的做法是在 render 中:
```typescript
{loading ? (
  <TableSkeleton />
) : data.length === 0 ? (
  <EmptyState description="暂无案件" />
) : (
  <CaseTable data={data} total={total} loading={false} ... />
)}
```

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

- [ ] **Step 2: 视觉验证**

```bash
# 启动前端
cd frontend && npm run dev
# 浏览器访问 localhost:5173
# 验证:
# 1. 仪表盘加载时是否闪现 CardSkeleton（网络慢时可观察）
# 2. 案件列表加载 → 表格骨架屏
# 3. 空列表 → EmptyState
# 4. 案件详情加载 → 详情骨架屏
# 5. 批量预测空列表 → EmptyState
# 6. 抛异常验证 ErrorBoundary（在控制台手动 throw Error）
```

- [ ] **Step 3: Commit（如有修复）**

```bash
git status
# 如有修复，commit
```
