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

## 模块 2-4（后续设计）

模块 2（数据管理）、3（打磨）将在各自阶段细化设计。
