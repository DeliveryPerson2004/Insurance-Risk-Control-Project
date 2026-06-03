import { useEffect, useState } from 'react';
import { Table } from 'antd';
import type { ColumnsType } from 'antd/es/table';
import { fetchHighRisk } from '../../api/dashboard';
import type { HighRiskItem } from '../../types';
import { TableSkeleton } from '../common/Skeleton';

const probColor = (v: number): string => {
  if (v >= 0.7) return '#DC2626';
  if (v >= 0.3) return '#947008';
  return '#4A5630';
};

const columns: ColumnsType<HighRiskItem> = [
  {
    title: '案件ID',
    dataIndex: 'policy_id',
    key: 'policy_id',
    width: 180,
    render: (v: string) => <span style={{ fontFamily: "'Inter', sans-serif", fontWeight: 500 }}>{v}</span>,
  },
  {
    title: '欺诈概率',
    dataIndex: 'fraud_prob',
    key: 'fraud_prob',
    width: 100,
    render: (v: number) => (
      <span style={{ fontWeight: 600, color: probColor(v), fontFamily: "'Inter', sans-serif", fontFeatureSettings: "'tnum'" }}>
        {(v * 100).toFixed(1)}%
      </span>
    ),
  },
  {
    title: '风险等级',
    dataIndex: 'risk_level',
    key: 'risk_level',
    width: 80,
    render: (v: string) => {
      const color = v === 'high' ? '#DC2626' : '#947008';
      return (
        <span style={{ display: 'inline-flex', alignItems: 'center', gap: 4, fontSize: 12 }}>
          <span style={{ width: 6, height: 6, borderRadius: '50%', background: color, display: 'inline-block' }} />
          <span style={{ color }}>{v === 'high' ? '高风险' : '中风险'}</span>
        </span>
      );
    },
  },
  {
    title: '理赔金额',
    dataIndex: 'claim_amount',
    key: 'claim_amount',
    width: 100,
    render: (v: number | null) => (
      <span style={{ fontFamily: "'Inter', sans-serif", fontFeatureSettings: "'tnum'" }}>
        {v != null ? `¥${v.toLocaleString()}` : '-'}
      </span>
    ),
  },
];

export default function HighRiskTable() {
  const [items, setItems] = useState<HighRiskItem[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    fetchHighRisk(5)
      .then(setItems)
      .catch(() => {})
      .finally(() => setLoading(false));

    const interval = setInterval(() => {
      fetchHighRisk(5).then(setItems).catch(() => {});
    }, 60_000);
    return () => clearInterval(interval);
  }, []);

  return (
    <div style={{
      background: '#FFFFFF',
      border: '1px solid #E7E5E2',
      borderRadius: 6,
      padding: '20px 24px',
      boxShadow: '0 1px 2px rgba(0,0,0,0.04)',
    }}>
      <h4 style={{ marginBottom: 16 }}>高风险案件 Top 5</h4>
      {loading ? (
        <TableSkeleton rows={5} />
      ) : (
        <Table
          columns={columns}
          dataSource={items}
          rowKey="id"
          size="small"
          pagination={false}
        />
      )}
    </div>
  );
}
