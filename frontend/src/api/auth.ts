import client from './client';
import type { ApiResponse, LoginRequest, LoginResponse, RegisterRequest, RefreshRequest, TokenResponse, User } from '../types';

export async function login(req: LoginRequest): Promise<LoginResponse> {
  const { data } = await client.post<ApiResponse<LoginResponse>>('/auth/login', req);
  return data.data;
}

export async function register(req: RegisterRequest): Promise<LoginResponse> {
  const { data } = await client.post<ApiResponse<LoginResponse>>('/auth/register', req);
  return data.data;
}

export async function refresh(req: RefreshRequest): Promise<TokenResponse> {
  const { data } = await client.post<ApiResponse<TokenResponse>>('/auth/refresh', req);
  return data.data;
}

export async function getMe(): Promise<User> {
  const { data } = await client.get<ApiResponse<User>>('/auth/me');
  return data.data;
}
