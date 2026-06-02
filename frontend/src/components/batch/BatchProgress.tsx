import { Progress, Button, Tag, Space, Typography } from 'antd';
import { DownloadOutlined } from '@ant-design/icons';
import type { BatchTaskStatus } from '../../types';

const { Text } = Typography;

interface Props {
  status: BatchTaskStatus;
  onDownload: () => void;
}

export default function BatchProgress({ status, onDownload }: Props) {
  const percent =
    status.total > 0
      ? Math.round(((status.processed || 0) / status.total) * 100)
      : 0;

  const statusColor: Record<string, string> = {
    pending: 'default',
    processing: 'processing',
    completed: 'success',
    failed: 'error',
  };

  const statusText: Record<string, string> = {
    pending: '等待中',
    processing: '处理中',
    completed: '已完成',
    failed: '失败',
  };

  return (
    <div style={{ padding: '24px 0' }}>
      <Space direction="vertical" style={{ width: '100%' }} size="middle">
        <div>
          <Tag color={statusColor[status.status]}>{statusText[status.status] || status.status}</Tag>
          <Text>
            {status.status === 'processing'
              ? `处理中: ${status.processed} / ${status.total}`
              : status.status === 'completed'
                ? `处理完成: ${status.success} 成功, ${status.failed} 失败`
                : status.status === 'failed'
                  ? '处理失败'
                  : '等待中...'}
          </Text>
        </div>

        <Progress
          percent={percent}
          status={status.status === 'failed' ? 'exception' : status.status === 'completed' ? 'success' : 'active'}
        />

        {status.status === 'completed' && (
          <Button type="primary" icon={<DownloadOutlined />} onClick={onDownload}>
            下载结果
          </Button>
        )}

        {status.status === 'failed' && status.error_message && (
          <Text type="danger">{status.error_message}</Text>
        )}
      </Space>
    </div>
  );
}
