import client from './client';
import type { ApiResponse, BatchTaskStatus, BatchTaskListResponse } from '../types';

export async function uploadBatch(file: File): Promise<{ task_id: string; status: string }> {
  const formData = new FormData();
  formData.append('file', file);
  const res = await client.post<ApiResponse<{ task_id: string; status: string }>>(
    '/predict/batch',
    formData,
    { headers: { 'Content-Type': 'multipart/form-data' } },
  );
  return res.data.data;
}

export async function fetchBatchStatus(taskId: string): Promise<BatchTaskStatus> {
  const res = await client.get<ApiResponse<BatchTaskStatus>>(`/predict/batch/${taskId}/status`);
  return res.data.data;
}

export async function fetchBatchList(
  page = 1,
  size = 20,
): Promise<BatchTaskListResponse> {
  const res = await client.get<ApiResponse<BatchTaskListResponse>>('/predict/batch', {
    params: { page, size },
  });
  return res.data.data;
}

export function getBatchDownloadUrl(taskId: string): string {
  return `${client.defaults.baseURL}/predict/batch/${taskId}/download`;
}
