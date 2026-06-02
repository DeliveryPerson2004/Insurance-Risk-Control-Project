import client from './client';
import type { ApiResponse } from '../types';

export interface AnalyzeResponse {
  report: string | null;
  model_used: string | null;
  cached: boolean;
  fallback: boolean;
  error: string | null;
}

export interface AgentHealth {
  available: boolean;
}

export async function fetchAgentHealth(): Promise<AgentHealth> {
  const res = await client.get<ApiResponse<AgentHealth>>('/agent/health');
  return res.data.data;
}

export async function analyzeCase(
  caseId: number,
  forceRefresh = false,
): Promise<AnalyzeResponse> {
  const res = await client.post<ApiResponse<AnalyzeResponse>>('/agent/analyze', {
    case_id: caseId,
    force_refresh: forceRefresh,
  });
  return res.data.data;
}
