// ---- API 通用 ----
export interface ApiResponse<T> {
  code: number;
  data: T;
  message: string;
}

// ---- 用户 ----
export interface User {
  user_id: string;
  username: string;
  display_name: string;
  user_role: 'admin' | 'reviewer';
  email: string | null;
  phone: string | null;
  is_active: boolean;
  last_login: string | null;
  created_at: string | null;
}

// ---- 认证 ----
export interface LoginRequest {
  username: string;
  password: string;
}

export interface RegisterRequest {
  username: string;
  password: string;
  display_name?: string;
  email?: string;
  phone?: string;
}

export interface TokenResponse {
  access_token: string;
  refresh_token: string;
  token_type: string;
}

export interface LoginResponse {
  user: User;
  tokens: TokenResponse;
}

export interface RefreshRequest {
  refresh_token: string;
}
