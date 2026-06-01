import client from './client';
import type { ApiResponse, DashboardStats, TrendItem, HighRiskItem } from '../types';

export async function fetchStats(): Promise<DashboardStats> {
  const res = await client.get<ApiResponse<DashboardStats>>('/dashboard/stats');
  return res.data.data;
}

export async function fetchTrend(days = 30): Promise<TrendItem[]> {
  const res = await client.get<ApiResponse<{ trend: TrendItem[] }>>('/dashboard/trend', { params: { days } });
  return res.data.data.trend;
}

export async function fetchHighRisk(limit = 5): Promise<HighRiskItem[]> {
  const res = await client.get<ApiResponse<{ items: HighRiskItem[] }>>('/dashboard/high-risk', { params: { limit } });
  return res.data.data.items;
}
