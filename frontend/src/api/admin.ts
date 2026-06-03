import client from './client';
import type { ApiResponse, User, UserListResponse, UpdateUserRequest } from '../types';

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
