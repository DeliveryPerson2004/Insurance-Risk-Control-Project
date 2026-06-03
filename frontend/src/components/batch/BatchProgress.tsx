import { Progress, Button, Space } from 'antd';
import { DownloadOutlined } from '@ant-design/icons';
import type { BatchTaskStatus } from '../../types';

interface Props {
  status: BatchTaskStatus;
  onDownload: () => void;
}

const STATUS_DOT: Record<string, string> = {
  pending: '#A8A29E',
  processing: '#4A5630',
  completed: '#4A5630',
  failed: '#DC2626',
};

const STATUS_LABEL: Record<string, string> = {
  pending: '等待中',
  processing: '处理中',
  completed: '已完成',
  failed: '失败',
};

export default function BatchProgress({ status, onDownload }: Props) {
  const percent =
    status.total > 0
      ? Math.round(((status.processed || 0) / status.total) * 100)
      : 0;

  return (
    <div style={{ padding: '16px 0' }}>
      <Space direction="vertical" style={{ width: '100%' }} size="middle">
        <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
          <span style={{
            width: 8,
            height: 8,
            borderRadius: '50%',
            background: STATUS_DOT[status.status] || '#A8A29E',
            display: 'inline-block',
            flexShrink: 0,
          }} />
          <span style={{ fontSize: 13, color: '#44403C', fontWeight: 500 }}>
            {STATUS_LABEL[status.status] || status.status}
          </span>
          <span style={{ fontSize: 12, color: '#6B625D', marginLeft: 4 }}>
            {status.status === 'processing'
              ? `${status.processed} / ${status.total}`
              : status.status === 'completed'
                ? `${status.success} 成功, ${status.failed} 失败`
                : status.status === 'failed'
                  ? '处理失败'
                  : '等待中...'}
          </span>
        </div>

        <Progress
          percent={percent}
          status={status.status === 'failed' ? 'exception' : status.status === 'completed' ? 'success' : 'active'}
          strokeColor={status.status === 'failed' ? '#DC2626' : '#4A5630'}
        />

        {status.status === 'completed' && (
          <Button type="primary" icon={<DownloadOutlined />} onClick={onDownload}>
            下载结果
          </Button>
        )}

        {status.status === 'failed' && status.error_message && (
          <div style={{ fontSize: 12, color: '#DC2626', background: '#FEF2F2', padding: '8px 12px', borderRadius: 4 }}>
            {status.error_message}
          </div>
        )}
      </Space>
    </div>
  );
}
