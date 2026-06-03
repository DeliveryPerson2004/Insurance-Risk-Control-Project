# Phase 4 模块 1: 用户管理 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 为管理员提供用户列表查看、角色修改、停用/启用功能

**Architecture:** 后端新增 admin router/service/schema 三层，复用 `require_admin` 权限依赖；前端新增 AdminPage（Tabs 容器）+ UserManagement 组件，替换现有 `/admin` 占位路由

**Tech Stack:** FastAPI + SQLAlchemy 2.0 async + Pydantic v2 + React 18 + TypeScript + Ant Design 5

---

### Task 1: 新增 Pydantic Schema

**Files:**
- Create: `backend/app/schemas/admin.py`

- [ ] **Step 1: 创建 admin schema 文件**

```python
"""管理面板相关 Pydantic v2 schemas."""

from datetime import datetime
from pydantic import BaseModel, Field


class UpdateUserRequest(BaseModel):
    user_role: str = Field(..., pattern="^(admin|reviewer)$")
    is_active: bool


class UserOut(BaseModel):
    user_id: str
    username: str
    display_name: str
    user_role: str
    email: str | None
    phone: str | None
    is_active: bool
    last_login: datetime | None
    created_at: datetime | None = None

    model_config = {"from_attributes": True}


class UserListResponse(BaseModel):
    items: list[UserOut]
    total: int
    page: int
    size: int
```

- [ ] **Step 2: 验证 schema 语法**

```bash
uv run python -c "from backend.app.schemas.admin import UpdateUserRequest, UserOut, UserListResponse; print('OK')"
```

- [ ] **Step 3: Commit**

```bash
git add backend/app/schemas/admin.py
git commit -m "feat: add admin Pydantic schemas for user management"
```

---

### Task 2: 新增 Admin Service

**Files:**
- Create: `backend/app/services/admin_service.py`

- [ ] **Step 1: 创建 admin service**

```python
"""管理面板业务逻辑."""

from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.models.user import User
from backend.app.utils.exceptions import AppException


async def list_users(
    db: AsyncSession,
    page: int = 1,
    size: int = 20,
    username: str | None = None,
) -> tuple[list[User], int]:
    """分页查询用户列表，支持按 username 模糊搜索."""
    base = select(User)
    count_base = select(func.count(User.user_id))

    if username:
        pattern = f"%{username}%"
        base = base.where(User.username.ilike(pattern))
        count_base = count_base.where(User.username.ilike(pattern))

    # 总数
    total_result = await db.execute(count_base)
    total = total_result.scalar() or 0

    # 分页
    offset = (page - 1) * size
    result = await db.execute(
        base.order_by(User.created_at.desc()).offset(offset).limit(size)
    )
    users = list(result.scalars().all())

    return users, total


async def update_user(
    db: AsyncSession,
    user_id: str,
    user_role: str | None,
    is_active: bool | None,
    operated_by: str,
) -> User:
    """修改用户角色或状态。operated_by 为操作者 ID，禁止修改自己."""
    if user_id == operated_by:
        raise AppException("不能修改自己的角色或状态", status_code=400)

    result = await db.execute(select(User).where(User.user_id == user_id))
    user = result.scalar_one_or_none()
    if user is None:
        raise AppException("用户不存在", status_code=404)

    if user_role is not None:
        user.user_role = user_role  # type: ignore
    if is_active is not None:
        user.is_active = is_active

    await db.commit()
    await db.refresh(user)
    return user
```

- [ ] **Step 2: 验证 service 语法**

```bash
uv run python -c "from backend.app.services import admin_service; print('OK')"
```

- [ ] **Step 3: Commit**

```bash
git add backend/app/services/admin_service.py
git commit -m "feat: add admin service for user list and update"
```

---

### Task 3: 新增 Admin Router

**Files:**
- Create: `backend/app/routers/admin.py`

- [ ] **Step 1: 创建 admin router**

```python
"""管理面板路由 — 用户管理."""

from fastapi import APIRouter, Depends, Query
from fastapi.responses import JSONResponse
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.database import get_db
from backend.app.deps import get_current_user, require_admin
from backend.app.models.user import User
from backend.app.schemas.admin import UpdateUserRequest, UserOut, UserListResponse
from backend.app.services import admin_service

router = APIRouter(prefix="/api/admin", tags=["admin"])


def ok(data):
    return JSONResponse(content={"code": 0, "data": data, "message": "ok"})


@router.get("/users")
async def list_users(
    page: int = Query(default=1, ge=1),
    size: int = Query(default=20, ge=1, le=100),
    username: str | None = Query(default=None),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_admin),
):
    users, total = await admin_service.list_users(db, page, size, username)
    return ok(
        UserListResponse(
            items=[UserOut.model_validate(u) for u in users],
            total=total,
            page=page,
            size=size,
        ).model_dump()
    )


@router.put("/users/{user_id}")
async def update_user(
    user_id: str,
    body: UpdateUserRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_admin),
):
    updated = await admin_service.update_user(
        db, user_id, body.user_role, body.is_active, current_user.user_id
    )
    return ok(UserOut.model_validate(updated).model_dump())
```

- [ ] **Step 2: 在 main.py 注册路由**

在 `backend/app/main.py` 中，agent 路由注册之后、health 端点之前添加：

```python
    # 注册 admin 路由（Phase 4）
    from backend.app.routers.admin import router as admin_router
    app.include_router(admin_router)
```

- [ ] **Step 3: 验证 router 语法**

```bash
uv run python -c "from backend.app.routers.admin import router; print('OK')"
```

- [ ] **Step 4: Commit**

```bash
git add backend/app/routers/admin.py backend/app/main.py
git commit -m "feat: add admin router for user management endpoints"
```

---

### Task 4: 前端类型定义

**Files:**
- Modify: `frontend/src/types/index.ts`

- [ ] **Step 1: 在 types/index.ts 末尾追加 admin 类型**

在文件末尾添加：

```typescript
// ---- 管理面板 ----
export interface UpdateUserRequest {
  user_role: 'admin' | 'reviewer';
  is_active: boolean;
}

export interface UserListResponse {
  items: User[];
  total: number;
  page: number;
  size: number;
}
```

- [ ] **Step 2: TypeScript 类型检查**

```bash
cd frontend && npx tsc --noEmit
```

- [ ] **Step 3: Commit**

```bash
git add frontend/src/types/index.ts
git commit -m "feat: add admin-related TypeScript types"
```

---

### Task 5: 前端 API 模块

**Files:**
- Create: `frontend/src/api/admin.ts`

- [ ] **Step 1: 创建 admin API 模块**

```typescript
import client from './client';
import type { ApiResponse, User, UserListResponse, UpdateUserRequest } from '../types';

export async function fetchUsers(params: {
  page?: number;
  size?: number;
  username?: string;
}): Promise<UserListResponse> {
  const res = await client.get<ApiResponse<UserListResponse>>('/admin/users', { params });
  return res.data.data;
}

export async function updateUser(
  userId: string,
  body: UpdateUserRequest,
): Promise<User> {
  const res = await client.put<ApiResponse<User>>(`/admin/users/${userId}`, body);
  return res.data.data;
}
```

- [ ] **Step 2: TypeScript 类型检查**

```bash
cd frontend && npx tsc --noEmit
```

- [ ] **Step 3: Commit**

```bash
git add frontend/src/api/admin.ts
git commit -m "feat: add admin API client module"
```

---

### Task 6: UserManagement 组件

**Files:**
- Create: `frontend/src/components/admin/UserManagement.tsx`

- [ ] **Step 1: 创建用户管理表格组件**

```typescript
import { useState, useEffect, useCallback } from 'react';
import {
  Table, Select, Switch, Input, message, Tag, Space, Typography,
} from 'antd';
import { SearchOutlined } from '@ant-design/icons';
import type { ColumnsType } from 'antd/es/table';
import { fetchUsers, updateUser } from '../../api/admin';
import { useAuthStore } from '../../store/authStore';
import type { User } from '../../types';

const { Text } = Typography;

const ROLE_OPTIONS = [
  { value: 'admin', label: '管理员' },
  { value: 'reviewer', label: '审核员' },
];

const ROLE_COLOR: Record<string, string> = {
  admin: 'red',
  reviewer: 'blue',
};

export default function UserManagement() {
  const [users, setUsers] = useState<User[]>([]);
  const [total, setTotal] = useState(0);
  const [page, setPage] = useState(1);
  const [size, setSize] = useState(20);
  const [loading, setLoading] = useState(false);
  const [search, setSearch] = useState('');
  const currentUser = useAuthStore((s) => s.user);

  const loadUsers = useCallback(async () => {
    setLoading(true);
    try {
      const res = await fetchUsers({ page, size, username: search || undefined });
      setUsers(res.items);
      setTotal(res.total);
    } catch {
      message.error('加载用户列表失败');
    } finally {
      setLoading(false);
    }
  }, [page, size, search]);

  useEffect(() => {
    loadUsers();
  }, [loadUsers]);

  const handleRoleChange = async (userId: string, userRole: string) => {
    try {
      await updateUser(userId, {
        user_role: userRole as 'admin' | 'reviewer',
        is_active: true,
      });
      message.success('角色已更新');
      loadUsers();
    } catch {
      message.error('更新角色失败');
    }
  };

  const handleActiveChange = async (userId: string, isActive: boolean) => {
    try {
      const target = users.find((u) => u.user_id === userId);
      await updateUser(userId, {
        user_role: target?.user_role || 'reviewer',
        is_active: isActive,
      });
      message.success(isActive ? '已启用' : '已停用');
      loadUsers();
    } catch {
      message.error('状态更新失败');
    }
  };

  const columns: ColumnsType<User> = [
    { title: '用户名', dataIndex: 'username', key: 'username' },
    { title: '显示名', dataIndex: 'display_name', key: 'display_name' },
    {
      title: '角色', dataIndex: 'user_role', key: 'user_role',
      render: (role: string, record: User) => {
        if (record.user_id === currentUser?.user_id) {
          return <Tag color={ROLE_COLOR[role]}>{ROLE_OPTIONS.find((o) => o.value === role)?.label}</Tag>;
        }
        return (
          <Select
            size="small"
            value={role}
            options={ROLE_OPTIONS}
            style={{ width: 90 }}
            onChange={(val) => handleRoleChange(record.user_id, val)}
          />
        );
      },
    },
    {
      title: '邮箱', dataIndex: 'email', key: 'email',
      render: (v: string | null) => v || '-',
    },
    {
      title: '状态', dataIndex: 'is_active', key: 'is_active',
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
            <Text type={v ? 'success' : 'secondary'}>{v ? '启用' : '停用'}</Text>
          </Space>
        );
      },
    },
    {
      title: '最后登录', dataIndex: 'last_login', key: 'last_login',
      render: (v: string | null) => v ? new Date(v).toLocaleString() : '从未登录',
    },
  ];

  return (
    <div>
      <Space style={{ marginBottom: 16 }}>
        <Input
          placeholder="搜索用户名"
          prefix={<SearchOutlined />}
          allowClear
          style={{ width: 240 }}
          value={search}
          onChange={(e) => {
            setSearch(e.target.value);
            setPage(1);
          }}
          onPressEnter={() => loadUsers()}
        />
      </Space>
      <Table
        rowKey="user_id"
        columns={columns}
        dataSource={users}
        loading={loading}
        pagination={{
          current: page,
          pageSize: size,
          total,
          showSizeChanger: true,
          showTotal: (t) => `共 ${t} 个用户`,
          onChange: (p, s) => { setPage(p); setSize(s); },
        }}
      />
    </div>
  );
}
```

- [ ] **Step 2: TypeScript 类型检查**

```bash
cd frontend && npx tsc --noEmit
```

- [ ] **Step 3: Commit**

```bash
git add frontend/src/components/admin/UserManagement.tsx
git commit -m "feat: add UserManagement component with role/status editing"
```

---

### Task 7: AdminPage 容器 + 路由接入

**Files:**
- Create: `frontend/src/pages/AdminPage.tsx`
- Modify: `frontend/src/App.tsx`

- [ ] **Step 1: 创建 AdminPage 容器**

```typescript
import { Tabs } from 'antd';
import { TeamOutlined } from '@ant-design/icons';
import UserManagement from '../components/admin/UserManagement';

export default function AdminPage() {
  return (
    <Tabs
      defaultActiveKey="users"
      items={[
        {
          key: 'users',
          label: (
            <span><TeamOutlined /> 用户管理</span>
          ),
          children: <UserManagement />,
        },
      ]}
    />
  );
}
```

- [ ] **Step 2: 替换 App.tsx 中的占位路由**

将 `App.tsx` 中第 67 行：

```typescript
<Route path="admin" element={<div>管理面板（Phase 4）</div>} />
```

替换为：

```typescript
<Route path="admin" element={<AdminPage />} />
```

并在文件顶部的 import 区域添加：

```typescript
import AdminPage from './pages/AdminPage';
```

- [ ] **Step 3: TypeScript 类型检查**

```bash
cd frontend && npx tsc --noEmit
```

- [ ] **Step 4: Commit**

```bash
git add frontend/src/pages/AdminPage.tsx frontend/src/App.tsx
git commit -m "feat: wire up AdminPage with user management tab"
```

---

### Task 8: 端到端验证

- [ ] **Step 1: 启动后端并验证 API**

```bash
# 终端 1: 启动后端
docker compose up -d postgres
uv run uvicorn backend.app.main:app --reload --port 8000

# 终端 2: 测试 API（需要先注册 admin 用户并获取 token）
# 1. 注册 admin
curl -s -X POST http://localhost:8000/api/auth/register \
  -H "Content-Type: application/json" \
  -d '{"username":"admin_test","password":"123456","display_name":"管理员"}'

# 2. 登录获取 token
TOKEN=$(curl -s -X POST http://localhost:8000/api/auth/login \
  -H "Content-Type: application/json" \
  -d '{"username":"admin_test","password":"123456"}' | python -c "import sys,json; print(json.load(sys.stdin)['data']['tokens']['access_token'])")

# 3. 测试用户列表
curl -s http://localhost:8000/api/admin/users?page=1\&size=10 \
  -H "Authorization: Bearer $TOKEN" | python -m json.tool

# 4. 测试用户更新（将 self 改为其他 user_id）
# curl -s -X PUT http://localhost:8000/api/admin/users/<user_id> \
#   -H "Authorization: Bearer $TOKEN" \
#   -H "Content-Type: application/json" \
#   -d '{"user_role":"admin","is_active":false}'
```

- [ ] **Step 2: 前端验证**

```bash
cd frontend && npm run dev
# 浏览器访问 localhost:5173
# 1. 用 admin 用户登录
# 2. 左侧菜单应显示"管理面板"
# 3. 进入管理面板 → 用户管理 tab
# 4. 验证用户列表加载、角色下拉切换、启用/停用开关
# 5. 验证当前用户不能修改自己的角色和状态
```

- [ ] **Step 3: 非 admin 用户验证**

```bash
# 注册一个 reviewer 用户
curl -s -X POST http://localhost:8000/api/auth/register \
  -H "Content-Type: application/json" \
  -d '{"username":"reviewer_test","password":"123456"}'

# 用 reviewer 登录验证：
# 1. 左侧菜单不应显示"管理面板"
# 2. 直接访问 /admin 应被后端 API 拦截（403）
```

- [ ] **Step 4: Commit（如有修改）**

```bash
git status
# 如有修复，commit
```
