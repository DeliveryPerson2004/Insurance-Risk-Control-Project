import { useState, useCallback, useRef, useEffect } from 'react';
import {
  Upload, Table, message, Tag, Typography,
} from 'antd';
import { InboxOutlined } from '@ant-design/icons';
import type { UploadProps } from 'antd';
import type { ColumnsType } from 'antd/es/table';
import { uploadData, fetchDataTasks, fetchDataTaskStatus } from '../../api/admin';
import type { DataTaskStatus } from '../../types';

const { Dragger } = Upload;
const { Text } = Typography;

const STATUS_COLOR: Record<string, string> = {
  pending: 'default',
  processing: 'processing',
  completed: 'success',
  failed: 'error',
};
const STATUS_LABEL: Record<string, string> = {
  pending: '等待中',
  processing: '处理中',
  completed: '已完成',
  failed: '失败',
};

interface TaskRecord extends DataTaskStatus {
  key: string;
}

export default function DataUpload() {
  const [tasks, setTasks] = useState<TaskRecord[]>([]);
  const [uploading, setUploading] = useState(false);
  // Map 管理多个并发轮询（每个进行中的任务一个 interval），避免单 ref 泄漏
  const pollMapRef = useRef<Map<string, ReturnType<typeof setInterval>>>(new Map());

  const startPolling = useCallback((taskId: string) => {
    // 已有轮询则跳过，避免重复
    if (pollMapRef.current.has(taskId)) return;

    let failCount = 0;
    const interval = setInterval(async () => {
      try {
        const status = await fetchDataTaskStatus(taskId);
        failCount = 0;  // 成功后重置
        setTasks((prev) =>
          prev.map((t) => (t.key === taskId ? { ...status, key: taskId } : t))
        );
        if (status.status === 'completed' || status.status === 'failed') {
          clearInterval(interval);
          pollMapRef.current.delete(taskId);
          if (status.status === 'completed') {
            message.success(`文件 ${status.filename} 导入完成: ${status.success} 条成功`);
          } else {
            message.error(`文件 ${status.filename} 导入失败: ${status.error_message}`);
          }
        }
      } catch {
        failCount++;
        // 连续失败 12 次（约 1 分钟）后停止轮询
        if (failCount >= 12) {
          clearInterval(interval);
          pollMapRef.current.delete(taskId);
          message.warning(`任务 ${taskId} 状态查询超时，请刷新页面查看`);
        }
      }
    }, 2000);  // 2 秒轮询，减少"等待中"感知延迟
    pollMapRef.current.set(taskId, interval);
  }, []);

  // 页面加载时恢复已有任务列表
  useEffect(() => {
    fetchDataTasks({ page: 1, size: 50 }).then((res) => {
      setTasks(res.items.map((item) => ({ ...item, key: item.task_id })));
      for (const item of res.items) {
        if (item.status === 'pending' || item.status === 'processing') {
          startPolling(item.task_id);
        }
      }
    }).catch(() => {
      // Redis 中无历史数据时忽略
    });

    // 组件卸载时清理所有 interval
    return () => {
      pollMapRef.current.forEach((interval) => clearInterval(interval));
      pollMapRef.current.clear();
    };
  }, []);  // eslint-disable-line react-hooks/exhaustive-deps

  const handleUpload: UploadProps['customRequest'] = useCallback(
    async (options) => {
      const { file, onSuccess, onError } = options as any;
      setUploading(true);
      try {
        const result = await uploadData(file as File);
        const newTask: TaskRecord = {
          key: result.task_id,
          task_id: result.task_id,
          filename: (file as File).name,
          status: 'pending',
          total: null,
          processed: null,
          success: null,
          failed: null,
          error_message: null,
          created_at: new Date().toISOString(),
          completed_at: null,
        };
        setTasks((prev) => [newTask, ...prev]);
        startPolling(result.task_id);
        onSuccess?.(result, file);
        message.success('文件已上传，开始处理');
      } catch (err: any) {
        onError?.(err);
        message.error('上传失败: ' + (err?.message || '未知错误'));
      } finally {
        setUploading(false);
      }
    },
    [startPolling],
  );

  const columns: ColumnsType<TaskRecord> = [
    { title: '文件名', dataIndex: 'filename', key: 'filename' },
    {
      title: '状态', dataIndex: 'status', key: 'status',
      render: (s: string) => <Tag color={STATUS_COLOR[s]}>{STATUS_LABEL[s] || s}</Tag>,
    },
    {
      title: '进度', key: 'progress',
      render: (_: unknown, r: TaskRecord) => {
        if (r.total == null) return '-';
        const pct = r.total > 0 ? Math.round(((r.processed ?? 0) / r.total) * 100) : 0;
        return `${r.processed ?? 0} / ${r.total} (${pct}%)`;
      },
    },
    {
      title: '成功/失败', key: 'result',
      render: (_: unknown, r: TaskRecord) => {
        if (r.success == null && r.failed == null) return '-';
        return (
          <span>
            <Text type="success">{r.success ?? 0}</Text>
            {' / '}
            <Text type="danger">{r.failed ?? 0}</Text>
          </span>
        );
      },
    },
    {
      title: '创建时间', dataIndex: 'created_at', key: 'created_at',
      render: (v: string | null) => v ? new Date(v).toLocaleString() : '-',
    },
  ];

  return (
    <div>
      <Dragger
        accept=".xlsx,.xls"
        maxCount={1}
        customRequest={handleUpload}
        disabled={uploading}
        showUploadList={false}
        style={{ marginBottom: 24 }}
      >
        <p className="ant-upload-drag-icon">
          <InboxOutlined />
        </p>
        <p className="ant-upload-text">点击或拖拽上传原始 Excel 文件</p>
        <p className="ant-upload-hint">支持 .xlsx / .xls 格式，最大 100MB</p>
      </Dragger>

      <Table
        rowKey="key"
        columns={columns}
        dataSource={tasks}
        pagination={false}
        locale={{ emptyText: '暂无导入任务' }}
      />
    </div>
  );
}
