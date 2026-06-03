import { Table } from 'antd';
import type { ColumnsType } from 'antd/es/table';
import { useNavigate } from 'react-router-dom';
import type { CaseListItem } from '../../types';

interface Props {
  data: CaseListItem[];
  loading: boolean;
  pagination: {
    current: number;
    pageSize: number;
    total: number;
  };
  onPageChange: (page: number, pageSize: number) => void;
}

const probColor = (v: number): string => {
  if (v >= 0.7) return '#DC2626';
  if (v >= 0.3) return '#947008';
  return '#4A5630';
};

const riskDotColor: Record<string, string> = {
  high: '#DC2626',
  medium: '#947008',
  low: '#4A5630',
};

const riskLabelMap: Record<string, string> = {
  high: '高风险',
  medium: '中风险',
  low: '低风险',
};

const resultColor: Record<string, string> = {
  pass: '#4A5630',
  reject: '#DC2626',
  investigate: '#947008',
};

const resultLabel: Record<string, string> = {
  pass: '通过',
  reject: '拒绝',
  investigate: '调查中',
};

export default function CaseTable({ data, loading, pagination, onPageChange }: Props) {
  const navigate = useNavigate();

  const columns: ColumnsType<CaseListItem> = [
    { title: 'ID', dataIndex: 'id', key: 'id', width: 72 },
    {
      title: '保单号', dataIndex: 'policy_id', key: 'policy_id',
      ellipsis: true, width: 160,
    },
    {
      title: '理赔金额', dataIndex: 'claim_amount', key: 'claim_amount', width: 130,
      render: (v: number | null) => (
        <span style={{ fontFamily: "'Inter', sans-serif", fontFeatureSettings: "'tnum'" }}>
          {v != null ? `¥${v.toLocaleString()}` : '-'}
        </span>
      ),
    },
    {
      title: '欺诈概率', dataIndex: 'fraud_prob', key: 'fraud_prob', width: 120,
      render: (v: number) => (
        <span style={{ fontWeight: 600, color: probColor(v), fontFamily: "'Inter', sans-serif", fontFeatureSettings: "'tnum'" }}>
          {(v * 100).toFixed(1)}%
        </span>
      ),
    },
    {
      title: '风险等级', dataIndex: 'risk_level', key: 'risk_level', width: 100,
      render: (level: string) => (
        <span style={{ display: 'inline-flex', alignItems: 'center', gap: 4, fontSize: 12 }}>
          <span style={{ width: 6, height: 6, borderRadius: '50%', background: riskDotColor[level] || '#A8A29E', display: 'inline-block' }} />
          <span style={{ color: riskDotColor[level] || '#A8A29E' }}>{riskLabelMap[level] || level}</span>
        </span>
      ),
    },
    {
      title: '人工判定', dataIndex: 'manual_result', key: 'manual_result', width: 110,
      render: (v: string | null) => {
        if (!v) return <span style={{ color: '#A8A29E', fontSize: 12 }}>待处理</span>;
        return (
          <span style={{ display: 'inline-flex', alignItems: 'center', gap: 4, fontSize: 12 }}>
            <span style={{ width: 6, height: 6, borderRadius: '50%', background: resultColor[v] || '#A8A29E', display: 'inline-block' }} />
            <span style={{ color: resultColor[v] || '#A8A29E' }}>{resultLabel[v] || v}</span>
          </span>
        );
      },
    },
    {
      title: 'AI 报告', dataIndex: 'has_agent_report', key: 'has_agent_report', width: 90,
      render: (v: boolean) => (v ? <span style={{ color: '#4A5630', fontSize: 12 }}>已生成</span> : <span style={{ color: '#A8A29E' }}>-</span>),
    },
    {
      title: '检测时间', dataIndex: 'detect_time', key: 'detect_time', width: 180,
      render: (v: string) => v ? new Date(v).toLocaleString() : '-',
    },
  ];

  return (
    <Table
      columns={columns}
      dataSource={data}
      rowKey="id"
      loading={loading}
      pagination={{
        current: pagination.current,
        pageSize: pagination.pageSize,
        total: pagination.total,
        showSizeChanger: true,
        showQuickJumper: true,
        pageSizeOptions: ['10', '20', '50'],
        showTotal: (total) => `共 ${total} 条`,
        onChange: (page, pageSize) => onPageChange(page, pageSize),
      }}
      onRow={(record) => ({
        style: { cursor: 'pointer' },
        onClick: () => navigate(`/cases/${record.id}`),
      })}
    />
  );
}
