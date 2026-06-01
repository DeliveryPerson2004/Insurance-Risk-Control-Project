import { useCallback } from 'react';
import { useNavigate } from 'react-router-dom';
import { useAuthStore } from '../store/authStore';
import * as authApi from '../api/auth';
import type { LoginRequest, RegisterRequest } from '../types';

export function useAuth() {
  const { user, isAuthenticated, setAuth, clearAuth } = useAuthStore();
  const navigate = useNavigate();

  const login = useCallback(
    async (req: LoginRequest) => {
      const res = await authApi.login(req);
      setAuth(res.user, res.tokens.access_token, res.tokens.refresh_token);
      navigate('/');
    },
    [setAuth, navigate],
  );

  const register = useCallback(
    async (req: RegisterRequest) => {
      const res = await authApi.register(req);
      setAuth(res.user, res.tokens.access_token, res.tokens.refresh_token);
      navigate('/');
    },
    [setAuth, navigate],
  );

  const logout = useCallback(() => {
    clearAuth();
    navigate('/login');
  }, [clearAuth, navigate]);

  const fetchMe = useCallback(async () => {
    try {
      const u = await authApi.getMe();
      useAuthStore.setState({ user: u });
    } catch {
      clearAuth();
      navigate('/login');
    }
  }, [clearAuth, navigate]);

  return { user, isAuthenticated, login, register, logout, fetchMe };
}
