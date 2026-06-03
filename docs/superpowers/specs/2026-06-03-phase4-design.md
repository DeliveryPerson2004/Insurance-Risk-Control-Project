# Phase 4: 管理面板 + 打磨 — 设计文档

## Phase 4 概览

3 个模块按优先级排列：用户管理 → 数据管理 → 打磨。（模型监控已取消：单模型无 ground truth，不具备实施条件）

---

## 模块 1: 用户管理

### 后端

**新增文件**：
- `backend/app/schemas/admin.py` — Pydantic 模型：
  - `UserOut` — 用户列表项（user_id, username, display_name, user_role, email, phone, is_active, last_login, created_at），复用现有 `types/index.ts` 中的 `User` 接口字段
  - `UserListResponse` — 分页响应（items: list[UserOut], total, page, size）
  - `UpdateUserRequest` — 修改请求（user_role: admin|reviewer, is_active: bool）
- `backend/app/services/admin_service.py` — 用户 CRUD 业务逻辑
- `backend/app/routers/admin.py` — 挂载 `/api/admin/*` 子路由，所有端点依赖 `require_admin`

**API 设计**：

| 方法 | 路径 | 说明 | 权限 |
|------|------|------|------|
| `GET` | `/api/admin/users` | 用户分页列表（支持 username 搜索） | admin |
| `PUT` | `/api/admin/users/{user_id}` | 修改角色 + 停用/启用 | admin |

**数据流**：Router → Service → SQLAlchemy async query → Pydantic 序列化。复用 `require_admin` 依赖。  
**约束**：用户不能编辑自己的角色或停用自己（API 层校验）。

### 前端

**新增文件**：
- `frontend/src/api/admin.ts` — admin API 调用
- `frontend/src/components/admin/UserManagement.tsx` — 用户表格 + 操作
- `frontend/src/pages/AdminPage.tsx` — 管理面板 Tabs 容器页

**修改文件**：
- `frontend/src/App.tsx` — 替换 `/admin` 占位路由为 `<AdminPage />`
- `frontend/src/types/index.ts` — 新增类型：
  - `UpdateUserRequest` — `{ user_role: 'admin' | 'reviewer'; is_active: boolean }`
  - `UserListResponse` — `{ items: User[]; total: number; page: number; size: number }`
  - （`User` 类型已存在，无需新增）

**UserManagement 组件**：
- Ant Design Table，列：用户名、显示名、角色、邮箱、状态、最后登录、操作
- 操作列：角色下拉切换 + 启用/停用 Switch
- 搜索框：按用户名模糊搜索
- 当前登录用户不能编辑自己的角色或停用自己

**AdminPage 组件**：
- Ant Design Tabs，Tab 1 = "用户管理"
- 后续 Phase 4 模块追加 Tab（数据管理）

### 路由守卫

- 已有 `ProtectedRoute`（检查登录态）
- 已有 `AppLayout` 中 admin 菜单仅对 admin 角色可见
- 后端 `require_admin` 依赖用于 API 层面控制

---

## 模块 2: 数据管理

### 管线架构

```
原始 Excel (108列)
    │
    ▼
┌─────────────────────────────┐
│ preprocess_service (新增)     │  ← 从 data/preprocessing.py 提取
│  金额清洗 / 日期特征 /        │
│  ICD-10映射 / BEN_HEAD拆分   │
│  PROV_LEVEL序数 / 聚合特征    │
│  → 输出 35 特征 (原始值)      │
└──────────────┬──────────────┘
               ▼
┌─────────────────────────────┐
│ feature_transform.py (现有)  │  ← 复用
│  缺失标记 / fill / winsor    │
│  log / scaler / 排序列       │
│  → 输出 35 特征 (缩放后)      │
└──────────────┬──────────────┘
               ▼
┌─────────────────────────────┐
│ model_service.py (现有)      │  ← 复用
│  XGBoost → Isotonic → 判定  │
└──────────────┬──────────────┘
               ▼
┌─────────────────────────────┐
│ 入库                         │
│  Insuree / Policy / Claim   │
│  FraudDetectResult           │
└─────────────────────────────┘
```

**关键约束**：
- FRAUD 标签不计算、不使用，即便 `RJ_CODE_LIST` 存在也不碰
- 预处理后的记录进入已有案件管理系统（`/cases`），无需新建结果展示页面
- 与老师标注的对比为线下操作，不在系统中

### 后端

**新增文件**：
- `backend/app/services/preprocess_service.py` — 从 `data/preprocessing.py` 提取的 108→35 预处理逻辑：
  - 金额清洗（RMB 去除、千位逗号、空值处理）
  - 日期特征（INCUR_DATE_FROM/TO → DAYS_*, INCUR_MONTH, INCUR_DAYOFWEEK, INCUR_QUARTER, INCUR_IS_WEEKEND, IS_INPATIENT）
  - ICD-10 章节映射（DIAG_CODE → ICD10_CHAPTER，含 D 系修正）
  - BEN_HEAD 拆分（BH_PREFIX + BH_CATEGORY）
  - PROV_LEVEL 序数化（一级→1, 二级→2, 三级→3, 医保→10, 非医保→11, etc.）
  - 被保人聚合特征（MBR_CLAIM_COUNT, MBR_AVG_SUB_AMT, MBR_UNIQUE_HOSPITALS）
  - 派生特征（RECEIPT_TO_SUB_RATIO, IS_NEW_INSURED, IS_LONGTERM_INSURED）
  - 类别特征标准化（MBR_TYPE, BEN_TYPE, KIND_CODE, POCY_PLAN_DESC → uppercase + UNKNOWN 填充）
  - 输出：35 特征 DataFrame（未经 winsor/log/scaler 处理，留给 feature_transform.py）
- `backend/app/tasks/data_tasks.py` — Celery 异步任务：
  - 解析上传的 Excel → 调 preprocess_service → 调 feature_transform → 调 model_service.predict → 入库
  - 进度追踪（复用现有 Redis 进度模式，参考 batch_tasks.py）
- 修改 `backend/app/tasks/celery_app.py` — include 新增 data_tasks

**修改文件**：
- `backend/app/routers/admin.py` — 追加 3 个端点：

| 方法 | 路径 | 说明 | 权限 |
|------|------|------|------|
| `POST` | `/api/admin/data/upload` | 上传原始 Excel，创建数据导入任务 | admin |
| `GET` | `/api/admin/data/tasks` | 历史导入任务列表（分页） | admin |
| `GET` | `/api/admin/data/tasks/{task_id}/status` | 任务进度查询 | admin |

- `backend/app/schemas/admin.py` — 追加 DataTaskStatus、DataTaskListResponse
- `backend/app/services/admin_service.py` — 追加数据任务相关查询

### 前端

**新增文件**：
- `frontend/src/components/admin/DataUpload.tsx` — 上传组件：
  - Ant Design Upload（拖拽上传，限制 .xlsx/.xls）
  - 任务列表 Table（状态、文件名、进度、时间）
  - 自动轮询进行中任务状态（30s）

**修改文件**：
- `frontend/src/pages/AdminPage.tsx` — 追加"数据管理"Tab
- `frontend/src/api/admin.ts` — 追加 `uploadData()`, `fetchDataTasks()`, `fetchDataTaskStatus()`
- `frontend/src/types/index.ts` — 追加 `DataTaskStatus`, `DataTaskItem`

---

## 模块 3（后续设计）

模块 3（打磨）将在数据管理完成后细化设计。
