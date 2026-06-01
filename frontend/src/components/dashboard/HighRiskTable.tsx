import { useEffect, useState } from 'react';
import { Table, Tag } from 'antd';
import type { ColumnsType } from 'antd/es/table';
import { fetchHighRisk } from '../../api/dashboard';
import type { HighRiskItem } from '../../types';

const columns: ColumnsType<HighRiskItem> = [
  { title: '案件ID', dataIndex: 'policy_id', key: 'policy_id', width: 180 },
  {
    title: '欺诈概率',
    dataIndex: 'fraud_prob',
    key: 'fraud_prob',
    width: 100,
    render: (v: number) => (
      <span style={{ fontWeight: 600, color: v >= 0.7 ? '#ff4d4f' : '#faad14' }}>
        {(v * 100).toFixed(1)}%
      </span>
    ),
  },
  {
    title: '风险等级',
    dataIndex: 'risk_level',
    key: 'risk_level',
    width: 80,
    render: (v: string) => <Tag color={v === 'high' ? 'red' : 'orange'}>{v}</Tag>,
  },
  {
    title: '理赔金额',
    dataIndex: 'claim_amount',
    key: 'claim_amount',
    width: 100,
    render: (v: number | null) => (v != null ? v.toFixed(2) : '-'),
  },
];

export default function HighRiskTable() {
  const [items, setItems] = useState<HighRiskItem[]>([]);

  useEffect(() => {
    fetchHighRisk(5).then(setItems).catch(() => {});
  }, []);

  return (
    <div>
      <div style={{ fontWeight: 600, fontSize: 14, color: '#666', marginBottom: 12 }}>
        高风险案件 Top 5
      </div>
      <Table
        columns={columns}
        dataSource={items}
        rowKey="id"
        size="small"
        pagination={false}
      />
    </div>
  );
}
