import { Tabs } from 'antd';
import UserManagement from '../components/admin/UserManagement';
import DataUpload from '../components/admin/DataUpload';

export default function AdminPage() {
  return (
    <Tabs
      defaultActiveKey="users"
      items={[
        { key: 'users', label: '用户管理', children: <UserManagement /> },
        { key: 'data', label: '数据管理', children: <DataUpload /> },
      ]}
    />
  );
}
