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
