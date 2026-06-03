import { Tabs } from 'antd';
import { TeamOutlined, CloudUploadOutlined } from '@ant-design/icons';
import UserManagement from '../components/admin/UserManagement';
import DataUpload from '../components/admin/DataUpload';

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
        {
          key: 'data',
          label: (
            <span><CloudUploadOutlined /> 数据管理</span>
          ),
          children: <DataUpload />,
        },
      ]}
    />
  );
}
