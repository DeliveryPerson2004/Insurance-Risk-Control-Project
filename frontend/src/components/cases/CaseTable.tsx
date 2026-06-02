import { Table, Tag } from 'antd';
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

const riskColorMap: Record<string, string> = {
  high: 'red',
  medium: 'orange',
  low: 'green',
};

const resultColorMap: Record<string, string> = {
  pass: 'green',
  reject: 'red',
  investigate: 'blue',
};

const resultLabelMap: Record<string, string> = {
  pass: '通过',
  reject: '拒绝',
  investigate: '调查中',
};

export default function CaseTable({ data, loading, pagination, onPageChange }: Props) {
  const navigate = useNavigate();

  const columns: ColumnsType<CaseListItem> = [
    {
      title: 'ID',
      dataIndex: 'id',
      key: 'id',
      width: 72,
    },
    {
      title: '保单号',
      dataIndex: 'policy_id',
      key: 'policy_id',
      ellipsis: true,
      width: 160,
    },
    {
      title: '理赔金额',
      dataIndex: 'claim_amount',
      key: 'claim_amount',
      width: 130,
      render: (v: number | null) => (v != null ? `¥${v.toLocaleString()}` : '-'),
    },
    {
      title: '欺诈概率',
      dataIndex: 'fraud_prob',
      key: 'fraud_prob',
      width: 120,
      render: (v: number) => `${(v * 100).toFixed(1)}%`,
    },
    {
      title: '风险等级',
      dataIndex: 'risk_level',
      key: 'risk_level',
      width: 100,
      render: (level: string) => (
        <Tag color={riskColorMap[level] || 'default'}>{level}</Tag>
      ),
    },
    {
      title: '人工判定',
      dataIndex: 'manual_result',
      key: 'manual_result',
      width: 110,
      render: (v: string | null) => {
        if (!v) return <Tag>待处理</Tag>;
        return (
          <Tag color={resultColorMap[v] || 'default'}>
            {resultLabelMap[v] || v}
          </Tag>
        );
      },
    },
    {
      title: 'AI 报告',
      dataIndex: 'has_agent_report',
      key: 'has_agent_report',
      width: 90,
      render: (v: boolean) => (v ? <Tag color="purple">已生成</Tag> : '-'),
    },
    {
      title: '检测时间',
      dataIndex: 'detect_time',
      key: 'detect_time',
      width: 180,
      render: (v: string) => v?.slice(0, 19) || '-',
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
