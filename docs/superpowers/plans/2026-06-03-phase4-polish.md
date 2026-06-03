# Phase 4 收尾修复 — 5 项已知问题 实现计划

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 修复 Phase 1-4 后 5 个已知问题：FEATURE_COLS 顺序不一致（JSON + 代码防御）、StatsCards 加载态缺失、ErrorBoundary 缺 componentDidCatch、Skeleton/EmptyState 视觉验证+补缺、批量预测端到端测试

**Architecture:** 5 个独立任务，前 4 个是代码修改（3 前端 + 1 后端），最后 1 个是功能测试。Task 1 是唯一涉及数据正确性的（JSON 对齐模型 + 代码防御重排），其余为前端体验优化和验证。

**Tech Stack:** Python 3（preprocess_params.json, feature_transform.py）+ React/TypeScript（StatsCards, ErrorBoundary, BatchPredictPage）

**关键发现:** `preprocess_params.json` 的 `feature_cols` 顺序为 `cont(23) → cat(7) → missing(5)`，而模型 pickle 期望 `cat(7) → missing(5) → cont(23)`，两者完全不同。

---

## 文件变更清单

| 文件 | 变更类型 | 职责 |
|------|----------|------|
| `backend/app/services/preprocess_params.json` | 修改 | 调整 feature_cols 顺序与模型一致 |
| `backend/app/services/feature_transform.py:184-185` | 修改 | 防御性重排：最终列序对齐模型 |
| `frontend/src/components/dashboard/StatsCards.tsx` | 修改 | 添加 loading 状态 + CardSkeleton |
| `frontend/src/components/common/ErrorBoundary.tsx` | 修改 | 补充 componentDidCatch 日志 |
| `frontend/src/pages/BatchPredictPage.tsx` | 修改 | 历史任务列表添加 TableSkeleton |

---

### Task 1: 修复 FEATURE_COLS 顺序 — JSON 对齐模型 + 代码防御

**根因:** `preprocess_params.json` 的 `feature_cols` 顺序 (cont→cat→missing) 与模型 pickle 期望的 `feature_cols` 顺序 (cat→missing→cont) 不一致。`batch_tasks.py:140` 的 `X = X[model_service.get_feature_cols()]` 是补丁式修复，根因未消除。`transform_single()` 内部应按模型顺序输出，而非依赖调用方重排。

**Files:**
- Modify: `backend/app/services/preprocess_params.json`
- Modify: `backend/app/services/feature_transform.py:184-185`

- [ ] **Step 1: 更新 `preprocess_params.json` 的 `feature_cols` 顺序**

将 `feature_cols` 数组（第 43-78 行）从 `cont_cols + cat_cols + missing_cols` 改为模型顺序 `cat_cols + missing_cols + cont_cols`。

当前顺序（cont→cat→missing）:
```json
"feature_cols": [
  "SUB_AMT",
  "TOTAL_RECEIPT_AMT",
  ...
  "MBR_UNIQUE_HOSPITALS",
  "ICD10_CHAPTER",
  ...
  "POCY_PLAN_DESC",
  "TOTAL_RECEIPT_AMT_MISSING",
  ...
  "KIND_CODE_MISSING"
]
```

改为模型顺序（cat→missing→cont）:
```json
"feature_cols": [
  "ICD10_CHAPTER",
  "BH_PREFIX",
  "BH_CATEGORY",
  "MBR_TYPE",
  "BEN_TYPE",
  "KIND_CODE",
  "POCY_PLAN_DESC",
  "TOTAL_RECEIPT_AMT_MISSING",
  "DAYS_INCUR_TO_PAY_MISSING",
  "DAYS_RCV_TO_CLOSE_MISSING",
  "DAYS_RCV_TO_PAY_MISSING",
  "KIND_CODE_MISSING",
  "SUB_AMT",
  "TOTAL_RECEIPT_AMT",
  "ORG_PRES_AMT_VALUE",
  "COPAY_PCT",
  "NO_OF_YR",
  "POLICY_CNT",
  "INVOICE_CNT",
  "DAYS_INCUR_TO_PAY",
  "DAYS_RCV_TO_CLOSE",
  "DAYS_HOSPITALIZATION",
  "DAYS_RCV_TO_PAY",
  "IS_INPATIENT",
  "INCUR_MONTH",
  "INCUR_DAYOFWEEK",
  "INCUR_QUARTER",
  "INCUR_IS_WEEKEND",
  "PROV_LEVEL_ORDINAL",
  "RECEIPT_TO_SUB_RATIO",
  "IS_NEW_INSURED",
  "IS_LONGTERM_INSURED",
  "MBR_CLAIM_COUNT",
  "MBR_AVG_SUB_AMT",
  "MBR_UNIQUE_HOSPITALS"
]
```

- [ ] **Step 2: 在 `feature_transform.py` 末尾添加防御性重排**

将 `transform_single` 函数的最后一行（当前为 `return df[FEATURE_COLS]`）改为使用模型期望的顺序：

```python
# feature_transform.py, line 184-185 — 替换这两行:
    # 6) 确保 final 列序（输入已验证完整，直接按 FEATURE_COLS 排列）
    return df[FEATURE_COLS]

# 改为:
    # 6) 确保 final 列序与模型期望一致（防御性对齐，防止 JSON 配置漂移）
    from backend.app.services import model_service
    model_cols = model_service.get_feature_cols()
    if list(df.columns) != model_cols:
        logger.warning(
            "transform_single: 列序与模型不一致，自动重排。请检查 preprocess_params.json 的 feature_cols。"
        )
        return df[model_cols]
    return df
```

> 说明：将 import 放在函数内部以避免模块级循环依赖（`feature_transform` 和 `model_service` 目前互不依赖）。

- [ ] **Step 3: 移除 batch_tasks.py 中的冗余重排**

`batch_tasks.py:140` 的 `X = X[model_service.get_feature_cols()]` 在 Step 2 后变为冗余（`transform_single` 已保证正确顺序）。移除该行及上方注释以消除混淆：

```python
# batch_tasks.py, 删除 line 138-140:
# 当前:
                X = feature_transform.transform_single(feature_dict)
                # transform_single 返回 params 顺序，模型要求不同顺序，需显式重排
                X = X[model_service.get_feature_cols()]

# 改为:
                X = feature_transform.transform_single(feature_dict)
```

- [ ] **Step 4: 验证修复**

```bash
uv run python -c "
from backend.app.services import feature_transform, model_service

d = {}
for c in model_service.get_feature_cols():
    d[c] = 0.0

X = feature_transform.transform_single(d)
expected = model_service.get_feature_cols()
actual = list(X.columns)
assert actual == expected, f'MISMATCH!\nExpected: {expected}\nActual:   {actual}'
print('PASS: transform_single column order matches model')
"
```

- [ ] **Step 5: Commit**

```bash
git add backend/app/services/preprocess_params.json backend/app/services/feature_transform.py backend/app/tasks/batch_tasks.py
git commit -m "fix: align preprocess_params.json feature_cols order with model, add defensive reorder in transform_single"
```

---

### Task 2: StatsCards 加载优化

**Files:**
- Modify: `frontend/src/components/dashboard/StatsCards.tsx`

- [ ] **Step 1: 添加 loading 状态和 CardSkeleton**

将 StatsCards 从初始显示 4 张全 0 卡片改为加载中显示 `CardSkeleton`，加载完成后显示数据。

完整修改后的文件：

```tsx
import { useEffect, useState } from 'react';
import { Card, Col, Row, Statistic } from 'antd';
import {
  ClockCircleOutlined,
  WarningOutlined,
  CheckCircleOutlined,
  DatabaseOutlined,
} from '@ant-design/icons';
import { fetchStats } from '../../api/dashboard';
import type { DashboardStats } from '../../types';
import { CardSkeleton } from '../common/Skeleton';

export default function StatsCards() {
  const [stats, setStats] = useState<DashboardStats | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    fetchStats()
      .then(setStats)
      .catch(() => {})
      .finally(() => setLoading(false));

    const interval = setInterval(() => {
      fetchStats().then(setStats).catch(() => {});
    }, 60_000);
    return () => clearInterval(interval);
  }, []);

  if (loading) {
    return <CardSkeleton count={4} />;
  }

  return (
    <Row gutter={16}>
      <Col span={6}>
        <Card>
          <Statistic
            title="今日待审核"
            value={stats?.today_pending ?? 0}
            prefix={<ClockCircleOutlined />}
          />
        </Card>
      </Col>
      <Col span={6}>
        <Card>
          <Statistic
            title="今日高风险"
            value={stats?.today_high_risk ?? 0}
            prefix={<WarningOutlined />}
            styles={{ content: { color: '#cf1322' } }}
          />
        </Card>
      </Col>
      <Col span={6}>
        <Card>
          <Statistic
            title="今日已处理"
            value={stats?.today_processed ?? 0}
            prefix={<CheckCircleOutlined />}
            styles={{ content: { color: '#3f8600' } }}
          />
        </Card>
      </Col>
      <Col span={6}>
        <Card>
          <Statistic
            title="累计检测量"
            value={stats?.total_detected ?? 0}
            prefix={<DatabaseOutlined />}
          />
        </Card>
      </Col>
    </Row>
  );
}
```

- [ ] **Step 2: TypeScript 检查**

```bash
cd frontend && npx tsc --noEmit
```

- [ ] **Step 3: Commit**

```bash
git add frontend/src/components/dashboard/StatsCards.tsx
git commit -m "feat: add CardSkeleton loading state to StatsCards"
```

---

### Task 3: ErrorBoundary 补充 componentDidCatch

**Files:**
- Modify: `frontend/src/components/common/ErrorBoundary.tsx`

- [ ] **Step 1: 添加 componentDidCatch 日志记录**

```tsx
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

  componentDidCatch(error: Error, info: React.ErrorInfo) {
    console.error('[ErrorBoundary] Uncaught error:', error.message);
    console.error('[ErrorBoundary] Component stack:', info.componentStack);
    // 后续可接入错误上报服务（如 Sentry）
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

- [ ] **Step 2: TypeScript 检查**

```bash
cd frontend && npx tsc --noEmit
```

- [ ] **Step 3: Commit**

```bash
git add frontend/src/components/common/ErrorBoundary.tsx
git commit -m "fix: add componentDidCatch logging to ErrorBoundary"
```

---

### Task 4: Skeleton/EmptyState 视觉验证 + 补充缺失加载态

**Files:**
- Modify: `frontend/src/pages/BatchPredictPage.tsx`
- Review（无需修改，仅验证）: `CaseListPage.tsx`, `CaseDetailPage.tsx`, `DashboardPage.tsx`, `AdminPage.tsx`, `UserManagement.tsx`, `DataUpload.tsx`

- [ ] **Step 1: BatchPredictPage 历史任务列表添加 TableSkeleton**

当前历史列表在 `loadTaskList` 执行期间无骨架屏。添加 `listLoading` 状态和 `TableSkeleton`。

```tsx
// BatchPredictPage.tsx — 新增 state:
const [listLoading, setListLoading] = useState(false);

// 修改 loadTaskList:
const loadTaskList = useCallback(async () => {
  setListLoading(true);
  try {
    const data = await fetchBatchList(1, 20);
    setTaskList(data.items);
  } catch {
    // ignore
  } finally {
    setListLoading(false);
  }
}, []);

// JSX — 在历史任务 Card 内添加 loading 分支:
<Card title="历史任务">
  {listLoading ? (
    <TableSkeleton rows={5} />
  ) : taskList.length === 0 ? (
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

顶部导入添加：
```tsx
import { TableSkeleton } from '../components/common/Skeleton';
```

- [ ] **Step 2: 逐页视觉验证清单**

启动前端开发服务器后，逐页检查：

| 页面 | 检查项 | 预期 |
|------|--------|------|
| DashboardPage | StatsCards 首次加载 | CardSkeleton（4 列骨架卡片），加载完成后显示数据 |
| DashboardPage | 趋势图首次加载 | Spin 居中显示 |
| DashboardPage | HighRiskTable 空数据 | 空表格（无特殊处理，可接受） |
| PredictionPage | 表单始终可见 | 无骨架（设计如此） |
| BatchPredictPage | 历史列表首次加载 | TableSkeleton（5 行），加载完成后显示数据或 EmptyState |
| BatchPredictPage | 空任务列表 | EmptyState "暂无批量预测任务" |
| CaseListPage | 列表首次加载 | TableSkeleton |
| CaseListPage | 筛选后无结果 | EmptyState "暂无案件" |
| CaseDetailPage | 详情加载 | DetailSkeleton（4 卡片） |
| CaseDetailPage | 案件不存在 | EmptyState "案件不存在" |
| AdminPage/用户管理 | 列表首次加载 | Table 内置 loading={true} |
| AdminPage/用户管理 | 空列表 | EmptyState "暂无用户" |
| AdminPage/数据管理 | 空任务 | Table locale "暂无导入任务" |

- [ ] **Step 3: TypeScript 检查**

```bash
cd frontend && npx tsc --noEmit
```

- [ ] **Step 4: Commit**

```bash
git add frontend/src/pages/BatchPredictPage.tsx
git commit -m "feat: add TableSkeleton loading state to BatchPredictPage history list"
```

---

### Task 5: 批量预测端到端功能测试

**Files:** 无代码修改，纯验证

- [ ] **Step 1: 准备测试数据**

创建测试 CSV 文件（5 行，包含全部 35 特征列，用模型期望的列名和顺序）:

```csv
ICD10_CHAPTER,BH_PREFIX,BH_CATEGORY,MBR_TYPE,BEN_TYPE,KIND_CODE,POCY_PLAN_DESC,TOTAL_RECEIPT_AMT_MISSING,DAYS_INCUR_TO_PAY_MISSING,DAYS_RCV_TO_CLOSE_MISSING,DAYS_RCV_TO_PAY_MISSING,KIND_CODE_MISSING,SUB_AMT,TOTAL_RECEIPT_AMT,ORG_PRES_AMT_VALUE,COPAY_PCT,NO_OF_YR,POLICY_CNT,INVOICE_CNT,DAYS_INCUR_TO_PAY,DAYS_RCV_TO_CLOSE,DAYS_HOSPITALIZATION,DAYS_RCV_TO_PAY,IS_INPATIENT,INCUR_MONTH,INCUR_DAYOFWEEK,INCUR_QUARTER,INCUR_IS_WEEKEND,PROV_LEVEL_ORDINAL,RECEIPT_TO_SUB_RATIO,IS_NEW_INSURED,IS_LONGTERM_INSURED,MBR_CLAIM_COUNT,MBR_AVG_SUB_AMT,MBR_UNIQUE_HOSPITALS
XIX,5500,17,GR,P20,3,PPPP2402,0,0,0,0,0,2500.00,3000.00,1500.00,20.0,5,2,3,10,5,2,7,0,3,3,1,0,3,0.83,0,1,1,2500.00,1
XIX,5500,17,GR,P20,3,PPPP2402,0,0,0,0,0,5000.00,6000.00,3000.00,10.0,3,1,1,15,3,0,5,1,6,2,2,0,2,0.83,1,0,2,5000.00,1
XIII,3400,12,GR,B20,2,PPPP2301,0,0,0,0,0,1500.00,1800.00,900.00,30.0,8,3,5,20,7,3,10,0,11,5,4,1,4,0.83,0,0,3,1500.00,2
XIX,5500,17,GR,P20,3,PPPP2402,0,0,0,0,0,1200.00,1500.00,800.00,25.0,2,1,2,8,2,1,4,0,2,1,1,0,1,0.80,1,1,0,0.00,0
XIII,3400,12,GR,B20,2,PPPP2301,0,0,0,0,0,8000.00,9000.00,5000.00,15.0,10,5,8,25,10,5,14,1,8,4,3,1,5,0.89,0,0,5,8000.00,3
```

> 注意：CSV 列顺序与 Task 1 修复后的模型期望顺序一致（cat→missing→cont）。

- [ ] **Step 2: 启动服务**

```bash
docker compose up -d postgres redis
uv run uvicorn backend.app.main:app --reload --port 8000 &
uv run celery -A backend.app.tasks.celery_app worker --loglevel=info --pool=solo --without-mingle --without-gossip --without-heartbeat &
cd frontend && npm run dev &
```

- [ ] **Step 3: 正常流程测试**

1. 登录系统
2. 进入"批量预测"页面
3. 上传测试 CSV 文件
4. 验证：
   - ✅ 上传后出现任务进度卡片
   - ✅ 状态从 pending → processing → completed
   - ✅ 进度数字递增
   - ✅ 完成后显示"下载结果"按钮
   - ✅ 下载结果 CSV 包含原始列 + `fraud_prob` + `risk_level` + `shap_top_features`
5. 刷新页面 → 历史任务列表显示该任务

- [ ] **Step 4: 边界情况测试**

| 测试场景 | 预期行为 |
|----------|----------|
| 上传非 CSV/Excel 文件（.txt） | 前端拦截 "仅支持 CSV 和 Excel 文件" |
| 上传缺少必需列的文件 | 行处理失败，risk_level 为 "error" |
| 上传空文件 | 后端返回 400 "文件为空" |
| Excel 格式 (.xlsx) | 正常处理，与 CSV 结果一致 |

- [ ] **Step 5: 记录结果**

测试完成后将结果写入 `docs/superpowers/plans/2026-06-03-phase4-polish-results.md`。
