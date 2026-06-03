import client from './client';
import type { ApiResponse, User, UserListResponse, UpdateUserRequest, DataTaskStatus, DataTaskListResponse } from '../types';

export async function fetchUsers(params: {
  page?: number;
  size?: number;
  username?: string;
}): Promise<UserListResponse> {
  const res = await client.get<ApiResponse<UserListResponse>>('/admin/users', { params });
  return res.data.data;
}

export async function updateUser(
  userId: string,
  body: UpdateUserRequest,
): Promise<User> {
  const res = await client.put<ApiResponse<User>>(`/admin/users/${userId}`, body);
  return res.data.data;
}

export async function fetchDataTasks(params: {
  page?: number;
  size?: number;
}): Promise<DataTaskListResponse> {
  const res = await client.get<ApiResponse<DataTaskListResponse>>('/admin/data/tasks', { params });
  return res.data.data;
}

export async function uploadData(file: File): Promise<{ task_id: string }> {
  const formData = new FormData();
  formData.append('file', file);
  // 不设 Content-Type，让 axios 自动添加正确的 boundary
  const res = await client.post<ApiResponse<{ task_id: string }>>('/admin/data/upload', formData, {
    timeout: 120000,  // 文件上传 2 分钟超时
  });
  return res.data.data;
}

export async function fetchDataTaskStatus(taskId: string): Promise<DataTaskStatus> {
  const res = await client.get<ApiResponse<DataTaskStatus>>(`/admin/data/tasks/${taskId}/status`);
  return res.data.data;
}
