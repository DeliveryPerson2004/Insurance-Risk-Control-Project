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
  const [keyword, setKeyword] = useState('');
  const currentUser = useAuthStore((s) => s.user);

  const loadUsers = useCallback(async () => {
    setLoading(true);
    try {
      const res = await fetchUsers({ page, size, username: keyword || undefined });
      setUsers(res.items);
      setTotal(res.total);
    } catch {
      message.error('加载用户列表失败');
    } finally {
      setLoading(false);
    }
  }, [page, size, keyword]);

  useEffect(() => {
    loadUsers();
  }, [loadUsers]);

  const handleSearch = () => {
    setKeyword(search);
    setPage(1);
  };

  const handleRoleChange = async (userId: string, userRole: string) => {
    try {
      await updateUser(userId, {
        user_role: userRole as 'admin' | 'reviewer',
      });
      message.success('角色已更新');
      loadUsers();
    } catch {
      message.error('更新角色失败');
    }
  };

  const handleActiveChange = async (userId: string, isActive: boolean) => {
    try {
      await updateUser(userId, {
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
          onChange={(e) => setSearch(e.target.value)}
          onPressEnter={handleSearch}
          onClear={() => {
            setSearch('');
            setKeyword('');
            setPage(1);
          }}
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
