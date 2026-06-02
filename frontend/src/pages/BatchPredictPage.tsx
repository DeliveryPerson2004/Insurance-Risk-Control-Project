import { useState, useCallback, useEffect, useRef } from 'react';
import { Card, Table, Tag, Typography } from 'antd';
import type { ColumnsType } from 'antd/es/table';
import BatchUpload from '../components/batch/BatchUpload';
import BatchProgress from '../components/batch/BatchProgress';
import {
  uploadBatch,
  fetchBatchStatus,
  fetchBatchList,
  getBatchDownloadUrl,
} from '../api/batch';
import type { BatchTaskStatus, BatchTaskItem } from '../types';

const { Title } = Typography;

export default function BatchPredictPage() {
  const [currentTask, setCurrentTask] = useState<BatchTaskStatus | null>(null);
  const [taskList, setTaskList] = useState<BatchTaskItem[]>([]);
  const [loading, setLoading] = useState(false);
  const pollingRef = useRef<ReturnType<typeof setInterval> | null>(null);

  const loadTaskList = useCallback(async () => {
    try {
      const data = await fetchBatchList(1, 20);
      setTaskList(data.items);
    } catch {
      // ignore
    }
  }, []);

  useEffect(() => {
    loadTaskList();
  }, [loadTaskList]);

  useEffect(() => {
    return () => {
      if (pollingRef.current) clearInterval(pollingRef.current);
    };
  }, []);

  const startPolling = useCallback((taskId: string) => {
    if (pollingRef.current) clearInterval(pollingRef.current);
    pollingRef.current = setInterval(async () => {
      try {
        const data = await fetchBatchStatus(taskId);
        setCurrentTask(data);
        if (data.status === 'completed' || data.status === 'failed') {
          if (pollingRef.current) {
            clearInterval(pollingRef.current);
            pollingRef.current = null;
          }
          loadTaskList();
        }
      } catch {
        if (pollingRef.current) {
          clearInterval(pollingRef.current);
          pollingRef.current = null;
        }
      }
    }, 3000);
  }, [loadTaskList]);

  const handleUpload = useCallback(
    async (file: File) => {
      setLoading(true);
      try {
        const { task_id } = await uploadBatch(file);
        setCurrentTask({
          task_id,
          status: 'pending',
          total: 0,
          processed: 0,
          success: 0,
          failed: 0,
          result_filename: null,
          error_message: null,
        });
        startPolling(task_id);
      } catch {
        // error handled by interceptor
      } finally {
        setLoading(false);
      }
    },
    [startPolling],
  );

  const handleDownload = useCallback(async () => {
    if (currentTask) {
      try {
        const token = localStorage.getItem('access_token');
        const response = await fetch(getBatchDownloadUrl(currentTask.task_id), {
          headers: { Authorization: `Bearer ${token}` },
        });
        if (response.ok) {
          const blob = await response.blob();
          const url = URL.createObjectURL(blob);
          const a = document.createElement('a');
          a.href = url;
          a.download = `batch_result_${currentTask.task_id}.csv`;
          a.click();
          URL.revokeObjectURL(url);
        }
      } catch {
        // ignore
      }
    }
  }, [currentTask]);

  const columns: ColumnsType<BatchTaskItem> = [
    { title: '任务 ID', dataIndex: 'task_id', key: 'task_id', ellipsis: true, width: 180 },
    { title: '文件名', dataIndex: 'filename', key: 'filename', ellipsis: true },
    {
      title: '状态',
      dataIndex: 'status',
      key: 'status',
      width: 100,
      render: (s: string) => {
        const color: Record<string, string> = {
          pending: 'default',
          processing: 'processing',
          completed: 'success',
          failed: 'error',
        };
        const text: Record<string, string> = {
          pending: '等待中',
          processing: '处理中',
          completed: '已完成',
          failed: '失败',
        };
        return <Tag color={color[s] || 'default'}>{text[s] || s}</Tag>;
      },
    },
    {
      title: '进度',
      key: 'progress',
      width: 120,
      render: (_, r) => (r.total ? `${r.processed ?? 0}/${r.total}` : '-'),
    },
    {
      title: '创建时间',
      dataIndex: 'created_at',
      key: 'created_at',
      width: 180,
      render: (v: string) => v?.slice(0, 19) || '-',
    },
  ];

  return (
    <div>
      <Title level={4} style={{ marginBottom: 24 }}>批量预测</Title>

      <Card style={{ marginBottom: 24 }}>
        <BatchUpload onUpload={handleUpload} disabled={loading || currentTask?.status === 'processing'} />
      </Card>

      {currentTask && (
        <Card style={{ marginBottom: 24 }}>
          <BatchProgress status={currentTask} onDownload={handleDownload} />
        </Card>
      )}

      <Card title="历史任务">
        <Table
          columns={columns}
          dataSource={taskList}
          rowKey="task_id"
          pagination={{ pageSize: 20, size: 'small' }}
          size="small"
        />
      </Card>
    </div>
  );
}
